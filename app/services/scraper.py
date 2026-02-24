"""Website scraper service.

Fetches a URL, extracts readable text content, and returns it
in a format suitable for the knowledge base.

Uses Playwright with anti-detection for Cloudflare-protected sites,
falls back to httpx for simple sites.
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
    """Try simple HTTP fetch first (fast path for non-protected sites)."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        resp.raise_for_status()
        html = resp.text
        # Check if we got a Cloudflare challenge page
        if "Just a moment" in html or "cf-mitigated" in html or "security verification" in html.lower():
            raise ValueError("Cloudflare challenge detected")
        return html


async def _scrape_with_playwright(url: str) -> str:
    """Use headless Chromium with anti-detection for Cloudflare-protected sites."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/Los_Angeles',
        )

        # Anti-detection: remove webdriver fingerprint
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)

        page = await context.new_page()
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)

            # Wait for Cloudflare challenge to resolve (up to 24s)
            for _ in range(12):
                await page.wait_for_timeout(2000)
                title = await page.title()
                if 'moment' not in title.lower() and title != '':
                    break

            # Additional wait for JavaScript-heavy sites to load content
            await page.wait_for_timeout(3000)
            
            # Try to wait for common content indicators
            try:
                await page.wait_for_selector('main, article, .content, #content, .container, p', timeout=3000)
            except:
                pass  # Continue if no common content selectors found

            html = await page.content()
        finally:
            await browser.close()

    return html


async def scrape_url(url: str, timeout: float = 15.0) -> dict:
    """Fetch a URL and extract readable text content.

    Tries httpx first (fast), falls back to Playwright with anti-detection
    for Cloudflare-protected sites.
    """
    html = None

    # Try simple HTTP first
    try:
        html = await _scrape_with_httpx(url, timeout)
        logger.info("Scraped %s via httpx", url)
    except Exception as e:
        logger.info("httpx failed for %s (%s), trying Playwright...", url, str(e)[:100])

    # Fall back to Playwright with anti-detection
    if html is None:
        try:
            html = await _scrape_with_playwright(url)
            logger.info("Scraped %s via Playwright (anti-detection)", url)
        except Exception as e:
            raise ValueError(
                f"Failed to fetch {url}: Could not load page. "
                f"Please try the PDF upload option instead. Error: {e}"
            )

    result = _extract_from_html(html)
    result["url"] = url

    extracted_content = result.get("content", "")

    # Detect Cloudflare challenge page (shouldn't happen with Playwright but just in case)
    if "security verification" in extracted_content.lower() or "Just a moment" in result.get("title", ""):
        raise ValueError(
            f"This website ({url}) has strong bot protection. "
            f"Please use the PDF upload option: save the page as PDF and upload it."
        )

    if len(extracted_content) < 50:
        raise ValueError(
            f"Could not extract enough content from {url} ({len(extracted_content)} chars). "
            f"The page may be JavaScript-heavy. Please try the PDF upload option."
        )

    return result
