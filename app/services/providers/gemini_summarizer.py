from __future__ import annotations

import os
import asyncio
import logging
from typing import Optional, Dict, Any

from fastapi import HTTPException

try:
    import google.generativeai as genai
except Exception as e:
    genai = None
    _import_err = e
else:
    _import_err = None

from app.core.config import SummarizeSettings
from app.services.summarize_provider import SummarizeProvider, SummarizeResult

log = logging.getLogger(__name__)

_settings = SummarizeSettings()

_SYSTEM_INSTRUCTION = (
    "You are a concise technical summarizer. Produce faithful, lossless summaries. "
    "Do not invent facts. Preserve key entities, values, and code semantics."
)

_STYLE_INSTRUCTIONS: Dict[str, str] = {
    "bullets": "Summarize as 5–10 crisp bullet points.",
    "paragraph": "Summarize as one concise paragraph.",
    "tldr": "Provide a short summary, ending with a single 'TL;DR:' line.",
    "title_and_bullets": "Return a short descriptive title, then 5–10 bullets.",
}


def _resolve_api_key() -> Optional[str]:
    """
    Prefer settings (reads .env) then raw env vars for maximum portability.
    Accepts either GEMINI_API_KEY or GOOGLE_API_KEY.
    """
    return (
        (_settings.GEMINI_API_KEY or "").strip()
        or (os.getenv("GOOGLE_API_KEY") or "").strip()
        or (os.getenv("GEMINI_API_KEY") or "").strip()
        or None
    )


def _user_prompt(text: str, language: str, style: str) -> str:
    style_instr = _STYLE_INSTRUCTIONS.get(style, _STYLE_INSTRUCTIONS["paragraph"])
    return (
        f"Summarize the following Markdown in {language}.\n"
        f"{style_instr}\n\n"
        f"CONTENT:\n{text}"
    )


def _truncate_if_needed(text: str, limit: int) -> str:
    if limit and len(text) > limit:
        return text[:limit]
    return text


class GeminiSummarizer(SummarizeProvider):
    """
    Gemini-based implementation of SummarizeProvider.

    - Doesn’t raise at import time.
    - Configures Google Generative AI on first use.
    - Offloads blocking SDK call via asyncio.to_thread.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> None:
        # Prefer env override then settings fallback
        self.model = model or (os.getenv("GEMINI_MODEL") or _settings.GEMINI_MODEL)
        self.temperature = temperature
        self._configured = False

    def _ensure_config(self) -> None:
        if self._configured:
            return

        if genai is None:
            # google-generativeai not installed / import failed
            raise HTTPException(
                status_code=500,
                detail=f"Gemini provider not available: {_import_err!s}",
            )

        api_key = _resolve_api_key()
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="Gemini API key missing. Set GOOGLE_API_KEY or GEMINI_API_KEY in your environment or .env.",
            )

        genai.configure(api_key=api_key)
        self._configured = True
        log.debug("Gemini configured with model '%s'", self.model)

    async def summarize(
        self,
        text: str,
        *,
        language: str,
        style: str,
        max_tokens: Optional[int] = None,
    ) -> SummarizeResult:
        """
        Summarize `text` using Gemini. Returns a dict with `summary`, `model`,
        and optional token usage fields.
        """
        self._ensure_config()

        # Enforce input size guardrail to avoid overlong prompts
        max_chars = max(0, int(_settings.MAX_CHARS_PER_CALL or 0))
        safe_text = _truncate_if_needed(text, max_chars) if max_chars else text

        def _call() -> Any:
            model = genai.GenerativeModel(
                self.model,
                system_instruction=_SYSTEM_INSTRUCTION,
            )
            return model.generate_content(
                _user_prompt(safe_text, language or _settings.LANGUAGE, style),
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": max_tokens or 600,
                },
            )

        try:
            resp = await asyncio.to_thread(_call)
        except Exception as e:  # surface provider errors clearly
            log.exception("Gemini generate_content failed")
            raise HTTPException(status_code=502, detail=f"Gemini error: {e}")

        # Extract text + usage metadata (SDK varies across versions)
        summary_text = getattr(resp, "text", None) or ""
        usage = getattr(resp, "usage_metadata", None)

        out: SummarizeResult = {
            "summary": summary_text,
            "model": self.model,
        }
        if usage:
            out.update(
                prompt_tokens=getattr(usage, "prompt_token_count", None),
                completion_tokens=getattr(usage, "candidates_token_count", None),
                total_tokens=getattr(usage, "total_token_count", None),
            )

        return out
