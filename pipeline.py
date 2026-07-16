"""End-to-end pipeline orchestrator.

Connects: Scraper → Cleaner → Event Extractor → Stock Detector → Sentiment Analyzer → Signal Generator.
"""

import logging
from typing import List, Optional
from schemas import (
    PipelineOutput, ArticleMetadata, StockImpactResult, DetectedEvent,
)
from scraper import LiveMintScraper
from cleaner import TextCleaner
from nifty_dictionary import NiftyDictionary
from event_extractor import EventExtractor
from stock_detector import StockDetector
from sentiment_analyzer import TargetedSentimentAnalyzer
from signal_generator import SignalGenerator

logger = logging.getLogger(__name__)


class FinancialNewsImpactPipeline:
    """Analyze a LiveMint article and produce per-stock impact signals."""

    def __init__(
        self,
        ollama_url: Optional[str] = "http://localhost:11434",
        ollama_model: str = "llama3.2:3b",
    ):
        self.scraper = LiveMintScraper()
        self.cleaner = TextCleaner()
        self.nifty_dict = NiftyDictionary()
        self.event_extractor = EventExtractor()
        self.stock_detector = StockDetector(self.nifty_dict)
        self.sentiment_analyzer = TargetedSentimentAnalyzer(ollama_url, ollama_model)

    def process_url(self, url: str, stocks: List[str]) -> PipelineOutput:
        """Fetch a URL, clean, and run the full analysis pipeline."""
        raw = self.scraper.scrape(url)
        cleaned = self.cleaner.clean(raw["text"])
        return self.process_text(
            title=raw["title"],
            date=raw["date"],
            url=url,
            text=cleaned,
            stocks=stocks,
        )

    def process_text(
        self,
        title: str,
        date: str,
        url: str,
        text: str,
        stocks: List[str],
    ) -> PipelineOutput:
        """Run analysis on pre-cleaned text."""

        article_meta = ArticleMetadata(title=title, date=date, url=url)

        # Step 1 — Event Detection
        detected_events = self.event_extractor.extract_events(text)
        logger.info(
            "Detected %d event(s): %s",
            len(detected_events),
            [e.event_type for e in detected_events],
        )

        # Step 2 — Relevant Stock Detection (returns per-stock sentences)
        detection_map = self.stock_detector.detect_affected_stocks(
            text, stocks, detected_events,
        )

        # Step 3 — Batch LLM for direct mentions (ONE call), heuristics for rest
        # Collect all directly-mentioned stocks for a single batch LLM call
        direct_stocks_sentences = {}
        stock_info = {}  # canonical -> (is_affected, mention_type, relevant_sents)

        for stock in stocks:
            canonical = self.nifty_dict.resolve_stock_name(stock) or stock
            is_affected, mention_type, relevant_sents = detection_map.get(
                canonical, (False, "none", []),
            )
            stock_info[canonical] = (is_affected, mention_type, relevant_sents)
            if is_affected and mention_type == "direct":
                direct_stocks_sentences[canonical] = relevant_sents

        # Single batch LLM call for all direct mentions
        batch_results = {}
        if direct_stocks_sentences:
            logger.info(
                "Sending %d direct-mention stocks to batch LLM analysis...",
                len(direct_stocks_sentences),
            )
            batch_results = self.sentiment_analyzer.batch_analyze_stocks(
                article_title=title,
                stocks_with_sentences=direct_stocks_sentences,
            )

        # Assemble final results
        results: List[StockImpactResult] = []
        for stock in stocks:
            canonical = self.nifty_dict.resolve_stock_name(stock) or stock
            is_affected, mention_type, relevant_sents = stock_info[canonical]

            if is_affected:
                # Check if batch LLM returned a result for this stock
                if canonical in batch_results:
                    sentiment, confidence, reason = batch_results[canonical]
                else:
                    # Fallback to heuristic (for indirect matches or LLM misses)
                    sentiment, confidence, reason = (
                        self.sentiment_analyzer.analyze_stock_impact(
                            stock_name=canonical,
                            article_title=title,
                            relevant_sentences=relevant_sents,
                            events=detected_events,
                            mention_type=mention_type,
                        )
                    )
                signal = SignalGenerator.generate_signal(True, sentiment, confidence)
            else:
                sentiment = None
                confidence = None
                signal = "NO IMPACT"
                reason = (
                    f"Article does not contain material business "
                    f"developments related to {canonical}."
                )

            results.append(
                StockImpactResult(
                    stock=canonical,
                    affected=is_affected,
                    mention_type=mention_type,
                    sentiment=sentiment,
                    confidence=confidence,
                    signal=signal,
                    reason=reason,
                )
            )

        return PipelineOutput(
            article=article_meta,
            detected_events=detected_events,
            results=results,
        )
