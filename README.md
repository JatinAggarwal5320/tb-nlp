# tb-nlp — Financial News Impact Analysis Pipeline for NIFTY Stocks

An end-to-end NLP pipeline that analyzes LiveMint financial news articles and determines which NIFTY 50 stocks are affected, the direction and strength of impact, and produces actionable trading signals.

Supports both **manual article URL processing** and **automated real-time LiveMint RSS feed ingestion**.

## Pipeline Architecture

```
LiveMint URL / RSS Feed
        │
        ▼
 RSS Consumer (rss_consumer.py)       ← auto-discovers live RSS articles
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

### Real-Time RSS Feed Auto-Discovery
Includes `rss_consumer.py` to automatically pull the latest market and corporate news articles from LiveMint RSS feeds (`markets`, `companies`, `news`). Each entry link is automatically scraped for full text and processed through the impact pipeline.

### Dismissive-Context Filtering
A stock being *mentioned* does not mean it is *affected*. If an article says "TCS traded flat" or "ITC remained range-bound", those stocks are excluded from analysis. The detector extracts the sentence around each mention and checks for dismissive language before marking a stock as impacted.

### Per-Stock Sentence Scoring
Sentiment is **not** computed globally on the full article. Each affected stock is scored only against the sentences that actually discuss it. This prevents an article that is positive for L&T and neutral for TCS from giving both the same signal.

### Direct vs Indirect Impact
- **Direct**: Stock or alias explicitly mentioned in a substantive context → higher base confidence (0.72)
- **Indirect (sector)**: Stock not mentioned, but its sector matches a detected macro event (e.g. rate cut → banking) → lower base confidence (0.62)

The `mention_type` field in the output makes this transparent.

## Modules

| File | Purpose |
|------|---------|
| `schemas.py` | Pydantic models for all pipeline stages |
| `rss_consumer.py` | LiveMint RSS feed parser and batch article processor |
| `scraper.py` | LiveMint HTML fetcher with retry + DOM cleanup |
| `cleaner.py` | Unicode normalization, financial figure preservation |
| `nifty_dictionary.py` | NIFTY 50 tickers, aliases, sector mappings, regex-safe matching |
| `event_extractor.py` | Multi-word phrase patterns for 9 event categories |
| `stock_detector.py` | Direct alias + indirect sector detection with dismissive filtering |
| `sentiment_analyzer.py` | Ollama LLM (primary) with weighted-keyword heuristic fallback |
| `signal_generator.py` | Confidence × sentiment → trading signal |
| `cli.py` | CLI entry point supporting single URLs and RSS feeds |
| `pipeline.py` | End-to-end orchestrator |

## Usage

### Install dependencies
```bash
pip install -r requirements.txt
```

### Automated Live RSS Feed Ingestion (New!)
Automatically pull and analyze the latest market articles from LiveMint RSS feeds:
```bash
python cli.py --rss --rss-category markets --rss-max 5
```

### Analyze a single live article URL
```bash
python cli.py --url "https://www.livemint.com/..." --stocks "Reliance,TCS,HDFC Bank,L&T"
```

### Benchmark Ollama Models (New!)
A benchmarking script `benchmark.py` is included to measure the execution time and JSON output format validity of different Ollama models (e.g. `llama3.2:1b`, `qwen2.5:1.5b`, `llama3.2:3b`, `qwen2.5:3b`, `gemma2:2b`, `llama3.1:8b`) on your CPU.

To run the benchmark:
```bash
python benchmark.py
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--rss` | `False` | Pull and analyze live RSS articles |
| `--rss-category` | `markets` | LiveMint feed category (`markets`, `companies`, `news`) |
| `--rss-max` | `3` | Max RSS articles to process in batch |
| `--url` | `None` | LiveMint article URL to analyze |
| `--stocks` | Top 20 NIFTY names | Comma-separated stock list |
| `--ollama-url` | `http://localhost:11434` | Ollama server URL |
| `--model` | `llama3.2:3b` | Ollama model name |
