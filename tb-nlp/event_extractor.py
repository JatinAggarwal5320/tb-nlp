import re
import logging
from typing import List
from schemas import DetectedEvent

logger = logging.getLogger(__name__)


class EventExtractor:
    """Detects core financial events (Rate cut, Earnings, Capex, Order win, Regulation, etc.) from article text."""

    EVENT_PATTERNS = {
        "Interest Rate / Monetary Policy": [
            r"\b(rate cut|interest rate|repo rate|rbi|monetary policy|central bank|inflation|liquidity)\b"
        ],
        "Government Capex & Infrastructure Spending": [
            r"\b(infrastructure spending|government spending|capex|budget allocation|highway|railway|national infrastructure pipeline|urban development)\b"
        ],
        "Quarterly Earnings & Revenue": [
            r"\b(q[1-4]|quarterly results|profit|net profit|revenue|ebitda|margin|earnings|pat|topline|bottomline)\b"
        ],
        "Order Win & Contract Award": [
            r"\b(order win|secures order|bagged order|awarded contract|contract worth|epc contract|project award)\b"
        ],
        "M&A, Stake Sale & Acquisition": [
            r"\b(acquisition|acquire|merger|stake sale|buyout|takeover|divestment|joint venture)\b"
        ],
        "Regulatory Action & Governance": [
            r"\b(sebi|rbi penalty|showcause notice|regulatory approval|compliance|penalty|cbi|ed probe|lawsuit)\b"
        ],
    }

    SECTOR_MAPPING = {
        "Interest Rate / Monetary Policy": ["Banking & Financial Services", "Real Estate", "Automobile"],
        "Government Capex & Infrastructure Spending": ["Infrastructure & Capital Goods", "Cement", "Steel"],
        "Quarterly Earnings & Revenue": ["General"],
        "Order Win & Contract Award": ["Infrastructure & Capital Goods", "IT Services", "Defense"],
        "M&A, Stake Sale & Acquisition": ["General"],
        "Regulatory Action & Governance": ["Banking & Financial Services", "Pharma", "Telecom"],
    }

    def extract_events(self, text: str) -> List[DetectedEvent]:
        """Extract financial events from article body.

        Args:
            text (str): Cleaned article text.

        Returns:
            List[DetectedEvent]: Identified financial events and affected sectors.
        """
        detected_events: List[DetectedEvent] = []
        text_lower = text.lower()

        for event_name, patterns in self.EVENT_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    # Formulate event summary
                    summary = f"Article mentions key financial developments regarding '{event_name}' (matched terms: {', '.join(set(matches[:3]))})."
                    impacted_sectors = self.SECTOR_MAPPING.get(event_name, ["General"])

                    detected_events.append(
                        DetectedEvent(
                            event_type=event_name,
                            summary=summary,
                            impacted_sectors=impacted_sectors
                        )
                    )
                    break

        if not detected_events:
            detected_events.append(
                DetectedEvent(
                    event_type="General Corporate News",
                    summary="General business news without specific major macro event trigger.",
                    impacted_sectors=["General"]
                )
            )

        return detected_events
