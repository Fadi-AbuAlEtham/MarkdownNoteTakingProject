from markdown_it import MarkdownIt
import bleach

_md = MarkdownIt("commonmark", {"linkify": True})

_ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS | {
    "p",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "span",
    "code",
    "blockquote",
    "ul",
    "ol",
    "li",
    "hr",
    "br",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
}
_ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "rel"],
    "span": ["class"],
    "code": ["class"],
    "th": ["align"],
    "td": ["align"],
}
_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def render_sanitized_html(markdown_text: str) -> str:
    html = _md.render(markdown_text or "")
    return bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
