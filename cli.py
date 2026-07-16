"""CLI entry-point for the Financial News Impact Pipeline and RSS Consumer."""

import argparse
import json
import logging
from pipeline import FinancialNewsImpactPipeline
from rss_consumer import LiveMintRSSConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


import sys


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(
        description="Analyze LiveMint articles or RSS feeds for NIFTY stock impact.",
    )
    parser.add_argument("--url", type=str, help="LiveMint article URL to analyze")
    parser.add_argument(
        "--rss", action="store_true", help="Automatically pull and analyze latest articles from LiveMint RSS feed"
    )
    parser.add_argument(
        "--rss-category", type=str, default="markets", choices=["markets", "companies", "news"],
        help="RSS category feed to pull ('markets', 'companies', 'news')"
    )
    parser.add_argument(
        "--rss-max", type=int, default=3, help="Maximum RSS feed articles to process in batch"
    )
    parser.add_argument(
        "--stocks",
        type=str,
        default=(
            "Reliance,TCS,Infosys,HDFC Bank,ICICI Bank,ITC,L&T,"
            "UltraTech Cement,State Bank of India,Tata Motors,"
            "Maruti Suzuki,Bharti Airtel,Kotak Mahindra Bank,"
            "Axis Bank,HUL,Sun Pharma,Wipro,Titan,Asian Paints,"
            "Bajaj Finance"
        ),
        help="Comma-separated list of NIFTY stocks to evaluate",
    )
    parser.add_argument(
        "--ollama-url", type=str, default="http://localhost:11434",
        help="Ollama base URL",
    )
    parser.add_argument(
        "--model", type=str, default="llama3.2:3b",
        help="Ollama LLM model name",
    )

    args = parser.parse_args()
    stock_list = [s.strip() for s in args.stocks.split(",") if s.strip()]
    pipeline = FinancialNewsImpactPipeline(
        ollama_url=args.ollama_url, ollama_model=args.model,
    )

    if args.rss:
        logger = logging.getLogger("cli")
        logger.info("Starting automated RSS ingestion (%s feed)...", args.rss_category)
        rss_consumer = LiveMintRSSConsumer(pipeline=pipeline)
        results = rss_consumer.process_rss_feed(
            category=args.rss_category, stocks=stock_list, max_entries=args.rss_max
        )
        output_data = [r.model_dump() for r in results]
        print(json.dumps(output_data, indent=2, ensure_ascii=False))

    elif args.url:
        result = pipeline.process_url(args.url, stock_list)
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
