from __future__ import annotations

import asyncio
import csv
import inspect
import json
import os
import random
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import AsyncGenerator, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import websockets

from config import RiskConfig, TradingMode, TimeFrame, SYMBOLS, get_logger

logger = get_logger(__name__)

DEFAULT_CAPITAL = 10000.0
DEFAULT_POLL_INTERVAL = 60
UPDATE_INTERVAL = 5.0
TRADES_DIR = os.path.join(os.path.dirname(__file__), "trades")
os.makedirs(TRADES_DIR, exist_ok=True)
SCALPER_LOG_PATH = os.path.join(TRADES_DIR, "scalper_trades.csv")

BOOK_TICKER_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "TRXUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "DOTUSDT",
    "MATICUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "XLMUSDT",
    "UNIUSDT",
    "ATOMUSDT",
    "FILUSDT",
    "NEARUSDT",
    "ICPUSDT",
]
BOOK_TICKER_URL = "wss://stream.binance.com:9443/ws/!bookTicker"
JUMP_THRESHOLD = 0.001
PULLBACK_TICKS = 5
PULLBACK_RATIO = 0.999
EXIT_DELAY = 2.0

RISK_CONFIG: Dict[str, float] = {
    "risk_per_trade": 0.02,
    "stop_loss_mult": 2.0,
    "take_profit_rr": 2.0,
    "max_drawdown": 0.15,
    "daily_loss": 6.0,
    "trailing_pct": 0.015,
    "timeout_hours": 6.0,
    "min_vol_atr": 0.5,
}


class MarketTracker:
    def __init__(self) -> None:
        self.available_pairs = list(SYMBOLS)
        self.gainers: List[Dict[str, float]] = []
        self.losers: List[Dict[str, float]] = []
        self.new_listings: List[Dict[str, float]] = []
        self.mode_metrics: Dict[str, Dict[str, float]] = {}

    def update_market_data(self) -> None:
        now = time.time()
        rng = random.Random(now)
        base_symbols = SYMBOLS[:3] if len(SYMBOLS) >= 3 else SYMBOLS
        self.gainers = [
            {
                "symbol": sym,
                "change": rng.uniform(0.5, 8.0),
                "volume": rng.uniform(5_000, 50_000),
                "price": rng.uniform(0.5, 250.0),
            }
            for sym in base_symbols
        ]
        losers_src = SYMBOLS[3:6] if len(SYMBOLS) >= 6 else SYMBOLS
        self.losers = [
            {
                "symbol": sym,
                "change": -rng.uniform(0.5, 6.0),
                "volume": rng.uniform(3_000, 40_000),
                "price": rng.uniform(0.05, 120.0),
            }
            for sym in losers_src
        ]
        self.new_listings = [
            {
                "symbol": f"NEW{i}USDT",
                "time": now,
                "price": rng.uniform(0.01, 10.0),
                "volume": rng.uniform(1_000, 15_000),
            }
            for i in range(1, 4)
        ]
        self.mode_metrics = {
            "Spot": {
                "trades": rng.randint(5, 25),
                "profit": rng.uniform(-250.0, 750.0),
                "max_drawdown": rng.uniform(2.0, 12.0),
            }
        }

    def search_pairs(self, text: str) -> List[str]:
        query = (text or "").upper()
        return [sym for sym in self.available_pairs if query in sym]


market_tracker = MarketTracker()


class PairState:
    def __init__(self) -> None:
        self.recent: deque = deque()
        self.state = "idle"
        self.last_price = 0.0
        self.spike_time = 0.0
        self.high_price = 0.0
        self.pullback_ticks = 0
        self.entry_price = 0.0
        self.entry_time: Optional[datetime] = None
        self.exit_task: Optional[asyncio.Task] = None


