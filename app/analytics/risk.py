from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class RiskCheckResult:
    passed: bool
    flags: list[str]


def check_price_history(prices: pd.DataFrame, as_of: date | None = None) -> RiskCheckResult:
    flags: list[str] = []
    if prices.empty:
        return RiskCheckResult(False, ["No price history is available."])
    if len(prices) < 120:
        flags.append("Less than 120 trading days of history are available.")
    returns = prices["close"].pct_change().dropna()
    if not returns.empty and returns.tail(30).std() * (252**0.5) > 0.6:
        flags.append("Recent annualized volatility is above 60%.")
    latest_date = prices.index.max()
    if as_of and hasattr(latest_date, "date"):
        latest_date = latest_date.date()
    if as_of and latest_date < as_of:
        flags.append("Latest available price is older than the requested analysis date.")
    return RiskCheckResult(passed=not flags, flags=flags)
