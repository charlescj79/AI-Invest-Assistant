import pandas as pd
import pytest

from app.portfolio.optimization import PortfolioOptimizationError, inverse_volatility_weights, project_to_bounds
from app.schemas.portfolio import PortfolioAssetConstraint


def test_inverse_volatility_weights_respect_bounds_and_sum_to_one():
    prices = pd.DataFrame(
        {
            "LOW": [100, 101, 102, 103, 104, 105],
            "HIGH": [100, 110, 95, 115, 90, 120],
        }
    )
    constraints = [
        PortfolioAssetConstraint(symbol="LOW", min_weight=0.2, max_weight=0.8),
        PortfolioAssetConstraint(symbol="HIGH", min_weight=0.2, max_weight=0.8),
    ]

    weights, diagnostics = inverse_volatility_weights(prices, constraints, lookback_days=5)

    assert weights.sum() == pytest.approx(1.0)
    assert 0.2 <= weights["LOW"] <= 0.8
    assert 0.2 <= weights["HIGH"] <= 0.8
    assert weights["LOW"] > weights["HIGH"]
    assert "volatility" in diagnostics


def test_project_to_bounds_rejects_infeasible_bounds():
    raw = pd.Series({"A": 0.5, "B": 0.5})
    min_bounds = pd.Series({"A": 0.8, "B": 0.3})
    max_bounds = pd.Series({"A": 0.9, "B": 0.5})

    with pytest.raises(PortfolioOptimizationError):
        project_to_bounds(raw, min_bounds, max_bounds)
