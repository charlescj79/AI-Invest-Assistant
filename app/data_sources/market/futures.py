FUTURES_ROOT_TO_YFINANCE = {
    "GC": "GC=F",  # Gold futures
    "SI": "SI=F",  # Silver futures
    "HG": "HG=F",  # Copper futures
    "NQ": "NQ=F",  # Nasdaq 100 E-mini futures
}

FUTURES_ROOT_NAMES = {
    "GC": "Gold Futures",
    "SI": "Silver Futures",
    "HG": "Copper Futures",
    "NQ": "Nasdaq 100 E-mini Futures",
}


def normalize_futures_root(symbol: str) -> str:
    normalized = symbol.strip().upper()
    return normalized[:-2] if normalized.endswith("=F") else normalized


def provider_symbol(symbol: str) -> str:
    root = normalize_futures_root(symbol)
    return FUTURES_ROOT_TO_YFINANCE.get(root, symbol.strip().upper())


def display_symbol(symbol: str) -> str:
    root = normalize_futures_root(symbol)
    if root in FUTURES_ROOT_TO_YFINANCE:
        return root
    for futures_root, yf_symbol in FUTURES_ROOT_TO_YFINANCE.items():
        if symbol.strip().upper() == yf_symbol:
            return futures_root
    return symbol.strip().upper()


def is_supported_futures_symbol(symbol: str) -> bool:
    return normalize_futures_root(symbol) in FUTURES_ROOT_TO_YFINANCE
