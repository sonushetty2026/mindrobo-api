"""Website scraper service.

Fetches a URL, extracts readable text content, and returns it
in a format suitable for the knowledge base.

Uses Playwright for Cloudflare-protected sites, falls back to httpx for simple sites.
"""

import logging
import re
from html.parser import HTMLParser

import httpx

logger = logging.getLogger(__name__)

_CONTENT_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "span", "div", "article", "section"}
_SKIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "svg", "iframe"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts: list[str] = []
        self.title: str = ""
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.text_parts.append(text)


def _clean_text(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw)
    lines = [line.strip() for line in text.split(".") if len(line.strip()) > 20]
    return ". ".join(lines)


def _extract_from_html(html: str) -> dict:
    extractor = _TextExtractor()
    extractor.feed(html)
    raw_text = " ".join(extractor.text_parts)
    content = _clean_text(raw_text)
    return {"title": extractor.title or None, "content": content[:50000]}


async def _scrape_with_httpx(url: str, timeout: float = 15.0) -> str:
    """Try simple HTTP fetch first."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        resp.raise_for_status()
        return resp.text


async def _scrape_with_playwright(url: str) -> str:
    """Use headless Chromium for Cloudflare-protected sites."""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            # Wait for Cloudflare challenge to complete (up to 15s)
            for _ in range(6):
                await page.wait_for_timeout(3000)
                html = await page.content()
                if "Just a moment" not in html and "security verification" not in html.lower():
                    break
            html = await page.content()
        finally:
            await browser.close()
    return html


async def scrape_url(url: str, timeout: float = 15.0) -> dict:
    """Fetch a URL and extract readable text content.
    
    Tries httpx first (fast), falls back to Playwright (handles Cloudflare).
    """
    html = None
    
    # Try simple HTTP first
    try:
        html = await _scrape_with_httpx(url, timeout)
        logger.info("Scraped %s via httpx", url)
    except Exception as e:
        logger.info("httpx failed for %s (%s), trying Playwright...", url, str(e)[:100])
    
    # Fall back to Playwright for bot-protected sites
    if html is None:
        try:
            html = await _scrape_with_playwright(url)
            logger.info("Scraped %s via Playwright", url)
        except Exception as e:
            raise ValueError(f"Failed to fetch {url}: Could not load page even with browser. Error: {e}")
    
    result = _extract_from_html(html)
    result["url"] = url
    
    extracted_content = result.get("content", "")
    
    # Detect Cloudflare challenge page
    if "security verification" in extracted_content.lower() or "Just a moment" in result.get("title", ""):
        raise ValueError(
            f"This website ({url}) is protected by Cloudflare and cannot be automatically scraped. "
            f"Please use the PDF upload option instead: save the website content as a PDF and upload it."
        )
    
    if len(extracted_content) < 50:
        raise ValueError(
            f"Could not extract enough content from {url} ({len(extracted_content)} chars). "
            f"The page may be JavaScript-heavy. Please use the PDF upload option instead."
        )
    
    return result
