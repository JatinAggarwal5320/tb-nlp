import logging
import re
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LiveMintScraper:
    """Scraper designed to extract clean title, published date, and body text from LiveMint URLs."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def scrape(self, url: str) -> Dict[str, str]:
        """Fetch article from URL and extract cleaned title, date, and body text.

        Args:
            url (str): Target LiveMint article URL.

        Returns:
            Dict[str, str]: Dictionary containing 'title', 'date', 'url', and 'text'.
        """
        logger.info(f"Fetching LiveMint article from: {url}")
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=self.timeout)
            response.raise_for_status()
            html_content = response.text
        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            raise RuntimeError(f"Could not download LiveMint article from {url}: {e}")

        return self.parse_html(html_content, url)

    def parse_html(self, html_content: str, url: str) -> Dict[str, str]:
        """Parse HTML string to extract article components."""
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extract Title
        title = ""
        h1_tag = soup.find("h1")
        if h1_tag:
            title = h1_tag.get_text(strip=True)
        elif soup.title:
            title = soup.title.get_text(strip=True)

        # 2. Extract Publication Date
        date_str = "Unknown"
        # Look for meta published_time or date tags
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
                date_str = time_tag.get_text(strip=True)

        # 3. Extract Article Body Text
        # Remove unwanted tags (script, style, nav, footer, ads, recommended)
        for selector in [
            "script", "style", "iframe", "header", "footer", "nav", "aside",
            ".ad", ".advertisement", ".paywall", ".recommended-stories",
            ".trending-stories", ".subscription-box", ".social-share"
        ]:
            for tag in soup.select(selector):
                tag.decompose()

        # Target LiveMint main content container
        content_container = (
            soup.find("div", class_=re.compile(r"contentSec|mainContent|article-body|storyContent", re.I))
            or soup.find("article")
            or soup.find("main")
            or soup.body
        )

        paragraphs = []
        if content_container:
            for p in content_container.find_all("p"):
                text = p.get_text(strip=True)
                # Filter out short disclaimer/ad text
                if len(text) > 25 and not text.startswith("Catch all the") and not text.startswith("Disclaimer:"):
                    paragraphs.append(text)

        raw_text = "\n\n".join(paragraphs) if paragraphs else content_container.get_text(separator="\n", strip=True)

        return {
            "title": title,
            "date": date_str,
            "url": url,
            "text": raw_text
        }
