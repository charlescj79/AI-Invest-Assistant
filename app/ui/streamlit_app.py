import os
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DISCLAIMER = (
    "该内容仅用于研究和决策辅助，不构成个性化投资建议或收益承诺。"
    "历史回测不代表未来表现，市场价格可能快速变化并导致本金损失。"
    "任何交易决策都需要用户结合自身风险承受能力进行人工复核和确认。"
)

st.set_page_config(page_title="AI Invest Assistant", page_icon="📈", layout="wide")
st.title("📈 AI Invest Assistant")
st.caption("研究与决策辅助工具；不构成个性化投资建议或收益承诺。")


def api(method: str, path: str, **kwargs):
    response = requests.request(method, f"{API_BASE_URL}{path}", timeout=180, **kwargs)
    response.raise_for_status()
    return response.json()


with st.sidebar:
    st.header("连接")
    st.write(f"API: `{API_BASE_URL}`")
    if st.button("检查服务"):
        st.json(api("GET", "/health"))
        st.json(api("GET", "/system/status"))

    st.header("Watchlist")
    symbol = st.text_input(
        "Symbol",
        value="SPY",
        help="支持股票/ETF，如 SPY；也支持期货根代码 GC/SI/HG/NQ。",
    ).upper().strip()
    name = st.text_input("Name", value="SPDR S&P 500 ETF Trust")
    asset_type = st.selectbox("Asset type", ["stock", "etf", "future", "index"], index=1)
    exchange = st.text_input("Exchange", value="NYSEARCA")
    if st.button("添加/更新标的", type="primary"):
        st.json(
            api(
                "POST",
                "/symbols",
                json={
                    "symbol": symbol,
                    "name": name,
                    "exchange": exchange,
                    "asset_type": asset_type,
                    "currency": "USD",
                    "sector": "Broad Market",
                },
            )
        )

try:
    symbols = api("GET", "/symbols")
except Exception as exc:
    st.error(f"无法连接 API：{exc}")
    st.stop()

symbol_options = [item["symbol"] for item in symbols] or ["SPY"]
market_tab, single_bt_tab, portfolio_tab, advice_tab = st.tabs(
    ["标的与行情", "单标的回测", "组合优化与回测", "简报与建议"]
)

with market_tab:
    left, right = st.columns([1, 2])
    with left:
        st.subheader("标的")
        st.dataframe(symbols, use_container_width=True)
    with right:
        st.subheader("行情采集")
        selected = st.selectbox("选择标的", symbol_options, key="market_symbol")
        start = st.date_input("开始日期", value=date.today() - timedelta(days=365), key="market_start")
        end = st.date_input("结束日期", value=date.today(), key="market_end")
        if st.button("采集行情", key="market_ingest"):
            st.json(api("POST", "/market/ingest", json={"symbols": [selected], "start": str(start), "end": str(end)}))
        try:
            prices = api("GET", f"/market/{selected}/prices")
        except Exception:
            prices = []
        if prices:
            frame = pd.DataFrame(prices)
            st.line_chart(frame.set_index("date")["close"])
            st.dataframe(frame.tail(20), use_container_width=True)
        else:
            st.info("暂无行情数据。请先采集。")

with single_bt_tab:
    st.subheader("单标的回测")
    selected = st.selectbox("选择标的", symbol_options, key="bt_symbol")
    start = st.date_input("开始日期", value=date.today() - timedelta(days=365), key="bt_start")
    end = st.date_input("结束日期", value=date.today(), key="bt_end")
    strategy = st.selectbox("策略", ["moving_average", "momentum", "rsi"])
    if strategy == "moving_average":
        parameters = {
            "short_window": st.number_input("短均线", min_value=2, value=20),
            "long_window": st.number_input("长均线", min_value=3, value=50),
        }
    elif strategy == "momentum":
        parameters = {"lookback": st.number_input("回看天数", min_value=5, value=63)}
    else:
        parameters = {
            "window": st.number_input("RSI 窗口", min_value=2, value=14),
            "buy_below": st.number_input("买入阈值", min_value=1, max_value=50, value=30),
            "sell_above": st.number_input("卖出阈值", min_value=50, max_value=99, value=70),
        }
    if st.button("运行回测", key="run_single_bt"):
        st.json(
            api(
                "POST",
                "/backtests/run",
                json={
                    "symbols": [selected],
                    "strategy": strategy,
                    "parameters": parameters,
                    "start": str(start),
                    "end": str(end),
                    "initial_cash": 100000,
                    "fee_bps": 1,
                    "slippage_bps": 2,
                },
            )
        )

