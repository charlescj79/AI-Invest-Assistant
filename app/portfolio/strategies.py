import math

import pandas as pd

from app.portfolio.optimization import project_to_bounds
from app.schemas.portfolio import (
    MADivergenceRebalanceParams,
    PortfolioAssetConstraint,
    PortfolioWeightRecommendation,
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
        min_bounds = pd.Series({item.symbol: item.min_weight for item in constraints}, dtype="float64")
        max_bounds = pd.Series({item.symbol: item.max_weight for item in constraints}, dtype="float64")
        rows = []
        for _, row in desired.iterrows():
            clipped = row.clip(lower=min_bounds, upper=max_bounds)
            if clipped.sum() > 1 or not self.params.allow_cash:
                clipped = project_to_bounds(clipped, min_bounds, max_bounds)
            rows.append(clipped)
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
        recs: list[PortfolioWeightRecommendation] = []
        constraints_by_symbol = {item.symbol: item for item in constraints}
        for symbol in target_weights.columns:
            constraint = constraints_by_symbol[symbol]
            tactical = float(target_weights.loc[latest_date, symbol])
            strategic = float(strategic_weights[symbol])
            current = constraint.current_weight
            latest_close = float(prices.loc[latest_date, symbol])
            ma_value_raw = ma.loc[latest_date, symbol]
            ma_value = None if pd.isna(ma_value_raw) else float(ma_value_raw)
            deviation = None if ma_value in (None, 0) else latest_close / ma_value - 1
            suggested_change = None if current is None else tactical - current
            reason = self._reason(symbol, strategic, tactical, deviation)
            recs.append(
                PortfolioWeightRecommendation(
                    symbol=symbol,
                    min_weight=constraint.min_weight,
                    max_weight=constraint.max_weight,
                    strategic_weight=strategic,
                    tactical_weight=tactical,
                    current_weight=current,
                    suggested_change=suggested_change,
                    latest_close=latest_close,
                    ma_value=ma_value,
                    ma_deviation=deviation,
                    reason=reason,
                )
            )
        return recs

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
            return f"{symbol}: insufficient 200-day moving average data; keep near strategic allocation."
        pct = abs(deviation) * 100
        if deviation > 0:
            return (
                f"{symbol}: price is {pct:.1f}% above the moving-average axis; "
                f"reduce from strategic {strategic:.1%} to tactical {tactical:.1%}."
            )
        if deviation < 0:
            return (
                f"{symbol}: price is {pct:.1f}% below the moving-average axis; "
                f"increase from strategic {strategic:.1%} to tactical {tactical:.1%}."
            )
        return f"{symbol}: price is near the moving-average axis; keep close to strategic allocation."
