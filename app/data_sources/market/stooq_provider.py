from datetime import date

from app.data_sources.base import MarketDataProvider, PriceBar


class StooqProvider(MarketDataProvider):
    source = "stooq"

    def get_daily_prices(self, symbols: list[str], start: date, end: date) -> list[PriceBar]:
        raise NotImplementedError("Stooq provider is reserved as a backup data source.")

    def get_latest_quote(self, symbol: str) -> PriceBar | None:
        raise NotImplementedError("Stooq provider is reserved as a backup data source.")
