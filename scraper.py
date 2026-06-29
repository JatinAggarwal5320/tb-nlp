"""LiveMint article scraper with retry and robust content extraction."""

import logging
import re
import time
from typing import Dict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LiveMintScraper:
    """Extracts title, published date, and body text from LiveMint article URLs.

    Includes retry logic with exponential back-off for transient network errors.
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
    }

    def __init__(self, timeout: int = 15, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

    def scrape(self, url: str) -> Dict[str, str]:
        """Fetch and parse a LiveMint article URL.

        Retries up to ``max_retries`` times on transient failures.

        Returns:
            Dict with keys: title, date, url, text.
        """
        logger.info("Fetching article from: %s", url)

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(
                    url, headers=self.HEADERS, timeout=self.timeout,
                )
                resp.raise_for_status()
                return self.parse_html(resp.text, url)
            except requests.exceptions.HTTPError as e:
                # Don't retry 4xx client errors (404, 403, etc.)
                if resp.status_code < 500:
                    raise RuntimeError(
                        f"HTTP {resp.status_code} for {url}: {e}"
                    ) from e
                last_err = e
            except Exception as e:
                last_err = e

            if attempt < self.max_retries:
                wait = 2 ** attempt
                logger.warning(
                    "Attempt %d/%d failed (%s). Retrying in %ds…",
                    attempt, self.max_retries, last_err, wait,
                )
                time.sleep(wait)

        raise RuntimeError(
            f"Failed to fetch {url} after {self.max_retries} attempts: {last_err}"
        )

    def parse_html(self, html_content: str, url: str) -> Dict[str, str]:
        """Parse HTML to extract article title, date, and body text."""
        soup = BeautifulSoup(html_content, "html.parser")

        # ── Title ──────────────────────────────────────────────────────
        title = ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        elif soup.title:
            title = soup.title.get_text(strip=True)

        # ── Publication Date ───────────────────────────────────────────
        date_str = "Unknown"
        meta_date = (
            soup.find("meta", property="article:published_time")
            or soup.find("meta", attrs={"name": "publish-date"})
            or soup.find("meta", attrs={"name": "last-modified"})
        )
        if meta_date and meta_date.get("content"):
            date_str = meta_date["content"].strip()
        else:
            time_tag = soup.find("time")
            if time_tag:
                date_str = (
                    time_tag.get("datetime")
                    or time_tag.get_text(strip=True)
                )

        # ── Remove unwanted DOM nodes ──────────────────────────────────
        for selector in [
            "script", "style", "iframe", "header", "footer", "nav", "aside",
            ".ad", ".advertisement", ".paywall", ".recommended-stories",
            ".trending-stories", ".subscription-box", ".social-share",
            ".also-read", ".related-stories", ".breadcrumb",
        ]:
            for tag in soup.select(selector):
                tag.decompose()

        # ── Body text ──────────────────────────────────────────────────
        content = (
            soup.find("div", class_=re.compile(
                r"contentSec|mainContent|article-body|storyContent|"
                r"articleBody|story_content|paywall",
                re.I,
            ))
            or soup.find("article")
            or soup.find("main")
            or soup.body
        )

        paragraphs = []
        if content:
            for p in content.find_all("p"):
                txt = p.get_text(strip=True)
                if (
                    len(txt) > 25
                    and not txt.startswith("Catch all the")
                    and not txt.startswith("Disclaimer:")
                    and "Download the App" not in txt
                ):
                    paragraphs.append(txt)

        body = (
            "\n\n".join(paragraphs)
            if paragraphs
            else content.get_text(separator="\n", strip=True)
        )

        return {
            "title": title,
            "date": date_str,
            "url": url,
            "text": body,
        }
