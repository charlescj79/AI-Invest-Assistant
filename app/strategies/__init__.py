from app.strategies.momentum import MomentumStrategy
from app.strategies.moving_average import MovingAverageCrossStrategy
from app.strategies.rsi import RSIMeanReversionStrategy


def build_strategy(name: str, parameters: dict):
    if name == "moving_average":
        return MovingAverageCrossStrategy(**parameters)
    if name == "momentum":
        return MomentumStrategy(**parameters)
    if name == "rsi":
        return RSIMeanReversionStrategy(**parameters)
    raise ValueError(f"Unsupported strategy: {name}")
