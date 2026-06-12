import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtesting.engine import BacktestEngine
from app.db.models import Asset, BacktestMetric, BacktestRun, DailyPrice, StrategyDefinition
from app.db.session import get_db
from app.schemas.strategy import BacktestRequest, BacktestRunRead
from app.strategies import build_strategy

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("/run", response_model=BacktestRunRead)
def run_backtest(payload: BacktestRequest, db: Session = Depends(get_db)) -> BacktestRun:
    if len(payload.symbols) != 1:
        raise HTTPException(status_code=400, detail="MVP backtests currently support one symbol per run")
    symbol = payload.symbols[0].upper()
    asset = db.scalar(select(Asset).where(Asset.symbol == symbol))
    if asset is None:
        raise HTTPException(status_code=404, detail="Symbol not found")

    prices = list(
        db.scalars(
            select(DailyPrice)
            .where(DailyPrice.asset_id == asset.id)
            .where(DailyPrice.date >= payload.start)
            .where(DailyPrice.date <= payload.end)
            .order_by(DailyPrice.date)
        )
    )
    if not prices:
        raise HTTPException(status_code=400, detail="No price data available for requested range")

    frame = pd.DataFrame(
        [{"date": row.date, "close": row.adjusted_close or row.close} for row in prices]
    ).set_index("date")

    strategy = build_strategy(payload.strategy, payload.parameters)
    engine = BacktestEngine(
        initial_cash=payload.initial_cash,
        fee_bps=payload.fee_bps,
        slippage_bps=payload.slippage_bps,
    )
    result = engine.run(frame, strategy)

    strategy_name = f"{payload.strategy}:{payload.parameters}"
    strategy_def = db.scalar(select(StrategyDefinition).where(StrategyDefinition.name == strategy_name))
    if strategy_def is None:
        strategy_def = StrategyDefinition(
            name=strategy_name,
            strategy_type=payload.strategy,
            parameters_json=payload.parameters,
        )
        db.add(strategy_def)
        db.flush()
    run = BacktestRun(
        strategy_id=strategy_def.id,
        asset_universe=[symbol],
        start_date=payload.start,
        end_date=payload.end,
        initial_cash=payload.initial_cash,
        fee_bps=payload.fee_bps,
        slippage_bps=payload.slippage_bps,
        status="completed",
    )
    db.add(run)
    db.flush()
    db.add(BacktestMetric(backtest_run_id=run.id, **result.metrics))
    db.commit()
    db.refresh(run)
    return run


@router.get("/{run_id}", response_model=BacktestRunRead)
def get_backtest(run_id: int, db: Session = Depends(get_db)) -> BacktestRun:
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return run
