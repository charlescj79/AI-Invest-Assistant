import pandas as pd

from app.analytics.indicators import moving_average
from app.strategies.base import Strategy


class MovingAverageCrossStrategy(Strategy):
    name = "moving_average"

    def __init__(self, short_window: int = 20, long_window: int = 50) -> None:
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window")
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        close = prices["close"]
        short_ma = moving_average(close, self.short_window)
        long_ma = moving_average(close, self.long_window)
        raw = (short_ma > long_ma).astype(float)
        return raw.shift(1).fillna(0.0)
