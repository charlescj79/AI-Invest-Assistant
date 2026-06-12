def format_metric_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2%}"


def build_text_report(metrics: dict) -> str:
    return "\n".join(
        [
            f"Total return: {format_metric_percent(metrics.get('total_return'))}",
            f"Annualized return: {format_metric_percent(metrics.get('annualized_return'))}",
            f"Volatility: {format_metric_percent(metrics.get('volatility'))}",
            f"Sharpe: {metrics.get('sharpe')}",
            f"Max drawdown: {format_metric_percent(metrics.get('max_drawdown'))}",
        ]
    )
