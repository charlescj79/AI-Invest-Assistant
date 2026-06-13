import json
import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TEMPLATE_PATH = Path(os.getenv("PORTFOLIO_TEMPLATE_PATH", "portfolio_templates.json"))
DISCLAIMER = (
    "该内容仅用于研究和决策辅助，不构成个性化投资建议或收益承诺。"
    "历史回测不代表未来表现，市场价格可能快速变化并导致本金损失。"
    "任何交易决策都需要用户结合自身风险承受能力进行人工复核和确认。"
)

st.set_page_config(page_title="AI Invest Assistant", page_icon="📈", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #f6f7fb; }
    .block-container { padding-top: 1.2rem; max-width: 1280px; }
    .hero {
      padding: 18px 22px; border-radius: 18px;
      background: #14213d; color: white; margin-bottom: 14px;
    }
    .hero h1 { margin: 0; font-size: 1.8rem; letter-spacing: -0.03em; }
    .hero p { margin: 6px 0 0 0; opacity: .86; font-size: .98rem; }
    .card {
      background: #ffffff; border: 1px solid #e5e7eb;
      border-radius: 16px; padding: 16px; margin-bottom: 14px;
    }
    div[data-testid="stMetric"] {
      background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px;
    }
    .risk-box {
      background: #fff7ed; color: #7c2d12; border: 1px solid #fed7aa;
      border-radius: 14px; padding: 14px; font-weight: 600;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
      background: #ffffff; border: 1px solid #d1d5db;
      border-radius: 10px; color: #111827 !important; padding: 10px 16px;
      font-weight: 800; text-shadow: none;
    }
    .stTabs [aria-selected="true"] { background: #ef4444 !important; color: #ffffff !important; border-color: #ef4444 !important; }
    .stTabs [data-baseweb="tab"] p { color: inherit !important; font-weight: 800; }
    .stButton > button {
      min-height: 3.1rem; border-radius: 12px; font-size: 1.05rem; font-weight: 800;
      border: 1px solid #111827; padding: .65rem 1rem;
    }
    .stButton > button[kind="primary"] { background: #ef4444; border-color: #ef4444; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="hero">
      <h1>📈 AI Invest Assistant</h1>
      <p>多资产行情、组合优化、策略回测与人工复核交易建议。</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def api(method: str, path: str, **kwargs):
    response = requests.request(method, f"{API_BASE_URL}{path}", timeout=180, **kwargs)
    response.raise_for_status()
    return response.json()


def load_templates() -> dict:
    if not TEMPLATE_PATH.exists():
        return {}
    try:
        return json.loads(TEMPLATE_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def save_templates(templates: dict) -> None:
    TEMPLATE_PATH.write_text(json.dumps(templates, indent=2, ensure_ascii=False))


def default_portfolio_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"symbol": "GC", "min_weight": 0.10, "max_weight": 0.50, "current_weight": 0.30},
            {"symbol": "SI", "min_weight": 0.00, "max_weight": 0.30, "current_weight": 0.10},
            {"symbol": "NQ", "min_weight": 0.20, "max_weight": 0.60, "current_weight": 0.50},
        ]
    )


with st.sidebar:
    st.header("连接")
    st.write(f"API: `{API_BASE_URL}`")
    if st.button("检查服务"):
        st.json(api("GET", "/health"))
        st.json(api("GET", "/system/status"))

    st.header("Watchlist")
    symbol = st.text_input("Symbol", value="SPY", help="支持股票/ETF，也支持期货根代码 GC/SI/HG/NQ。 ").upper().strip()
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
market_tab, single_bt_tab, portfolio_tab, advice_tab = st.tabs(["标的与行情", "单标的回测", "组合优化与回测", "简报与建议"])

with market_tab:
    left, right = st.columns([1, 2])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("标的池")
        sort_by = st.selectbox("排序", ["symbol", "asset_type", "exchange", "id"], index=0)
        symbols_frame = pd.DataFrame(symbols).sort_values(sort_by) if symbols else pd.DataFrame()
        st.dataframe(symbols_frame, use_container_width=True)
        delete_symbol = st.selectbox("删除/停用标的", symbol_options, key="delete_symbol")
        if st.button("删除选中标的", key="delete_symbol_button"):
            st.json(api("DELETE", f"/symbols/{delete_symbol}"))
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("行情采集与价格曲线")
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
        st.markdown("</div>", unsafe_allow_html=True)

with single_bt_tab:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("单标的策略回测")
    selected = st.selectbox("选择标的", symbol_options, key="bt_symbol")
    start = st.date_input("开始日期", value=date.today() - timedelta(days=365), key="bt_start")
    end = st.date_input("结束日期", value=date.today(), key="bt_end")
    strategy = st.selectbox("策略", ["moving_average", "momentum", "rsi"])
    if strategy == "moving_average":
        parameters = {"short_window": st.number_input("短均线", min_value=2, value=20), "long_window": st.number_input("长均线", min_value=3, value=50)}
    elif strategy == "momentum":
        parameters = {"lookback": st.number_input("回看天数", min_value=5, value=63)}
    else:
        parameters = {"window": st.number_input("RSI 窗口", min_value=2, value=14), "buy_below": st.number_input("买入阈值", min_value=1, max_value=50, value=30), "sell_above": st.number_input("卖出阈值", min_value=50, max_value=99, value=70)}
    if st.button("运行回测", key="run_single_bt"):
        st.json(api("POST", "/backtests/run", json={"symbols": [selected], "strategy": strategy, "parameters": parameters, "start": str(start), "end": str(end), "initial_cash": 100000, "fee_bps": 1, "slippage_bps": 2}))
    st.markdown("</div>", unsafe_allow_html=True)

with portfolio_tab:
    templates = load_templates()
    if "portfolio_df" not in st.session_state:
        st.session_state.portfolio_df = default_portfolio_frame()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("组合优化与回测")
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    selected_template = c1.selectbox("模板", ["<默认>", *sorted(templates.keys())])
    template_name = c2.text_input("保存为", value="metals_nasdaq")
    if selected_template != "<默认>" and c3.button("加载"):
        st.session_state.portfolio_df = pd.DataFrame(templates[selected_template])
    if c4.button("保存"):
        templates[template_name] = st.session_state.portfolio_df.to_dict("records")
        save_templates(templates)
        st.success(f"已保存模板：{template_name}")
    portfolio_df = st.data_editor(st.session_state.portfolio_df, num_rows="dynamic", use_container_width=True, key="portfolio_editor")
    st.session_state.portfolio_df = portfolio_df
    clean_portfolio = portfolio_df.dropna(subset=["symbol"]).copy()
    clean_portfolio["symbol"] = clean_portfolio["symbol"].astype(str).str.upper().str.strip()
    assets = clean_portfolio.to_dict("records")

    p_left, p_mid, p_right = st.columns(3)
    with p_left:
        p_start = st.date_input("组合开始日期", value=date.today() - timedelta(days=365 * 3), key="p_start")
        p_end = st.date_input("组合结束日期", value=date.today(), key="p_end")
        initial_cash = st.number_input("初始资金", min_value=1000.0, value=100000.0, step=1000.0)
        method = st.selectbox("权重优化方法", ["inverse_volatility", "mean_variance_simple"])
    with p_mid:
        portfolio_strategy = st.selectbox("组合策略", ["ma_deviation_200", "fixed_rebalance", "momentum_filter", "volatility_target"])
        fee_bps = st.number_input("手续费 bps", min_value=0.0, value=1.0)
        slippage_bps = st.number_input("滑点 bps", min_value=0.0, value=2.0)
        roll_cost_bps = st.number_input("展期成本 bps", min_value=0.0, value=0.0)
    with p_right:
        ma_window = st.number_input("均线窗口", min_value=2, value=200)
        deviation_step = st.number_input("偏离分档", min_value=0.01, max_value=1.0, value=0.05, step=0.01)
        adjustment_per_step = st.number_input("每档调整比例", min_value=0.0, max_value=1.0, value=0.10, step=0.01)
        allow_cash = st.checkbox("允许保留现金", value=True)
        rebalance_frequency_days = st.number_input("固定/动量再平衡天数", min_value=1, value=20)
        momentum_lookback_days = st.number_input("动量回看天数", min_value=5, value=63)
        target_vol = st.number_input("目标年化波动率", min_value=0.01, max_value=2.0, value=0.15)

    if st.button("采集组合行情", key="portfolio_ingest"):
        st.json(api("POST", "/market/ingest", json={"symbols": [item["symbol"] for item in assets], "start": str(p_start), "end": str(p_end)}))

    optimize_payload = {"assets": assets, "start": str(p_start), "end": str(p_end), "lookback_days": 252, "method": method}
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
        "fee_bps": fee_bps,
        "slippage_bps": slippage_bps,
        "roll_cost_bps": roll_cost_bps,
        "optimization_method": method,
        "rebalance_strategy": portfolio_strategy,
        "rebalance_params": {"ma_window": int(ma_window), "deviation_step": float(deviation_step), "adjustment_per_step": float(adjustment_per_step), "min_multiplier": 0.5, "max_multiplier": 1.5, "allow_cash": allow_cash},
        "fixed_rebalance_params": {"rebalance_frequency_days": int(rebalance_frequency_days), "allow_cash": False},
        "momentum_filter_params": {"lookback_days": int(momentum_lookback_days), "rebalance_frequency_days": int(rebalance_frequency_days), "negative_momentum_multiplier": 0.25, "positive_momentum_multiplier": 1.0, "allow_cash": allow_cash},
        "volatility_target_params": {"lookback_days": int(momentum_lookback_days), "target_annual_volatility": float(target_vol), "min_scale": 0.25, "max_scale": 1.25, "allow_cash": allow_cash},
    }
    if st.button("运行组合回测与再平衡建议", key="portfolio_backtest"):
        result = api("POST", "/portfolios/backtest", json=backtest_payload)
        recs = pd.DataFrame(result["recommendations"])
        m1, m2, m3 = st.columns(3)
        m1.metric("现金权重", f"{result['cash_weight']:.1%}")
        m2.metric("VaR 95%", f"{result['risk_metrics'].get('var_95') or 0:.2%}")
        m3.metric("最大集中度", f"{result['risk_metrics'].get('max_concentration') or 0:.1%}")
        st.dataframe(recs, use_container_width=True)
        st.bar_chart(recs.set_index("symbol")[["strategic_weight", "tactical_weight", "current_weight"]])
        equity = pd.DataFrame(result["equity_curve"])
        if not equity.empty:
            st.line_chart(equity.set_index("date")["equity"])
        st.subheader("风险指标")
        st.json(result["risk_metrics"])
        st.subheader("回测指标")
        st.json(result["metrics"])
    st.markdown("</div>", unsafe_allow_html=True)

with advice_tab:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("简报与建议")
    selected = st.selectbox("选择标的", symbol_options, key="advice_symbol")
    end = st.date_input("分析日期", value=date.today(), key="advice_date")
    if st.button("生成每日简报"):
        st.json(api("POST", "/briefs/daily/generate", json={"symbols": [selected], "date": str(end)}))
    if st.button("生成交易建议"):
        st.json(api("POST", "/advice/generate", json={"symbol": selected, "as_of": str(end)}))
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f'<div class="risk-box">{DISCLAIMER}</div>', unsafe_allow_html=True)
