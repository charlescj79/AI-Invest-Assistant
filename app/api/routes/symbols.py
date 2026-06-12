from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset
from app.db.session import get_db
from app.schemas.market import AssetCreate, AssetRead

router = APIRouter(prefix="/symbols", tags=["symbols"])


@router.post("", response_model=AssetRead)
def upsert_symbol(payload: AssetCreate, db: Session = Depends(get_db)) -> Asset:
    symbol = payload.symbol.upper().strip()
    asset = db.scalar(select(Asset).where(Asset.symbol == symbol))
    if asset is None:
        asset = Asset(symbol=symbol)
        db.add(asset)
    asset.name = payload.name
    asset.exchange = payload.exchange
    asset.asset_type = payload.asset_type
    asset.currency = payload.currency
    asset.sector = payload.sector
    asset.is_active = True
    db.commit()
    db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetRead])
def list_symbols(db: Session = Depends(get_db)) -> list[Asset]:
    return list(db.scalars(select(Asset).order_by(Asset.symbol)))


@router.get("/{symbol}", response_model=AssetRead)
def get_symbol(symbol: str, db: Session = Depends(get_db)) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.symbol == symbol.upper()))
    if asset is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return asset
