import argparse
import json
import sys
import logging
from pipeline import FinancialNewsImpactPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Financial News Impact Analysis Pipeline for NIFTY Stocks")
    parser.add_argument("--url", type=str, help="LiveMint article URL to analyze")
    parser.add_argument(
        "--stocks",
        type=str,
        default="Reliance,TCS,Infosys,HDFC Bank,ICICI Bank,ITC,L&T,UltraTech Cement",
        help="Comma-separated list of NIFTY stocks to analyze"
    )
    parser.add_argument("--ollama-url", type=str, default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--model", type=str, default="llama3.1:8b", help="Ollama LLM model name")

    args = parser.parse_args()

    stock_list = [s.strip() for s in args.stocks.split(",") if s.strip()]

    pipeline = FinancialNewsImpactPipeline(ollama_url=args.ollama_url, ollama_model=args.model)

    if args.url:
        result = pipeline.process_url(args.url, stock_list)
    else:
        # Demo execution using sample article text if no URL provided
        print("No --url provided. Running demo on sample financial article text...\n")
        sample_title = "Government Boosts Infrastructure Capex; RBI Hints at Rate Adjustments"
        sample_date = "2026-06-29"
        sample_url = "https://www.livemint.com/market/infrastructure-capex-boost-2026"
        sample_text = """
        The Indian government today announced a major ₹2.5 lakh crore allocation for highways and urban infrastructure projects.
        Larsen & Toubro (L&T) and UltraTech Cement are positioned as key beneficiaries of this massive capex drive.
        Meanwhile, HDFC Bank and ICICI Bank shares showed momentum following liquidity easing measures by the central bank.
        IT majors like TCS and Infosys traded flat amidst global tech spending caution.
        """
        result = pipeline.process_text(sample_title, sample_date, sample_url, sample_text, stock_list)

    # Output pretty JSON
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
