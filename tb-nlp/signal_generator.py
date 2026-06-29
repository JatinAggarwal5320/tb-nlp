from typing import Optional
from schemas import SentimentType, SignalType


class SignalGenerator:
    """Converts targeted sentiment and confidence scores into actionable trading signals."""

    @staticmethod
    def generate_signal(
        affected: bool,
        sentiment: Optional[SentimentType],
        confidence: Optional[float]
    ) -> SignalType:
        """Derive final trading signal based on strict rule mapping matrix.

        Rules:
            - Not affected -> NO IMPACT
            - Positive & confidence > 0.80 -> BUY
            - Positive & 0.60 <= confidence <= 0.80 -> WEAK BUY
            - Neutral -> HOLD
            - Negative & 0.60 <= confidence <= 0.80 -> WEAK SELL
            - Negative & confidence > 0.80 -> SELL
        """
        if not affected or sentiment is None or confidence is None:
            return "NO IMPACT"

        if sentiment == "Positive":
            if confidence > 0.80:
                return "BUY"
            elif confidence >= 0.60:
                return "WEAK BUY"
            else:
                return "HOLD"

        elif sentiment == "Negative":
            if confidence > 0.80:
                return "SELL"
            elif confidence >= 0.60:
                return "WEAK SELL"
            else:
                return "HOLD"

        elif sentiment == "Neutral":
            return "HOLD"

        return "NO IMPACT"
