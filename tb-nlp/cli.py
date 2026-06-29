"""CLI entry-point for the Financial News Impact Pipeline."""

import argparse
import json
import logging
from pipeline import FinancialNewsImpactPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a LiveMint article for NIFTY stock impact.",
    )
    parser.add_argument("--url", type=str, help="LiveMint article URL to analyze")
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
        "--model", type=str, default="llama3.1:8b",
        help="Ollama LLM model name",
    )

    args = parser.parse_args()
    stock_list = [s.strip() for s in args.stocks.split(",") if s.strip()]
    pipeline = FinancialNewsImpactPipeline(
        ollama_url=args.ollama_url, ollama_model=args.model,
    )

    if args.url:
        result = pipeline.process_url(args.url, stock_list)
    else:
        print("No --url provided. Running demo on sample article text…\n")
        result = pipeline.process_text(
            title="Government Boosts Infrastructure Capex; RBI Hints at Rate Adjustments",
            date="2026-06-29",
            url="https://www.livemint.com/market/infrastructure-capex-boost-2026",
            text=(
                "The Indian government today announced a major ₹2.5 lakh crore "
                "allocation for highways and urban infrastructure projects. "
                "Larsen & Toubro (L&T) and UltraTech Cement are positioned as key "
                "beneficiaries of this massive capex drive, with order wins expected "
                "to surge over the next two quarters.\n"
                "HDFC Bank and ICICI Bank shares showed strong momentum following "
                "liquidity easing measures announced by the RBI governor. "
                "The rate cut is expected to boost loan demand across the banking sector.\n"
                "IT majors like TCS and Infosys traded flat amidst global tech "
                "spending caution, with analysts maintaining a neutral outlook.\n"
                "ITC remained range-bound as FMCG demand showed no new catalyst.\n"
                "Reliance Industries announced plans to expand Jio's 5G network "
                "coverage to 1,000 cities, signalling aggressive growth in telecom."
            ),
            stocks=stock_list,
        )

    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
