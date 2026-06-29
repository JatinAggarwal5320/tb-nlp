"""LiveMint RSS Feed Ingestion and Automated News Impact Analysis Module.

Auto-discovers latest market and corporate news articles from LiveMint RSS feeds,
fetches full text via LiveMintScraper, and executes targeted NIFTY stock analysis.
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import requests

from pipeline import FinancialNewsImpactPipeline
from schemas import PipelineOutput

logger = logging.getLogger(__name__)


class LiveMintRSSConsumer:
    """RSS Feed Consumer for LiveMint Markets and Companies channels."""

    RSS_FEEDS = {
        "markets": "https://www.livemint.com/rss/markets",
        "companies": "https://www.livemint.com/rss/companies",
        "news": "https://www.livemint.com/rss/news",
    }

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }

    def __init__(self, pipeline: Optional[FinancialNewsImpactPipeline] = None):
        self.pipeline = pipeline or FinancialNewsImpactPipeline()

    def fetch_feed_entries(self, category: str = "markets", max_entries: int = 5) -> List[Dict[str, str]]:
        """Fetch latest article headers and links from LiveMint RSS feed.

        Args:
            category (str): Feed category ('markets', 'companies', 'news').
            max_entries (int): Maximum number of entries to pull from feed.

        Returns:
            List[Dict[str, str]]: List of dicts with 'title', 'link', 'pubDate', 'description'.
        """
        feed_url = self.RSS_FEEDS.get(category.lower(), self.RSS_FEEDS["markets"])
        logger.info("Fetching LiveMint RSS feed (%s): %s", category, feed_url)

        try:
            resp = requests.get(feed_url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            xml_data = resp.content
        except Exception as e:
            logger.error("Failed to download RSS feed %s: %s", feed_url, e)
            raise RuntimeError(f"Could not download RSS feed from {feed_url}: {e}")

        entries = []
        try:
            root = ET.fromstring(xml_data)
            # Standard RSS channel/item parsing
            channel = root.find("channel")
            if channel is not None:
                items = channel.findall("item")
                for item in items[:max_entries]:
                    title = item.findtext("title", default="").strip()
                    link = item.findtext("link", default="").strip()
                    pub_date = item.findtext("pubDate", default="").strip()
                    desc = item.findtext("description", default="").strip()

                    # Clean description tags
                    clean_desc = re.sub(r"<[^>]*>", "", desc).strip()

                    if link:
                        entries.append({
                            "title": title,
                            "link": link,
                            "pubDate": pub_date,
                            "description": clean_desc
                        })
        except Exception as parse_err:
            logger.error("Error parsing RSS XML: %s", parse_err)

        logger.info("Retrieved %d article links from LiveMint RSS (%s)", len(entries), category)
        return entries

    def process_rss_feed(
        self,
        category: str = "markets",
        stocks: Optional[List[str]] = None,
        max_entries: int = 3
    ) -> List[PipelineOutput]:
        """Fetch RSS feed and run full end-to-end impact pipeline on each article.

        Args:
            category (str): LiveMint RSS category.
            stocks (List[str]): Candidate stocks to analyze.
            max_entries (int): Max articles to process in batch.

        Returns:
            List[PipelineOutput]: Structured pipeline outputs for each RSS article.
        """
        if stocks is None:
            stocks = [
                "Reliance", "TCS", "Infosys", "HDFC Bank", "ICICI Bank",
                "ITC", "L&T", "UltraTech Cement", "State Bank of India", "Tata Motors"
            ]

        entries = self.fetch_feed_entries(category=category, max_entries=max_entries)
        results: List[PipelineOutput] = []

        for idx, entry in enumerate(entries, 1):
            url = entry["link"]
            logger.info("[%d/%d] Processing RSS Article: %s", idx, len(entries), url)
            try:
                output = self.pipeline.process_url(url=url, stocks=stocks)
                results.append(output)
            except Exception as err:
                logger.error("Skipping failed article (%s): %s", url, err)

        return results
