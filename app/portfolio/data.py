from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, DailyPrice
from app.ingestion.normalize import normalize_symbol


class PortfolioDataError(ValueError):
    pass


def load_close_price_matrix(db: Session, symbols: list[str], start: date, end: date) -> pd.DataFrame:
    frames: list[pd.Series] = []
    normalized_symbols = [normalize_symbol(symbol) for symbol in symbols]
    for symbol in normalized_symbols:
        asset = db.scalar(select(Asset).where(Asset.symbol == symbol))
        if asset is None:
            raise PortfolioDataError(f"Symbol not found: {symbol}")
        rows = list(
            db.scalars(
                select(DailyPrice)
                .where(DailyPrice.asset_id == asset.id)
                .where(DailyPrice.date >= start)
                .where(DailyPrice.date <= end)
                .order_by(DailyPrice.date)
            )
        )
        if not rows:
            raise PortfolioDataError(f"No price data available for {symbol}")
        series = pd.Series(
            data=[row.adjusted_close or row.close for row in rows],
            index=pd.to_datetime([row.date for row in rows]),
            name=symbol,
            dtype="float64",
        )
        frames.append(series)
    matrix = pd.concat(frames, axis=1, join="inner").dropna()
    if matrix.empty:
        raise PortfolioDataError("No overlapping price history is available for the requested symbols")
    return matrix