class BookTickerScalper:
    def __init__(self, symbols: List[str], quantity: float = 1.0, log_path: Optional[str] = None) -> None:
        self.symbols = {s.upper() for s in symbols}
        self.quantity = float(quantity)
        self.states: Dict[str, PairState] = {s: PairState() for s in self.symbols}
        self.log_path = log_path or SCALPER_LOG_PATH
        self._ensure_log_file()

    def _ensure_log_file(self) -> None:
        if not self.log_path:
            return
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            if not os.path.exists(self.log_path):
                with open(self.log_path, "w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["entry_time", "exit_time", "symbol", "entry_price", "exit_price", "profit"])
        except Exception as exc:
            logger.error("Log file setup failed: %s", exc)
            self.log_path = None

    async def run(self) -> None:
        while True:
            try:
                async with websockets.connect(BOOK_TICKER_URL, ping_interval=10, ping_timeout=10) as ws:
                    logger.info("BookTicker scalper connected")
                    async for raw in ws:
                        symbol = None
                        try:
                            data = json.loads(raw)
                            symbol = data.get("s")
                            if not symbol or symbol not in self.states:
                                continue
                            bid_raw = data.get("b")
                            ask_raw = data.get("a")
                            bid_price = float(bid_raw) if bid_raw is not None else 0.0
                            ask_price = float(ask_raw) if ask_raw is not None else 0.0
                            price = 0.0
                            if bid_price and ask_price:
                                price = (bid_price + ask_price) * 0.5
                            else:
                                price = bid_price or ask_price
                            if price <= 0.0:
                                continue
                            try:
                                await self._handle_tick(symbol, price)
                            except Exception as exc:
                                logger.error("Handler error %s: %s", symbol, exc)
                        except Exception as exc:
                            if symbol:
                                logger.error("Tick error for %s: %s", symbol, exc)
                            else:
                                logger.error("Tick error: %s", exc)
                logger.warning("BookTicker scalper disconnected")
            except Exception as exc:
                logger.error("BookTicker scalper connection error: %s", exc)
            await asyncio.sleep(1.0)

    def _record_trade(
        self,
        entry_time: str,
        exit_time: str,
        symbol: str,
        entry_price: float,
        exit_price: float,
        profit: float,
    ) -> None:
        logger.info(
            "TRADE %s %s %s %.6f %.6f %.6f",
            exit_time,
            symbol,
            entry_time,
            entry_price,
            exit_price,
            profit,
        )
        if not self.log_path:
            return
        try:
            with open(self.log_path, "a", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([entry_time, exit_time, symbol, f"{entry_price:.6f}", f"{exit_price:.6f}", f"{profit:.6f}"])
        except Exception as exc:
            logger.error("Trade log write failed: %s", exc)

    async def _handle_tick(self, symbol: str, price: float) -> None:
        state = self.states[symbol]
        now = time.time()
        state.last_price = price
        state.recent.append((now, price))
        while state.recent and now - state.recent[0][0] > 10.0:
            state.recent.popleft()
        if state.state == "idle":
            if state.recent:
                base_price = min(p for _, p in state.recent)
                if base_price > 0.0 and price >= base_price * (1.0 + JUMP_THRESHOLD):
                    state.state = "waiting"
                    state.spike_time = now
                    state.high_price = price
                    state.pullback_ticks = 0
            return
        if state.state == "waiting":
            if price > state.high_price:
                state.high_price = price
            state.pullback_ticks += 1
            if price <= state.high_price * PULLBACK_RATIO and state.pullback_ticks >= PULLBACK_TICKS:
                await self._enter(symbol, price)
                return
            if now - state.spike_time > 10.0:
                self._reset_state(symbol)
            return
        if state.state == "in_position":
            return

    async def _enter(self, symbol: str, price: float) -> None:
        state = self.states[symbol]
        state.state = "in_position"
        state.entry_price = price
        state.entry_time = datetime.utcnow()
        logger.info("ENTRY %s %s %.6f", state.entry_time.isoformat(), symbol, price)
        if state.exit_task and not state.exit_task.done():
            state.exit_task.cancel()
        state.exit_task = asyncio.create_task(self._schedule_exit(symbol))

    async def _schedule_exit(self, symbol: str) -> None:
        state = self.states[symbol]
        try:
            await asyncio.sleep(EXIT_DELAY)
            exit_price = state.last_price if state.last_price else state.entry_price
            entry_price = state.entry_price if state.entry_price else exit_price
            profit = (exit_price - entry_price) * self.quantity
            exit_time = datetime.utcnow().isoformat()
            entry_time = state.entry_time.isoformat() if state.entry_time else exit_time
            self._record_trade(entry_time, exit_time, symbol, entry_price, exit_price, profit)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Exit error for %s: %s", symbol, exc)
        finally:
            self._reset_state(symbol)

    def _reset_state(self, symbol: str) -> None:
        state = self.states[symbol]
        current_task = None
        try:
            current_task = asyncio.current_task()
        except RuntimeError:
            current_task = None
        if state.exit_task and not state.exit_task.done() and state.exit_task is not current_task:
            state.exit_task.cancel()
        state.state = "idle"
        state.spike_time = 0.0
        state.high_price = 0.0
        state.pullback_ticks = 0
        state.entry_price = 0.0
        state.entry_time = None
        state.exit_task = None


_client_connected = False
_stop_lock = threading.Lock()
_active_async_event: Optional[asyncio.Event] = None
_active_async_loop: Optional[asyncio.AbstractEventLoop] = None
_active_thread_event: Optional[threading.Event] = None
_live_prices: Dict[str, float] = {}


def reconnect_client(use_testnet: bool = True) -> None:
    global _client_connected
    _client_connected = True
    logger.info("Client reconnected (testnet=%s)", use_testnet)


def ensure_trades_csv(path: str) -> None:
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "symbol", "side", "price", "qty"])
            writer.writeheader()


