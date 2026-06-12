from dataclasses import dataclass


@dataclass(frozen=True)
class FuturesContractSpec:
    root: str
    provider_symbol: str
    name: str
    exchange: str
    contract_multiplier: float
    margin_rate: float
    typical_roll_cost_bps: float


FUTURES_SPECS = {
    "GC": FuturesContractSpec("GC", "GC=F", "Gold Futures", "COMEX", 100.0, 0.08, 5.0),
    "SI": FuturesContractSpec("SI", "SI=F", "Silver Futures", "COMEX", 5_000.0, 0.10, 7.0),
    "HG": FuturesContractSpec("HG", "HG=F", "Copper Futures", "COMEX", 25_000.0, 0.10, 7.0),
    "NQ": FuturesContractSpec("NQ", "NQ=F", "Nasdaq 100 E-mini Futures", "CME", 20.0, 0.07, 6.0),
}

FUTURES_ROOT_TO_YFINANCE = {root: spec.provider_symbol for root, spec in FUTURES_SPECS.items()}
FUTURES_ROOT_NAMES = {root: spec.name for root, spec in FUTURES_SPECS.items()}


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


def get_futures_spec(symbol: str) -> FuturesContractSpec | None:
    return FUTURES_SPECS.get(normalize_futures_root(symbol))
