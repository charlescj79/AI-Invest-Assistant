from dataclasses import dataclass

import pandas as pd

from app.backtesting.metrics import summarize
from app.strategies.base import Strategy


@dataclass(frozen=True)
class BacktestResult:
    equity: pd.Series
    returns: pd.Series
    target_weights: pd.Series
    metrics: dict


class BacktestEngine:
    def __init__(self, initial_cash: float = 100_000.0, fee_bps: float = 1.0, slippage_bps: float = 2.0):
        self.initial_cash = initial_cash
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps

    def run(self, prices: pd.DataFrame, strategy: Strategy) -> BacktestResult:
        if prices.empty:
            raise ValueError("prices cannot be empty")
        frame = prices.sort_index().copy()
        frame["asset_return"] = frame["close"].pct_change().fillna(0.0)
        target_weights = strategy.generate_signals(frame).clip(lower=0.0, upper=1.0)
        turnover = target_weights.diff().abs().fillna(target_weights.abs())
        cost = turnover * ((self.fee_bps + self.slippage_bps) / 10_000)
        strategy_returns = target_weights.fillna(0.0) * frame["asset_return"] - cost
        equity = (1 + strategy_returns).cumprod() * self.initial_cash
        metrics = summarize(equity=equity, returns=strategy_returns, turnover=turnover)
        return BacktestResult(
            equity=equity,
            returns=strategy_returns,
            target_weights=target_weights,
            metrics=metrics,
        )
