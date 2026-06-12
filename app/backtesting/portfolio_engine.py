from dataclasses import dataclass

import pandas as pd

from app.backtesting.metrics import summarize


@dataclass(frozen=True)
class PortfolioBacktestResult:
    equity: pd.Series
    returns: pd.Series
    target_weights: pd.DataFrame
    turnover: pd.Series
    metrics: dict


class PortfolioBacktestEngine:
    def __init__(self, initial_cash: float = 100_000.0, fee_bps: float = 1.0, slippage_bps: float = 2.0):
        self.initial_cash = initial_cash
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps

    def run(self, prices: pd.DataFrame, target_weights: pd.DataFrame) -> PortfolioBacktestResult:
        if prices.empty:
            raise ValueError("prices cannot be empty")
        aligned_prices, aligned_weights = prices.align(target_weights, join="inner", axis=0)
        aligned_weights = aligned_weights.reindex(columns=aligned_prices.columns).fillna(0.0)
        asset_returns = aligned_prices.pct_change().fillna(0.0)
        turnover = aligned_weights.diff().abs().sum(axis=1).fillna(aligned_weights.abs().sum(axis=1))
        cost = turnover * ((self.fee_bps + self.slippage_bps) / 10_000)
        portfolio_returns = (aligned_weights * asset_returns).sum(axis=1) - cost
        equity = (1 + portfolio_returns).cumprod() * self.initial_cash
        metrics = summarize(equity=equity, returns=portfolio_returns, turnover=turnover)
        return PortfolioBacktestResult(
            equity=equity,
            returns=portfolio_returns,
            target_weights=aligned_weights,
            turnover=turnover,
            metrics=metrics,
        )
