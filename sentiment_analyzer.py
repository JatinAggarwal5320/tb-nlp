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
from typing import Dict, List, Optional, Tuple
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
        self.ollama_offline = False

    # ------------------------------------------------------------------
    # Batch LLM analysis — mini-batches of 3 stocks to avoid CPU timeouts
    # ------------------------------------------------------------------
    def batch_analyze_stocks(
        self,
        article_title: str,
        stocks_with_sentences: Dict[str, List[str]],
    ) -> Dict[str, Tuple[SentimentType, float, str]]:
        """Analyze multiple stocks via LLM in mini-batches of 3.

        Splitting into small batches ensures each call finishes in ~60s on CPU,
        well within the timeout. Total time scales linearly but reliably.
        """
        if not stocks_with_sentences or not self.ollama_url or self.ollama_offline:
            return {}

        all_results = {}
        stock_items = list(stocks_with_sentences.items())
        batch_size = 3

        for i in range(0, len(stock_items), batch_size):
            if self.ollama_offline:
                break
            chunk = dict(stock_items[i:i + batch_size])
            chunk_results = self._run_single_batch(article_title, chunk)
            all_results.update(chunk_results)

        if all_results:
            logger.info(
                "Batch LLM analysis returned results for %d/%d stocks.",
                len(all_results), len(stocks_with_sentences),
            )
        return all_results

    def _run_single_batch(
        self,
        article_title: str,
        stocks_with_sentences: Dict[str, List[str]],
    ) -> Dict[str, Tuple[SentimentType, float, str]]:
        """Execute a single mini-batch LLM call for up to 3 stocks."""
        stock_blocks = []
        for stock, sents in stocks_with_sentences.items():
            stock_blocks.append(f"**{stock}**: {' '.join(sents[:3])}")
        combined_context = "\n".join(stock_blocks)
        stock_list = list(stocks_with_sentences.keys())

        prompt = (
            "You are a senior Indian equity research analyst.\n"
            f"Headline: {article_title}\n\n"
            "Relevant excerpts per stock:\n"
            f"{combined_context[:3000]}\n\n"
            f"Analyze the impact on EACH of these stocks: {', '.join(stock_list)}\n\n"
            "Respond ONLY in valid JSON as an array:\n"
            '[{"stock": "<name>", "sentiment": "Positive"|"Negative"|"Neutral", '
            '"confidence": <float 0.50-0.99>, '
            '"reason": "<2-3 sentences>"}]\n'
            "Include one entry per stock. No extra text."
        )

        for attempt in range(2):
            try:
                res = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                    timeout=120,  # 2 min per mini-batch of 3 stocks
                )
                if res.status_code == 200:
                    data = res.json().get("response", "")
                    parsed = json.loads(data)

                    # Handle both array and dict-wrapped-array formats
                    if isinstance(parsed, dict):
                        for key in ("results", "stocks", "analysis"):
                            if key in parsed and isinstance(parsed[key], list):
                                parsed = parsed[key]
                                break

                    if isinstance(parsed, list):
                        results = {}
                        for item in parsed:
                            name = item.get("stock", "")
                            sent = item.get("sentiment", "Neutral")
                            conf = float(item.get("confidence", 0.70))
                            reason = item.get("reason", f"LLM analysis for {name}.")
                            if sent in ("Positive", "Negative", "Neutral") and name:
                                results[name] = (sent, min(max(conf, 0.0), 1.0), reason)
                        if results:
                            return results
            except Exception as e:
                if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                    logger.warning("Ollama mini-batch call failed or timed out. Disabling LLM path.")
                    self.ollama_offline = True
                    return {}
                if attempt == 0:
                    logger.debug("Mini-batch attempt 1 failed (%s), retrying…", e)
                else:
                    logger.debug("Mini-batch unavailable (%s). Falling back.", e)

        return {}

    def analyze_stock_impact(
        self,
        stock_name: str,
        article_title: str,
        relevant_sentences: List[str],
        events: List[DetectedEvent],
        mention_type: MentionType = "direct",
    ) -> Tuple[SentimentType, float, str]:
        """Analyze sentiment for a specific stock (heuristic-only path).

        The LLM path is now handled by batch_analyze_stocks.
        This method is used for indirect matches or as fallback.
        """
        stock_text = " ".join(relevant_sentences)

        # Heuristic analysis for indirect matches or when LLM batch missed this stock
        return self._heuristic_analysis(
            stock_name, article_title, stock_text, events, mention_type,
        )

    # ------------------------------------------------------------------
    # LLM path (Ollama)
    # ------------------------------------------------------------------
    def _call_ollama(
        self, stock_name: str, title: str, text: str,
    ) -> Optional[Tuple[SentimentType, float, str]]:
        if not self.ollama_url or self.ollama_offline:
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
                    timeout=90,  # raised to 90s — local CPU generation needs headroom
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
                # If we encounter a connection issue or timeout, disable Ollama globally for this run
                if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                    logger.warning("Ollama connection failed or timed out. Disabling LLM path for subsequent stocks.")
                    self.ollama_offline = True
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
