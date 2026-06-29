"""Event extraction — classifies the macro/corporate catalyst in an article.

Uses targeted multi-word phrase patterns instead of single generic words
to avoid false positives (e.g. "profit" alone fires on every article).
"""

import re
import logging
from typing import List
from schemas import DetectedEvent

logger = logging.getLogger(__name__)


class EventExtractor:
    """Detect core financial events from article text using phrase-level patterns."""

    # Each pattern list uses multi-word phrases or narrow terms to cut noise.
    EVENT_PATTERNS = {
        "Interest Rate / Monetary Policy": [
            r"\b(rate\s+cut|rate\s+hike|repo\s+rate|reverse\s+repo|monetary\s+policy|policy\s+rate|interest\s+rate\s+(?:decision|change|reduction|increase))\b",
            r"\b(rbi\s+(?:governor|meeting|decision|panel|committee|announces?|holds?|cuts?|hikes?|keeps?))\b",
            r"\b(liquidity\s+(?:easing|tightening|injection|crunch|surplus))\b",
        ],
        "Government Capex & Infrastructure Spending": [
            r"\b(infrastructure\s+(?:spending|investment|push|allocation|project|plan))\b",
            r"\b(government\s+(?:spending|capex|allocation|outlay))\b",
            r"\b(budget\s+(?:allocation|outlay|push|boost))\b",
            r"\b(highway|railway|metro\s+project|smart\s+city|national\s+infrastructure\s+pipeline)\b",
        ],
        "Quarterly Earnings & Revenue": [
            r"\b(q[1-4]\s+(?:results|earnings|profit|revenue|numbers))\b",
            r"\b(quarterly\s+(?:results|earnings|profit|numbers))\b",
            r"\b((?:net\s+)?profit\s+(?:jumps?|surges?|rises?|falls?|drops?|declines?|plunges?|doubles?|triples?))\b",
            r"\b(revenue\s+(?:grows?|rises?|falls?|jumps?|declines?|misses?))\b",
            r"\b((?:beat|miss(?:es)?)\s+(?:estimates?|expectations?|consensus))\b",
            r"\b(ebitda\s+(?:margin|grows?|expands?|contracts?))\b",
        ],
        "Order Win & Contract Award": [
            r"\b((?:order|contract)\s+(?:win|wins|won|awarded?|bags?|bagged|secures?|secured|worth))\b",
            r"\b(epc\s+contract|project\s+award)\b",
        ],
        "M&A, Stake Sale & Acquisition": [
            r"\b(acquir(?:es?|ed|ing)|acquisition|merger|stake\s+sale|buyout|takeover|divestment)\b",
            r"\b(joint\s+venture|strategic\s+partnership|open\s+offer)\b",
        ],
        "Regulatory Action & Governance": [
            r"\b(sebi\s+(?:order|penalty|ban|investigation|notice))\b",
            r"\b(rbi\s+(?:penalty|fine|action))\b",
            r"\b(showcause\s+notice|regulatory\s+(?:approval|clearance|hurdle))\b",
            r"\b(cbi\s+(?:probe|raid|investigation)|ed\s+(?:probe|raid|investigation))\b",
            r"\b(class\s+action|lawsuit\s+(?:filed|against))\b",
        ],
        "Management Change & Corporate Action": [
            r"\b(ceo\s+(?:resigns?|appointed|steps\s+down)|cfo\s+(?:resigns?|appointed))\b",
            r"\b(board\s+(?:approves?|clears?)|dividend\s+(?:declared|announced))\b",
            r"\b(stock\s+split|bonus\s+(?:issue|shares?)|buyback)\b",
        ],
        "Crude Oil & Commodity": [
            r"\b(crude\s+(?:oil|price)|brent\s+crude|oil\s+price)\b",
            r"\b(commodity\s+(?:prices?|rally|crash|surge))\b",
        ],
        "FII / DII Flow": [
            r"\b(fii\s+(?:buying|selling|inflow|outflow)|dii\s+(?:buying|selling|inflow|outflow))\b",
            r"\b(foreign\s+(?:institutional|portfolio)\s+(?:investor|investment))\b",
        ],
    }

    SECTOR_MAPPING = {
        "Interest Rate / Monetary Policy": [
            "Banking & Financial Services", "Insurance", "Real Estate", "Automobile",
        ],
        "Government Capex & Infrastructure Spending": [
            "Infrastructure & Capital Goods", "Metals & Mining",
        ],
        "Quarterly Earnings & Revenue": ["General"],
        "Order Win & Contract Award": [
            "Infrastructure & Capital Goods", "IT Services", "Defense",
        ],
        "M&A, Stake Sale & Acquisition": ["General"],
        "Regulatory Action & Governance": [
            "Banking & Financial Services", "Pharma", "Telecom",
        ],
        "Management Change & Corporate Action": ["General"],
        "Crude Oil & Commodity": [
            "Energy & Retail", "Metals & Mining",
        ],
        "FII / DII Flow": ["General"],
    }

    def extract_events(self, text: str) -> List[DetectedEvent]:
        """Extract financial events from cleaned article body.

        Returns at least one DetectedEvent (falls back to 'General Corporate News').
        """
        detected: List[DetectedEvent] = []
        text_lower = text.lower()

        for event_name, patterns in self.EVENT_PATTERNS.items():
            matched_terms: set = set()
            for pattern in patterns:
                hits = re.findall(pattern, text_lower)
                matched_terms.update(hits)

            if matched_terms:
                summary = (
                    f"Article discusses {event_name.lower()} "
                    f"(matched: {', '.join(sorted(matched_terms)[:4])})."
                )
                detected.append(
                    DetectedEvent(
                        event_type=event_name,
                        summary=summary,
                        impacted_sectors=self.SECTOR_MAPPING.get(event_name, ["General"]),
                    )
                )

        if not detected:
            detected.append(
                DetectedEvent(
                    event_type="General Corporate News",
                    summary="General business news without a specific macro event trigger.",
                    impacted_sectors=["General"],
                )
            )

        return detected
