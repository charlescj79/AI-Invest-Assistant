# AI Invest Assistant

AI Invest Assistant is a research-oriented investment assistant for US stocks, ETFs, and selected futures. It collects market data and news, runs simple strategy backtests, and generates Claude-assisted market briefs and trade suggestions for human review.

> This project is for research and decision support only. It does not place trades and does not provide guaranteed returns or personalized financial advice.

## MVP Scope

- US stocks, ETFs, and selected futures
- Web/API first via FastAPI
- Free data sources first: `yfinance` and RSS feeds
- Futures roots supported in MVP: `GC` gold, `SI` silver, `HG` copper, `NQ` Nasdaq 100 E-mini. These map to Yahoo Finance tickers `GC=F`, `SI=F`, `HG=F`, and `NQ=F` during ingestion.
- Daily OHLCV ingestion
- News ingestion and deduplication
- Basic strategies and daily backtesting
- Claude structured outputs for market briefs and trade suggestions
- Deterministic risk gate and mandatory human confirmation

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs>.

## Local Docker

```bash
cp .env.example .env
docker compose up --build
```

- API: <http://127.0.0.1:8000/docs>
- Streamlit UI: <http://127.0.0.1:8501>

The Compose stack stores SQLite data in the `invest_data` Docker volume.

## Streamlit UI Without Docker

Run the API in one terminal:

```bash
python -m uvicorn app.main:app --reload
```

Run the UI in another terminal:

```bash
API_BASE_URL=http://127.0.0.1:8000 python -m streamlit run app/ui/streamlit_app.py
```

## Example Flow

1. Add watchlist symbols: `SPY`, `QQQ`, `AAPL`, `MSFT`, `NVDA`, and futures roots such as `GC`, `SI`, `HG`, `NQ`.
2. Run market ingestion for historical daily bars.
3. Run a backtest.
4. Generate a daily brief or trade suggestion.
5. Review the risk flags and approve/reject manually.

## Portfolio Optimization

The MVP includes portfolio allocation and backtesting for multiple assets such as `GC`, `SI`, and `NQ`.

### Strategic Weight Recommendation

Use `POST /portfolios/optimize` to recommend strategic weights from user-defined bounds. The default method is inverse volatility:

```json
{
  "assets": [
    {"symbol": "GC", "min_weight": 0.10, "max_weight": 0.50, "current_weight": 0.30},
    {"symbol": "SI", "min_weight": 0.00, "max_weight": 0.30, "current_weight": 0.10},
    {"symbol": "NQ", "min_weight": 0.20, "max_weight": 0.60, "current_weight": 0.50}
  ],
  "start": "2023-01-01",
  "end": "2026-06-12",
  "lookback_days": 252,
  "method": "inverse_volatility"
}
```

### 200-Day Moving Average Rebalance

Use `POST /portfolios/backtest` to apply a 200-day moving-average deviation strategy. Above the moving average, the system gradually lowers tactical allocation; below it, the system gradually raises tactical allocation.

```json
{
  "assets": [
    {"symbol": "GC", "min_weight": 0.10, "max_weight": 0.50, "current_weight": 0.30},
    {"symbol": "SI", "min_weight": 0.00, "max_weight": 0.30, "current_weight": 0.10},
    {"symbol": "NQ", "min_weight": 0.20, "max_weight": 0.60, "current_weight": 0.50}
  ],
  "start": "2021-01-01",
  "end": "2026-06-12",
  "initial_cash": 100000,
  "fee_bps": 1,
  "slippage_bps": 2,
  "optimization_method": "inverse_volatility",
  "rebalance_strategy": "ma_deviation_200",
  "rebalance_params": {
    "ma_window": 200,
    "deviation_step": 0.05,
    "adjustment_per_step": 0.10,
    "min_multiplier": 0.50,
    "max_multiplier": 1.50,
    "allow_cash": true
  }
}
```

MVP limitations: daily close only, long-only, no leverage, no futures margin or contract multiplier modeling, no futures roll modeling, and cash earns 0.

## Safety Boundary

The system intentionally does not implement order placement in the MVP. Any trade suggestion is stored as `review_required` and includes `requires_human_confirmation=true`.

Required disclaimer:

> 该内容仅用于研究和决策辅助，不构成个性化投资建议或收益承诺。历史回测不代表未来表现，市场价格可能快速变化并导致本金损失。任何交易决策都需要用户结合自身风险承受能力进行人工复核和确认。
