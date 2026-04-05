import threading
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import crypto_engine
from config import DEFAULT_SYMBOL, SYMBOLS

TRADES_DIR = Path(__file__).resolve().parent / "trades"
SYMBOL_LIST = SYMBOLS or [DEFAULT_SYMBOL]
DEFAULT_PAIR = DEFAULT_SYMBOL if DEFAULT_SYMBOL in SYMBOL_LIST else SYMBOL_LIST[0]


def ensure_client():
    client = getattr(crypto_engine, "client", None)
    if client is None:
        try:
            crypto_engine.reconnect_client()
        except Exception:
            pass
        client = getattr(crypto_engine, "client", None)
    return client


@st.cache_data(ttl=60)
def fetch_candles(symbol: str, days: int) -> pd.DataFrame:
    try:
        data = crypto_engine.get_historical_data_with_indicators(symbol=symbol, days=days)
    except Exception:
        return pd.DataFrame()
    if data.empty:
        return data
    data = data.tail(100).copy()
    data["open_time"] = pd.to_datetime(data["open_time"], errors="coerce")
    data = data.dropna(subset=["open_time"])
    return data


def fetch_order_book(symbol: str, depth: int = 10):
    client = ensure_client()
    if client is None or not hasattr(client, "get_order_book"):
        empty = pd.DataFrame(columns=["price", "quantity", "total"])
        return empty, empty
    try:
        raw = client.get_order_book(symbol=symbol, limit=depth)
    except Exception:
        empty = pd.DataFrame(columns=["price", "quantity", "total"])
        return empty, empty
    bids = raw.get("bids", [])[:depth]
    asks = raw.get("asks", [])[:depth]
    bids_df = pd.DataFrame(bids, columns=["price", "quantity"])
    asks_df = pd.DataFrame(asks, columns=["price", "quantity"])
    for frame in (bids_df, asks_df):
        if not frame.empty:
            frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
            frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
            frame["total"] = frame["price"] * frame["quantity"]
            frame.dropna(inplace=True)
    if not bids_df.empty:
        bids_df = bids_df.sort_values("price", ascending=False)
    if not asks_df.empty:
        asks_df = asks_df.sort_values("price", ascending=True)
    return bids_df, asks_df


def load_recent_trades(limit: int = 10) -> pd.DataFrame:
    if not TRADES_DIR.exists():
        return pd.DataFrame()
    frames = []
    accumulated = 0
    for path in sorted(TRADES_DIR.glob("*_trades_*.csv"), reverse=True):
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        if frame.empty:
            continue
        frames.append(frame)
        accumulated += len(frame)
        if accumulated >= limit:
            break
    if not frames:
        return pd.DataFrame()
    data = pd.concat(frames, ignore_index=True)
    if "timestamp" in data.columns:
        data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    else:
        data["timestamp"] = pd.NaT
    if "quantity" in data.columns:
        data["quantity"] = pd.to_numeric(data["quantity"], errors="coerce")
    elif "size" in data.columns:
        data["quantity"] = pd.to_numeric(data["size"], errors="coerce")
    if "price" in data.columns:
        data["price"] = pd.to_numeric(data["price"], errors="coerce")
    if "pnl" in data.columns:
        data["pnl"] = pd.to_numeric(data["pnl"], errors="coerce")
    if "balance" in data.columns:
        data["balance"] = pd.to_numeric(data["balance"], errors="coerce")
    if "side" not in data.columns and "reason" in data.columns:
        data["side"] = data["reason"]
    data = data.dropna(subset=["timestamp"])
    data = data.sort_values("timestamp", ascending=False)
    return data.head(limit)


