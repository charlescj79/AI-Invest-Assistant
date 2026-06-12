def score_strategy(metrics: dict) -> float:
    annual_return = metrics.get("annualized_return") or 0.0
    sharpe = metrics.get("sharpe") or 0.0
    max_drawdown = abs(metrics.get("max_drawdown") or 0.0)
    turnover = metrics.get("turnover") or 0.0
    return 0.30 * annual_return + 0.25 * sharpe - 0.25 * max_drawdown - 0.10 * turnover


def rank_strategies(results: list[dict]) -> list[dict]:
    enriched = [{**result, "score": score_strategy(result.get("metrics", {}))} for result in results]
    return sorted(enriched, key=lambda item: item["score"], reverse=True)
