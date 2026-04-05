"""
Professional Binance-like Live Trading View
Real-time candlestick charts with indicators, tools, multi-chart hub, and timeframe toggle
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, colorchooser
from typing import Optional, Dict, Any, List, Callable
import logging
from datetime import datetime
import threading
import time

try:
    import requests
except ImportError:  # pragma: no cover - requests is expected in prod, but handle gracefully
    requests = None

try:
    from config import SYMBOLS as BASE_SYMBOLS
except ImportError:  # pragma: no cover - fallback list if config isn't available
    BASE_SYMBOLS = [
        'BTCUSDT',
        'ETHUSDT',
        'BNBUSDT',
        'SOLUSDT',
        'ADAUSDT',
        'XRPUSDT',
        'DOGEUSDT',
        'MATICUSDT',
        'LINKUSDT',
    ]

try:
    import pandas as pd
    import numpy as np
    import mplfinance as mpf
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    HAS_CHARTS = True
except ImportError:  # pragma: no cover - charts disabled when deps missing
    HAS_CHARTS = False


logger = logging.getLogger(__name__)

BINANCE_EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
_SYMBOL_CACHE: List[str] = []


def fetch_binance_usdt_symbols(limit: int = 200) -> List[str]:
    """Fetch tradable USDT pairs from Binance. Falls back to base symbols when offline."""
    global _SYMBOL_CACHE

    if _SYMBOL_CACHE:
        return _SYMBOL_CACHE[:limit] if limit else list(_SYMBOL_CACHE)

    if requests is None:
        _SYMBOL_CACHE = list(BASE_SYMBOLS)
        return _SYMBOL_CACHE[:limit] if limit else list(_SYMBOL_CACHE)

    try:
        response = requests.get(BINANCE_EXCHANGE_INFO_URL, timeout=6)
        response.raise_for_status()
        data = response.json()
        usdt_pairs = [
            symbol_info['symbol']
            for symbol_info in data.get('symbols', [])
            if symbol_info.get('quoteAsset') == 'USDT' and symbol_info.get('status') == 'TRADING'
        ]
        usdt_pairs = sorted(set(usdt_pairs))
        if not usdt_pairs:
            raise ValueError("No USDT pairs returned from Binance")
        _SYMBOL_CACHE = usdt_pairs
    except Exception as exc:  # pragma: no cover - network fallback path
        logger.warning("Falling back to packaged symbol list: %s", exc)
        _SYMBOL_CACHE = list(BASE_SYMBOLS)

    return _SYMBOL_CACHE[:limit] if limit else list(_SYMBOL_CACHE)


class BinanceLiveView:
    """Professional Binance-like trading view with real-time charts."""

    def __init__(self, parent: tk.Widget, theme_manager=None,
                 symbol_change_callback: Optional[Callable[["BinanceLiveView", str], None]] = None):
        self.parent = parent
        self.theme_manager = theme_manager
        self.has_charts = HAS_CHARTS

        # Trading data
        self.symbol = "BTCUSDT"
        self.timeframe = "1h"
        self.environment = "Testnet"
        self.chart_data = None
        self.is_updating = True
        self.update_thread = None
        self._symbol_callback = symbol_change_callback

        # Create main frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)

        # Dynamic UI vars
        self.symbol_value_var = tk.StringVar(self.frame, value=self.symbol)
        self.environment_value_var = tk.StringVar(self.frame, value=self.environment.upper())
        self.time_label_var = tk.StringVar(self.frame, value=datetime.now().strftime("%H:%M:%S"))

        # Indicator states
        self.show_sma = tk.BooleanVar(value=True)
        self.show_rsi = tk.BooleanVar(value=True)
        self.show_macd = tk.BooleanVar(value=True)
        self.show_volume = tk.BooleanVar(value=True)
        self.indicator_color = '#ffb74d'
        self.secondary_indicator_color = '#ef5350'
        self.rsi_line_color = '#2196f3'
        self.macd_line_color = '#26a69a'
        self.macd_signal_color = '#ffb74d'
        self.grid_color = '#4c4c4c'

        self.timeframe_var = tk.StringVar(value=self.timeframe)
        self._time_updater_stop = threading.Event()

        # Build UI
        self._create_header()
        self._create_toolbar()
        self._create_chart_area()
        self._create_info_panel()

    # ------------------------------------------------------------------ UI Builders
    def _create_header(self) -> None:
        """Create professional header with symbol, environment badge, and time."""
        header = ttk.Frame(self.frame)
        header.pack(fill='x', padx=12, pady=12)

        # Symbol + environment container
        info_frame = ttk.Frame(header)
        info_frame.pack(side='left', fill='x', expand=True)

        ttk.Label(
            info_frame,
            text="📊 LIVE TRADING VIEW",
            font=('Segoe UI', 14, 'bold')
        ).pack(side='left', padx=(0, 12))

        ttk.Label(
            info_frame,
            text="Symbol:",
            font=('Segoe UI', 11, 'bold')
        ).pack(side='left')

        self.symbol_label = ttk.Label(
            info_frame,
            textvariable=self.symbol_value_var,
            font=('Segoe UI', 11)
        )
        self.symbol_label.pack(side='left', padx=(6, 18))

        self.environment_label = ttk.Label(
            info_frame,
            textvariable=self.environment_value_var,
            font=('Segoe UI', 10, 'bold')
        )
        self.environment_label.pack(side='left')
        self._update_environment_badge()

        # Live time display
        self.time_label = ttk.Label(
            header,
            textvariable=self.time_label_var,
            font=('Segoe UI', 10)
        )
        self.time_label.pack(side='right', padx=10)

        self._start_time_update()

    def _create_toolbar(self) -> None:
        """Create professional toolbar with timeframe controls and indicator toggles."""
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill='x', padx=12, pady=(0, 10))

        # Left side - Timeframe toggle
        left_frame = ttk.Frame(toolbar)
        left_frame.pack(side='left', fill='x', expand=True)

        ttk.Label(
            left_frame,
            text="⏱️ Timeframe:",
            font=('Segoe UI', 10, 'bold')
        ).pack(side='left', padx=(0, 6))

        timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']
        for tf in timeframes:
            btn = ttk.Button(
                left_frame,
                text=tf,
                width=4,
                command=lambda t=tf: self._change_timeframe(t)
            )
            btn.pack(side='left', padx=2)

        # Right side - Indicator controls
        right_frame = ttk.Frame(toolbar)
        right_frame.pack(side='right')

        ttk.Label(
            right_frame,
            text="🛠️ Indicators:",
            font=('Segoe UI', 10, 'bold')
        ).pack(side='left', padx=(0, 6))

        ttk.Checkbutton(
            right_frame,
            text="SMA 20/50",
            variable=self.show_sma,
            command=self._refresh_chart
        ).pack(side='left', padx=4)

        ttk.Checkbutton(
            right_frame,
            text="RSI 14",
            variable=self.show_rsi,
            command=self._refresh_chart
        ).pack(side='left', padx=4)

        ttk.Checkbutton(
            right_frame,
            text="MACD",
            variable=self.show_macd,
            command=self._refresh_chart
        ).pack(side='left', padx=4)

        ttk.Checkbutton(
            right_frame,
            text="Volume",
            variable=self.show_volume,
            command=self._refresh_chart
        ).pack(side='left', padx=4)
        ttk.Button(
            right_frame,
            text="Line Color",
            command=self._choose_line_color
        ).pack(side='left', padx=4)

    def _choose_line_color(self) -> None:
        result = colorchooser.askcolor(color=self.indicator_color, title="Select Line Color")
        if result and result[1]:
            chosen = result[1]
            self.indicator_color = chosen
            self.secondary_indicator_color = self._shift_color(chosen, -0.3)
            self.rsi_line_color = chosen
            self.macd_line_color = self._shift_color(chosen, -0.5)
            self.macd_signal_color = self._shift_color(chosen, 0.15)
            self._refresh_chart()

    def _shift_color(self, hex_color: str, factor: float) -> str:
        if not hex_color or not hex_color.startswith('#') or len(hex_color) != 7:
            return hex_color
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        if factor >= 0:
            r = int(r + (255 - r) * factor)
            g = int(g + (255 - g) * factor)
            b = int(b + (255 - b) * factor)
        else:
            r = int(r * (1 + factor))
            g = int(g * (1 + factor))
            b = int(b * (1 + factor))
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _create_chart_area(self) -> None:
        """Create the main chart display area with mplfinance-backed charts."""
        chart_frame = ttk.LabelFrame(
            self.frame,
            text="📈 Price Chart",
            padding=12
        )
        chart_frame.pack(fill='both', expand=True, padx=12, pady=(0, 10))

        if not HAS_CHARTS:
            ttk.Label(
                chart_frame,
                text=(
                    "⚠️ Charts require: pip install mplfinance matplotlib pandas numpy\n"
                    "Install the packages and rebuild to enable live charting."
                ),
                justify='center'
            ).pack(expand=True, pady=40)
            self.canvas = None
            self.fig = None
            self.axes = []
            return

        self.fig, self.axes = plt.subplots(
            3,
            1,
            figsize=(14, 8),
            gridspec_kw={'height_ratios': [3, 1, 1]},
            facecolor='#1a1a1a'
        )

        for ax in self.axes:
            ax.set_facecolor('#2d2d2d')
            ax.grid(True, color=self.grid_color, alpha=0.5, linestyle='--', linewidth=0.6)

        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        self._plot_sample_chart()

    def _create_info_panel(self) -> None:
        """Create information panel with market stats."""
        info_frame = ttk.LabelFrame(
            self.frame,
            text="📊 Market Information",
            padding=12
        )
        info_frame.pack(fill='x', padx=12, pady=(0, 10))

        cols = []
        for _ in range(4):
            col = ttk.Frame(info_frame)
            col.pack(side='left', fill='both', expand=True, padx=10)
            cols.append(col)

        ttk.Label(cols[0], text="Current Price", font=('Segoe UI', 9, 'bold')).pack()
        self.price_label = ttk.Label(
            cols[0],
            text="$0.00",
            font=('Segoe UI', 11, 'bold'),
            foreground='#26a69a'
        )
        self.price_label.pack()

        ttk.Label(cols[1], text="24h Change", font=('Segoe UI', 9, 'bold')).pack()
        self.change_label = ttk.Label(
            cols[1],
            text="0.00%",
            font=('Segoe UI', 11, 'bold'),
            foreground='#26a69a'
        )
        self.change_label.pack()

        ttk.Label(cols[2], text="24h High/Low", font=('Segoe UI', 9, 'bold')).pack()
        self.hl_label = ttk.Label(
            cols[2],
            text="$0.00 / $0.00",
            font=('Segoe UI', 10)
        )
        self.hl_label.pack()

        ttk.Label(cols[3], text="24h Volume", font=('Segoe UI', 9, 'bold')).pack()
        self.vol_label = ttk.Label(
            cols[3],
            text="$0.0B",
            font=('Segoe UI', 10)
        )
        self.vol_label.pack()

    # ------------------------------------------------------------------ Utility methods
    def _start_time_update(self) -> None:
        """Update time display in real-time."""
        def update_time():
            while not self._time_updater_stop.is_set():
                try:
                    self.time_label_var.set(datetime.now().strftime("%H:%M:%S"))
                    time.sleep(1)
                except tk.TclError:
                    break
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.debug("Time update loop interrupted: %s", exc)
                    break

        thread = threading.Thread(target=update_time, daemon=True)
        thread.start()

    def _change_timeframe(self, timeframe: str) -> None:
        """Change chart timeframe."""
        self.timeframe = timeframe
        self.timeframe_var.set(timeframe)
        self._refresh_chart()

    def _refresh_chart(self) -> None:
        """Refresh chart with current settings."""
        try:
            self._plot_sample_chart()
        except Exception as exc:
            logger.error("Chart refresh error: %s", exc)

    def set_symbol(self, symbol: str) -> None:
        """Update active symbol and refresh display."""
        self.symbol = symbol
        self.symbol_value_var.set(symbol)
        if self._symbol_callback:
            self._symbol_callback(self, symbol)
        self._refresh_chart()

    def set_environment(self, environment: str) -> None:
        """Set environment badge to TESTNET or LIVE."""
        self.environment = environment
        self.environment_value_var.set(environment.upper())
        self._update_environment_badge()

    def _update_environment_badge(self) -> None:
        env = self.environment.upper()
        color = '#26a69a' if env == 'TESTNET' else '#ef5350'
        if hasattr(self, 'environment_label'):
            self.environment_label.configure(foreground=color)

    def open_indicator_manager(self) -> None:
        messagebox = tk.messagebox if hasattr(tk, 'messagebox') else None
        if messagebox:
            messagebox.showinfo(
                "Indicators",
                "Indicator manager coming soon! Configure EMA, Bollinger Bands, and more."
            )

    def open_layout_manager(self) -> None:
        messagebox = tk.messagebox if hasattr(tk, 'messagebox') else None
        if messagebox:
            messagebox.showinfo(
                "Layouts",
                "Layout hub coming soon! Arrange multiple charts and save layouts."
            )

    def update_prices(self, symbol: str, price: float, change_percent: float,
                      high: float, low: float, volume: float) -> None:
        try:
            self.symbol = symbol
            self.symbol_value_var.set(symbol)
            self.price_label.config(text=f"${price:,.2f}")
            color = '#26a69a' if change_percent >= 0 else '#ef5350'
            self.change_label.config(text=f"{change_percent:+.2f}%", foreground=color)
            self.hl_label.config(text=f"${high:,.2f} / ${low:,.2f}")
            self.vol_label.config(text=f"${volume/1e9:.1f}B")
        except Exception as exc:
            logger.error("Price update error: %s", exc)

    # ------------------------------------------------------------------ Chart rendering helpers
    def _plot_sample_chart(self) -> None:
        if not HAS_CHARTS or self.canvas is None:
            return

        dates = pd.date_range(end=datetime.now(), periods=120, freq='1h')
        closes = np.cumsum(np.random.randn(len(dates))) + 100
        highs = closes + np.abs(np.random.randn(len(dates)) * 2)
        lows = closes - np.abs(np.random.randn(len(dates)) * 2)
        opens = np.roll(closes, 1)
        opens[0] = closes[0]
        volumes = np.random.rand(len(dates)) * 1000

        df = pd.DataFrame({
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes
        }, index=dates)

        ax_candle, ax_rsi, ax_macd = self.axes
        ax_candle.clear()
        ax_rsi.clear()
        ax_macd.clear()

        for ax in self.axes:
            ax.set_facecolor('#2d2d2d')
            ax.grid(True, color=self.grid_color, alpha=0.5, linestyle='--', linewidth=0.6)
            ax.tick_params(colors='white')

        width = 0.6
        for idx, row in df.iterrows():
            i = df.index.get_loc(idx)
            o, c, h, l = row[['Open', 'Close', 'High', 'Low']]
            color = '#26a69a' if c >= o else '#ef5350'
            ax_candle.plot([i, i], [l, h], color=color, linewidth=1)
            body_height = abs(c - o)
            body_bottom = min(o, c)
            ax_candle.add_patch(
                plt.Rectangle((i - width / 2, body_bottom), width, body_height,
                              facecolor=color, edgecolor=color, linewidth=1)
            )

        ax_candle.set_title(f'{self.symbol} - {self.timeframe} Candles', color='white', fontsize=12, fontweight='bold')
        ax_candle.set_ylabel('Price', color='white')
        ax_candle.tick_params(colors='white')

        if self.show_sma.get():
            sma20 = df['Close'].rolling(20).mean()
            sma50 = df['Close'].rolling(50).mean()
            ax_candle.plot(range(len(sma20)), sma20, label='SMA20', color=self.indicator_color, linewidth=1.5)
            ax_candle.plot(range(len(sma50)), sma50, label='SMA50', color=self.secondary_indicator_color, linewidth=1.5, linestyle='--')
            ax_candle.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='white')

        if self.show_rsi.get():
            delta = df['Close'].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace({0: float('nan')})
            rsi = 100 - (100 / (1 + rs))
            band_color = self._shift_color(self.grid_color, 0.4)
            ax_rsi.fill_between(range(len(rsi)), 30, 70, alpha=0.15, color=band_color)
            ax_rsi.plot(range(len(rsi)), rsi, color=self.rsi_line_color, linewidth=2, label='RSI14')
            ax_rsi.set_ylabel('RSI', color='white')
            ax_rsi.set_ylim(0, 100)
            ax_rsi.axhline(30, color=self.secondary_indicator_color, linestyle='--', alpha=0.5)
            ax_rsi.axhline(70, color=self.secondary_indicator_color, linestyle='--', alpha=0.5)
            ax_rsi.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='white')

        if self.show_volume.get():
            colors = ['#26a69a' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef5350'
                      for i in range(len(df))]
            ax_macd.bar(range(len(volumes)), volumes, color=colors, alpha=0.7)
            ax_macd.set_ylabel('Volume', color='white')
            ax_macd.set_xlabel('Time', color='white')
            ax_macd.tick_params(colors='white')

        if self.show_macd.get():
            short_ema = df['Close'].ewm(span=12, adjust=False).mean()
            long_ema = df['Close'].ewm(span=26, adjust=False).mean()
            macd = short_ema - long_ema
            signal = macd.ewm(span=9, adjust=False).mean()
            ax_macd.plot(range(len(macd)), macd, label='MACD', color=self.macd_line_color, linewidth=1.5)
            ax_macd.plot(range(len(signal)), signal, label='Signal', color=self.macd_signal_color, linewidth=1.2)
            ax_macd.axhline(0, color=self.grid_color, linewidth=0.8, linestyle='--', alpha=0.6)
            ax_macd.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='white')

        self.fig.tight_layout()
        self.canvas.draw()

    def destroy(self) -> None:
        self._time_updater_stop.set()
        self.frame.destroy()


class ChartTab:
    def __init__(self, parent_notebook, title, symbol_provider, on_symbol_change, on_environment_toggle, theme_manager=None):
        self.parent_notebook = parent_notebook
        self.title = title
        self.symbol_provider = symbol_provider
        self.on_symbol_change = on_symbol_change
        self.on_environment_toggle = on_environment_toggle
        self.theme_manager = theme_manager
        self.frame = ttk.Frame(parent_notebook)
        self.parent_notebook.add(self.frame, text=title)
        self.symbols = self._load_symbols()
        default_symbol = self.symbols[0] if self.symbols else "BTCUSDT"
        self.symbol_var = tk.StringVar(self.frame, value=default_symbol)
        self.environment_var = tk.StringVar(self.frame, value="Testnet")
        self._build_controls()
        self.view = BinanceLiveView(
            self.frame,
            theme_manager=theme_manager,
            symbol_change_callback=self._handle_view_symbol_change
        )
        self.view.set_symbol(self.symbol_var.get())
        self.view.set_environment(self.environment_var.get())

    def _build_controls(self):
        container = ttk.Frame(self.frame)
        container.pack(fill="x", padx=12, pady=(12, 0))
        ttk.Label(
            container,
            text="Symbol:",
            font=('Segoe UI', 10, 'bold')
        ).pack(side="left")
        self.symbol_combo = ttk.Combobox(
            container,
            textvariable=self.symbol_var,
            values=self.symbols,
            state="readonly",
            width=14
        )
        self.symbol_combo.pack(side="left", padx=(6, 16))
        self.symbol_combo.bind("<<ComboboxSelected>>", self._on_symbol_selected)
        self.symbol_combo.configure(postcommand=self._refresh_symbols)
        ttk.Label(
            container,
            text="Environment:",
            font=('Segoe UI', 10, 'bold')
        ).pack(side="left")
        env_frame = ttk.Frame(container)
        env_frame.pack(side="left", padx=(6, 0))
        ttk.Radiobutton(
            env_frame,
            text="🧪 Testnet",
            value="Testnet",
            variable=self.environment_var,
            command=self._on_environment_selected
        ).pack(side="left", padx=(0, 8))
        ttk.Radiobutton(
            env_frame,
            text="🔴 Live",
            value="Live",
            variable=self.environment_var,
            command=self._on_environment_selected
        ).pack(side="left")
        actions = ttk.Frame(container)
        actions.pack(side="right")
        ttk.Button(
            actions,
            text="Indicators",
            command=self._open_indicators
        ).pack(side="left", padx=4)
        ttk.Button(
            actions,
            text="Layouts",
            command=self._open_layouts
        ).pack(side="left", padx=4)

    def _load_symbols(self):
        try:
            symbols = self.symbol_provider() if self.symbol_provider else []
        except Exception:
            symbols = []
        return symbols if symbols else ["BTCUSDT"]

    def _refresh_symbols(self):
        symbols = self._load_symbols()
        if symbols != self.symbols:
            self.symbols = symbols
            self.symbol_combo.configure(values=self.symbols)
        if self.symbol_var.get() not in self.symbols:
            self.symbol_var.set(self.symbols[0])
            if hasattr(self, "view"):
                self.view.set_symbol(self.symbol_var.get())

    def _on_symbol_selected(self, _event=None):
        if hasattr(self, "view"):
            self.view.set_symbol(self.symbol_var.get())

    def _handle_view_symbol_change(self, _view, symbol):
        if self.symbol_var.get() != symbol:
            self.symbol_var.set(symbol)
        if self.on_symbol_change:
            self.on_symbol_change(symbol)

    def _on_environment_selected(self):
        environment = self.environment_var.get()
        if hasattr(self, "view"):
            self.view.set_environment(environment)
        if self.on_environment_toggle:
            self.on_environment_toggle(environment)

    def _open_indicators(self):
        if hasattr(self, "view"):
            self.view.open_indicator_manager()

    def _open_layouts(self):
        if hasattr(self, "view"):
            self.view.open_layout_manager()

    def set_environment(self, environment):
        self.environment_var.set(environment)
        if hasattr(self, "view"):
            self.view.set_environment(environment)

    def destroy(self):
        if hasattr(self, "view"):
            self.view.destroy()
        if self.frame.winfo_exists():
            self.frame.destroy()


class LiveTradingPanel(ttk.Frame):
    """Integrated live trading panel with chart hub and controls."""

    def __init__(self, parent, theme_manager=None):
        super().__init__(parent)
        self.theme_manager = theme_manager

        self.symbols = fetch_binance_usdt_symbols(limit=120)
        self.environment = 'Testnet'

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=12, pady=12)

        self.tabs: List[ChartTab] = []
        self._create_initial_tabs()

        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_change)

    def _create_initial_tabs(self) -> None:
        self._add_chart_tab("Primary Chart")
        self._add_chart_tab("Secondary Chart")

    def _add_chart_tab(self, title: str) -> None:
        tab = ChartTab(
            parent_notebook=self.notebook,
            title=title,
            symbol_provider=self.get_symbols,
            on_symbol_change=self._handle_symbol_change,
            on_environment_toggle=self._handle_environment_toggle,
            theme_manager=self.theme_manager
        )
        tab.set_environment(self.environment)
        self.tabs.append(tab)

    def get_symbols(self) -> List[str]:
        return list(self.symbols)

    def _handle_symbol_change(self, symbol: str) -> None:
        current_tab = self.notebook.index(self.notebook.select())
        logger.debug("Tab %s switched symbol to %s", current_tab, symbol)

    def _handle_environment_toggle(self, environment: str) -> None:
        self.environment = environment
        for tab in self.tabs:
            tab.set_environment(environment)

    def _on_tab_change(self, _event=None) -> None:
        current_tab = self.notebook.index(self.notebook.select())
        logger.debug("Active chart tab changed to %s", current_tab)

    def destroy(self) -> None:
        for tab in self.tabs:
            tab.destroy()
        super().destroy()