from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Invest Assistant"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./invest_assistant.db"
    anthropic_api_key: str | None = None
    claude_model: str = "claude-opus-4-8"
    default_market_source: str = "yfinance"
    default_news_feeds: str = Field(
        default="https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY"
    )
    scheduler_enabled: bool = False

    @property
    def news_feed_urls(self) -> list[str]:
        return [url.strip() for url in self.default_news_feeds.split(",") if url.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
