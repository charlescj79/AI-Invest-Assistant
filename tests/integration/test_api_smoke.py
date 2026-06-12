from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Asset, DailyPrice
from app.db.session import get_db
from app.main import app
from app.schemas.advice import DISCLAIMER, MarketBriefOutput, TradeAdviceOutput


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client, TestingSessionLocal
    finally:
        app.dependency_overrides.clear()


def test_api_smoke_flow_without_external_services(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.advice.generate_market_brief",
        lambda context, as_of=None: MarketBriefOutput(
            summary="Fixture brief",
            key_news=[],
            risk_flags=[],
            sources=[],
            disclaimer=DISCLAIMER,
        ),
    )
    monkeypatch.setattr(
        "app.api.routes.advice.generate_trade_advice",
        lambda symbol, context, as_of=None: TradeAdviceOutput(
            action="watch",
            asset=symbol,
            confidence=0,
            rationale="Fixture advice",
            risks=["Fixture risk"],
            requires_human_confirmation=True,
            disclaimer=DISCLAIMER,
        ),
    )

    test_client, SessionLocal = client

    assert test_client.get("/health").json() == {"status": "ok"}

    created = test_client.post(
        "/symbols",
        json={
            "symbol": "SPY",
            "name": "SPDR S&P 500 ETF Trust",
            "exchange": "NYSEARCA",
            "asset_type": "etf",
            "currency": "USD",
            "sector": "Broad Market",
        },
    )
    assert created.status_code == 200
    assert created.json()["symbol"] == "SPY"

    with SessionLocal() as db:
        asset = db.scalar(select(Asset).where(Asset.symbol == "SPY"))
        assert asset is not None
        start = date(2024, 1, 1)
        for idx in range(90):
            db.add(
                DailyPrice(
                    asset_id=asset.id,
                    date=start + timedelta(days=idx),
                    open=100 + idx,
                    high=101 + idx,
                    low=99 + idx,
                    close=100 + idx,
                    adjusted_close=100 + idx,
                    volume=1_000_000,
                    source="fixture",
                )
            )
        db.commit()

    prices = test_client.get("/market/SPY/prices")
    assert prices.status_code == 200
    assert len(prices.json()) == 90

    backtest = test_client.post(
        "/backtests/run",
        json={
            "symbols": ["SPY"],
            "strategy": "moving_average",
            "parameters": {"short_window": 5, "long_window": 20},
            "start": "2024-01-01",
            "end": "2024-03-31",
            "initial_cash": 100000,
            "fee_bps": 1,
            "slippage_bps": 2,
        },
    )
    assert backtest.status_code == 200
    assert backtest.json()["status"] == "completed"
    assert backtest.json()["metrics"] is not None

    brief = test_client.post("/briefs/daily/generate", json={"symbols": ["SPY"], "date": "2024-03-31"})
    assert brief.status_code == 200
    assert "不构成个性化投资建议" in brief.json()["disclaimer"]

    advice = test_client.post("/advice/generate", json={"symbol": "SPY", "as_of": "2024-03-31"})
    assert advice.status_code == 200
    assert advice.json()["requires_human_confirmation"] is True
    assert advice.json()["status"] == "review_required"
