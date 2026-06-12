from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import NewsArticle
from app.db.session import get_db
from app.ingestion.news_ingestor import NewsIngestor
from app.schemas.news import IngestNewsRequest, NewsArticleRead

router = APIRouter(prefix="/news", tags=["news"])


@router.post("/ingest")
def ingest_news(payload: IngestNewsRequest, db: Session = Depends(get_db)) -> dict[str, int]:
    feeds = [str(feed) for feed in payload.feeds] if payload.feeds else None
    count = NewsIngestor(db).ingest(feeds=feeds, symbols=payload.symbols)
    return {"rows_inserted": count}


@router.get("", response_model=list[NewsArticleRead])
def list_news(limit: int = 50, db: Session = Depends(get_db)) -> list[NewsArticle]:
    stmt = select(NewsArticle).order_by(NewsArticle.published_at.desc().nullslast()).limit(limit)
    return list(db.scalars(stmt))
