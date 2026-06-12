import math

import pandas as pd

from app.portfolio.optimization import project_to_bounds
from app.schemas.portfolio import (
    FixedRebalanceParams,
    MADivergenceRebalanceParams,
    MomentumFilterParams,
    PortfolioAssetConstraint,
    PortfolioWeightRecommendation,
    VolatilityTargetParams,
)


def _bounds(constraints: list[PortfolioAssetConstraint]) -> tuple[pd.Series, pd.Series]:
    min_bounds = pd.Series({item.symbol: item.min_weight for item in constraints}, dtype="float64")
    max_bounds = pd.Series({item.symbol: item.max_weight for item in constraints}, dtype="float64")
    return min_bounds, max_bounds


def _apply_bounds(row: pd.Series, constraints: list[PortfolioAssetConstraint], allow_cash: bool) -> pd.Series:
    min_bounds, max_bounds = _bounds(constraints)
    clipped = row.clip(lower=min_bounds, upper=max_bounds)
    if clipped.sum() > 1 or not allow_cash:
        return project_to_bounds(clipped, min_bounds, max_bounds)
    return clipped


class FixedRebalanceStrategy:
    def __init__(self, params: FixedRebalanceParams) -> None:
        self.params = params

    def generate_target_weights(
        self,
        prices: pd.DataFrame,
        strategic_weights: pd.Series,
        constraints: list[PortfolioAssetConstraint],
    ) -> pd.DataFrame:
        rows = []
        last = strategic_weights.copy()
        for idx, _ in enumerate(prices.index):
            if idx % self.params.rebalance_frequency_days == 0:
                last = _apply_bounds(strategic_weights.copy(), constraints, self.params.allow_cash)
            rows.append(last.copy())
        return pd.DataFrame(rows, index=prices.index, columns=prices.columns).fillna(0.0)

    def latest_recommendations(self, prices, strategic_weights, target_weights, constraints):
        return _generic_recommendations(
            prices,
            strategic_weights,
            target_weights,
            constraints,
            "Fixed-ratio periodic rebalance target.",
        )


class MomentumFilterStrategy:
    def __init__(self, params: MomentumFilterParams) -> None:
        self.params = params

    def generate_target_weights(
        self,
        prices: pd.DataFrame,
        strategic_weights: pd.Series,
        constraints: list[PortfolioAssetConstraint],
    ) -> pd.DataFrame:
        momentum = prices.pct_change(self.params.lookback_days).shift(1)
        rows = []
        last = strategic_weights.copy()
        for idx, row in enumerate(momentum.iterrows()):
            _, values = row
            if idx % self.params.rebalance_frequency_days == 0:
                multipliers = values.apply(
                    lambda value: self.params.positive_momentum_multiplier
                    if pd.notna(value) and value >= 0
                    else self.params.negative_momentum_multiplier
                )
                desired = strategic_weights.mul(multipliers).fillna(strategic_weights)
                last = _apply_bounds(desired, constraints, self.params.allow_cash)
            rows.append(last.copy())
        return pd.DataFrame(rows, index=prices.index, columns=prices.columns).fillna(0.0)

    def latest_recommendations(self, prices, strategic_weights, target_weights, constraints):
        lookback_returns = prices.pct_change(self.params.lookback_days).iloc[-1]
        reasons = {
            symbol: (
                f"Momentum over {self.params.lookback_days} days is {value:.1%}; "
                f"{'keep/increase exposure' if value >= 0 else 'reduce exposure'}."
            )
            for symbol, value in lookback_returns.items()
        }
        return _generic_recommendations(prices, strategic_weights, target_weights, constraints, reasons)


class VolatilityTargetStrategy:
    def __init__(self, params: VolatilityTargetParams) -> None:
        self.params = params

    def generate_target_weights(
        self,
        prices: pd.DataFrame,
        strategic_weights: pd.Series,
        constraints: list[PortfolioAssetConstraint],
    ) -> pd.DataFrame:
        returns = prices.pct_change().fillna(0.0)
        portfolio_returns = returns.mul(strategic_weights, axis=1).sum(axis=1)
        realized_vol = portfolio_returns.rolling(self.params.lookback_days).std().shift(1) * math.sqrt(252)
        rows = []
        for vol in realized_vol:
            if pd.isna(vol) or vol <= 0:
                scale = 1.0
            else:
                scale = self.params.target_annual_volatility / vol
            scale = min(self.params.max_scale, max(self.params.min_scale, scale))
            desired = strategic_weights * scale
            rows.append(_apply_bounds(desired, constraints, self.params.allow_cash))
        return pd.DataFrame(rows, index=prices.index, columns=prices.columns).fillna(0.0)

    def latest_recommendations(self, prices, strategic_weights, target_weights, constraints):
        return _generic_recommendations(
            prices,
            strategic_weights,
            target_weights,
            constraints,
            f"Volatility-target strategy adjusts exposure toward {self.params.target_annual_volatility:.1%} annualized volatility.",
        )


