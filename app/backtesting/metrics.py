import numpy as np
import pandas as pd

TRADING_DAYS = 252


def total_return(equity: pd.Series) -> float:
    if equity.empty or equity.iloc[0] == 0:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1)


def annualized_return(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] == 0:
        return 0.0
    years = len(equity) / TRADING_DAYS
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)


def annualized_volatility(returns: pd.Series) -> float:
    return float(returns.std(ddof=0) * np.sqrt(TRADING_DAYS)) if not returns.empty else 0.0


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float | None:
    excess = returns - risk_free_rate / TRADING_DAYS
    vol = excess.std(ddof=0)
    if vol == 0 or np.isnan(vol):
        return None
    return float(excess.mean() / vol * np.sqrt(TRADING_DAYS))


def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float | None:
    excess = returns - risk_free_rate / TRADING_DAYS
    downside = excess[excess < 0]
    downside_vol = downside.std(ddof=0)
    if downside_vol == 0 or np.isnan(downside_vol):
        return None
    return float(excess.mean() / downside_vol * np.sqrt(TRADING_DAYS))


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    return float(drawdown.min())


def win_rate(returns: pd.Series) -> float | None:
    non_zero = returns[returns != 0]
    if non_zero.empty:
        return None
    return float((non_zero > 0).mean())


def summarize(equity: pd.Series, returns: pd.Series, turnover: pd.Series) -> dict:
    return {
        "total_return": total_return(equity),
        "annualized_return": annualized_return(equity),
        "volatility": annualized_volatility(returns),
        "sharpe": sharpe_ratio(returns),
        "sortino": sortino_ratio(returns),
        "max_drawdown": max_drawdown(equity),
        "win_rate": win_rate(returns),
        "turnover": float(turnover.sum()) if not turnover.empty else 0.0,
        "trade_count": int((turnover > 0).sum()),
    }
