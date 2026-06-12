from datetime import date

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1)
    strategy: str = "moving_average"
    parameters: dict = Field(default_factory=lambda: {"short_window": 20, "long_window": 50})
    start: date
    end: date
    initial_cash: float = 100_000.0
    fee_bps: float = 1.0
    slippage_bps: float = 2.0


class BacktestMetricRead(BaseModel):
    total_return: float
    annualized_return: float
    volatility: float
    sharpe: float | None
    sortino: float | None
    max_drawdown: float
    win_rate: float | None
    turnover: float | None
    trade_count: int

    model_config = {"from_attributes": True}


class BacktestRunRead(BaseModel):
    id: int
    asset_universe: list[str]
    start_date: date
    end_date: date
    initial_cash: float
    fee_bps: float
    slippage_bps: float
    status: str
    metrics: BacktestMetricRead | None = None

    model_config = {"from_attributes": True}
