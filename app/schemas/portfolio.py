from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.strategy import BacktestMetricRead


class PortfolioAssetConstraint(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    min_weight: float = Field(ge=0, le=1)
    max_weight: float = Field(ge=0, le=1)
    current_weight: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self):
        self.symbol = self.symbol.strip().upper()
        if self.min_weight > self.max_weight:
            raise ValueError("min_weight must be <= max_weight")
        return self


class PortfolioRequestMixin(BaseModel):
    assets: list[PortfolioAssetConstraint] = Field(..., min_length=2)
    start: date
    end: date

    @model_validator(mode="after")
    def validate_portfolio_request(self):
        if self.start >= self.end:
            raise ValueError("start must be before end")
        total_min = sum(asset.min_weight for asset in self.assets)
        total_max = sum(asset.max_weight for asset in self.assets)
        if total_min > 1 + 1e-9:
            raise ValueError("sum of min_weight cannot exceed 1")
        if total_max < 1 - 1e-9:
            raise ValueError("sum of max_weight must be at least 1")
        return self


class PortfolioOptimizeRequest(PortfolioRequestMixin):
    lookback_days: int = Field(default=252, ge=20)
    method: Literal["inverse_volatility", "mean_variance_simple"] = "inverse_volatility"


class MADivergenceRebalanceParams(BaseModel):
    ma_window: int = Field(default=200, ge=2)
    deviation_step: float = Field(default=0.05, gt=0, le=1)
    adjustment_per_step: float = Field(default=0.10, ge=0, le=1)
    min_multiplier: float = Field(default=0.50, ge=0, le=1)
    max_multiplier: float = Field(default=1.50, ge=1, le=5)
    allow_cash: bool = True


class PortfolioBacktestRequest(PortfolioRequestMixin):
    initial_cash: float = Field(default=100_000.0, gt=0)
    fee_bps: float = Field(default=1.0, ge=0)
    slippage_bps: float = Field(default=2.0, ge=0)
    optimization_method: Literal["inverse_volatility", "mean_variance_simple"] = "inverse_volatility"
    rebalance_strategy: Literal["ma_deviation_200"] = "ma_deviation_200"
    rebalance_params: MADivergenceRebalanceParams = Field(default_factory=MADivergenceRebalanceParams)


class PortfolioWeightRecommendation(BaseModel):
    symbol: str
    min_weight: float
    max_weight: float
    strategic_weight: float
    tactical_weight: float
    current_weight: float | None = None
    suggested_change: float | None = None
    latest_close: float | None = None
    ma_value: float | None = None
    ma_deviation: float | None = None
    reason: str


class PortfolioOptimizeResponse(BaseModel):
    method: str
    weights: list[PortfolioWeightRecommendation]
    diagnostics: dict = Field(default_factory=dict)


class PortfolioBacktestResponse(BaseModel):
    run_id: int | None = None
    metrics: BacktestMetricRead
    recommendations: list[PortfolioWeightRecommendation]
    cash_weight: float
    equity_curve: list[dict]
    latest_target_weights: dict[str, float]
