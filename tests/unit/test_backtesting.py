import pandas as pd

from app.backtesting.engine import BacktestEngine
from app.strategies.moving_average import MovingAverageCrossStrategy


def test_backtest_runs_without_lookahead_crash():
    prices = pd.DataFrame(
        {"close": [100, 101, 102, 103, 104, 105, 106]},
        index=pd.date_range("2024-01-01", periods=7, freq="D"),
    )
    strategy = MovingAverageCrossStrategy(short_window=2, long_window=3)
    result = BacktestEngine(initial_cash=1000).run(prices, strategy)

    assert result.equity.iloc[0] > 0
    assert "total_return" in result.metrics
    assert result.target_weights.iloc[0] == 0