class MovingAverageDeviationRebalanceStrategy:
    def __init__(self, params: MADivergenceRebalanceParams) -> None:
        self.params = params

    def generate_target_weights(
        self,
        prices: pd.DataFrame,
        strategic_weights: pd.Series,
        constraints: list[PortfolioAssetConstraint],
    ) -> pd.DataFrame:
        ma = prices.rolling(self.params.ma_window, min_periods=self.params.ma_window).mean()
        deviation = (prices / ma - 1).shift(1)
        multipliers = deviation.map(self._multiplier)
        desired = multipliers.mul(strategic_weights, axis=1).fillna(strategic_weights)
        rows = [_apply_bounds(row, constraints, self.params.allow_cash) for _, row in desired.iterrows()]
        return pd.DataFrame(rows, index=desired.index, columns=desired.columns).fillna(0.0)

    def latest_recommendations(
        self,
        prices: pd.DataFrame,
        strategic_weights: pd.Series,
        target_weights: pd.DataFrame,
        constraints: list[PortfolioAssetConstraint],
    ) -> list[PortfolioWeightRecommendation]:
        ma = prices.rolling(self.params.ma_window, min_periods=self.params.ma_window).mean()
        latest_date = target_weights.dropna(how="all").index[-1]
        reasons = {}
        for symbol in target_weights.columns:
            latest_close = float(prices.loc[latest_date, symbol])
            ma_value_raw = ma.loc[latest_date, symbol]
            ma_value = None if pd.isna(ma_value_raw) else float(ma_value_raw)
            deviation = None if ma_value in (None, 0) else latest_close / ma_value - 1
            reasons[symbol] = self._reason(symbol, float(strategic_weights[symbol]), float(target_weights.loc[latest_date, symbol]), deviation)
        return _generic_recommendations(prices, strategic_weights, target_weights, constraints, reasons, ma, self.params.ma_window)

    def _multiplier(self, deviation: float) -> float:
        if pd.isna(deviation):
            return 1.0
        levels = math.floor(abs(float(deviation)) / self.params.deviation_step)
        if deviation > 0:
            return max(self.params.min_multiplier, 1 - levels * self.params.adjustment_per_step)
        if deviation < 0:
            return min(self.params.max_multiplier, 1 + levels * self.params.adjustment_per_step)
        return 1.0

    def _reason(self, symbol: str, strategic: float, tactical: float, deviation: float | None) -> str:
        if deviation is None:
            return f"{symbol}: insufficient moving-average data; keep near strategic allocation."
        pct = abs(deviation) * 100
        if deviation > 0:
            return f"{symbol}: price is {pct:.1f}% above the moving-average axis; reduce from strategic {strategic:.1%} to tactical {tactical:.1%}."
        if deviation < 0:
            return f"{symbol}: price is {pct:.1f}% below the moving-average axis; increase from strategic {strategic:.1%} to tactical {tactical:.1%}."
        return f"{symbol}: price is near the moving-average axis; keep close to strategic allocation."


def build_portfolio_strategy(name: str, payload):
    if name == "ma_deviation_200":
        return MovingAverageDeviationRebalanceStrategy(payload.rebalance_params)
    if name == "fixed_rebalance":
        return FixedRebalanceStrategy(payload.fixed_rebalance_params)
    if name == "momentum_filter":
        return MomentumFilterStrategy(payload.momentum_filter_params)
    if name == "volatility_target":
        return VolatilityTargetStrategy(payload.volatility_target_params)
    raise ValueError(f"Unsupported portfolio strategy: {name}")


def _generic_recommendations(
    prices: pd.DataFrame,
    strategic_weights: pd.Series,
    target_weights: pd.DataFrame,
    constraints: list[PortfolioAssetConstraint],
    reasons,
    moving_average: pd.DataFrame | None = None,
    ma_window: int | None = None,
) -> list[PortfolioWeightRecommendation]:
    latest_date = target_weights.dropna(how="all").index[-1]
    constraints_by_symbol = {item.symbol: item for item in constraints}
    recs = []
    for symbol in target_weights.columns:
        constraint = constraints_by_symbol[symbol]
        latest_close = float(prices.loc[latest_date, symbol])
        ma_value = None
        deviation = None
        if moving_average is not None:
            raw = moving_average.loc[latest_date, symbol]
            ma_value = None if pd.isna(raw) else float(raw)
            deviation = None if ma_value in (None, 0) else latest_close / ma_value - 1
        reason = reasons.get(symbol) if isinstance(reasons, dict) else reasons
        recs.append(
            PortfolioWeightRecommendation(
                symbol=symbol,
                min_weight=constraint.min_weight,
                max_weight=constraint.max_weight,
                strategic_weight=float(strategic_weights[symbol]),
                tactical_weight=float(target_weights.loc[latest_date, symbol]),
                current_weight=constraint.current_weight,
                suggested_change=None if constraint.current_weight is None else float(target_weights.loc[latest_date, symbol]) - constraint.current_weight,
                latest_close=latest_close,
                ma_value=ma_value,
                ma_deviation=deviation,
                reason=reason or "Portfolio strategy target allocation.",
            )
        )
    return recs
