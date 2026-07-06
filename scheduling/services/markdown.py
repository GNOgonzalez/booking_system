"""Safe Markdown rendering — one shared pipeline for blog posts and homework journals.

Store Markdown source in the existing TextFields; render to HTML through this
allowlist so user input can never inject scripts, iframes, or javascript: URLs.
Preview and publish use the same function, so what users see is what ships.
"""

import bleach
import markdown

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'a',
    'ul', 'ol', 'li',
    'blockquote', 'code', 'pre',
    'h1', 'h2', 'h3',
    'hr',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel'],
    'code': ['class'],  # fenced code language hint, e.g. class="language-python"
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def render_safe_markdown(text):
    """Markdown source → sanitized HTML string ('' for blank input)."""
    if not text or not text.strip():
        return ''
    raw_html = markdown.markdown(
        text,
        extensions=['fenced_code', 'nl2br'],
        output_format='html',
    )
    clean = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    # Force rel on links so user content can't leak referrers / exploit window.opener.
    return bleach.linkify(
        clean,
        callbacks=[
            bleach.callbacks.nofollow,
            bleach.callbacks.target_blank,
        ],
        skip_tags=['code', 'pre'],
    )