def build_portfolio_metrics(trades: pd.DataFrame, symbol: str):
    balance = None
    pnl = None
    open_positions = None
    client = ensure_client()
    if client is not None:
        try:
            bal_info = client.get_asset_balance(asset="USDT")
            if isinstance(bal_info, dict):
                balance = float(bal_info.get("free", 0.0))
        except Exception:
            pass
        try:
            orders = client.get_open_orders(symbol=symbol)
            open_positions = len(orders)
        except Exception:
            pass
    if trades is not None and not trades.empty:
        ordered = trades.sort_values("timestamp")
        if "balance" in ordered.columns:
            last_balance = ordered.iloc[-1].get("balance")
            if pd.notna(last_balance):
                balance = float(last_balance)
        if "pnl" in ordered.columns:
            pnl = float(ordered["pnl"].fillna(0).sum())
    if balance is None:
        balance = 0.0
    if pnl is None:
        pnl = 0.0
    if open_positions is None:
        open_positions = 0
    return balance, pnl, open_positions


def get_last_signal(trades: pd.DataFrame) -> str:
    if trades is None or trades.empty:
        return "N/A"
    for column in ("signal", "reason", "side"):
        if column in trades.columns:
            value = trades.iloc[0].get(column)
            if pd.notna(value):
                return str(value)
    return "N/A"


def evaluate_bot_status() -> bool:
    status_attr = getattr(crypto_engine, "is_running", False)
    if callable(status_attr):
        try:
            return bool(status_attr())
        except Exception:
            return False
    return bool(status_attr)


def ensure_order_book_runner(symbol: str, enabled: bool) -> None:
    if "order_book_thread" not in st.session_state:
        st.session_state["order_book_thread"] = None
    if "order_book_thread_stop" not in st.session_state:
        st.session_state["order_book_thread_stop"] = False
    st.session_state["order_book_symbol"] = symbol
    thread = st.session_state.get("order_book_thread")
    if enabled:
        st.session_state["order_book_thread_stop"] = False
        if thread is None or not thread.is_alive():
            def _order_book_worker():
                while not st.session_state.get("order_book_thread_stop", False):
                    active_symbol = st.session_state.get("order_book_symbol", symbol)
                    bids, asks = fetch_order_book(active_symbol)
                    st.session_state["order_book_data"] = {
                        "symbol": active_symbol,
                        "bids": bids.copy(),
                        "asks": asks.copy(),
                        "timestamp": time.time(),
                    }
                    time.sleep(5)
            worker = threading.Thread(target=_order_book_worker, daemon=True)
            worker.start()
            st.session_state["order_book_thread"] = worker
    else:
        st.session_state["order_book_thread_stop"] = True
        if thread is not None and not thread.is_alive():
            st.session_state["order_book_thread"] = None


def get_order_book_snapshot(symbol: str):
    stored = st.session_state.get("order_book_data")
    if stored and stored.get("symbol") == symbol:
        bids = stored.get("bids")
        asks = stored.get("asks")
        if isinstance(bids, pd.DataFrame) and isinstance(asks, pd.DataFrame):
            return bids, asks, stored.get("timestamp", 0.0)
    bids, asks = fetch_order_book(symbol)
    st.session_state["order_book_data"] = {
        "symbol": symbol,
        "bids": bids.copy(),
        "asks": asks.copy(),
        "timestamp": time.time(),
    }
    return bids, asks, st.session_state["order_book_data"]["timestamp"]


st.set_page_config(page_title="Binance Dashboard", layout="wide")
st.markdown(
    """
    <style>
    .stApp {background-color: #0b0f19; color: #f5f7fa;}
    .stMetric {background-color: #121826; padding: 16px; border-radius: 12px;}
    .block-container {padding-top: 1.5rem;}
    .stDataFrame thead tr {background-color: #182235; color: #f5f7fa;}
    .stDataFrame tbody tr {background-color: #101727; color: #e1e5ee;}
    </style>
    """,
    unsafe_allow_html=True,
)

if "dashboard_started" not in st.session_state:
    st.session_state["dashboard_started"] = False
if st.sidebar.button("Start Dashboard"):
    st.session_state["dashboard_started"] = True
st.sidebar.write("Run: streamlit run dashboard.py")
if not st.session_state["dashboard_started"]:
    st.stop()

