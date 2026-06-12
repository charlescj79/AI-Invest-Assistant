from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, DailyPrice
from app.db.session import get_db
from app.ingestion.market_ingestor import MarketIngestor
from app.schemas.market import DailyPriceRead, IngestMarketRequest

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/ingest")
def ingest_market(payload: IngestMarketRequest, db: Session = Depends(get_db)) -> dict[str, int]:
    symbols = payload.symbols or [asset.symbol for asset in db.scalars(select(Asset).where(Asset.is_active))]
    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols provided or configured")
    end = payload.end or date.today()
    start = payload.start or (end - timedelta(days=365 * 2))
    count = MarketIngestor(db).ingest(symbols=symbols, start=start, end=end)
    return {"rows_upserted": count}


@router.get("/{symbol}/prices", response_model=list[DailyPriceRead])
def get_prices(symbol: str, db: Session = Depends(get_db)) -> list[DailyPrice]:
    asset = db.scalar(select(Asset).where(Asset.symbol == symbol.upper()))
    if asset is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    stmt = select(DailyPrice).where(DailyPrice.asset_id == asset.id).order_by(DailyPrice.date)
    return list(db.scalars(stmt))
