from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class AssetType(StrEnum):
    STOCK = "stock"
    ETF = "etf"
    INDEX = "index"
    FUTURE = "future"


class RecommendationStatus(StrEnum):
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(32), default=AssetType.STOCK)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    prices: Mapped[list["DailyPrice"]] = relationship(back_populates="asset")
    news_links: Mapped[list["NewsAssetLink"]] = relationship(back_populates="asset")


class DailyPrice(Base):
    __tablename__ = "daily_prices"
    __table_args__ = (UniqueConstraint("asset_id", "date", "source", name="uq_daily_price"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    close: Mapped[float] = mapped_column(Float)
    adjusted_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="yfinance")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    asset: Mapped[Asset] = relationship(back_populates="prices")


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(Text, unique=True)
    source: Mapped[str] = mapped_column(String(128))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dedupe_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    asset_links: Mapped[list["NewsAssetLink"]] = relationship(back_populates="news")


class NewsAssetLink(Base):
    __tablename__ = "news_asset_links"
    __table_args__ = (UniqueConstraint("news_id", "asset_id", name="uq_news_asset"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    news_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    news: Mapped[NewsArticle] = relationship(back_populates="asset_links")
    asset: Mapped[Asset] = relationship(back_populates="news_links")


class StrategyDefinition(Base):
    __tablename__ = "strategy_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    strategy_type: Mapped[str] = mapped_column(String(64))
    parameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_definitions.id"), nullable=True)
    asset_universe: Mapped[list[str]] = mapped_column(JSON, default=list)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    initial_cash: Mapped[float] = mapped_column(Float, default=100_000.0)
    fee_bps: Mapped[float] = mapped_column(Float, default=1.0)
    slippage_bps: Mapped[float] = mapped_column(Float, default=2.0)
    status: Mapped[str] = mapped_column(String(32), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    metrics: Mapped["BacktestMetric | None"] = relationship(back_populates="run")


class BacktestMetric(Base):
    __tablename__ = "backtest_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    backtest_run_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), unique=True)
    total_return: Mapped[float] = mapped_column(Float)
    annualized_return: Mapped[float] = mapped_column(Float)
    volatility: Mapped[float] = mapped_column(Float)
    sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    sortino: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float] = mapped_column(Float)
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)

    run: Mapped[BacktestRun] = relationship(back_populates="metrics")


class TradeSignal(Base):
    __tablename__ = "trade_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_definitions.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    signal: Mapped[str] = mapped_column(String(32))
    target_weight: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class DailyBrief(Base):
    __tablename__ = "daily_briefs"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True)
    market_summary: Mapped[str] = mapped_column(Text)
    key_news: Mapped[list[dict]] = mapped_column(JSON, default=list)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    llm_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TradeRecommendation(Base):
    __tablename__ = "trade_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(32))
    suggested_position_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    rationale: Mapped[str] = mapped_column(Text)
    risk_assessment: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[dict]] = mapped_column(JSON, default=list)
    requires_human_confirmation: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default=RecommendationStatus.REVIEW_REQUIRED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
