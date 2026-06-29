import re
import logging
from typing import List, Dict, Set
from nifty_dictionary import NiftyDictionary
from schemas import DetectedEvent

logger = logging.getLogger(__name__)


class StockDetector:
    """Stage 1: Determines which stocks from a candidate list are materially affected (directly or indirectly)."""

    def __init__(self, nifty_dict: NiftyDictionary):
        self.nifty_dict = nifty_dict

    def detect_affected_stocks(
        self,
        text: str,
        candidate_stocks: List[str],
        events: List[DetectedEvent]
    ) -> Dict[str, bool]:
        """Determine affected status for each candidate stock.

        Args:
            text (str): Cleaned article text.
            candidate_stocks (List[str]): List of stock names or tickers to evaluate.
            events (List[DetectedEvent]): Core financial events extracted from article.

        Returns:
            Dict[str, bool]: Map of stock canonical name -> is_affected (True/False).
        """
        results: Dict[str, bool] = {}
        text_lower = text.lower()

        # Extract impacted sectors from events
        event_sectors: Set[str] = set()
        for ev in events:
            for sec in ev.impacted_sectors:
                event_sectors.add(sec)

        for stock in candidate_stocks:
            canonical = self.nifty_dict.resolve_stock_name(stock) or stock
            is_affected = False

            # 1. Direct Alias Matching
            aliases = self.nifty_dict.get_aliases_for_stock(canonical)
            for alias in aliases:
                # Use word boundaries to match exact mentions
                pattern = rf"\b{re.escape(alias.lower())}\b"
                if re.search(pattern, text_lower):
                    is_affected = True
                    logger.info(f"Direct match found for stock '{canonical}' via alias '{alias}'.")
                    break

            # 2. Indirect Event & Sector Impact Detection
            if not is_affected:
                stock_sector = self.nifty_dict.get_sector_for_stock(canonical)
                if stock_sector in event_sectors and stock_sector != "General":
                    is_affected = True
                    logger.info(f"Indirect macro match found for stock '{canonical}' via sector '{stock_sector}'.")

            results[canonical] = is_affected

        return results
