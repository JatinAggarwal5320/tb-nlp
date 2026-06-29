"""Stage 2 — Targeted Financial Sentiment Analysis.

Key improvements over v1:
  1. **Per-stock sentence scoring** — the heuristic engine now scores only the
     sentences that actually mention the stock, not the whole article globally.
  2. **Differentiated confidence** — direct mentions get a higher base
     confidence than indirect sector matches.
  3. **Richer keyword set** with weighted categories (strong vs. mild signals).
  4. **Ollama timeout raised to 30s** with a retry.
"""

import logging
import json
from typing import List, Optional, Tuple
import requests
from schemas import SentimentType, DetectedEvent, MentionType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword banks — split into strong and mild to weight confidence properly.
# ---------------------------------------------------------------------------
_STRONG_POSITIVE = [
    "record revenue", "record profit", "all-time high", "order win",
    "beat estimates", "beats estimates", "strong growth", "robust demand",
    "upgrade", "outperform", "capex boost", "rate cut",
    "profit surges", "profit jumps", "revenue surges",
    "profit doubles", "profit triples", "massive order",
]
_MILD_POSITIVE = [
    "growth", "expansion", "positive", "recovery", "uptick",
    "dividend", "approval", "beneficiary", "momentum", "rally",
    "upside", "bullish", "improve", "gains",
]
_STRONG_NEGATIVE = [
    "profit falls", "profit plunges", "revenue declines", "revenue falls",
    "misses estimates", "debt default", "downgrade", "underperform",
    "margin compression", "significant loss", "sharp decline",
    "fraud", "scam", "ban",
]
_MILD_NEGATIVE = [
    "loss", "slump", "penalty", "lawsuit", "probe", "investigation",
    "caution", "headwind", "risk", "volatile", "bearish", "sell-off",
    "weakness", "slowdown", "muted", "pressure",
]


class TargetedSentimentAnalyzer:
    """Produces per-stock sentiment, confidence, and explanation."""

    def __init__(
        self,
        ollama_url: Optional[str] = "http://localhost:11434",
        model_name: str = "llama3.1:8b",
    ):
        self.ollama_url = ollama_url
        self.model_name = model_name

    def analyze_stock_impact(
        self,
        stock_name: str,
        article_title: str,
        relevant_sentences: List[str],
        events: List[DetectedEvent],
        mention_type: MentionType = "direct",
    ) -> Tuple[SentimentType, float, str]:
        """Analyze sentiment for a specific stock using only its relevant text.

        Args:
            stock_name: Canonical stock name.
            article_title: Full article title (always included as context).
            relevant_sentences: Sentences that mention or relate to this stock.
            events: Detected macro events.
            mention_type: How the stock was linked (direct / indirect_sector).

        Returns:
            (sentiment, confidence, reason)
        """
        stock_text = " ".join(relevant_sentences)

        # Try LLM first
        llm_result = self._call_ollama(stock_name, article_title, stock_text)
        if llm_result:
            return llm_result

        # Fallback to improved heuristic
        return self._heuristic_analysis(
            stock_name, article_title, stock_text, events, mention_type,
        )

    # ------------------------------------------------------------------
    # LLM path (Ollama)
    # ------------------------------------------------------------------
    def _call_ollama(
        self, stock_name: str, title: str, text: str,
    ) -> Optional[Tuple[SentimentType, float, str]]:
        if not self.ollama_url:
            return None

        prompt = (
            "You are a senior Indian equity research analyst.\n"
            f"Evaluate the impact of this news specifically on **{stock_name}**.\n\n"
            f"Headline: {title}\n"
            f"Relevant excerpt:\n{text[:2500]}\n\n"
            "Respond ONLY in valid JSON:\n"
            '{"sentiment": "Positive"|"Negative"|"Neutral", '
            '"confidence": <float 0.50-0.99>, '
            f'"reason": "<2-3 sentences about impact on {stock_name}>"'
            "}"
        )

        for attempt in range(2):  # one retry
            try:
                res = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                    timeout=30,  # raised from 8s — 8B models need headroom
                )
                if res.status_code == 200:
                    data = res.json().get("response", "")
                    parsed = json.loads(data)
                    sent = parsed.get("sentiment", "Neutral")
                    conf = float(parsed.get("confidence", 0.70))
                    reason = parsed.get(
                        "reason",
                        f"LLM analysis for {stock_name}.",
                    )
                    if sent in ("Positive", "Negative", "Neutral"):
                        return sent, min(max(conf, 0.0), 1.0), reason
            except Exception as e:
                if attempt == 0:
                    logger.debug("Ollama attempt 1 failed (%s), retrying…", e)
                else:
                    logger.debug("Ollama unavailable (%s). Falling back to heuristics.", e)

        return None

    # ------------------------------------------------------------------
    # Heuristic path — now scores per-stock text, not the global article
    # ------------------------------------------------------------------
    def _heuristic_analysis(
        self,
        stock_name: str,
        title: str,
        stock_text: str,
        events: List[DetectedEvent],
        mention_type: MentionType,
    ) -> Tuple[SentimentType, float, str]:
        """Score only the sentences relevant to this stock."""
        combined = (title + " " + stock_text).lower()

        # Weighted scoring: strong keywords count 2, mild count 1
        pos_score = (
            sum(2 for kw in _STRONG_POSITIVE if kw in combined)
            + sum(1 for kw in _MILD_POSITIVE if kw in combined)
        )
        neg_score = (
            sum(2 for kw in _STRONG_NEGATIVE if kw in combined)
            + sum(1 for kw in _MILD_NEGATIVE if kw in combined)
        )

        event_desc = events[0].event_type if events else "corporate development"

        # Base confidence differs by mention type
        if mention_type == "direct":
            base_conf = 0.72
        else:
            base_conf = 0.62  # less certain for indirect/sector matches

        if pos_score > neg_score:
            sentiment: SentimentType = "Positive"
            # Scale confidence with the strength gap, capped at 0.95
            confidence = min(base_conf + (pos_score - neg_score) * 0.04, 0.95)
            reason = (
                f"Positive catalysts in {event_desc.lower()} context are expected to "
                f"support {stock_name}'s near-term outlook. "
                f"Key signals include growth-oriented developments mentioned alongside the company."
            )
        elif neg_score > pos_score:
            sentiment: SentimentType = "Negative"
            confidence = min(base_conf + (neg_score - pos_score) * 0.04, 0.95)
            reason = (
                f"Adverse developments in {event_desc.lower()} context present headwinds "
                f"for {stock_name}. "
                f"Risk indicators such as margin pressure or regulatory concerns were noted."
            )
        else:
            sentiment: SentimentType = "Neutral"
            confidence = base_conf
            reason = (
                f"The article references {stock_name} in the context of {event_desc.lower()}, "
                f"but the signals are balanced with no clear directional bias."
            )

        return sentiment, round(confidence, 2), reason
