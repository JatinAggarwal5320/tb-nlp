from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Supported Sentiments
SentimentType = Literal["Positive", "Negative", "Neutral"]

# Supported Trading Signals
SignalType = Literal["BUY", "WEAK BUY", "HOLD", "WEAK SELL", "SELL", "NO IMPACT"]


class ArticleMetadata(BaseModel):
    """Metadata extracted from the financial news article."""
    title: str = Field(..., description="Title of the news article")
    date: str = Field(..., description="Publication date or ISO timestamp")
    url: str = Field(..., description="Source URL of the article")


class DetectedEvent(BaseModel):
    """Financial event detected within the article text."""
    event_type: str = Field(..., description="Category of event (e.g. Rate Cut, Earnings, Order Win, Capex)")
    summary: str = Field(..., description="Brief summary of the detected event")
    impacted_sectors: List[str] = Field(default_factory=list, description="Sectors or industries affected by this event")


class StockImpactResult(BaseModel):
    """Targeted impact analysis result for a specific NIFTY stock."""
    stock: str = Field(..., description="Name or ticker of the NIFTY stock")
    affected: bool = Field(..., description="Whether the stock is materially affected by the article news")
    sentiment: Optional[SentimentType] = Field(None, description="Company-specific sentiment (Positive, Negative, Neutral)")
    confidence: Optional[float] = Field(None, description="Confidence score between 0.00 and 1.00")
    signal: SignalType = Field(..., description="Trading signal derived from sentiment and confidence")
    reason: str = Field(..., description="Concise 2-3 sentence explanation for the prediction")


class PipelineOutput(BaseModel):
    """Final structured JSON output returned by the Financial News Impact Pipeline."""
    article: ArticleMetadata
    detected_events: List[DetectedEvent] = Field(default_factory=list, description="Core financial events identified in article")
    results: List[StockImpactResult] = Field(..., description="Targeted sentiment and signal results for each requested stock")
