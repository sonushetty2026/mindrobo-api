"""Website scraper service.

Fetches a URL, extracts readable text content, and returns it
in a format suitable for the knowledge base.
"""

import logging
import re
from html.parser import HTMLParser

import httpx

logger = logging.getLogger(__name__)

# Tags whose content we want to extract
_CONTENT_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "span", "div", "article", "section"}
_SKIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "svg", "iframe"}


class _TextExtractor(HTMLParser):
    """Simple HTML → text extractor. No external dependencies."""

    def __init__(self):
        super().__init__()
        self.text_parts: list[str] = []
        self.title: str = ""
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str):
        if self._in_title:
            self.title += data.strip()
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.text_parts.append(text)


def _clean_text(raw: str) -> str:
    """Collapse whitespace and remove junk."""
    text = re.sub(r"\s+", " ", raw)
    # Remove very short lines (likely menu items, buttons)
    lines = [line.strip() for line in text.split(".") if len(line.strip()) > 20]
    return ". ".join(lines)


async def scrape_url(url: str, timeout: float = 15.0) -> dict:
    """Fetch a URL and extract readable text content.

    Returns:
        {"title": str, "content": str, "url": str}

    Raises:
        ValueError: if URL is unreachable or content is empty
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url, headers={
                "User-Agent": "MindRobo-Bot/1.0 (knowledge-base-ingestion)"
            })
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise ValueError(f"Failed to fetch {url}: {e}")

    content_type = resp.headers.get("content-type", "")
    if "html" not in content_type:
        raise ValueError(f"URL {url} returned non-HTML content: {content_type}")

    html = resp.text
    extractor = _TextExtractor()
    extractor.feed(html)

    raw_text = " ".join(extractor.text_parts)
    content = _clean_text(raw_text)

    if len(content) < 50:
        raise ValueError(f"Extracted content from {url} is too short ({len(content)} chars). Page may be JavaScript-rendered.")

    # Truncate to ~50K chars to avoid storing massive pages
    content = content[:50000]

    return {
        "title": extractor.title or None,
        "content": content,
        "url": url,
    }
