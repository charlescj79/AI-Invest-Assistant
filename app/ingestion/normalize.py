from app.data_sources.market.futures import display_symbol


def normalize_symbol(symbol: str) -> str:
    return display_symbol(symbol)
