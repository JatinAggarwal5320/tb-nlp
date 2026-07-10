# tb-nlp — Financial News Impact Analysis Pipeline for NIFTY Stocks

An end-to-end NLP pipeline that analyzes LiveMint financial news articles and determines which NIFTY 50 stocks are affected, the direction and strength of impact, and produces actionable trading signals.

## Pipeline Architecture

```
LiveMint URL / Raw Text
        │
        ▼
 Article Scraper (scraper.py)         ← retry with exponential backoff
        │
        ▼
 Text Cleaning (cleaner.py)           ← preserves ₹, %, company names
        │
        ▼
 Event Detection (event_extractor.py) ← Rate Cut, Earnings, Capex, Order Win, M&A, etc.
        │
        ▼
 Stock Detection (stock_detector.py)  ← direct alias match + indirect sector routing
        │                                + dismissive-context filtering
        ▼
 Targeted Sentiment (sentiment_analyzer.py) ← per-stock sentence scoring
        │                                      Ollama LLM (primary) → heuristic (fallback)
        ▼
 Signal Generation (signal_generator.py)    ← BUY / WEAK BUY / HOLD / WEAK SELL / SELL / NO IMPACT
        │
        ▼
 Structured JSON Output
```

## Key Design Decisions

### Dismissive-Context Filtering
A stock being *mentioned* does not mean it is *affected*. If an article says "TCS traded flat" or "ITC remained range-bound", those stocks are excluded from analysis. The detector extracts the sentence around each mention and checks for dismissive language before marking a stock as impacted.

### Per-Stock Sentence Scoring
Sentiment is **not** computed globally on the full article. Each affected stock is scored only against the sentences that actually discuss it. This prevents an article that is positive for L&T and neutral for TCS from giving both the same signal.

### Direct vs Indirect Impact
- **Direct**: Stock or alias explicitly mentioned in a substantive context → higher base confidence (0.72)
- **Indirect (sector)**: Stock not mentioned, but its sector matches a detected macro event (e.g. rate cut → banking) → lower base confidence (0.62)

The `mention_type` field in the output makes this transparent.

### Signal Matrix

| Sentiment | Confidence | Signal |
|-----------|-----------|--------|
| Positive | > 0.80 | **BUY** |
| Positive | 0.60 – 0.80 | **WEAK BUY** |
| Neutral | any | **HOLD** |
| Negative | 0.60 – 0.80 | **WEAK SELL** |
| Negative | > 0.80 | **SELL** |
| Not affected | — | **NO IMPACT** |

## Modules

| File | Purpose |
|------|---------|
| `schemas.py` | Pydantic models for all pipeline stages |
| `scraper.py` | LiveMint HTML fetcher with retry + DOM cleanup |
| `cleaner.py` | Unicode normalization, financial figure preservation |
| `nifty_dictionary.py` | NIFTY 50 tickers, aliases, sector mappings, regex-safe matching |
| `event_extractor.py` | Multi-word phrase patterns for 9 event categories |
| `stock_detector.py` | Direct alias + indirect sector detection with dismissive filtering |
| `sentiment_analyzer.py` | Ollama LLM (primary) with weighted-keyword heuristic fallback |
| `signal_generator.py` | Confidence × sentiment → trading signal |
| `pipeline.py` | End-to-end orchestrator |
| `cli.py` | CLI entry point with built-in demo |

## Usage

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run demo (no URL needed)
```bash
python cli.py
```

### Analyze a - live article
```bash
python cli.py --url "https://www.livemint.com/..." --stocks "Reliance,TCS,HDFC Bank,L&T"
```

### Python API
```python
from pipeline import FinancialNewsImpactPipeline

pipeline = FinancialNewsImpactPipeline()
result = pipeline.process_url(
    url="https://www.livemint.com/...",
    stocks=["Reliance", "TCS", "HDFC Bank", "L&T", "UltraTech Cement"]
)
print(result.model_dump_json(indent=2))
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | *(demo mode)* | LiveMint article URL |
| `--stocks` | Top 20 NIFTY names | Comma-separated stock list |
| `--ollama-url` | `http://localhost:11434` | Ollama server URL |
| `--model` | `llama3.1:8b` | Ollama model name |

## LLM Backend

The sentiment analyzer tries **Ollama first** (30s timeout, 1 retry) for high-quality contextual reasoning. If Ollama is unavailable, it silently falls back to the deterministic heuristic engine — no setup required to get started.

Supported models: `llama3.1:8b`, `qwen2.5:7b`, or any Ollama-hosted model that can output structured JSON.

## Example Output

```json
{
  "article": {
    "title": "Government Boosts Infrastructure Capex; RBI Hints at Rate Adjustments",
    "date": "2026-06-29",
    "url": "https://www.livemint.com/market/infrastructure-capex-boost-2026"
  },
  "detected_events": [
    {
      "event_type": "Interest Rate / Monetary Policy",
      "summary": "Article discusses interest rate / monetary policy (matched: liquidity easing, rate cut, rbi governor).",
      "impacted_sectors": ["Banking & Financial Services", "Insurance", "Real Estate", "Automobile"]
    },
    {
      "event_type": "Government Capex & Infrastructure Spending",
      "summary": "Article discusses government capex & infrastructure spending (matched: infrastructure projects).",
      "impacted_sectors": ["Infrastructure & Capital Goods", "Metals & Mining"]
    }
  ],
  "results": [
    {
      "stock": "L&T",
      "affected": true,
      "mention_type": "direct",
      "sentiment": "Positive",
      "confidence": 0.88,
      "signal": "BUY",
      "reason": "Positive catalysts in interest rate / monetary policy context are expected to support L&T's near-term outlook."
    },
    {
      "stock": "TCS",
      "affected": false,
      "mention_type": "none",
      "sentiment": null,
      "confidence": null,
      "signal": "NO IMPACT",
      "reason": "Article does not contain material business developments related to TCS."
    },
    {
      "stock": "State Bank of India",
      "affected": true,
      "mention_type": "indirect_sector",
      "sentiment": "Positive",
      "confidence": 0.78,
      "signal": "WEAK BUY",
      "reason": "Positive catalysts in interest rate / monetary policy context are expected to support State Bank of India's near-term outlook."
    }
  ]
}
```
