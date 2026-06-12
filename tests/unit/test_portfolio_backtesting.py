import pandas as pd

from app.backtesting.portfolio_engine import PortfolioBacktestEngine


def test_portfolio_backtest_generates_equity_and_metrics():
    prices = pd.DataFrame(
        {"A": [100, 101, 102, 103], "B": [100, 99, 101, 102]},
        index=pd.date_range("2024-01-01", periods=4),
    )
    weights = pd.DataFrame(
        {"A": [0.5, 0.5, 0.4, 0.4], "B": [0.5, 0.5, 0.4, 0.4]},
        index=prices.index,
    )

    result = PortfolioBacktestEngine(initial_cash=1000).run(prices, weights)

    assert len(result.equity) == 4
    assert result.metrics["trade_count"] >= 1
    assert "total_return" in result.metrics


def test_portfolio_backtest_costs_reduce_returns():
    prices = pd.DataFrame({"A": [100, 110], "B": [100, 100]}, index=pd.date_range("2024-01-01", periods=2))
    weights = pd.DataFrame({"A": [0, 1], "B": [0, 0]}, index=prices.index)

    no_cost = PortfolioBacktestEngine(initial_cash=1000, fee_bps=0, slippage_bps=0).run(prices, weights)
    with_cost = PortfolioBacktestEngine(initial_cash=1000, fee_bps=10, slippage_bps=10).run(prices, weights)

    assert with_cost.equity.iloc[-1] < no_cost.equity.iloc[-1]
