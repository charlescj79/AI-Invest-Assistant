import pandas as pd

from app.analytics.indicators import rsi
from app.strategies.base import Strategy


class RSIMeanReversionStrategy(Strategy):
    name = "rsi"

    def __init__(self, window: int = 14, buy_below: float = 30, sell_above: float = 70) -> None:
        self.window = window
        self.buy_below = buy_below
        self.sell_above = sell_above

    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        values = rsi(prices["close"], self.window)
        target = pd.Series(index=prices.index, data=0.0)
        target[values < self.buy_below] = 1.0
        target[values > self.sell_above] = 0.0
        return target.ffill().shift(1).fillna(0.0)
