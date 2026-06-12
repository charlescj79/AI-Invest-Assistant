from datetime import date, timedelta

from app.db.models import Asset
from app.db.session import SessionLocal
from app.ingestion.market_ingestor import MarketIngestor
from app.ingestion.news_ingestor import NewsIngestor
from app.recommendations.market_brief import generate_market_brief


def ingest_market_job() -> int:
    end = date.today()
    start = end - timedelta(days=10)
    with SessionLocal() as db:
        symbols = [asset.symbol for asset in db.query(Asset).filter(Asset.is_active).all()]
        return MarketIngestor(db).ingest(symbols=symbols, start=start, end=end) if symbols else 0


def ingest_news_job() -> int:
    with SessionLocal() as db:
        return NewsIngestor(db).ingest()


def generate_daily_brief_job():
    return generate_market_brief(context={"key_news": [], "sources": []}, as_of=date.today())
