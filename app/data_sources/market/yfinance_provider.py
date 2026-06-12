from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from app.data_sources.base import MarketDataProvider, PriceBar
from app.data_sources.market.futures import display_symbol, provider_symbol


class YFinanceProvider(MarketDataProvider):
    source = "yfinance"

    def get_daily_prices(self, symbols: list[str], start: date, end: date) -> list[PriceBar]:
        bars: list[PriceBar] = []
        for symbol in symbols:
            ticker_symbol = provider_symbol(symbol)
            ticker = yf.Ticker(ticker_symbol)
            frame = ticker.history(start=start.isoformat(), end=(end + timedelta(days=1)).isoformat())
            if frame.empty:
                continue
            bars.extend(self._frame_to_bars(display_symbol(symbol), frame))
        return bars

    def get_latest_quote(self, symbol: str) -> PriceBar | None:
        end = date.today()
        bars = self.get_daily_prices([symbol], start=end - timedelta(days=7), end=end)
        return bars[-1] if bars else None

    def _frame_to_bars(self, symbol: str, frame: pd.DataFrame) -> list[PriceBar]:
        normalized = frame.reset_index()
        result: list[PriceBar] = []
        for row in normalized.to_dict("records"):
            dt = row.get("Date")
            if dt is None:
                continue
            result.append(
                PriceBar(
                    symbol=symbol.upper(),
                    date=dt.date() if hasattr(dt, "date") else pd.to_datetime(dt).date(),
                    open=_clean_float(row.get("Open")),
                    high=_clean_float(row.get("High")),
                    low=_clean_float(row.get("Low")),
                    close=float(row["Close"]),
                    adjusted_close=_clean_float(row.get("Close")),
                    volume=_clean_int(row.get("Volume")),
                    source=self.source,
                )
            )
        return result


def _clean_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _clean_int(value) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)
