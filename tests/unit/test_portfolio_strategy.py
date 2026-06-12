import pandas as pd

from app.portfolio.strategies import (
    FixedRebalanceStrategy,
    MomentumFilterStrategy,
    MovingAverageDeviationRebalanceStrategy,
    VolatilityTargetStrategy,
)
from app.schemas.portfolio import (
    FixedRebalanceParams,
    MADivergenceRebalanceParams,
    MomentumFilterParams,
    PortfolioAssetConstraint,
    VolatilityTargetParams,
)


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


def test_fixed_rebalance_strategy_keeps_strategic_weights():
    index = pd.date_range("2024-01-01", periods=5)
    prices = pd.DataFrame({"A": [100, 101, 102, 103, 104], "B": [100, 99, 98, 97, 96]}, index=index)
    constraints = [
        PortfolioAssetConstraint(symbol="A", min_weight=0.0, max_weight=1.0),
        PortfolioAssetConstraint(symbol="B", min_weight=0.0, max_weight=1.0),
    ]
    strategic = pd.Series({"A": 0.6, "B": 0.4})

    weights = FixedRebalanceStrategy(FixedRebalanceParams(rebalance_frequency_days=2)).generate_target_weights(
        prices, strategic, constraints
    )

    assert weights.iloc[-1]["A"] == 0.6
    assert weights.iloc[-1]["B"] == 0.4


def test_momentum_filter_reduces_negative_momentum_asset():
    index = pd.date_range("2024-01-01", periods=8)
    prices = pd.DataFrame({"UP": [100, 101, 102, 103, 104, 105, 106, 107], "DOWN": [100, 99, 98, 97, 96, 95, 94, 93]}, index=index)
    constraints = [
        PortfolioAssetConstraint(symbol="UP", min_weight=0.0, max_weight=1.0),
        PortfolioAssetConstraint(symbol="DOWN", min_weight=0.0, max_weight=1.0),
    ]
    strategic = pd.Series({"UP": 0.5, "DOWN": 0.5})
    strategy = MomentumFilterStrategy(
        MomentumFilterParams(lookback_days=5, rebalance_frequency_days=1, negative_momentum_multiplier=0.25)
    )

    weights = strategy.generate_target_weights(prices, strategic, constraints)

    assert weights.iloc[-1]["DOWN"] < 0.5
    assert weights.iloc[-1]["UP"] == 0.5


def test_volatility_target_scales_down_high_volatility_portfolio():
    index = pd.date_range("2024-01-01", periods=80)
    prices = pd.DataFrame(
        {
            "A": [100 + ((-1) ** idx) * idx for idx in range(80)],
            "B": [100 + idx * 0.1 for idx in range(80)],
        },
        index=index,
    ).abs()
    constraints = [
        PortfolioAssetConstraint(symbol="A", min_weight=0.0, max_weight=1.0),
        PortfolioAssetConstraint(symbol="B", min_weight=0.0, max_weight=1.0),
    ]
    strategic = pd.Series({"A": 0.5, "B": 0.5})
    strategy = VolatilityTargetStrategy(VolatilityTargetParams(lookback_days=20, target_annual_volatility=0.05))

    weights = strategy.generate_target_weights(prices, strategic, constraints)

    assert weights.iloc[-1].sum() < 1.0
