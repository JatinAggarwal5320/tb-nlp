# Financial News Impact Analysis Pipeline for NIFTY Stocks (`tb-nlp`)

An end-to-end NLP and LLM financial intelligence pipeline that analyzes LiveMint news articles to determine stock-specific impacts, confidence scores, targeted sentiments, and trading signals for NIFTY companies.

## Pipeline Architecture

```
LiveMint URL / Text
      │
      ▼
Article Scraper (scraper.py)
      │
      ▼
Text Cleaning & Preprocessing (cleaner.py)
      │
      ▼
Event Detection (event_extractor.py)  <-- Event Extraction Stage
      │
      ▼
Relevant Stock Detection (stock_detector.py)  <-- Direct & Indirect (Stage 1)
      │
      ▼
Targeted Sentiment & Reasoning (sentiment_analyzer.py) <-- Stock-Specific (Stage 2)
      │
      ▼
Signal Generation (signal_generator.py) <-- BUY / WEAK BUY / HOLD / WEAK SELL / SELL / NO IMPACT
      │
      ▼
Structured JSON Output
```

## Features

1. **Targeted Sentiment Analysis**: Evaluates sentiment per company individually rather than scoring overall article sentiment.
2. **Intermediate Event Detection**: Classifies financial catalysts (Rate Cuts, Earnings Beats, Capex Allocations, Order Wins, Regulatory Actions).
3. **Direct & Indirect Relevance Engine**: Matches direct company aliases (e.g., `HDFC` -> `HDFC Bank`) and detects indirect macro sector effects (e.g., infrastructure budget -> `L&T`, `UltraTech Cement`).
4. **Calibrated Signal Matrix**: Converts confidence (`0.0`-`1.0`) and sentiment into exact signals (`BUY`, `WEAK BUY`, `HOLD`, `WEAK SELL`, `SELL`, `NO IMPACT`).
5. **JSON API Ready**: Formatted according to strict Pydantic models.

## Usage

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Command Line Interface (CLI)

Run demo test:
```bash
python cli.py
```

Analyze live LiveMint URL:
```bash
python cli.py --url "https://www.livemint.com/..." --stocks "Reliance,TCS,HDFC Bank,L&T"
```

### 3. Python API Integration

```python
from pipeline import FinancialNewsImpactPipeline

pipeline = FinancialNewsImpactPipeline()
result = pipeline.process_url(
    url="https://www.livemint.com/...",
    stocks=["Reliance", "TCS", "Infosys", "HDFC Bank", "L&T"]
)

print(result.model_dump_json(indent=2))
```
