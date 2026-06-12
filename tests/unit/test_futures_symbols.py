from app.data_sources.market.futures import display_symbol, is_supported_futures_symbol, provider_symbol
from app.ingestion.normalize import normalize_symbol


def test_futures_roots_map_to_yfinance_symbols():
    assert provider_symbol("GC") == "GC=F"
    assert provider_symbol("SI") == "SI=F"
    assert provider_symbol("HG") == "HG=F"
    assert provider_symbol("NQ") == "NQ=F"


def test_yfinance_futures_symbols_normalize_back_to_roots():
    assert display_symbol("GC=F") == "GC"
    assert normalize_symbol("nq=f") == "NQ"
    assert is_supported_futures_symbol("HG")
