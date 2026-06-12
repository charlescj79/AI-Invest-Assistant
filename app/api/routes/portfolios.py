from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtesting.portfolio_engine import PortfolioBacktestEngine
from app.data_sources.market.futures import get_futures_spec
from app.db.models import BacktestMetric, BacktestRun, StrategyDefinition
from app.db.session import get_db
from app.portfolio.data import PortfolioDataError, load_close_price_matrix
from app.portfolio.optimization import PortfolioOptimizationError, optimize_portfolio
from app.portfolio.risk import portfolio_risk_metrics
from app.portfolio.strategies import build_portfolio_strategy
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
        _with_futures_exposure(
            PortfolioWeightRecommendation(
                symbol=asset.symbol,
                min_weight=asset.min_weight,
                max_weight=asset.max_weight,
                strategic_weight=float(weights[asset.symbol]),
                tactical_weight=float(weights[asset.symbol]),
                current_weight=asset.current_weight,
                suggested_change=None
                if asset.current_weight is None
                else float(weights[asset.symbol]) - asset.current_weight,
                latest_close=float(prices[asset.symbol].iloc[-1]),
                reason="Strategic allocation recommended by inverse-volatility or simple mean-variance optimizer.",
            ),
            portfolio_value=100_000.0,
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
        _validate_strategy_history(prices, payload)
        strategic_weights, diagnostics = optimize_portfolio(
            prices=prices,
            constraints=payload.assets,
            method=payload.optimization_method,
            lookback_days=min(252, max(20, len(prices) - 1)),
        )
        strategy = build_portfolio_strategy(payload.rebalance_strategy, payload)
        target_weights = strategy.generate_target_weights(prices, strategic_weights, payload.assets)
        result = PortfolioBacktestEngine(
            initial_cash=payload.initial_cash,
            fee_bps=payload.fee_bps,
            slippage_bps=payload.slippage_bps,
            roll_cost_bps=payload.roll_cost_bps,
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

    latest_weights = {symbol: float(value) for symbol, value in result.target_weights.iloc[-1].items()}
    risk_metrics = portfolio_risk_metrics(prices, result.target_weights.iloc[-1])
    recommendations = [
        _with_futures_exposure(rec, portfolio_value=float(result.equity.iloc[-1]))
        for rec in strategy.latest_recommendations(prices, strategic_weights, result.target_weights, payload.assets)
    ]
    cash_weight = max(0.0, 1.0 - sum(latest_weights.values()))
    equity_curve = [
        {"date": idx.date().isoformat() if hasattr(idx, "date") else str(idx), "equity": float(value)}
        for idx, value in result.equity.items()
    ]
    return PortfolioBacktestResponse(
        run_id=run.id,
        metrics=BacktestMetricRead.model_validate(metric),
        risk_metrics=risk_metrics,
        recommendations=recommendations,
        cash_weight=cash_weight,
        equity_curve=equity_curve,
        latest_target_weights=latest_weights,
    )


def _validate_strategy_history(prices, payload: PortfolioBacktestRequest) -> None:
    required_rows = 2
    if payload.rebalance_strategy == "ma_deviation_200":
        required_rows = payload.rebalance_params.ma_window + 2
    elif payload.rebalance_strategy == "momentum_filter":
        required_rows = payload.momentum_filter_params.lookback_days + 2
    elif payload.rebalance_strategy == "volatility_target":
        required_rows = payload.volatility_target_params.lookback_days + 2
    if len(prices) < required_rows:
        raise PortfolioDataError(
            f"At least {required_rows} aligned price rows are required for {payload.rebalance_strategy}"
        )


def _get_or_create_strategy(db: Session, payload: PortfolioBacktestRequest, diagnostics: dict) -> StrategyDefinition:
    parameters = payload.model_dump(mode="json")
    parameters["diagnostics"] = diagnostics
    strategy_name = f"portfolio:{payload.optimization_method}:{payload.rebalance_strategy}:{_strategy_param_key(payload)}"
    strategy_def = db.scalar(select(StrategyDefinition).where(StrategyDefinition.name == strategy_name))
    if strategy_def is not None:
        return strategy_def
    strategy_def = StrategyDefinition(
        name=strategy_name,
        strategy_type=f"portfolio_{payload.rebalance_strategy}",
        parameters_json=parameters,
    )
    db.add(strategy_def)
    db.flush()
    return strategy_def


def _strategy_param_key(payload: PortfolioBacktestRequest) -> str:
    if payload.rebalance_strategy == "ma_deviation_200":
        return payload.rebalance_params.model_dump_json()
    if payload.rebalance_strategy == "fixed_rebalance":
        return payload.fixed_rebalance_params.model_dump_json()
    if payload.rebalance_strategy == "momentum_filter":
        return payload.momentum_filter_params.model_dump_json()
    if payload.rebalance_strategy == "volatility_target":
        return payload.volatility_target_params.model_dump_json()
    return "{}"


def _with_futures_exposure(
    recommendation: PortfolioWeightRecommendation,
    portfolio_value: float,
) -> PortfolioWeightRecommendation:
    spec = get_futures_spec(recommendation.symbol)
    if spec is None or recommendation.latest_close is None:
        return recommendation
    notional = portfolio_value * recommendation.tactical_weight
    margin_requirement = notional * spec.margin_rate
    updated = recommendation.model_copy(
        update={
            "contract_multiplier": spec.contract_multiplier,
            "margin_rate": spec.margin_rate,
            "notional_exposure": notional,
            "margin_requirement": margin_requirement,
        }
    )
    return updated
