import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtesting.portfolio_engine import PortfolioBacktestEngine
from app.db.models import BacktestMetric, BacktestRun, StrategyDefinition
from app.db.session import get_db
from app.portfolio.data import PortfolioDataError, load_close_price_matrix
from app.portfolio.optimization import PortfolioOptimizationError, optimize_portfolio
from app.portfolio.strategies import MovingAverageDeviationRebalanceStrategy
from app.schemas.portfolio import (
    PortfolioBacktestRequest,
    PortfolioBacktestResponse,
    PortfolioOptimizeRequest,
    PortfolioOptimizeResponse,
    PortfolioWeightRecommendation,
)
from app.schemas.strategy import BacktestMetricRead

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("/optimize", response_model=PortfolioOptimizeResponse)
def optimize_portfolio_endpoint(
    payload: PortfolioOptimizeRequest,
    db: Session = Depends(get_db),
) -> PortfolioOptimizeResponse:
    try:
        prices = load_close_price_matrix(
            db,
            [asset.symbol for asset in payload.assets],
            payload.start,
            payload.end,
        )
        weights, diagnostics = optimize_portfolio(
            prices=prices,
            constraints=payload.assets,
            method=payload.method,
            lookback_days=payload.lookback_days,
        )
    except (PortfolioDataError, PortfolioOptimizationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    recommendations = [
        PortfolioWeightRecommendation(
            symbol=asset.symbol,
            min_weight=asset.min_weight,
            max_weight=asset.max_weight,
            strategic_weight=float(weights[asset.symbol]),
            tactical_weight=float(weights[asset.symbol]),
            current_weight=asset.current_weight,
            suggested_change=None if asset.current_weight is None else float(weights[asset.symbol]) - asset.current_weight,
            latest_close=float(prices[asset.symbol].iloc[-1]),
            reason="Strategic allocation recommended by inverse-volatility or simple mean-variance optimizer.",
        )
        for asset in payload.assets
    ]
    return PortfolioOptimizeResponse(method=payload.method, weights=recommendations, diagnostics=diagnostics)


@router.post("/backtest", response_model=PortfolioBacktestResponse)
def backtest_portfolio_endpoint(
    payload: PortfolioBacktestRequest,
    db: Session = Depends(get_db),
) -> PortfolioBacktestResponse:
    try:
        prices = load_close_price_matrix(
            db,
            [asset.symbol for asset in payload.assets],
            payload.start,
            payload.end,
        )
        if len(prices) < payload.rebalance_params.ma_window + 2:
            raise PortfolioDataError(
                f"At least {payload.rebalance_params.ma_window + 2} aligned price rows are required "
                "for moving-average rebalance backtests"
            )
        strategic_weights, diagnostics = optimize_portfolio(
            prices=prices,
            constraints=payload.assets,
            method=payload.optimization_method,
            lookback_days=min(252, max(20, len(prices) - 1)),
        )
        strategy = MovingAverageDeviationRebalanceStrategy(payload.rebalance_params)
        target_weights = strategy.generate_target_weights(prices, strategic_weights, payload.assets)
        result = PortfolioBacktestEngine(
            initial_cash=payload.initial_cash,
            fee_bps=payload.fee_bps,
            slippage_bps=payload.slippage_bps,
        ).run(prices, target_weights)
    except (PortfolioDataError, PortfolioOptimizationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    strategy_def = _get_or_create_strategy(db, payload, diagnostics)
    run = BacktestRun(
        strategy_id=strategy_def.id,
        asset_universe=[asset.symbol for asset in payload.assets],
        start_date=payload.start,
        end_date=payload.end,
        initial_cash=payload.initial_cash,
        fee_bps=payload.fee_bps,
        slippage_bps=payload.slippage_bps,
        status="completed",
    )
    db.add(run)
    db.flush()
    metric = BacktestMetric(backtest_run_id=run.id, **result.metrics)
    db.add(metric)
    db.commit()
    db.refresh(run)
    db.refresh(metric)

    recommendations = strategy.latest_recommendations(prices, strategic_weights, result.target_weights, payload.assets)
    latest_weights = {symbol: float(value) for symbol, value in result.target_weights.iloc[-1].items()}
    cash_weight = max(0.0, 1.0 - sum(latest_weights.values()))
    equity_curve = [
        {"date": idx.date().isoformat() if hasattr(idx, "date") else str(idx), "equity": float(value)}
        for idx, value in result.equity.items()
    ]
    return PortfolioBacktestResponse(
        run_id=run.id,
        metrics=BacktestMetricRead.model_validate(metric),
        recommendations=recommendations,
        cash_weight=cash_weight,
        equity_curve=equity_curve,
        latest_target_weights=latest_weights,
    )


def _get_or_create_strategy(db: Session, payload: PortfolioBacktestRequest, diagnostics: dict) -> StrategyDefinition:
    parameters = payload.model_dump(mode="json")
    parameters["diagnostics"] = diagnostics
    strategy_name = f"portfolio:{payload.optimization_method}:{payload.rebalance_strategy}:{payload.rebalance_params.model_dump_json()}"
    strategy_def = db.scalar(select(StrategyDefinition).where(StrategyDefinition.name == strategy_name))
    if strategy_def is not None:
        return strategy_def
    strategy_def = StrategyDefinition(
        name=strategy_name,
        strategy_type="portfolio_ma_deviation",
        parameters_json=parameters,
    )
    db.add(strategy_def)
    db.flush()
    return strategy_def
