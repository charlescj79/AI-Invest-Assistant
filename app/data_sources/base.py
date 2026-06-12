from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class PriceBar:
    symbol: str
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    adjusted_close: float | None
    volume: int | None
    source: str


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    source: str
    published_at: datetime | None
    raw_text: str | None = None
    summary: str | None = None


class MarketDataProvider(ABC):
    source: str

    @abstractmethod
    def get_daily_prices(self, symbols: list[str], start: date, end: date) -> list[PriceBar]:
        raise NotImplementedError

    @abstractmethod
    def get_latest_quote(self, symbol: str) -> PriceBar | None:
        raise NotImplementedError


class NewsProvider(ABC):
    source: str

    @abstractmethod
    def fetch_latest(self, query: str | None = None) -> list[NewsItem]:
        raise NotImplementedError

    @abstractmethod
    def fetch_by_symbol(self, symbol: str) -> list[NewsItem]:
        raise NotImplementedError
