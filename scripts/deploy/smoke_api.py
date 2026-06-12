import json
import urllib.request

BASE_URL = "http://127.0.0.1:8000"


def request(method: str, path: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode())


def main() -> None:
    print(request("GET", "/health"))
    for symbol in ["GC", "SI", "NQ"]:
        print(request("POST", "/symbols", {"symbol": symbol, "name": f"{symbol} Future", "exchange": "CME", "asset_type": "future", "currency": "USD"}))
    print(request("POST", "/market/ingest", {"symbols": ["GC", "SI", "NQ"], "start": "2023-01-01", "end": "2024-01-31"}))
    payload = {
        "assets": [
            {"symbol": "GC", "min_weight": 0.1, "max_weight": 0.5, "current_weight": 0.3},
            {"symbol": "SI", "min_weight": 0.0, "max_weight": 0.3, "current_weight": 0.1},
            {"symbol": "NQ", "min_weight": 0.2, "max_weight": 0.6, "current_weight": 0.5},
        ],
        "start": "2023-01-01",
        "end": "2024-01-31",
        "initial_cash": 100000,
        "optimization_method": "inverse_volatility",
        "rebalance_strategy": "momentum_filter",
        "momentum_filter_params": {"lookback_days": 63, "rebalance_frequency_days": 20, "allow_cash": True},
    }
    result = request("POST", "/portfolios/backtest", payload)
    print({"run_id": result["run_id"], "metrics": result["metrics"], "risk_metrics": result["risk_metrics"]})


if __name__ == "__main__":
    main()
