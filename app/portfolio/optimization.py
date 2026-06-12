import math

import pandas as pd

from app.schemas.portfolio import PortfolioAssetConstraint


class PortfolioOptimizationError(ValueError):
    pass


def validate_bounds(constraints: list[PortfolioAssetConstraint]) -> None:
    total_min = sum(item.min_weight for item in constraints)
    total_max = sum(item.max_weight for item in constraints)
    if total_min > 1 + 1e-9:
        raise PortfolioOptimizationError("sum of min_weight cannot exceed 1")
    if total_max < 1 - 1e-9:
        raise PortfolioOptimizationError("sum of max_weight must be at least 1")


def project_to_bounds(
    raw_weights: pd.Series,
    min_bounds: pd.Series,
    max_bounds: pd.Series,
    target_sum: float = 1.0,
    tolerance: float = 1e-9,
) -> pd.Series:
    if min_bounds.sum() > target_sum + tolerance:
        raise PortfolioOptimizationError("Minimum weights exceed target sum")
    if max_bounds.sum() < target_sum - tolerance:
        raise PortfolioOptimizationError("Maximum weights are below target sum")

    weights = raw_weights.reindex(min_bounds.index).fillna(0.0).clip(lower=min_bounds, upper=max_bounds)
    for _ in range(100):
        gap = target_sum - float(weights.sum())
        if abs(gap) <= tolerance:
            return weights
        if gap > 0:
            capacity = (max_bounds - weights).clip(lower=0)
            capacity_sum = float(capacity.sum())
            if capacity_sum <= tolerance:
                break
            weights = weights + capacity / capacity_sum * gap
            weights = weights.clip(lower=min_bounds, upper=max_bounds)
        else:
            reducible = (weights - min_bounds).clip(lower=0)
            reducible_sum = float(reducible.sum())
            if reducible_sum <= tolerance:
                break
            weights = weights + reducible / reducible_sum * gap
            weights = weights.clip(lower=min_bounds, upper=max_bounds)
    if abs(float(weights.sum()) - target_sum) > 1e-6:
        raise PortfolioOptimizationError("Unable to project weights into requested bounds")
    return weights


def _constraint_series(constraints: list[PortfolioAssetConstraint]) -> tuple[pd.Series, pd.Series]:
    symbols = [item.symbol for item in constraints]
    min_bounds = pd.Series([item.min_weight for item in constraints], index=symbols, dtype="float64")
    max_bounds = pd.Series([item.max_weight for item in constraints], index=symbols, dtype="float64")
    return min_bounds, max_bounds


def inverse_volatility_weights(
    prices: pd.DataFrame,
    constraints: list[PortfolioAssetConstraint],
    lookback_days: int = 252,
) -> tuple[pd.Series, dict]:
    validate_bounds(constraints)
    returns = prices.pct_change().dropna().tail(lookback_days)
    if returns.empty:
        raise PortfolioOptimizationError("Not enough price history to compute returns")
    volatility = returns.std(ddof=0) * math.sqrt(252)
    safe_volatility = volatility.replace(0, pd.NA).fillna(volatility[volatility > 0].median())
    if safe_volatility.isna().any() or (safe_volatility <= 0).all():
        raw = pd.Series(1.0, index=prices.columns, dtype="float64")
    else:
        raw = 1 / safe_volatility.clip(lower=1e-9)
    raw = raw / raw.sum()
    min_bounds, max_bounds = _constraint_series(constraints)
    weights = project_to_bounds(raw, min_bounds, max_bounds)
    diagnostics = {
        "lookback_days_used": int(len(returns)),
        "volatility": volatility.to_dict(),
        "raw_weights": raw.to_dict(),
        "projected_weights": weights.to_dict(),
    }
    return weights, diagnostics


def mean_variance_simple_weights(
    prices: pd.DataFrame,
    constraints: list[PortfolioAssetConstraint],
    lookback_days: int = 252,
) -> tuple[pd.Series, dict]:
    validate_bounds(constraints)
    returns = prices.pct_change().dropna().tail(lookback_days)
    if returns.empty:
        raise PortfolioOptimizationError("Not enough price history to compute returns")
    mean_returns = returns.mean() * 252
    variance = returns.var(ddof=0) * 252
    score = mean_returns.clip(lower=0) / variance.replace(0, pd.NA)
    if score.isna().all() or score.sum() <= 0:
        return inverse_volatility_weights(prices, constraints, lookback_days)
    raw = score.fillna(0) / score.fillna(0).sum()
    min_bounds, max_bounds = _constraint_series(constraints)
    weights = project_to_bounds(raw, min_bounds, max_bounds)
    diagnostics = {
        "lookback_days_used": int(len(returns)),
        "mean_returns": mean_returns.to_dict(),
        "variance": variance.to_dict(),
        "raw_weights": raw.to_dict(),
        "projected_weights": weights.to_dict(),
    }
    return weights, diagnostics


def optimize_portfolio(
    prices: pd.DataFrame,
    constraints: list[PortfolioAssetConstraint],
    method: str = "inverse_volatility",
    lookback_days: int = 252,
) -> tuple[pd.Series, dict]:
    if method == "inverse_volatility":
        return inverse_volatility_weights(prices, constraints, lookback_days)
    if method == "mean_variance_simple":
        return mean_variance_simple_weights(prices, constraints, lookback_days)
    raise PortfolioOptimizationError(f"Unsupported optimization method: {method}")
