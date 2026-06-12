import pandas as pd

from app.strategies.base import Strategy


class MomentumStrategy(Strategy):
    name = "momentum"

    def __init__(self, lookback: int = 63) -> None:
        self.lookback = lookback

    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        returns = prices["close"].pct_change(self.lookback)
        return (returns > 0).astype(float).shift(1).fillna(0.0)
