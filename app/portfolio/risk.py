import numpy as np
import pandas as pd


def correlation_matrix(prices: pd.DataFrame) -> dict:
    returns = prices.pct_change().dropna()
    if returns.empty:
        return {}
    return returns.corr().round(4).to_dict()


def portfolio_risk_metrics(
    prices: pd.DataFrame,
    weights: pd.Series,
    confidence: float = 0.95,
) -> dict:
    returns = prices.pct_change().dropna()
    if returns.empty:
        return {
            "correlation_matrix": {},
            "var_95": None,
            "cvar_95": None,
            "max_concentration": float(weights.max()) if not weights.empty else 0.0,
            "max_concentration_symbol": weights.idxmax() if not weights.empty else None,
        }
    aligned_weights = weights.reindex(returns.columns).fillna(0.0)
    portfolio_returns = returns.mul(aligned_weights, axis=1).sum(axis=1)
    alpha = 1 - confidence
    var = float(np.quantile(portfolio_returns, alpha))
    tail = portfolio_returns[portfolio_returns <= var]
    cvar = float(tail.mean()) if not tail.empty else var
    max_symbol = aligned_weights.idxmax() if not aligned_weights.empty else None
    return {
        "correlation_matrix": correlation_matrix(prices),
        "var_95": var,
        "cvar_95": cvar,
        "max_concentration": float(aligned_weights.max()) if not aligned_weights.empty else 0.0,
        "max_concentration_symbol": max_symbol,
    }
