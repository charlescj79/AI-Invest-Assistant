from datetime import datetime

from pydantic import BaseModel, HttpUrl


class NewsArticleRead(BaseModel):
    id: int
    title: str
    url: str
    source: str
    published_at: datetime | None
    summary: str | None
    sentiment: str | None
    relevance_score: float | None

    model_config = {"from_attributes": True}


class IngestNewsRequest(BaseModel):
    feeds: list[HttpUrl] | None = None
    symbols: list[str] | None = None
