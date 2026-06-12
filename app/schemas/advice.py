from datetime import date as Date, datetime
from typing import Literal

from pydantic import BaseModel, Field


DISCLAIMER = (
    "该内容仅用于研究和决策辅助，不构成个性化投资建议或收益承诺。"
    "历史回测不代表未来表现，市场价格可能快速变化并导致本金损失。"
    "任何交易决策都需要用户结合自身风险承受能力进行人工复核和确认。"
)


class GenerateBriefRequest(BaseModel):
    date: Date | None = None
    symbols: list[str] | None = None


class GenerateAdviceRequest(BaseModel):
    symbol: str
    as_of: Date | None = None


class MarketBriefOutput(BaseModel):
    summary: str
    key_news: list[dict] = Field(default_factory=list)
    market_regime: str | None = None
    watchlist_impacts: list[dict] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER


class TradeAdviceOutput(BaseModel):
    action: Literal["buy", "sell", "hold", "watch"]
    asset: str
    confidence: float = Field(ge=0, le=1)
    rationale: str
    supporting_data: list[dict] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    invalidating_conditions: list[str] = Field(default_factory=list)
    suggested_position_limit: float | None = Field(default=None, ge=0, le=1)
    requires_human_confirmation: bool = True
    disclaimer: str = DISCLAIMER


class TradeRecommendationRead(BaseModel):
    id: int
    action: str
    suggested_position_change: float | None
    rationale: str
    risk_assessment: str
    evidence: list[dict]
    requires_human_confirmation: bool
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
