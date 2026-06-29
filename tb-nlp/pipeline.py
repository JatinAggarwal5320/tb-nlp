import logging
from typing import List, Dict, Any, Optional
from schemas import (
    PipelineOutput, ArticleMetadata, StockImpactResult, DetectedEvent
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
    """End-to-end NLP & Financial Reasoning Pipeline for LiveMint NIFTY Stock Impact Analysis."""

    def __init__(
        self,
        ollama_url: Optional[str] = "http://localhost:11434",
        ollama_model: str = "llama3.1:8b"
    ):
        self.scraper = LiveMintScraper()
        self.cleaner = TextCleaner()
        self.nifty_dict = NiftyDictionary()
        self.event_extractor = EventExtractor()
        self.stock_detector = StockDetector(self.nifty_dict)
        self.sentiment_analyzer = TargetedSentimentAnalyzer(ollama_url, ollama_model)

    def process_url(self, url: str, stocks: List[str]) -> PipelineOutput:
        """Process a LiveMint article URL and return structured stock impact analysis.

        Args:
            url (str): Target LiveMint article URL.
            stocks (List[str]): List of NIFTY stock names or tickers to evaluate.

        Returns:
            PipelineOutput: Standardized Pydantic JSON model.
        """
        # Step 2: Fetch Article
        raw_article = self.scraper.scrape(url)

        # Step 3: Text Cleaning
        cleaned_text = self.cleaner.clean(raw_article["text"])

        return self.process_text(
            title=raw_article["title"],
            date=raw_article["date"],
            url=url,
            text=cleaned_text,
            stocks=stocks
        )

    def process_text(
        self,
        title: str,
        date: str,
        url: str,
        text: str,
        stocks: List[str]
    ) -> PipelineOutput:
        """Process pre-cleaned or raw article text directly."""
        article_meta = ArticleMetadata(title=title, date=date, url=url)

        # Step 4: Event Detection (Added Intermediate Stage)
        detected_events = self.event_extractor.extract_events(text)

        # Step 5: Relevant Stock Detection (Stage 1)
        affected_map = self.stock_detector.detect_affected_stocks(text, stocks, detected_events)

        # Step 6, 7 & 8: Targeted Sentiment Analysis (Stage 2), Confidence Scoring & Signal Generation
        stock_results: List[StockImpactResult] = []

        for stock in stocks:
            canonical_stock = self.nifty_dict.resolve_stock_name(stock) or stock
            is_affected = affected_map.get(canonical_stock, False)

            if is_affected:
                sentiment, confidence, reason = self.sentiment_analyzer.analyze_stock_impact(
                    canonical_stock, title, text, detected_events
                )
                signal = SignalGenerator.generate_signal(True, sentiment, confidence)
            else:
                sentiment = None
                confidence = None
                signal = "NO IMPACT"
                reason = f"Article does not contain material business developments related to {canonical_stock}."

            stock_results.append(
                StockImpactResult(
                    stock=canonical_stock,
                    affected=is_affected,
                    sentiment=sentiment,
                    confidence=confidence,
                    signal=signal,
                    reason=reason
                )
            )

        return PipelineOutput(
            article=article_meta,
            detected_events=detected_events,
            results=stock_results
        )
