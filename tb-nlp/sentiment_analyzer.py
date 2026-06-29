import logging
import re
import json
from typing import Dict, Any, Optional, Tuple
import requests
from schemas import SentimentType, DetectedEvent

logger = logging.getLogger(__name__)


class TargetedSentimentAnalyzer:
    """Stage 2: Targeted Financial Sentiment Analysis, Confidence Scoring, and Explanation Generation."""

    def __init__(self, ollama_url: Optional[str] = "http://localhost:11434", model_name: str = "llama3.1:8b"):
        self.ollama_url = ollama_url
        self.model_name = model_name

    def analyze_stock_impact(
        self,
        stock_name: str,
        article_title: str,
        article_text: str,
        events: list[DetectedEvent]
    ) -> Tuple[SentimentType, float, str]:
        """Analyze financial sentiment, confidence, and generate rationale for a specific stock.

        Returns:
            Tuple[SentimentType, float, str]: (sentiment, confidence, explanation)
        """
        # Attempt LLM reasoning first if Ollama is accessible
        llm_result = self._call_ollama_reasoning(stock_name, article_title, article_text)
        if llm_result:
            return llm_result

        # Fallback to deterministic financial heuristic reasoning engine
        return self._heuristic_financial_analysis(stock_name, article_title, article_text, events)

    def _call_ollama_reasoning(
        self, stock_name: str, title: str, text: str
    ) -> Optional[Tuple[SentimentType, float, str]]:
        """Call local Ollama endpoint for targeted structured sentiment analysis."""
        if not self.ollama_url:
            return None

        prompt = f"""You are a senior financial analyst analyzing Indian stock market news.
Evaluate the specific financial impact of the following news article on the company: '{stock_name}'.

Article Title: {title}
Article Excerpt: {text[:2000]}

Respond ONLY in valid raw JSON with this exact structure:
{{
  "sentiment": "Positive" | "Negative" | "Neutral",
  "confidence": float between 0.50 and 0.99,
  "reason": "Concise 2-3 sentence explanation of why this news impacts {stock_name} in this way."
}}
"""
        try:
            res = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=8
            )
            if res.status_code == 200:
                data = res.json().get("response", "")
                parsed = json.loads(data)
                sent = parsed.get("sentiment", "Neutral")
                conf = float(parsed.get("confidence", 0.75))
                reason = parsed.get("reason", f"The news directly impacts operational and financial outlook for {stock_name}.")
                if sent in ["Positive", "Negative", "Neutral"]:
                    return sent, min(max(conf, 0.0), 1.0), reason
        except Exception as e:
            logger.debug(f"Ollama LLM call skipped or unavailable ({e}). Using financial heuristics engine.")

        return None

    def _heuristic_financial_analysis(
        self,
        stock_name: str,
        title: str,
        text: str,
        events: list[DetectedEvent]
    ) -> Tuple[SentimentType, float, str]:
        """Financial rules-based sentiment analyzer as robust fallback."""
        combined_text = (title + " " + text).lower()

        positive_keywords = [
            "profit jumps", "surges", "rally", "record revenue", "order win", "beat estimates",
            "growth", "rate cut", "upgrade", "expansion", "dividend", "approval", "capex boost"
        ]
        negative_keywords = [
            "profit falls", "plunges", "slump", "loss", "misses estimates", "downgrade",
            "penalty", "lawsuit", "probe", "investigation", "debt default", "margin compression"
        ]

        pos_score = sum(1 for kw in positive_keywords if kw in combined_text)
        neg_score = sum(1 for kw in negative_keywords if kw in combined_text)

        event_desc = events[0].event_type if events else "Corporate Development"

        if pos_score > neg_score:
            sentiment: SentimentType = "Positive"
            confidence = min(0.70 + (pos_score * 0.05), 0.95)
            reason = f"Positive news catalysts and strong growth indicators surrounding {event_desc.lower()} expected to boost operational outlook for {stock_name}."
        elif neg_score > pos_score:
            sentiment: SentimentType = "Negative"
            confidence = min(0.70 + (neg_score * 0.05), 0.95)
            reason = f"Adverse developments and margin pressure highlighted in {event_desc.lower()} present potential head-winds for {stock_name} near-term profitability."
        else:
            sentiment: SentimentType = "Neutral"
            confidence = 0.75
            reason = f"The article details neutral or balanced operational updates regarding {event_desc.lower()} with limited direct directional impact on {stock_name}."

        return sentiment, confidence, reason
