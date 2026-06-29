"""NIFTY 50 stock metadata: canonical names, NSE tickers, aliases, and sector tags.

The dictionary drives two things:
  1. Alias resolution  — map messy article mentions to a single canonical name.
  2. Sector routing    — indirect-impact detection via event→sector mapping.

To add a stock, append an entry with at minimum a ticker, one alias, and a sector.
"""

import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Master NIFTY-50 metadata (alphabetical by canonical name)
# ---------------------------------------------------------------------------
NIFTY_STOCKS_METADATA: Dict[str, Dict] = {
    "Adani Enterprises": {
        "ticker": "ADANIENT",
        "full_name": "Adani Enterprises Limited",
        "aliases": ["Adani Enterprises", "Adani", "ADANIENT"],
        "sector": "Infrastructure & Capital Goods",
    },
    "Adani Ports": {
        "ticker": "ADANIPORTS",
        "full_name": "Adani Ports and Special Economic Zone Limited",
        "aliases": ["Adani Ports", "APSEZ", "ADANIPORTS"],
        "sector": "Infrastructure & Capital Goods",
    },
    "Apollo Hospitals": {
        "ticker": "APOLLOHOSP",
        "full_name": "Apollo Hospitals Enterprise Limited",
        "aliases": ["Apollo Hospitals", "Apollo", "APOLLOHOSP"],
        "sector": "Healthcare",
    },
    "Asian Paints": {
        "ticker": "ASIANPAINT",
        "full_name": "Asian Paints Limited",
        "aliases": ["Asian Paints", "ASIANPAINT"],
        "sector": "Consumer Goods",
    },
    "Axis Bank": {
        "ticker": "AXISBANK",
        "full_name": "Axis Bank Limited",
        "aliases": ["Axis Bank", "Axis", "AXISBANK"],
        "sector": "Banking & Financial Services",
    },
    "Bajaj Auto": {
        "ticker": "BAJAJ-AUTO",
        "full_name": "Bajaj Auto Limited",
        "aliases": ["Bajaj Auto", "BAJAJ-AUTO"],
        "sector": "Automobile",
    },
    "Bajaj Finance": {
        "ticker": "BAJFINANCE",
        "full_name": "Bajaj Finance Limited",
        "aliases": ["Bajaj Finance", "BAJFINANCE"],
        "sector": "Banking & Financial Services",
    },
    "Bajaj Finserv": {
        "ticker": "BAJAJFINSV",
        "full_name": "Bajaj Finserv Limited",
        "aliases": ["Bajaj Finserv", "BAJAJFINSV"],
        "sector": "Banking & Financial Services",
    },
    "Bharti Airtel": {
        "ticker": "BHARTIARTL",
        "full_name": "Bharti Airtel Limited",
        "aliases": ["Airtel", "Bharti Airtel", "BHARTIARTL"],
        "sector": "Telecom",
    },
    "BPCL": {
        "ticker": "BPCL",
        "full_name": "Bharat Petroleum Corporation Limited",
        "aliases": ["BPCL", "Bharat Petroleum"],
        "sector": "Energy & Retail",
    },
    "Britannia": {
        "ticker": "BRITANNIA",
        "full_name": "Britannia Industries Limited",
        "aliases": ["Britannia", "BRITANNIA"],
        "sector": "FMCG",
    },
    "Cipla": {
        "ticker": "CIPLA",
        "full_name": "Cipla Limited",
        "aliases": ["Cipla", "CIPLA"],
        "sector": "Pharma",
    },
    "Coal India": {
        "ticker": "COALINDIA",
        "full_name": "Coal India Limited",
        "aliases": ["Coal India", "CIL", "COALINDIA"],
        "sector": "Energy & Retail",
    },
    "Divi's Laboratories": {
        "ticker": "DIVISLAB",
        "full_name": "Divi's Laboratories Limited",
        "aliases": ["Divi's Labs", "Divis Labs", "Divi's Laboratories", "DIVISLAB"],
        "sector": "Pharma",
    },
    "Dr. Reddy's": {
        "ticker": "DRREDDY",
        "full_name": "Dr. Reddy's Laboratories Limited",
        "aliases": ["Dr Reddy's", "Dr. Reddy's", "Dr Reddys", "DRREDDY"],
        "sector": "Pharma",
    },
    "Eicher Motors": {
        "ticker": "EICHERMOT",
        "full_name": "Eicher Motors Limited",
        "aliases": ["Eicher Motors", "Royal Enfield", "EICHERMOT"],
        "sector": "Automobile",
    },
    "Grasim": {
        "ticker": "GRASIM",
        "full_name": "Grasim Industries Limited",
        "aliases": ["Grasim", "Grasim Industries", "GRASIM"],
        "sector": "Infrastructure & Capital Goods",
    },
    "HCL Technologies": {
        "ticker": "HCLTECH",
        "full_name": "HCL Technologies Limited",
        "aliases": ["HCL Tech", "HCL Technologies", "HCLTECH", "HCL"],
        "sector": "IT Services",
    },
    "HDFC Bank": {
        "ticker": "HDFCBANK",
        "full_name": "HDFC Bank Limited",
        "aliases": ["HDFC Bank", "HDFC", "HDFCBANK"],
        "sector": "Banking & Financial Services",
    },
    "HDFC Life": {
        "ticker": "HDFCLIFE",
        "full_name": "HDFC Life Insurance Company Limited",
        "aliases": ["HDFC Life", "HDFCLIFE"],
        "sector": "Insurance",
    },
    "Hero MotoCorp": {
        "ticker": "HEROMOTOCO",
        "full_name": "Hero MotoCorp Limited",
        "aliases": ["Hero MotoCorp", "Hero Moto", "HEROMOTOCO"],
        "sector": "Automobile",
    },
    "Hindalco": {
        "ticker": "HINDALCO",
        "full_name": "Hindalco Industries Limited",
        "aliases": ["Hindalco", "Novelis", "HINDALCO"],
        "sector": "Metals & Mining",
    },
    "HUL": {
        "ticker": "HINDUNILVR",
        "full_name": "Hindustan Unilever Limited",
        "aliases": ["HUL", "Hindustan Unilever", "HINDUNILVR"],
        "sector": "FMCG",
    },
    "ICICI Bank": {
        "ticker": "ICICIBANK",
        "full_name": "ICICI Bank Limited",
        "aliases": ["ICICI Bank", "ICICI", "ICICIBANK"],
        "sector": "Banking & Financial Services",
    },
    "IndusInd Bank": {
        "ticker": "INDUSINDBK",
        "full_name": "IndusInd Bank Limited",
        "aliases": ["IndusInd Bank", "IndusInd", "INDUSINDBK"],
        "sector": "Banking & Financial Services",
    },
    "Infosys": {
        "ticker": "INFY",
        "full_name": "Infosys Limited",
        "aliases": ["Infosys", "Infy", "INFY"],
        "sector": "IT Services",
    },
    "ITC": {
        "ticker": "ITC",
        "full_name": "ITC Limited",
        "aliases": ["ITC", "ITC Ltd"],
        "sector": "FMCG",
    },
    "JSW Steel": {
        "ticker": "JSWSTEEL",
        "full_name": "JSW Steel Limited",
        "aliases": ["JSW Steel", "JSW", "JSWSTEEL"],
        "sector": "Metals & Mining",
    },
    "Kotak Mahindra Bank": {
        "ticker": "KOTAKBANK",
        "full_name": "Kotak Mahindra Bank Limited",
        "aliases": ["Kotak Mahindra Bank", "Kotak Bank", "Kotak", "KOTAKBANK"],
        "sector": "Banking & Financial Services",
    },
    "L&T": {
        "ticker": "LT",
        "full_name": "Larsen & Toubro Limited",
        "aliases": ["L&T", "Larsen & Toubro", "Larsen and Toubro", "LT"],
        "sector": "Infrastructure & Capital Goods",
    },
    "M&M": {
        "ticker": "M&M",
        "full_name": "Mahindra & Mahindra Limited",
        "aliases": ["M&M", "Mahindra & Mahindra", "Mahindra", "M and M"],
        "sector": "Automobile",
    },
    "Maruti Suzuki": {
        "ticker": "MARUTI",
        "full_name": "Maruti Suzuki India Limited",
        "aliases": ["Maruti", "Maruti Suzuki", "MARUTI"],
        "sector": "Automobile",
    },
    "Nestle India": {
        "ticker": "NESTLEIND",
        "full_name": "Nestle India Limited",
        "aliases": ["Nestle India", "Nestle", "NESTLEIND"],
        "sector": "FMCG",
    },
    "NTPC": {
        "ticker": "NTPC",
        "full_name": "NTPC Limited",
        "aliases": ["NTPC"],
        "sector": "Energy & Retail",
    },
    "ONGC": {
        "ticker": "ONGC",
        "full_name": "Oil and Natural Gas Corporation Limited",
        "aliases": ["ONGC", "Oil and Natural Gas"],
        "sector": "Energy & Retail",
    },
    "Power Grid": {
        "ticker": "POWERGRID",
        "full_name": "Power Grid Corporation of India Limited",
        "aliases": ["Power Grid", "POWERGRID", "PGCIL"],
        "sector": "Energy & Retail",
    },
    "Reliance": {
        "ticker": "RELIANCE",
        "full_name": "Reliance Industries Limited",
        "aliases": ["Reliance", "RIL", "Reliance Industries", "Jio", "Reliance Retail"],
        "sector": "Energy & Retail",
    },
    "SBI Life": {
        "ticker": "SBILIFE",
        "full_name": "SBI Life Insurance Company Limited",
        "aliases": ["SBI Life", "SBILIFE"],
        "sector": "Insurance",
    },
    "State Bank of India": {
        "ticker": "SBIN",
        "full_name": "State Bank of India",
        "aliases": ["SBI", "State Bank of India", "State Bank", "SBIN"],
        "sector": "Banking & Financial Services",
    },
    "Sun Pharma": {
        "ticker": "SUNPHARMA",
        "full_name": "Sun Pharmaceutical Industries Limited",
        "aliases": ["Sun Pharma", "Sun Pharmaceutical", "SUNPHARMA"],
        "sector": "Pharma",
    },
    "Tata Consumer": {
        "ticker": "TATACONSUM",
        "full_name": "Tata Consumer Products Limited",
        "aliases": ["Tata Consumer", "Tata Consumer Products", "TATACONSUM"],
        "sector": "FMCG",
    },
    "Tata Motors": {
        "ticker": "TATAMOTORS",
        "full_name": "Tata Motors Limited",
        "aliases": ["Tata Motors", "JLR", "Jaguar Land Rover", "TATAMOTORS"],
        "sector": "Automobile",
    },
    "Tata Steel": {
        "ticker": "TATASTEEL",
        "full_name": "Tata Steel Limited",
        "aliases": ["Tata Steel", "TATASTEEL"],
        "sector": "Metals & Mining",
    },
    "TCS": {
        "ticker": "TCS",
        "full_name": "Tata Consultancy Services Limited",
        "aliases": ["TCS", "Tata Consultancy Services", "Tata Consultancy"],
        "sector": "IT Services",
    },
    "Tech Mahindra": {
        "ticker": "TECHM",
        "full_name": "Tech Mahindra Limited",
        "aliases": ["Tech Mahindra", "TechM", "TECHM"],
        "sector": "IT Services",
    },
    "Titan": {
        "ticker": "TITAN",
        "full_name": "Titan Company Limited",
        "aliases": ["Titan", "Titan Company", "Tanishq", "TITAN"],
        "sector": "Consumer Goods",
    },
    "UltraTech Cement": {
        "ticker": "ULTRACEMCO",
        "full_name": "UltraTech Cement Limited",
        "aliases": ["UltraTech Cement", "UltraTech", "Ultratech", "ULTRACEMCO"],
        "sector": "Infrastructure & Capital Goods",
    },
    "UPL": {
        "ticker": "UPL",
        "full_name": "UPL Limited",
        "aliases": ["UPL"],
        "sector": "Chemicals",
    },
    "Wipro": {
        "ticker": "WIPRO",
        "full_name": "Wipro Limited",
        "aliases": ["Wipro", "WIPRO"],
        "sector": "IT Services",
    },
}


