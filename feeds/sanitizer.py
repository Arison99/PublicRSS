"""
Feed Content Sanitizer
Strips HTML, script tags, control characters, and enforces strict character limits
to prevent XSS, prompt injection, and excessive token usage.
"""
import re
import html
from bs4 import BeautifulSoup

# Character limits defined by the Intelligence Contract specification:
LIMIT_FEED_TITLE = 200
LIMIT_FEED_DESCRIPTION = 500
LIMIT_FEED_PUBLISHER = 100
LIMIT_ARTICLE_TITLE = 150
LIMIT_ARTICLE_SUMMARY = 300
TARGET_SAMPLE_ARTICLE_COUNT = 7

# Control characters and dangerous sequences
CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')
WHITESPACE_RE = re.compile(r'\s+')

# URL regex to sanitize any accidental URLs inside summaries before sending to AI
URL_PATTERN_RE = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)


def sanitize_text(text: str | None, max_length: int | None = None, strip_urls: bool = False) -> str:
    """
    Strips HTML tags, decodes HTML entities, removes control characters,
    normalizes whitespace, optionally strips URLs, and truncates to max_length.
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # 1. Strip HTML tags using BeautifulSoup with html.parser
    try:
        soup = BeautifulSoup(text, "html.parser")
        # Remove script and style elements completely
        for tag in soup(["script", "style", "iframe", "noscript", "object", "embed"]):
            tag.decompose()
        cleaned = soup.get_text(separator=" ")
    except Exception:
        # Fallback regex tag stripper if BeautifulSoup parser fails
        cleaned = re.sub(r'<[^>]*?>', ' ', text)

    # 2. Decode HTML entities (e.g. &amp;, &lt;)
    cleaned = html.unescape(cleaned)

    # 3. Strip URLs if required (No URLs should be sent to Gemma model per spec)
    if strip_urls:
        cleaned = URL_PATTERN_RE.sub('[link]', cleaned)

    # 4. Remove control characters
    cleaned = CONTROL_CHARS_RE.sub('', cleaned)

    # 5. Normalize whitespace (collapse multiple spaces, tabs, newlines)
    cleaned = WHITESPACE_RE.sub(' ', cleaned).strip()

    # 6. Bound length strictly without breaking words awkwardly
    if max_length and len(cleaned) > max_length:
        truncated = cleaned[:max_length].rstrip()
        return truncated

    return cleaned


def sanitize_feed_metadata(raw_title: str | None, raw_description: str | None, raw_publisher: str | None) -> dict[str, str]:
    """
    Sanitizes channel/feed level metadata strictly adhering to spec bounds.
    """
    title = sanitize_text(raw_title, max_length=LIMIT_FEED_TITLE, strip_urls=True) or "Untitled Feed"
    description = sanitize_text(raw_description, max_length=LIMIT_FEED_DESCRIPTION, strip_urls=True)
    publisher = sanitize_text(raw_publisher, max_length=LIMIT_FEED_PUBLISHER, strip_urls=True) or "Unknown Publisher"

    return {
        "title": title,
        "description": description,
        "publisher": publisher,
    }


def sanitize_article(raw_title: str | None, raw_summary: str | None) -> dict[str, str]:
    """
    Sanitizes article title and summary strictly adhering to spec bounds:
    - title: max 150 chars, no HTML, no URLs
    - summary: max 300 chars, no HTML, no URLs
    """
    title = sanitize_text(raw_title, max_length=LIMIT_ARTICLE_TITLE, strip_urls=True) or "Untitled Article"
    summary = sanitize_text(raw_summary, max_length=LIMIT_ARTICLE_SUMMARY, strip_urls=True)

    return {
        "title": title,
        "summary": summary,
    }
