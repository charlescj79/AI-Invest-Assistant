from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.data_sources.registry import get_market_provider
from app.data_sources.market.futures import FUTURES_ROOT_NAMES, is_supported_futures_symbol
from app.db.models import Asset, AssetType, DailyPrice
from app.ingestion.normalize import normalize_symbol


class MarketIngestor:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.provider = get_market_provider(get_settings().default_market_source)

    def ingest(self, symbols: list[str], start: date, end: date) -> int:
        normalized = [normalize_symbol(symbol) for symbol in symbols]
        bars = self.provider.get_daily_prices(normalized, start=start, end=end)
        count = 0
        for bar in bars:
            asset = self._get_or_create_asset(bar.symbol)
            stmt = insert(DailyPrice).values(
                asset_id=asset.id,
                date=bar.date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                adjusted_close=bar.adjusted_close,
                volume=bar.volume,
                source=bar.source,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["asset_id", "date", "source"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "adjusted_close": stmt.excluded.adjusted_close,
                    "volume": stmt.excluded.volume,
                },
            )
            self.db.execute(stmt)
            count += 1
        self.db.commit()
        return count

    def _get_or_create_asset(self, symbol: str) -> Asset:
        asset = self.db.scalar(select(Asset).where(Asset.symbol == symbol))
        if asset is not None:
            return asset
        asset_type = AssetType.FUTURE if is_supported_futures_symbol(symbol) else AssetType.STOCK
        asset = Asset(
            symbol=symbol,
            name=FUTURES_ROOT_NAMES.get(symbol),
            asset_type=asset_type,
            currency="USD",
        )
        self.db.add(asset)
        self.db.flush()
        return asset
