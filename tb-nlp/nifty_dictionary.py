from typing import Dict, List, Optional

# Master NIFTY stock metadata mapping
NIFTY_STOCKS_METADATA: Dict[str, Dict[str, any]] = {
    "Reliance": {
        "ticker": "RELIANCE",
        "full_name": "Reliance Industries Limited",
        "aliases": ["Reliance", "RIL", "Reliance Industries", "Jio", "Reliance Retail"],
        "sector": "Energy & Retail"
    },
    "TCS": {
        "ticker": "TCS",
        "full_name": "Tata Consultancy Services Limited",
        "aliases": ["TCS", "Tata Consultancy Services", "Tata Consultancy"],
        "sector": "IT Services"
    },
    "Infosys": {
        "ticker": "INFY",
        "full_name": "Infosys Limited",
        "aliases": ["Infosys", "Infy"],
        "sector": "IT Services"
    },
    "HDFC Bank": {
        "ticker": "HDFCBANK",
        "full_name": "HDFC Bank Limited",
        "aliases": ["HDFC Bank", "HDFC", "HDFC Corp"],
        "sector": "Banking & Financial Services"
    },
    "ICICI Bank": {
        "ticker": "ICICIBANK",
        "full_name": "ICICI Bank Limited",
        "aliases": ["ICICI Bank", "ICICI"],
        "sector": "Banking & Financial Services"
    },
    "ITC": {
        "ticker": "ITC",
        "full_name": "ITC Limited",
        "aliases": ["ITC", "ITC Ltd"],
        "sector": "FMCG"
    },
    "L&T": {
        "ticker": "LT",
        "full_name": "Larsen & Toubro Limited",
        "aliases": ["L&T", "Larsen & Toubro", "Larsen and Toubro", "Larsen"],
        "sector": "Infrastructure & Capital Goods"
    },
    "UltraTech Cement": {
        "ticker": "ULTRACEMCO",
        "full_name": "UltraTech Cement Limited",
        "aliases": ["UltraTech Cement", "UltraTech", "Ultratech"],
        "sector": "Infrastructure & Capital Goods"
    },
    "State Bank of India": {
        "ticker": "SBIN",
        "full_name": "State Bank of India",
        "aliases": ["SBI", "State Bank of India", "State Bank"],
        "sector": "Banking & Financial Services"
    },
    "Tata Motors": {
        "ticker": "TATAMOTORS",
        "full_name": "Tata Motors Limited",
        "aliases": ["Tata Motors", "TaMo", "JLR", "Jaguar Land Rover"],
        "sector": "Automobile"
    },
    "Maruti Suzuki": {
        "ticker": "MARUTI",
        "full_name": "Maruti Suzuki India Limited",
        "aliases": ["Maruti", "Maruti Suzuki"],
        "sector": "Automobile"
    },
    "Bharti Airtel": {
        "ticker": "BHARTIARTL",
        "full_name": "Bharti Airtel Limited",
        "aliases": ["Airtel", "Bharti Airtel"],
        "sector": "Telecom"
    },
}


class NiftyDictionary:
    """Helper for resolving stock names, aliases, and sector mappings."""

    def __init__(self, custom_dictionary: Optional[Dict[str, Dict[str, any]]] = None):
        self.metadata = custom_dictionary or NIFTY_STOCKS_METADATA

    def get_all_stock_names(self) -> List[str]:
        """Return canonical names of all stocks in dictionary."""
        return list(self.metadata.keys())

    def resolve_stock_name(self, query: str) -> Optional[str]:
        """Resolve an alias or partial name to canonical stock name."""
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

    def get_sector_for_stock(self, canonical_name: str) -> str:
        """Return sector for a canonical stock name."""
        if canonical_name in self.metadata:
            return self.metadata[canonical_name].get("sector", "General")
        return "General"