def _write_trade_csv(trade: Dict[str, float], path: Optional[str]) -> None:
    if not path:
        return
    try:
        with open(path, "a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "symbol", "side", "price", "qty"])
            writer.writerow(trade)
    except Exception as exc:
        logger.debug("Trade export failed: %s", exc)


def get_historical_data_with_indicators(symbol: str, days: int = 30) -> pd.DataFrame:
    periods = max(days * 24, 120)
    index = pd.date_range(end=datetime.utcnow(), periods=periods, freq="H")
    drift = np.cumsum(np.random.normal(0, 1, size=periods))
    base = 100 + np.random.normal(0, 2)
    close = base + drift
    high = close + np.abs(np.random.normal(0, 1, size=periods))
    low = close - np.abs(np.random.normal(0, 1, size=periods))
    open_price = np.concatenate(([close[0]], close[:-1]))
    volume = np.abs(np.random.normal(5_000, 1_500, size=periods))
    df = pd.DataFrame(
        {
            "open_time": index,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    df["ATR_14"] = tr.rolling(14).mean().fillna(method="bfill")
    df.reset_index(drop=True, inplace=True)
    return df


async def tune_xgboost(df: pd.DataFrame, n_trials: int = 10) -> Dict[str, float]:
    await asyncio.sleep(0)
    return {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.1}


class MLModel:
    def __init__(self) -> None:
        self.feature_cols: List[str] = []

    async def train(self, df: pd.DataFrame) -> None:
        await asyncio.sleep(0)
        self.feature_cols = [col for col in df.columns if col not in ["open_time"]]

    async def predict(self, row: pd.Series) -> int:
        await asyncio.sleep(0)
        return 1 if random.random() > 0.5 else -1


class RiskManagedMLStrategy:
    def __init__(self, model: MLModel, capital: float, symbol: str, trades_path: Optional[str] = None) -> None:
        self.model = model
        self.capital = capital
        self.symbol = symbol
        self.position = 0.0
        self.equity = capital
        self.trades: List[Dict[str, float]] = []
        self.trades_path = trades_path

    async def on_data(self, row: pd.Series) -> None:
        prediction = await self.model.predict(row)
        price = float(row.get("close", 0.0))
        if price <= 0:
            return
        risk_amount = self.capital * RISK_CONFIG["risk_per_trade"]
        qty = risk_amount / price
        timestamp = row.get("open_time", datetime.utcnow())
        trade: Optional[Dict[str, float]] = None
        if prediction > 0 and self.position <= 0:
            self.position += qty
            trade = {
                "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
                "symbol": self.symbol,
                "side": "BUY",
                "price": price,
                "qty": qty,
            }
        elif prediction < 0 and self.position >= 0:
            self.position -= qty
            trade = {
                "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
                "symbol": self.symbol,
                "side": "SELL",
                "price": price,
                "qty": qty,
            }
        if trade:
            self.trades.append(trade)
            _write_trade_csv(trade, self.trades_path)
            logger.info("Trade executed: %s", trade)
        self.equity = self.capital + self.position * price


def update_risk_config(new_vals: Dict[str, float]) -> None:
    for key, value in new_vals.items():
        if key in RISK_CONFIG:
            RISK_CONFIG[key] = float(value)
    RiskConfig.RISK_PER_TRADE = RISK_CONFIG["risk_per_trade"]
    RiskConfig.STOP_LOSS_ATR_MULT = RISK_CONFIG["stop_loss_mult"]
    RiskConfig.TAKE_PROFIT_RR = RISK_CONFIG["take_profit_rr"]
    RiskConfig.MAX_DRAWDOWN = RISK_CONFIG["max_drawdown"]
    RiskConfig.DAILY_LOSS_LIMIT = RISK_CONFIG["daily_loss"]
    RiskConfig.TRAILING_STOP_PCT = RISK_CONFIG["trailing_pct"]
    RiskConfig.POSITION_TIMEOUT_HOURS = RISK_CONFIG["timeout_hours"]
    RiskConfig.MIN_VOLATILITY_ATR = RISK_CONFIG["min_vol_atr"]
    logger.info("Risk configuration updated: %s", RISK_CONFIG)


async def run_backtest(model: MLModel, df: Optional[pd.DataFrame] = None) -> Dict[str, List[float]]:
    if df is None:
        df = get_historical_data_with_indicators(SYMBOLS[0] if SYMBOLS else "BTCUSDT", days=60)
    await model.train(df)
    strategy = RiskManagedMLStrategy(model, DEFAULT_CAPITAL, SYMBOLS[0] if SYMBOLS else "BTCUSDT")
    equity_curve: List[float] = []
    for _, row in df.iterrows():
        await strategy.on_data(row)
        equity_curve.append(strategy.equity)
    return {"equity_curve": equity_curve, "final_equity": strategy.equity}


async def example_live_data_generator(symbol: str) -> AsyncGenerator[pd.Series, None]:
    while True:
        yield await _next_live_row(symbol)
        await asyncio.sleep(1)


def _step_price(symbol: str) -> float:
    base = _live_prices.get(symbol, 100.0)
    base += random.uniform(-1.5, 1.5)
    base = max(1.0, base)
    _live_prices[symbol] = base
    return base


async def _next_live_row(symbol: str) -> pd.Series:
    price = _step_price(symbol)
    volume = abs(random.gauss(1_000, 250))
    return pd.Series({
        "open_time": datetime.utcnow(),
        "symbol": symbol,
        "close": price,
        "volume": volume,
    })


def _dispatch_update(callback: Callable, balance: float, pnl: float, equity_slice: List[float], trades: List[Dict[str, float]]) -> None:
    try:
        argc = len(inspect.signature(callback).parameters)
    except (TypeError, ValueError):
        argc = 3
    try:
        if argc >= 4:
            callback(balance, pnl, equity_slice, trades)
        elif argc == 3:
            callback(balance, pnl, equity_slice)
        elif argc == 2:
            prices = [t.get("price", 0.0) for t in trades]
            callback(balance, prices)
        elif argc == 1:
            callback(balance)
        else:
            callback()
    except Exception as exc:
        logger.debug("Update callback error: %s", exc)


async def _run_live_session(
    model: MLModel,
    initial_capital: float,
    symbol: str,
    trades_path: Optional[str],
    poll_interval: int,
    stop_event: asyncio.Event,
    update_callback: Optional[Callable],
    generator: Optional[AsyncGenerator[pd.Series, None]] = None,
) -> Tuple[List[float], List[Dict[str, float]]]:
    strategy = RiskManagedMLStrategy(model, initial_capital, symbol, trades_path)
    equity_curve: List[float] = [initial_capital]
    last_update = 0.0
    while not stop_event.is_set():
        if generator is None:
            row = await _next_live_row(symbol)
        else:
            try:
                row = await generator.__anext__()
            except StopAsyncIteration:
                break
            if "symbol" in row:
                symbol = str(row["symbol"])
        await strategy.on_data(row)
        equity_curve.append(strategy.equity)
        pnl = strategy.equity - initial_capital
        now = time.time()
        if update_callback and now - last_update >= UPDATE_INTERVAL:
            _dispatch_update(update_callback, strategy.equity, pnl, equity_curve[-500:], strategy.trades)
            last_update = now
        await asyncio.sleep(max(1, poll_interval))
    return equity_curve, list(strategy.trades)


async def live_trading_loop(
    model: MLModel,
    df_generator: Optional[AsyncGenerator[pd.Series, None]] = None,
    update_callback: Optional[Callable] = None,
) -> Tuple[float, List[float]]:
    loop = asyncio.get_running_loop()
    event = asyncio.Event()
    with _stop_lock:
        global _active_async_event, _active_async_loop
        _active_async_event = event
        _active_async_loop = loop
    try:
        equity_curve, _ = await _run_live_session(
            model,
            DEFAULT_CAPITAL,
            SYMBOLS[0] if SYMBOLS else "BTCUSDT",
            None,
            1,
            event,
            update_callback,
            df_generator,
        )
        return equity_curve[-1] if equity_curve else DEFAULT_CAPITAL, equity_curve
    finally:
        with _stop_lock:
            if _active_async_event is event:
                _active_async_event = None
                _active_async_loop = None


def run_live_in_thread(
    model: MLModel,
    initial_capital: float,
    symbol: str,
    trades_csv: Optional[str],
    poll_interval_sec: int,
    stop_thread_event: threading.Event,
    update_callback: Optional[Callable] = None,
) -> threading.Thread:
    ensure_trades_csv(trades_csv or "")

    def thread_target() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        event = asyncio.Event()

        def watcher() -> None:
            stop_thread_event.wait()
            loop.call_soon_threadsafe(event.set)

        watcher_thread = threading.Thread(target=watcher, daemon=True)
        watcher_thread.start()
        with _stop_lock:
            global _active_async_event, _active_async_loop, _active_thread_event
            _active_async_event = event
            _active_async_loop = loop
            _active_thread_event = stop_thread_event
        try:
            loop.run_until_complete(
                _run_live_session(
                    model,
                    initial_capital,
                    symbol,
                    trades_csv,
                    poll_interval_sec,
                    event,
                    update_callback,
                )
            )
        finally:
            with _stop_lock:
                if _active_async_event is event:
                    _active_async_event = None
                    _active_async_loop = None
                    _active_thread_event = None
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()
    return thread


def start_book_ticker_scalper(quantity: float = 1.0) -> threading.Thread:
    scalper = BookTickerScalper(BOOK_TICKER_SYMBOLS, quantity)

    def runner() -> None:
        asyncio.run(scalper.run())

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return thread


def stop_live_trading() -> None:
    targets: List[Tuple[Optional[asyncio.AbstractEventLoop], Optional[asyncio.Event]]] = []
    thread_event: Optional[threading.Event]
    with _stop_lock:
        thread_event = _active_thread_event
        targets.append((_active_async_loop, _active_async_event))
    if thread_event:
        thread_event.set()
    for loop, event in targets:
        if event is None:
            continue
        if loop and loop.is_running():
            loop.call_soon_threadsafe(event.set)
        else:
            event.set()


__all__ = [
    "TradingMode",
    "TimeFrame",
    "RiskConfig",
    "market_tracker",
    "MLModel",
    "BookTickerScalper",
    "run_backtest",
    "live_trading_loop",
    "run_live_in_thread",
    "start_book_ticker_scalper",
    "stop_live_trading",
    "update_risk_config",
    "tune_xgboost",
    "get_historical_data_with_indicators",
    "reconnect_client",
    "ensure_trades_csv",
    "TRADES_DIR",
    "SYMBOLS",
    "DEFAULT_POLL_INTERVAL",
    "example_live_data_generator",
]
