from pydantic import BaseModel, Field


class StrategyReviewOutput(BaseModel):
    ranking: list[dict] = Field(default_factory=list)
    best_strategy_id: int | None = None
    metric_comparison: dict = Field(default_factory=dict)
    overfitting_warnings: list[str] = Field(default_factory=list)
    recommended_use_case: str | None = None
