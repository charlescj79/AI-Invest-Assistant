import pandas as pd

from app.portfolio.risk import portfolio_risk_metrics


def test_portfolio_risk_metrics_include_correlation_var_cvar_and_concentration():
    prices = pd.DataFrame(
        {
            "A": [100, 101, 99, 102, 98, 103],
            "B": [100, 100.5, 101, 100, 102, 101],
        }
    )
    weights = pd.Series({"A": 0.7, "B": 0.2})

    metrics = portfolio_risk_metrics(prices, weights)

    assert "correlation_matrix" in metrics
    assert metrics["var_95"] is not None
    assert metrics["cvar_95"] is not None
    assert metrics["max_concentration"] == 0.7
    assert metrics["max_concentration_symbol"] == "A"