with portfolio_tab:
    st.subheader("组合优化与 200 日均线再平衡")
    default_portfolio = pd.DataFrame(
        [
            {"symbol": "GC", "min_weight": 0.10, "max_weight": 0.50, "current_weight": 0.30},
            {"symbol": "SI", "min_weight": 0.00, "max_weight": 0.30, "current_weight": 0.10},
            {"symbol": "NQ", "min_weight": 0.20, "max_weight": 0.60, "current_weight": 0.50},
        ]
    )
    portfolio_df = st.data_editor(default_portfolio, num_rows="dynamic", use_container_width=True)
    clean_portfolio = portfolio_df.dropna(subset=["symbol"]).copy()
    clean_portfolio["symbol"] = clean_portfolio["symbol"].astype(str).str.upper().str.strip()
    assets = clean_portfolio.to_dict("records")

    p_left, p_right = st.columns(2)
    with p_left:
        p_start = st.date_input("组合开始日期", value=date.today() - timedelta(days=365 * 3), key="p_start")
        p_end = st.date_input("组合结束日期", value=date.today(), key="p_end")
        initial_cash = st.number_input("初始资金", min_value=1000.0, value=100000.0, step=1000.0)
        method = st.selectbox("权重优化方法", ["inverse_volatility", "mean_variance_simple"])
    with p_right:
        ma_window = st.number_input("均线窗口", min_value=20, value=200)
        deviation_step = st.number_input("偏离分档", min_value=0.01, max_value=1.0, value=0.05, step=0.01)
        adjustment_per_step = st.number_input("每档调整比例", min_value=0.0, max_value=1.0, value=0.10, step=0.01)
        allow_cash = st.checkbox("允许保留现金", value=True)

    if st.button("采集组合行情", key="portfolio_ingest"):
        st.json(
            api(
                "POST",
                "/market/ingest",
                json={"symbols": [item["symbol"] for item in assets], "start": str(p_start), "end": str(p_end)},
            )
        )

    optimize_payload = {
        "assets": assets,
        "start": str(p_start),
        "end": str(p_end),
        "lookback_days": 252,
        "method": method,
    }
    if st.button("计算推荐权重", key="portfolio_optimize"):
        result = api("POST", "/portfolios/optimize", json=optimize_payload)
        weights_frame = pd.DataFrame(result["weights"])
        st.dataframe(weights_frame, use_container_width=True)
        st.bar_chart(weights_frame.set_index("symbol")[["strategic_weight", "current_weight"]])
        st.json(result["diagnostics"])

    backtest_payload = {
        "assets": assets,
        "start": str(p_start),
        "end": str(p_end),
        "initial_cash": initial_cash,
        "fee_bps": 1,
        "slippage_bps": 2,
        "optimization_method": method,
        "rebalance_strategy": "ma_deviation_200",
        "rebalance_params": {
            "ma_window": int(ma_window),
            "deviation_step": float(deviation_step),
            "adjustment_per_step": float(adjustment_per_step),
            "min_multiplier": 0.5,
            "max_multiplier": 1.5,
            "allow_cash": allow_cash,
        },
    }
    if st.button("运行组合回测与再平衡建议", key="portfolio_backtest"):
        result = api("POST", "/portfolios/backtest", json=backtest_payload)
        recs = pd.DataFrame(result["recommendations"])
        st.metric("现金权重", f"{result['cash_weight']:.1%}")
        st.dataframe(recs, use_container_width=True)
        st.bar_chart(recs.set_index("symbol")[["strategic_weight", "tactical_weight", "current_weight"]])
        equity = pd.DataFrame(result["equity_curve"])
        if not equity.empty:
            st.line_chart(equity.set_index("date")["equity"])
        st.json(result["metrics"])

with advice_tab:
    st.subheader("简报与建议")
    selected = st.selectbox("选择标的", symbol_options, key="advice_symbol")
    end = st.date_input("分析日期", value=date.today(), key="advice_date")
    if st.button("生成每日简报"):
        st.json(api("POST", "/briefs/daily/generate", json={"symbols": [selected], "date": str(end)}))
    if st.button("生成交易建议"):
        st.json(api("POST", "/advice/generate", json={"symbol": selected, "as_of": str(end)}))

st.warning(DISCLAIMER)