def_index = SYMBOL_LIST.index(DEFAULT_PAIR) if DEFAULT_PAIR in SYMBOL_LIST else 0
symbol = st.sidebar.selectbox("Symbol", SYMBOL_LIST, index=def_index)
lookback_days = st.sidebar.slider("Lookback (days)", min_value=5, max_value=120, value=30)
auto_refresh = st.sidebar.checkbox("Auto refresh every 10s", value=True)

ensure_order_book_runner(symbol, auto_refresh)
market_tab, = st.tabs(["📈 Market"])
with market_tab:
    st.title("Binance-Style Live Trading Dashboard")
    trades_df = load_recent_trades(50)
    balance_value, pnl_value, open_positions_value = build_portfolio_metrics(trades_df, symbol)
    last_signal_value = get_last_signal(trades_df)
    status_running = evaluate_bot_status()
    status_label = "Running" if status_running else "Stopped"
    metrics = st.columns(5)
    metrics[0].metric("Balance (USDT)", f"{balance_value:,.2f}")
    metrics[1].metric("PNL (USDT)", f"{pnl_value:,.2f}")
    metrics[2].metric("Open Positions", str(open_positions_value))
    metrics[3].metric("Status", status_label)
    metrics[4].metric("Last Signal", last_signal_value)

    candles = fetch_candles(symbol, lookback_days)
    if not candles.empty:
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.6, 0.2, 0.2])
        fig.add_trace(go.Candlestick(x=candles["open_time"], open=candles["open"], high=candles["high"], low=candles["low"], close=candles["close"], name="Price"), row=1, col=1)
        fig.add_trace(go.Bar(x=candles["open_time"], y=candles["volume"], name="Volume", marker_color="#1f77b4"), row=2, col=1)
        if "RSI_14" in candles.columns:
            fig.add_trace(go.Scatter(x=candles["open_time"], y=candles["RSI_14"], name="RSI 14", line=dict(color="#ffb74d", width=2)), row=3, col=1)
            fig.add_hline(y=70, line=dict(color="#ef5350", width=1, dash="dash"), row=3, col=1)
            fig.add_hline(y=30, line=dict(color="#26a69a", width=1, dash="dash"), row=3, col=1)
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis_rangeslider_visible=False,
            height=720,
            paper_bgcolor="#0b0f19",
            plot_bgcolor="#0b0f19",
        )
        fig.update_xaxes(showgrid=True, gridcolor="#ffffff", gridwidth=0.2, zeroline=False, color="#f5f7fa")
        fig.update_yaxes(showgrid=True, gridcolor="#ffffff", gridwidth=0.2, zeroline=False, color="#f5f7fa")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No candlestick data available for the selected symbol.")

    order_container = st.container()
    with order_container:
        st.subheader("Order Book (Top 10)")
        order_cols = st.columns(2)
        order_cols[0].subheader("Top Bids")
        bids_placeholder = order_cols[0].empty()
        order_cols[1].subheader("Top Asks")
        asks_placeholder = order_cols[1].empty()

    def render_order_tables():
        bids_table, asks_table, timestamp_value = get_order_book_snapshot(symbol)
        bids_placeholder.dataframe(bids_table, use_container_width=True, height=310)
        asks_placeholder.dataframe(asks_table, use_container_width=True, height=310)
        return timestamp_value

    last_order_timestamp = render_order_tables()
    if last_order_timestamp:
        order_container.caption(f"Last order book update: {time.strftime('%H:%M:%S', time.localtime(last_order_timestamp))}")

    st.subheader("Recent Trades")
    if trades_df is not None and not trades_df.empty:
        display_cols = [col for col in ["timestamp", "symbol", "side", "price", "quantity", "pnl", "balance"] if col in trades_df.columns]
        display = trades_df.copy().head(10)
        if "timestamp" in display.columns:
            display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        for field in ("price", "quantity", "pnl", "balance"):
            if field in display.columns:
                display[field] = display[field].map(lambda x: f"{x:,.4f}" if pd.notna(x) else "-")
        st.dataframe(display[display_cols], use_container_width=True, height=360)
    else:
        st.info("No recent trades recorded yet.")

if auto_refresh:
    time.sleep(10)
    st.rerun()
