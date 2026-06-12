from datetime import date, datetime

from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    name: str | None = None
    exchange: str | None = None
    asset_type: str = "stock"
    currency: str = "USD"
    sector: str | None = None


class AssetRead(BaseModel):
    id: int
    symbol: str
    name: str | None
    exchange: str | None
    asset_type: str
    currency: str
    sector: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class DailyPriceRead(BaseModel):
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    adjusted_close: float | None
    volume: int | None
    source: str
    ingested_at: datetime

    model_config = {"from_attributes": True}


class IngestMarketRequest(BaseModel):
    symbols: list[str] | None = None
    start: date | None = None
    end: date | None = None
