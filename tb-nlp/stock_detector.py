"""Stage 1 — Relevant Stock Detection.

Determines *which* stocks from a candidate list are materially affected,
and *how* they were matched (direct alias mention vs. indirect sector routing).

Key improvement over v1: a direct mention of "TCS traded flat" no longer
counts the same as "L&T is a key beneficiary".  We extract the surrounding
sentence and classify the mention context before marking a stock affected.
"""

import re
import logging
from typing import List, Dict, Set, Tuple
from nifty_dictionary import NiftyDictionary
from schemas import DetectedEvent, MentionType

logger = logging.getLogger(__name__)

# Words/phrases near a stock mention that signal the stock is NOT materially
# impacted — it's just mentioned in passing or explicitly said to be unaffected.
_DISMISSIVE_PATTERNS = re.compile(
    r"\b(traded\s+flat|remain(?:s|ed)?\s+(?:flat|unchanged|unaffected)|"
    r"no\s+(?:impact|effect|change)|not\s+(?:affected|impacted)|"
    r"muted|subdued|range[- ]?bound|sideways|negligible\s+impact)\b",
    re.IGNORECASE,
)


def _sentence_tokenize(text: str) -> List[str]:
    """Split text into sentences, keeping financial numbers intact.

    Avoids splitting on abbreviations like 'Rs.' or 'Dr.' or decimals like '1.5%'.
    """
    # Split on period/question/exclamation followed by whitespace and uppercase,
    # or on newlines.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\u0900-\u097F])|(?:\n{1,})", text)
    return [s.strip() for s in parts if s and s.strip()]


class StockDetector:
    """Determines which stocks are materially affected (directly or indirectly)."""

    def __init__(self, nifty_dict: NiftyDictionary):
        self.nifty_dict = nifty_dict

    def detect_affected_stocks(
        self,
        text: str,
        candidate_stocks: List[str],
        events: List[DetectedEvent],
    ) -> Dict[str, Tuple[bool, MentionType, List[str]]]:
        """Determine affected status for each candidate stock.

        Returns:
            Dict mapping canonical_name -> (is_affected, mention_type, relevant_sentences).
            The relevant_sentences list is used downstream by the sentiment analyzer
            so it can score *only* the text about that specific stock.
        """
        results: Dict[str, Tuple[bool, MentionType, List[str]]] = {}

        sentences = _sentence_tokenize(text)

        # Collect impacted sectors from detected events
        event_sectors: Set[str] = set()
        for ev in events:
            for sec in ev.impacted_sectors:
                event_sectors.add(sec)

        for stock in candidate_stocks:
            canonical = self.nifty_dict.resolve_stock_name(stock) or stock
            mention_type: MentionType = "none"
            relevant_sents: List[str] = []

            # ── 1. Direct alias matching at sentence level ──────────────
            alias_patterns = self.nifty_dict.get_alias_patterns(canonical)
            for sent in sentences:
                for pat, alias_text in alias_patterns:
                    if pat.search(sent):
                        relevant_sents.append(sent)
                        break  # one match per sentence is enough

            if relevant_sents:
                # Check if ALL matching sentences are dismissive
                non_dismissive = [
                    s for s in relevant_sents if not _DISMISSIVE_PATTERNS.search(s)
                ]
                if non_dismissive:
                    mention_type = "direct"
                    relevant_sents = non_dismissive  # keep only substantive sentences
                    logger.info(
                        "Direct material match for '%s' in %d sentence(s).",
                        canonical, len(relevant_sents),
                    )
                else:
                    # Stock is mentioned, but only in dismissive context
                    logger.info(
                        "Stock '%s' mentioned but in dismissive context — not marking affected.",
                        canonical,
                    )
                    relevant_sents = []  # clear so it falls through

            # ── 2. Indirect sector routing (only if no direct match) ────
            if not relevant_sents:
                stock_sector = self.nifty_dict.get_sector_for_stock(canonical)
                if stock_sector in event_sectors and stock_sector != "General":
                    mention_type = "indirect_sector"
                    # Use the full article as context for indirect matches
                    relevant_sents = sentences[:5]  # first 5 sentences as context
                    logger.info(
                        "Indirect sector match for '%s' via sector '%s'.",
                        canonical, stock_sector,
                    )

            is_affected = bool(relevant_sents)
            if not is_affected:
                mention_type = "none"

            results[canonical] = (is_affected, mention_type, relevant_sents)

        return results