# ---------------------------------------------------------------------------
# Regex helper — builds a pattern that works for aliases containing special
# characters like & (which breaks \b word-boundary matching).
# ---------------------------------------------------------------------------
def _build_alias_pattern(alias: str) -> re.Pattern:
    """Build a compiled regex for an alias that handles special chars like &.

    Standard ``\\b`` word boundaries don't fire around ``&`` because it is not
    a word character.  For aliases that contain non-word chars we fall back to
    lookarounds that match word-boundary-OR-string-boundary on each side.
    """
    escaped = re.escape(alias)
    has_special = bool(re.search(r"[^\w\s]", alias))
    if has_special:
        # Use lookarounds: preceded by start-of-string or non-alnum,
        # followed by end-of-string or non-alnum.
        pattern = rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])"
    else:
        pattern = rf"\b{escaped}\b"
    return re.compile(pattern, re.IGNORECASE)


class NiftyDictionary:
    """Resolve stock names / aliases and look up sector mappings."""

    def __init__(self, custom_dictionary: Optional[Dict[str, Dict]] = None):
        self.metadata = custom_dictionary or NIFTY_STOCKS_METADATA
        # Pre-compile alias patterns once at init time
        self._alias_patterns: Dict[str, List[tuple[re.Pattern, str]]] = {}
        for canonical, info in self.metadata.items():
            pats = []
            for alias in info["aliases"]:
                pats.append((_build_alias_pattern(alias), alias))
            self._alias_patterns[canonical] = pats

    def get_all_stock_names(self) -> List[str]:
        """Return canonical names of all stocks in dictionary."""
        return list(self.metadata.keys())

    def resolve_stock_name(self, query: str) -> Optional[str]:
        """Resolve an alias, ticker, or partial name to canonical stock name."""
        query_clean = query.strip().lower()
        for canonical, info in self.metadata.items():
            if query_clean == canonical.lower() or query_clean == info["ticker"].lower():
                return canonical
            for alias in info["aliases"]:
                if query_clean == alias.lower():
                    return canonical
        return None

    def get_aliases_for_stock(self, canonical_name: str) -> List[str]:
        """Return aliases for a canonical stock name."""
        if canonical_name in self.metadata:
            return self.metadata[canonical_name]["aliases"]
        return [canonical_name]

    def get_alias_patterns(self, canonical_name: str) -> List[tuple[re.Pattern, str]]:
        """Return pre-compiled (pattern, alias_text) tuples for a stock."""
        return self._alias_patterns.get(canonical_name, [])

    def get_sector_for_stock(self, canonical_name: str) -> str:
        """Return sector for a canonical stock name."""
        if canonical_name in self.metadata:
            return self.metadata[canonical_name].get("sector", "General")
        return "General"
