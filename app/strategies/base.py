from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    name: str

    @abstractmethod
    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        """Return target weights indexed by date. Signals must use only historical data."""
        raise NotImplementedError
