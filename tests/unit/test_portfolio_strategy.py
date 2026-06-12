import pandas as pd

from app.portfolio.strategies import MovingAverageDeviationRebalanceStrategy
from app.schemas.portfolio import MADivergenceRebalanceParams, PortfolioAssetConstraint


def test_ma_deviation_strategy_reduces_above_ma_and_increases_below_ma():
    index = pd.date_range("2024-01-01", periods=10)
    prices = pd.DataFrame(
        {
            "ABOVE": [100, 100, 100, 100, 100, 100, 100, 130, 130, 130],
            "BELOW": [100, 100, 100, 100, 100, 100, 100, 70, 70, 70],
        },
        index=index,
    )
    constraints = [
        PortfolioAssetConstraint(symbol="ABOVE", min_weight=0.1, max_weight=0.9),
        PortfolioAssetConstraint(symbol="BELOW", min_weight=0.1, max_weight=0.9),
    ]
    strategic = pd.Series({"ABOVE": 0.5, "BELOW": 0.5})
    strategy = MovingAverageDeviationRebalanceStrategy(
        MADivergenceRebalanceParams(ma_window=3, deviation_step=0.05, adjustment_per_step=0.1)
    )

    weights = strategy.generate_target_weights(prices, strategic, constraints)

    assert weights.iloc[-1]["ABOVE"] < 0.5
    assert weights.iloc[-1]["BELOW"] > 0.5


def test_ma_deviation_strategy_uses_shift_to_avoid_same_day_signal():
    index = pd.date_range("2024-01-01", periods=5)
    prices = pd.DataFrame({"A": [100, 100, 100, 100, 150], "B": [100, 100, 100, 100, 100]}, index=index)
    constraints = [
        PortfolioAssetConstraint(symbol="A", min_weight=0.0, max_weight=1.0),
        PortfolioAssetConstraint(symbol="B", min_weight=0.0, max_weight=1.0),
    ]
    strategic = pd.Series({"A": 0.5, "B": 0.5})
    strategy = MovingAverageDeviationRebalanceStrategy(
        MADivergenceRebalanceParams(ma_window=3, deviation_step=0.05, adjustment_per_step=0.1)
    )

    weights = strategy.generate_target_weights(prices, strategic, constraints)

    assert weights.iloc[-1]["A"] == 0.5
