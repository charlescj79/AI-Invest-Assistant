from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Asset, AssetType, DailyPrice
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
        with TestingSessionLocal() as db:
            _seed_prices(db)
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_portfolio_optimize_and_backtest(client):
    payload = {
        "assets": [
            {"symbol": "GC", "min_weight": 0.1, "max_weight": 0.5, "current_weight": 0.3},
            {"symbol": "SI", "min_weight": 0.0, "max_weight": 0.3, "current_weight": 0.1},
            {"symbol": "NQ", "min_weight": 0.2, "max_weight": 0.6, "current_weight": 0.5},
        ],
        "start": "2023-01-01",
        "end": "2023-10-31",
        "lookback_days": 120,
        "method": "inverse_volatility",
    }

    optimized = client.post("/portfolios/optimize", json=payload)
    assert optimized.status_code == 200
    weights = optimized.json()["weights"]
    assert sum(item["strategic_weight"] for item in weights) == pytest.approx(1.0)
    assert all(item["min_weight"] <= item["strategic_weight"] <= item["max_weight"] for item in weights)

    backtest_payload = {
        **{key: value for key, value in payload.items() if key not in {"method", "lookback_days"}},
        "initial_cash": 100000,
        "fee_bps": 1,
        "slippage_bps": 2,
        "optimization_method": "inverse_volatility",
        "rebalance_strategy": "ma_deviation_200",
        "rebalance_params": {
            "ma_window": 20,
            "deviation_step": 0.05,
            "adjustment_per_step": 0.1,
            "min_multiplier": 0.5,
            "max_multiplier": 1.5,
            "allow_cash": True,
        },
    }
    backtest = client.post("/portfolios/backtest", json=backtest_payload)
    assert backtest.status_code == 200
    body = backtest.json()
    assert body["run_id"] is not None
    assert body["metrics"] is not None
    assert body["risk_metrics"]["correlation_matrix"]
    assert body["risk_metrics"]["max_concentration"] >= 0
    assert len(body["recommendations"]) == 3
    assert body["recommendations"][0]["contract_multiplier"] is not None
    assert body["recommendations"][0]["margin_requirement"] is not None
    assert body["latest_target_weights"]
    assert body["equity_curve"]


def test_portfolio_backtest_supports_additional_strategies(client):
    base_payload = {
        "assets": [
            {"symbol": "GC", "min_weight": 0.1, "max_weight": 0.5, "current_weight": 0.3},
            {"symbol": "SI", "min_weight": 0.0, "max_weight": 0.3, "current_weight": 0.1},
            {"symbol": "NQ", "min_weight": 0.2, "max_weight": 0.6, "current_weight": 0.5},
        ],
        "start": "2023-01-01",
        "end": "2023-10-31",
        "initial_cash": 100000,
        "optimization_method": "inverse_volatility",
    }
    for strategy in ["fixed_rebalance", "momentum_filter", "volatility_target"]:
        response = client.post("/portfolios/backtest", json={**base_payload, "rebalance_strategy": strategy})
        assert response.status_code == 200
        assert response.json()["run_id"] is not None


    response = client.post(
        "/portfolios/optimize",
        json={
            "assets": [
                {"symbol": "GC", "min_weight": 0.1, "max_weight": 0.8},
                {"symbol": "MISSING", "min_weight": 0.1, "max_weight": 0.8},
            ],
            "start": "2023-01-01",
            "end": "2023-10-31",
        },
    )
    assert response.status_code == 400


def _seed_prices(db):
    symbols = ["GC", "SI", "NQ"]
    assets = []
    for symbol in symbols:
        asset = Asset(symbol=symbol, name=f"{symbol} fixture", asset_type=AssetType.FUTURE, currency="USD")
        db.add(asset)
        assets.append(asset)
    db.flush()
    start = date(2023, 1, 1)
    for idx in range(260):
        for asset_idx, asset in enumerate(assets):
            base = 100 + asset_idx * 10
            trend = idx * (0.05 + asset_idx * 0.02)
            wave = ((idx % 20) - 10) * (asset_idx + 1) * 0.1
            close = base + trend + wave
            db.add(
                DailyPrice(
                    asset_id=asset.id,
                    date=start + timedelta(days=idx),
                    open=close - 0.5,
                    high=close + 1,
                    low=close - 1,
                    close=close,
                    adjusted_close=close,
                    volume=1_000_000,
                    source="fixture",
                )
            )
    db.commit()
