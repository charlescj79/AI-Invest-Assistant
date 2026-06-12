from app.data_sources.market.yfinance_provider import YFinanceProvider
from app.data_sources.news.rss_provider import RSSNewsProvider


def get_market_provider(name: str = "yfinance"):
    if name == "yfinance":
        return YFinanceProvider()
    raise ValueError(f"Unsupported market provider: {name}")


def get_news_provider(feeds: list[str] | None = None):
    return RSSNewsProvider(feeds=feeds)
