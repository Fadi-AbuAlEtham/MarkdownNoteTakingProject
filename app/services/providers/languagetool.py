from typing import List, Optional, Dict, Any
import httpx

from app.services.grammar_provider import GrammarProvider, IssueIn


class LanguageToolProvider(GrammarProvider):
    """
    LanguageTool-backed grammar provider.

    Works with:
      - Self-hosted LanguageTool: base_url="http://localhost:8010"
      - Public LT (rate-limited): base_url="https://api.languagetool.org"
      - LT Premium: base_url="https://api.languagetoolplus.com"
        (set api_key or auth_header if your plan requires it)
    """

    def __init__(
        self,
        base_url: str = "https://api.languagetool.org",
        *,
        api_key: Optional[str] = None,        # sent as form field "apiKey"
        auth_header: Optional[str] = None,    # e.g., "Bearer <token>"
        timeout: float = 15.0,
        level: str = "default",               # "default" | "picky"
        enabled_categories: Optional[List[str]] = None,
        disabled_categories: Optional[List[str]] = None,
        enabled_rules: Optional[List[str]] = None,
        disabled_rules: Optional[List[str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.auth_header = auth_header
        self.timeout = timeout
        self.level = level
        self.enabled_categories = enabled_categories or []
        self.disabled_categories = disabled_categories or []
        self.enabled_rules = enabled_rules or []
        self.disabled_rules = disabled_rules or []

    @staticmethod
    def _severity(issue_type: Optional[str]) -> str:
        """
        Map LT issue types to our severity.
        """
        it = (issue_type or "").lower()
        if it in {"misspelling", "typographical"}:
            return "warning"
        if it in {"grammar"}:
            return "warning"
        if it in {"style"}:
            return "info"
        if it in {"duplication", "confused"}:
            return "info"
        return "info"

    async def analyze(self, text: str, language: str = "en") -> List[IssueIn]:
        url = f"{self.base_url}/v2/check"

        headers: Dict[str, str] = {}
        if self.auth_header:
            headers["Authorization"] = self.auth_header

        # LanguageTool expects form-encoded data.
        data: Dict[str, Any] = {
            "text": text,
            "language": language,
            "level": self.level,          # "default" or "picky"
            "enabledOnly": "false",
        }
        if self.api_key:
            data["apiKey"] = self.api_key
        if self.enabled_categories:
            data["enabledCategories"] = ",".join(self.enabled_categories)
        if self.disabled_categories:
            data["disabledCategories"] = ",".join(self.disabled_categories)
        if self.enabled_rules:
            data["enabledRules"] = ",".join(self.enabled_rules)
        if self.disabled_rules:
            data["disabledRules"] = ",".join(self.disabled_rules)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, data=data, headers=headers)
            resp.raise_for_status()
            payload = resp.json()

        matches = payload.get("matches", []) or []
        out: List[IssueIn] = []

        for m in matches:
            start = int(m.get("offset", 0))
            length = int(m.get("length", 0))
            rule = m.get("rule") or {}
            rule_cat = rule.get("category") or {}
            replacements = [r.get("value") for r in (m.get("replacements") or []) if r.get("value")]

            # Safe slice for "original"
            try:
                original = text[start:start + length]
            except Exception:
                original = ""

            out.append({
                "start": start,
                "length": length,
                "message": m.get("message", ""),
                "rule_id": rule.get("id"),
                "category": rule_cat.get("id") or rule_cat.get("name"),
                "severity": self._severity(rule.get("issueType")),
                "original": original,
                "replacements": replacements,
            })

        return out