"""
Complete Tkinter GUI with all advanced features
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from config import GUIConfig, SYMBOLS, get_logger
from market_analysis import MarketVolatilityAnalyzer, MarketTracker
from crypto_engine import (
    reconnect_client, get_historical_data_with_indicators, MLModel,
    run_backtest, live_trading_loop, update_risk_config, is_running,
    tune_xgboost, RiskConfig
)

logger = get_logger(__name__)


# ==================== UI Components ====================
class ToolTip:
    """Tooltip widget for buttons"""
    
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tw = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.tw or not self.text:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tw, text=self.text, bg="#ffffe0", relief="solid",
                       borderwidth=1, font=("Arial", 8))
        lbl.pack()

    def hide(self, _=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None


class ThemeManager:
    """Manage GUI themes"""
    
    def __init__(self):
        self.current_theme = 'dark'
        self.themes = GUIConfig.THEMES
    
    def apply_theme(self, root: tk.Tk) -> None:
        """Apply theme to root window"""
        colors = self.themes[self.current_theme]
        root.configure(bg=colors['bg'])
    
    def get_colors(self) -> Dict[str, str]:
        """Get current theme colors"""
        return self.themes[self.current_theme]
    
    def switch_theme(self) -> None:
        """Switch between light and dark theme"""
        self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'


# ==================== Main GUI Class ====================
class CryptoBotGUI:
    """Main GUI application with all features"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Crypto Scalper Bot – Advanced Dashboard")
        self.root.geometry(f"{GUIConfig.WINDOW_WIDTH}x{GUIConfig.WINDOW_HEIGHT}")
        self.root.configure(bg="#1a1a1a")
        self.root.resizable(True, True)

        # Initialize theme and analysis tools
        self.theme_manager = ThemeManager()
        self.vol_analyzer = MarketVolatilityAnalyzer()
        self.market_tracker = MarketTracker()
        
        # State management
        self.is_running_flag = False
        self.trading_thread = None
        self.auto_switch_var = tk.BooleanVar(value=True)
        self.current_symbol = 'SOLUSDT'
        self.is_testnet = True
        
        # Setup styles
        self._setup_styles()
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
        
        # Create UI
        self._create_status_bar()
        self._create_header()
        self._create_main_content()
        
        logger.info("GUI initialized successfully")

    def _setup_styles(self) -> None:
        """Setup ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        colors = self.theme_manager.get_colors()
        
        style.configure('TButton', font=('Arial', 11), padding=12)
        style.configure('TLabel', font=('Arial', 12), background='#1a1a1a', foreground='white')
        style.configure('TFrame', background='#1a1a1a')
    
    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts"""
        self.root.bind('<Control-s>', lambda e: self._start_live() if not self.is_running_flag else self._stop_bot())
        self.root.bind('<Control-b>', lambda e: self._start_backtest())
        self.root.bind('<Control-r>', lambda e: reconnect_client())
        self.root.bind('<Control-t>', lambda e: self._toggle_test_mode())
        self.root.bind('<F5>', lambda e: self._refresh_market_analysis())
        self.root.bind('<F1>', lambda e: self._show_help())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<Control-w>', lambda e: self._apply_risk_settings())
        self.root.bind('<Escape>', lambda e: self._stop_bot())
    
    def _toggle_test_mode(self) -> None:
        """Toggle between test and live mode"""
        current_val = self.env_var.get()
        self.env_var.set(1.0 - current_val)
        self._update_environment(str(1.0 - current_val))
    
    def _show_help(self) -> None:
        """Show help window"""
        try:
            from gui_help import show_help_window
            show_help_window(self.root)
        except ImportError:
            messagebox.showinfo("Help", "F1: Show Help\nCtrl+S: Start/Stop\nCtrl+B: Backtest\nCtrl+T: Toggle Test\nF5: Refresh\nEsc: Stop All")
        except Exception as e:
            messagebox.showerror("Help Error", f"Error: {e}")

    def _create_status_bar(self) -> None:
        """Create status bar at bottom"""
        self.status_var = tk.StringVar(value="Ready")
        sb = tk.Frame(self.root, bg="#333333", height=30)
        sb.pack(side='bottom', fill='x')
        tk.Label(sb, textvariable=self.status_var, fg='white', bg="#333333",
                 font=('Arial', 10), anchor='w').pack(fill='x', padx=10, pady=5)

    def _create_header(self) -> None:
        """Create header with balance, environment, and controls"""
        hdr = tk.Frame(self.root, bg="#1a1a1a")
        hdr.pack(pady=10, padx=20, fill='x')

        # Hamburger menu button
        self.menu_btn = tk.Button(hdr, text="☰ MENU", command=self._open_settings_menu,
                                  bg='#2196F3', fg='white', font=('Arial', 11, 'bold'), width=8)
        self.menu_btn.pack(side='left', padx=5)
        
        # Balance and symbol display
        self.balance_lbl = tk.Label(hdr, text="Balance: $10,000", fg='green',
                                    bg="#1a1a1a", font=('Arial', 16, 'bold'))
        self.balance_lbl.pack(side='left')

        self.sym_lbl = tk.Label(hdr, text="Current: SOLUSDT", fg='yellow',
                                bg="#1a1a1a", font=('Arial', 12))
        self.sym_lbl.pack(side='left', padx=30)

        # Environment toggle (TestNet/Live)
        env_frame = tk.LabelFrame(hdr, text="Environment", bg="#1a1a1a", fg='white', font=('Arial', 10, 'bold'))
        env_frame.pack(side='left', padx=10)

        self.env_var = tk.IntVar(value=1)  # 1 for TestNet, 0 for Live
        self.env_lbl = tk.Label(env_frame, text="TestNet", fg='yellow', bg="#1a1a1a", font=('Arial', 9, 'bold'))
        self.env_lbl.pack(side='left', padx=5)

        self.env_slider = ttk.Scale(env_frame, from_=0, to=1, orient='horizontal', length=100,
                                    variable=self.env_var, command=self._update_environment)
        self.env_slider.pack(side='left', padx=5)

        # Trading controls
        ctrl = tk.LabelFrame(hdr, text="Trading Controls", bg="#1a1a1a",
                            fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        ctrl.pack(side='right', padx=20)

        self.back_btn = tk.Button(ctrl, text="Run Backtest", command=self._start_backtest,
                                  bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'))
        self.back_btn.pack(side='left', padx=5)
        ToolTip(self.back_btn, "Run historical backtest on selected symbol")

        self.live_btn = tk.Button(ctrl, text="Start Live", command=self._start_live,
                                  bg='#2196F3', fg='white', font=('Arial', 11, 'bold'))
        self.live_btn.pack(side='left', padx=5)
        ToolTip(self.live_btn, "Start paper-trading with real-time data")

        self.stop_btn = tk.Button(ctrl, text="Stop Bot", command=self._stop_bot,
                                  bg='#f44336', fg='white', font=('Arial', 11, 'bold'), state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        ToolTip(self.stop_btn, "Emergency stop")

        # Symbol switcher
        sw = tk.LabelFrame(hdr, text="Symbol Switcher", bg="#1a1a1a",
                          fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        sw.pack(side='left', padx=20)

        tk.Label(sw, text="Select:", fg='yellow', bg="#1a1a1a", font=('Arial', 10)).pack(side='left')
        self.sym_var = tk.StringVar(value='SOLUSDT')
        self.sym_cbo = ttk.Combobox(sw, textvariable=self.sym_var,
                                    values=SYMBOLS, state='readonly', width=12)
        self.sym_cbo.pack(side='left', padx=5)

        self.sw_btn = tk.Button(sw, text="Switch", command=self._manual_switch,
                                bg='#FF9800', fg='white', font=('Arial', 10))
        self.sw_btn.pack(side='left', padx=5)

        self.auto_chk = tk.Checkbutton(sw, text="Auto-Switch", variable=self.auto_switch_var,
                                       fg='white', bg="#1a1a1a", selectcolor="#1a1a1a",
                                       font=('Arial', 10))
        self.auto_chk.pack(side='left', padx=10)

    def _create_main_content(self) -> None:
        """Create main notebook with tabs"""
        main = tk.Frame(self.root, bg="#1a1a1a")
        main.pack(pady=10, padx=20, fill='both', expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill='both', expand=True)

        # Dashboard tab
        self._create_dashboard_tab()
        
        # Trading Controls tab
        self._create_trading_controls_tab()
        
        # Mode Switcher tab
        self._create_mode_switcher_tab()
        
        # Volatility Analysis tab
        self._create_volatility_tab()
        
        # Risk Controls tab
        self._create_risk_controls_tab()
        
        # Risk Settings tab
        self._create_risk_settings_tab()
        
        # Market Analysis tab
        self._create_market_analysis_tab()
        
        # Market Tracker tab
        self._create_market_tracker_tab()
        
        # Analytics tab
        self._create_analytics_tab()
        
        # ML Monitor tab
        self._create_ml_monitor_tab()
        
        # Backtest tab
        self._create_backtest_tab()

    def _create_trading_controls_tab(self) -> None:
        """Create trading controls tab"""
        from gui_trading_controls import TradingControlsFrame
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🎛️ Trading Controls")
        try:
            controls = TradingControlsFrame(tab)
        except Exception as e:
            lbl = ttk.Label(tab, text=f"Trading Controls Error: {e}")
            lbl.pack(padx=10, pady=10)
    
    def _create_mode_switcher_tab(self) -> None:
        """Create mode switcher tab"""
        from gui_mode_switcher import TradingModeSwitcher
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚙️ Mode Switcher")
        try:
            self.mode_switcher = TradingModeSwitcher(tab)
        except Exception as e:
            lbl = ttk.Label(tab, text=f"Mode Switcher Error: {e}")
            lbl.pack(padx=10, pady=10)
    
    def _create_volatility_tab(self) -> None:
        """Create volatility analysis tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📊 Volatility Analysis")
        
        # Volatility frame
        vol_frame = ttk.LabelFrame(tab, text="Market Volatility Analysis", padding=10)
        vol_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Current volatility
        v1 = ttk.Frame(vol_frame)
        v1.pack(fill='x', pady=5)
        ttk.Label(v1, text="Current Volatility:", font=('Arial', 10, 'bold')).pack(side='left')
        self.vol_val = ttk.Label(v1, text="0.35 (High)", foreground='orange', font=('Arial', 10))
        self.vol_val.pack(side='left', padx=10)
        
        # Volatility regime
        v2 = ttk.Frame(vol_frame)
        v2.pack(fill='x', pady=5)
        ttk.Label(v2, text="Volatility Regime:", font=('Arial', 10, 'bold')).pack(side='left')
        self.regime_val = ttk.Label(v2, text="High", foreground='#FF9800', font=('Arial', 10))
        self.regime_val.pack(side='left', padx=10)
        
        # Trading windows
        v3 = ttk.LabelFrame(vol_frame, text="Trading Windows", padding=5)
        v3.pack(fill='both', expand=True, pady=10)
        
        high_frame = ttk.Frame(v3)
        high_frame.pack(fill='x', pady=5)
        ttk.Label(high_frame, text="High Vol Hours:", font=('Arial', 9, 'bold')).pack(side='left')
        self.high_vol_lbl = ttk.Label(high_frame, text="9, 14, 16", font=('Arial', 9))
        self.high_vol_lbl.pack(side='left', padx=10)
        
        low_frame = ttk.Frame(v3)
        low_frame.pack(fill='x', pady=5)
        ttk.Label(low_frame, text="Low Vol Hours:", font=('Arial', 9, 'bold')).pack(side='left')
        self.low_vol_lbl = ttk.Label(low_frame, text="2, 5, 11", font=('Arial', 9))
        self.low_vol_lbl.pack(side='left', padx=10)
        
        # Trading recommendation
        v4 = ttk.LabelFrame(vol_frame, text="Trading Recommendation", padding=5)
        v4.pack(fill='x', pady=10)
        
        score_frame = ttk.Frame(v4)
        score_frame.pack(fill='x', pady=5)
        ttk.Label(score_frame, text="Trading Score:", font=('Arial', 9, 'bold')).pack(side='left')
        self.trading_score = ttk.Label(score_frame, text="75/100 (HIGH)", foreground='#4CAF50', font=('Arial', 9, 'bold'))
        self.trading_score.pack(side='left', padx=10)
        
        rec_frame = ttk.Frame(v4)
        rec_frame.pack(fill='x', pady=5)
        ttk.Label(rec_frame, text="Recommendation:", font=('Arial', 9, 'bold')).pack(side='left')
        self.rec_lbl = ttk.Label(rec_frame, text="OPTIMAL CONDITIONS", foreground='#4CAF50', font=('Arial', 9, 'bold'))
        self.rec_lbl.pack(side='left', padx=10)
    
    def _create_risk_controls_tab(self) -> None:
        """Create risk controls tab"""
        from gui_risk_controls import RiskControlPanel
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🛡️ Risk Controls")
        try:
            self.risk_panel = RiskControlPanel(tab)
        except Exception as e:
            lbl = ttk.Label(tab, text=f"Risk Controls Error: {e}")
            lbl.pack(padx=10, pady=10)
    
    def _create_analytics_tab(self) -> None:
        """Create analytics tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📈 Analytics")
        
        # Create analytics components
        analytics_frame = ttk.LabelFrame(tab, text="Performance Analytics", padding=10)
        analytics_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Performance metrics
        metrics_frame = ttk.LabelFrame(analytics_frame, text="Performance Metrics", padding=5)
        metrics_frame.pack(fill='x', pady=5)
        
        metrics = [
            ("Total Return:", "12.5%", "green"),
            ("Win Rate:", "62.5%", "green"),
            ("Sharpe Ratio:", "1.85", "green"),
            ("Max Drawdown:", "8.2%", "orange"),
            ("Profit Factor:", "2.34", "green"),
        ]
        
        for label, value, color in metrics:
            mf = ttk.Frame(metrics_frame)
            mf.pack(fill='x', pady=2)
            ttk.Label(mf, text=label, font=('Arial', 9)).pack(side='left', padx=5)
            ttk.Label(mf, text=value, foreground=color, font=('Arial', 9, 'bold')).pack(side='left', padx=10)
        
        # Trade history
        history_frame = ttk.LabelFrame(analytics_frame, text="Trade History (Last 5)", padding=5)
        history_frame.pack(fill='both', expand=True, pady=5)
        
        cols = ("Entry", "Exit", "P&L", "Return")
        tree = ttk.Treeview(history_frame, columns=cols, height=5)
        tree.column("#0", width=100)
        tree.column("Entry", width=80)
        tree.column("Exit", width=80)
        tree.column("P&L", width=80)
        tree.column("Return", width=80)
        tree.heading("#0", text="Symbol")
        tree.heading("Entry", text="Entry")
        tree.heading("Exit", text="Exit")
        tree.heading("P&L", text="P&L $")
        tree.heading("Return", text="Return %")
        
        # Sample data
        sample_trades = [
            ("SOLUSDT", "150.23", "152.45", "+22.22", "+1.5%"),
            ("BTCUSDT", "43500", "43800", "+300", "+0.7%"),
            ("ETHUSDT", "2200", "2150", "-50", "-2.3%"),
        ]
        for i, (sym, entry, exit_p, pnl, ret) in enumerate(sample_trades):
            tree.insert("", i, text=sym, values=(entry, exit_p, pnl, ret))
        
        tree.pack(fill='both', expand=True)
    
    def _create_ml_monitor_tab(self) -> None:
        """Create ML monitoring tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🤖 ML Monitor")
        
        ml_frame = ttk.LabelFrame(tab, text="Machine Learning Model Metrics", padding=10)
        ml_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Model metrics
        metrics_frame = ttk.LabelFrame(ml_frame, text="Model Performance", padding=5)
        metrics_frame.pack(fill='x', pady=5)
        
        ml_metrics = [
            ("Accuracy:", "87.5%", "green"),
            ("Precision:", "85.2%", "green"),
            ("Recall:", "88.9%", "green"),
            ("F1 Score:", "0.869", "green"),
            ("ROC AUC:", "0.925", "green"),
        ]
        
        for label, value, color in ml_metrics:
            mf = ttk.Frame(metrics_frame)
            mf.pack(fill='x', pady=2)
            ttk.Label(mf, text=label, font=('Arial', 9)).pack(side='left', padx=5)
            ttk.Label(mf, text=value, foreground=color, font=('Arial', 9, 'bold')).pack(side='left', padx=10)
        
        # Predictions
        pred_frame = ttk.LabelFrame(ml_frame, text="Recent Predictions", padding=5)
        pred_frame.pack(fill='both', expand=True, pady=5)
        
        cols = ("Time", "Prediction", "Confidence", "Actual")
        pred_tree = ttk.Treeview(pred_frame, columns=cols, height=6)
        pred_tree.column("#0", width=100)
        pred_tree.column("Time", width=80)
        pred_tree.column("Prediction", width=80)
        pred_tree.column("Confidence", width=100)
        pred_tree.column("Actual", width=80)
        pred_tree.heading("#0", text="ID")
        pred_tree.heading("Time", text="Time")
        pred_tree.heading("Prediction", text="Prediction")
        pred_tree.heading("Confidence", text="Confidence")
        pred_tree.heading("Actual", text="Actual")
        
        pred_tree.pack(fill='both', expand=True)
    
    def _create_backtest_tab(self) -> None:
        """Create backtest tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📉 Backtest")
        
        backtest_frame = ttk.LabelFrame(tab, text="Backtest Results", padding=10)
        backtest_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Backtest controls
        ctrl_frame = ttk.LabelFrame(backtest_frame, text="Configuration", padding=5)
        ctrl_frame.pack(fill='x', pady=5)
        
        cf = ttk.Frame(ctrl_frame)
        cf.pack(fill='x', pady=2)
        ttk.Label(cf, text="Symbol:").pack(side='left', padx=5)
        sym_combo = ttk.Combobox(cf, values=SYMBOLS, width=12, state='readonly')
        sym_combo.pack(side='left', padx=5)
        sym_combo.set('SOLUSDT')
        
        cf2 = ttk.Frame(ctrl_frame)
        cf2.pack(fill='x', pady=2)
        ttk.Label(cf2, text="Days:").pack(side='left', padx=5)
        days_spin = ttk.Spinbox(cf2, from_=1, to=365, width=10)
        days_spin.set(30)
        days_spin.pack(side='left', padx=5)
        
        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="Run Backtest", command=self._start_backtest).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Export Results").pack(side='left', padx=5)
        
        # Results
        res_frame = ttk.LabelFrame(backtest_frame, text="Results", padding=5)
        res_frame.pack(fill='both', expand=True, pady=5)
        
        backtest_results = [
            ("Total Trades", "45"),
            ("Winning Trades", "28"),
            ("Losing Trades", "17"),
            ("Return", "-12.46%"),
            ("Win Rate", "62.2%"),
            ("Profit Factor", "1.85"),
            ("Max Drawdown", "18.5%"),
            ("Sharpe Ratio", "0.45"),
        ]
        
        for label, value in backtest_results:
            rf = ttk.Frame(res_frame)
            rf.pack(fill='x', pady=2)
            ttk.Label(rf, text=f"{label}:", font=('Arial', 9)).pack(side='left', padx=5)
            color = "red" if "%" in value and "-" in value else "green"
            ttk.Label(rf, text=value, foreground=color, font=('Arial', 9, 'bold')).pack(side='left', padx=10)

    def _create_dashboard_tab(self) -> None:
        """Create dashboard with equity curve"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📊 Dashboard")
        
        # Equity curve chart
        ch = tk.LabelFrame(tab, text="Equity Curve", bg="#1a1a1a",
                          fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        ch.pack(pady=10, padx=20, fill='both', expand=True)

        self.fig, self.ax = plt.subplots(figsize=(GUIConfig.CHART_WIDTH, GUIConfig.CHART_HEIGHT), 
                                         facecolor="#1a1a1a")
        self.ax.set_facecolor('#2d2d2d')
        self.canvas = FigureCanvasTkAgg(self.fig, master=ch)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.toolbar = NavigationToolbar2Tk(self.canvas, ch)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def _create_risk_settings_tab(self) -> None:
        """Create risk settings configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Risk Settings")

        frame = tk.Frame(tab, bg="#1a1a1a")
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        tk.Label(frame, text="Advanced Risk Settings", fg='white', bg="#1a1a1a",
                 font=('Arial', 14, 'bold')).pack(pady=10)

        # Risk per trade
        r1 = tk.Frame(frame, bg="#1a1a1a")
        r1.pack(fill='x', pady=5)
        tk.Label(r1, text="Risk per Trade (%):", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 10)).pack(side='left')
        self.risk_var = tk.DoubleVar(value=RiskConfig.RISK_PER_TRADE * 100)
        self.risk_scl = ttk.Scale(r1, from_=0.5, to=5.0, variable=self.risk_var,
                                 orient='horizontal', length=200)
        self.risk_scl.pack(side='left', padx=5, fill='x', expand=True)
        self.risk_val_lbl = tk.Label(r1, text="2.0%", fg='cyan', bg="#1a1a1a", width=5)
        self.risk_val_lbl.pack(side='left', padx=5)
        self.risk_var.trace('w', lambda *args: self.risk_val_lbl.config(text=f"{self.risk_var.get():.1f}%"))
        ToolTip(self.risk_scl, "Max % of capital risked per trade")

        # Stop-Loss ATR multiplier
        r2 = tk.Frame(frame, bg="#1a1a1a")
        r2.pack(fill='x', pady=5)
        tk.Label(r2, text="Stop-Loss ATR Multiplier:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 10)).pack(side='left')
        self.sl_var = tk.DoubleVar(value=RiskConfig.STOP_LOSS_ATR_MULT)
        self.sl_scl = ttk.Scale(r2, from_=1.0, to=5.0, variable=self.sl_var,
                               orient='horizontal', length=200)
        self.sl_scl.pack(side='left', padx=5, fill='x', expand=True)
        self.sl_val_lbl = tk.Label(r2, text="2.0x", fg='cyan', bg="#1a1a1a", width=5)
        self.sl_val_lbl.pack(side='left', padx=5)
        self.sl_var.trace('w', lambda *args: self.sl_val_lbl.config(text=f"{self.sl_var.get():.1f}x"))
        ToolTip(self.sl_scl, "ATR multiplier for stop-loss")

        # Take Profit Risk-Reward
        r3 = tk.Frame(frame, bg="#1a1a1a")
        r3.pack(fill='x', pady=5)
        tk.Label(r3, text="Take Profit R:R:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 10)).pack(side='left')
        self.tp_var = tk.DoubleVar(value=RiskConfig.TAKE_PROFIT_RR)
        self.tp_scl = ttk.Scale(r3, from_=1.0, to=5.0, variable=self.tp_var,
                               orient='horizontal', length=200)
        self.tp_scl.pack(side='left', padx=5, fill='x', expand=True)
        self.tp_val_lbl = tk.Label(r3, text="2.0:1", fg='cyan', bg="#1a1a1a", width=5)
        self.tp_val_lbl.pack(side='left', padx=5)
        self.tp_var.trace('w', lambda *args: self.tp_val_lbl.config(text=f"{self.tp_var.get():.1f}:1"))
        ToolTip(self.tp_scl, "Risk-Reward ratio for take profit")

        # Max Drawdown
        r4 = tk.Frame(frame, bg="#1a1a1a")
        r4.pack(fill='x', pady=5)
        tk.Label(r4, text="Max Drawdown (%):", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 10)).pack(side='left')
        self.dd_var = tk.DoubleVar(value=RiskConfig.MAX_DRAWDOWN * 100)
        self.dd_scl = ttk.Scale(r4, from_=5.0, to=30.0, variable=self.dd_var,
                               orient='horizontal', length=200)
        self.dd_scl.pack(side='left', padx=5, fill='x', expand=True)
        self.dd_val_lbl = tk.Label(r4, text="15.0%", fg='cyan', bg="#1a1a1a", width=5)
        self.dd_val_lbl.pack(side='left', padx=5)
        self.dd_var.trace('w', lambda *args: self.dd_val_lbl.config(text=f"{self.dd_var.get():.1f}%"))
        ToolTip(self.dd_scl, "Max acceptable drawdown")

        # Daily loss limit
        r5 = tk.Frame(frame, bg="#1a1a1a")
        r5.pack(fill='x', pady=5)
        tk.Label(r5, text="Daily Loss Limit ($):", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 10)).pack(side='left')
        self.daily_var = tk.DoubleVar(value=RiskConfig.DAILY_LOSS_LIMIT)
        self.daily_ent = tk.Entry(r5, textvariable=self.daily_var, width=10,
                                 bg='#2d2d2d', fg='white')
        self.daily_ent.pack(side='left', padx=5)
        ToolTip(self.daily_ent, "Max $ loss per day before pause")

        # Apply button
        self.apply_btn = tk.Button(frame, text="Apply Settings",
                                  command=self._apply_risk_settings,
                                  bg='#9C27B0', fg='white', font=('Arial', 12, 'bold'), pady=10)
        self.apply_btn.pack(pady=20)

    def _create_market_analysis_tab(self) -> None:
        """Create market volatility analysis tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Market Analysis")

        frame = tk.Frame(tab, bg="#1a1a1a")
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        tk.Label(frame, text="Market Volatility Analysis", fg='white', bg="#1a1a1a",
                 font=('Arial', 14, 'bold')).pack(pady=10)

        # Analysis results display
        self.analysis_text = tk.Text(frame, height=20, width=80, bg='#2d2d2d',
                                     fg='white', font=('Courier', 10))
        self.analysis_text.pack(fill='both', expand=True, padx=10, pady=10)

        # Refresh button
        self.analysis_refresh_btn = tk.Button(frame, text="Analyze Current Market",
                                             command=self._refresh_market_analysis,
                                             bg='#2196F3', fg='white', font=('Arial', 11, 'bold'))
        self.analysis_refresh_btn.pack(pady=10)

    def _create_market_tracker_tab(self) -> None:
        """Create market tracker tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Market Tracker")

        frame = tk.Frame(tab, bg="#1a1a1a")
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        tk.Label(frame, text="Market Tracker - Gainers & Losers", fg='white', bg="#1a1a1a",
                 font=('Arial', 14, 'bold')).pack(pady=10)

        # Market data display
        self.tracker_text = tk.Text(frame, height=20, width=80, bg='#2d2d2d',
                                    fg='white', font=('Courier', 10))
        self.tracker_text.pack(fill='both', expand=True, padx=10, pady=10)

        # Refresh button
        self.tracker_refresh_btn = tk.Button(frame, text="Update Market Data",
                                            command=self._refresh_market_tracker,
                                            bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'))
        self.tracker_refresh_btn.pack(pady=10)

    # ==================== Event Handlers ====================
    def _update_environment(self, value: str) -> None:
        """Handle environment toggle"""
        is_testnet = bool(int(float(value)))
        self.is_testnet = is_testnet
        
        if is_testnet:
            self.env_lbl.config(text="TestNet", fg='yellow')
        else:
            self.env_lbl.config(text="LIVE", fg='red')
        
        reconnect_client(is_testnet)
        self.status_var.set(f"Switched to {'TestNet' if is_testnet else 'LIVE'}")

    def _start_backtest(self) -> None:
        """Start backtest in separate thread"""
        symbol = self.sym_var.get()
        self.status_var.set(f"Running backtest for {symbol}...")
        self.back_btn.config(state='disabled')
        
        threading.Thread(target=self._backtest_thread, args=(symbol,), daemon=True).start()

    def _backtest_thread(self, symbol: str) -> None:
        """Backtest thread worker"""
        try:
            results = run_backtest(symbol)
            equity_curve = results.get('equity_curve', [10000])
            self.root.after(0, lambda: self._update_equity_curve(equity_curve))
            final_balance = equity_curve[-1] if equity_curve else 10000.0
            self.root.after(0, lambda: self.balance_lbl.config(text=f"Balance: ${final_balance:.2f}"))
            
            msg = f"Backtest complete: {results.get('total_return', 0):.2%} return, {results.get('win_rate', 0):.1%} win rate"
            self.root.after(0, lambda: self.status_var.set(msg))
            self.root.after(0, lambda: self.back_btn.config(state='normal'))
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            self.root.after(0, lambda: self.status_var.set(f"Backtest error: {e}"))
            self.root.after(0, lambda: self.back_btn.config(state='normal'))

    def _start_live(self) -> None:
        """Start live trading"""
        if not self.is_running_flag:
            symbol = self.sym_var.get()
            self.is_running_flag = True
            self.live_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.status_var.set(f"Live trading active for {symbol} ({'TestNet' if self.is_testnet else 'LIVE'})")
            
            self.trading_thread = threading.Thread(target=lambda: live_trading_loop(symbol, self._update_gui_live),
                                                   daemon=True)
            self.trading_thread.start()

    def _stop_bot(self) -> None:
        """Stop bot"""
        global is_running
        is_running = False
        self.is_running_flag = False
        self.live_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_var.set("Bot stopped")

    def _manual_switch(self) -> None:
        """Manually switch symbol"""
        sym = self.sym_var.get()
        self.current_symbol = sym
        self.sym_lbl.config(text=f"Current: {sym}")
        self.status_var.set(f"Manually switched to {sym}")

    def _apply_risk_settings(self) -> None:
        """Apply risk settings"""
        new_vals = {
            'risk_per_trade': self.risk_var.get() / 100,
            'stop_loss_mult': self.sl_var.get(),
            'take_profit_rr': self.tp_var.get(),
            'max_dd': self.dd_var.get() / 100,
            'daily_loss': self.daily_var.get(),
        }
        update_risk_config(new_vals)
        self.status_var.set("Risk settings applied successfully")

    def _update_equity_curve(self, equity_data: List[float]) -> None:
        """Update equity curve chart"""
        self.ax.clear()
        self.ax.plot(equity_data, color='lime', linewidth=2)
        self.ax.set_title("Equity Curve", color='white', fontsize=14)
        self.ax.set_xlabel("Time", color='white')
        self.ax.set_ylabel("Balance ($)", color='white')
        self.ax.tick_params(colors='white')
        self.ax.set_facecolor('#2d2d2d')
        self.ax.grid(True, alpha=0.3)
        self.fig.tight_layout()
        self.canvas.draw()

    def _update_gui_live(self, balance: float, equity_curve: List[float]) -> None:
        """Update GUI during live trading"""
        self.root.after(0, lambda: self.balance_lbl.config(text=f"Balance: ${balance:.2f}"))
        self.root.after(0, lambda: self._update_equity_curve(equity_curve))

    def _refresh_market_analysis(self) -> None:
        """Refresh market analysis"""
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, "Analyzing market volatility...\n\n")
        
        threading.Thread(target=self._analysis_thread, daemon=True).start()

    def _analysis_thread(self) -> None:
        """Market analysis thread worker"""
        try:
            symbol = self.current_symbol
            df = get_historical_data_with_indicators(symbol, days=30)
            analysis = self.vol_analyzer.analyze_volatility(symbol, df)
            recommendation = self.vol_analyzer.get_trading_recommendation(symbol, analysis.get('current_volatility', 0))
            
            text = f"Symbol: {symbol}\n"
            text += f"Current Volatility: {analysis.get('current_volatility', 0):.4f}\n"
            text += f"Garman-Klass Vol: {analysis.get('garman_klass_vol', 0):.4f}\n"
            text += f"Parkinson Vol: {analysis.get('parkinson_vol', 0):.4f}\n"
            text += f"Volatility Regime: {analysis.get('volatility_regime', 'N/A')}\n"
            text += f"\nTrading Recommendation:\n"
            text += f"  Score: {recommendation.get('trading_score', 0)}/100\n"
            text += f"  Recommendation: {recommendation.get('recommendation', 'N/A')}\n"
            text += f"  Current Hour: {recommendation.get('current_hour', 0)}\n"
            text += f"  High Vol Window: {recommendation.get('is_high_vol_window', False)}\n"
            text += f"  Low Vol Window: {recommendation.get('is_low_vol_window', False)}\n"
            
            self.root.after(0, lambda: self._display_analysis(text))
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            self.root.after(0, lambda: self._display_analysis(f"Analysis error: {str(e)}"))

    def _display_analysis(self, text: str) -> None:
        """Display analysis results"""
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, text)

    def _refresh_market_tracker(self) -> None:
        """Refresh market tracker"""
        self.tracker_text.delete(1.0, tk.END)
        self.tracker_text.insert(tk.END, "Updating market data...\n\n")
        
        threading.Thread(target=self._tracker_thread, daemon=True).start()

    def _tracker_thread(self) -> None:
        """Market tracker thread worker"""
        try:
            self.market_tracker.update_market_data()
            
            text = "TOP GAINERS:\n"
            for pair in self.market_tracker.get_gainers()[:5]:
                text += f"  {pair.get('symbol', 'N/A')}: +{pair.get('change', 0):.2f}% @ ${pair.get('price', 0):.2f}\n"
            
            text += "\nTOP LOSERS:\n"
            for pair in self.market_tracker.get_losers()[:5]:
                text += f"  {pair.get('symbol', 'N/A')}: {pair.get('change', 0):.2f}% @ ${pair.get('price', 0):.2f}\n"
            
            text += "\nNEW LISTINGS:\n"
            for pair in self.market_tracker.get_new_listings()[:5]:
                text += f"  {pair.get('symbol', 'N/A')}: ${pair.get('price', 0):.2f}\n"
            
            self.root.after(0, lambda: self._display_tracker(text))
        except Exception as e:
            logger.error(f"Tracker error: {e}")
            self.root.after(0, lambda: self._display_tracker(f"Tracker error: {str(e)}"))

    def _display_tracker(self, text: str) -> None:
        """Display tracker results"""
        self.tracker_text.delete(1.0, tk.END)
        self.tracker_text.insert(tk.END, text)

    def _open_settings_menu(self) -> None:
        """Open settings menu (hamburger menu)"""
        try:
            from gui_settings_menu import BotSettingsMenu
            BotSettingsMenu(self.root)
        except ImportError:
            messagebox.showwarning("Settings", "Settings menu not available")
        except Exception as e:
            messagebox.showerror("Settings Error", f"Error opening settings: {e}")
    
    def _update_environment(self, value: str) -> None:
        """Update trading environment"""
        val = int(float(value))
        if val == 1:
            self.is_testnet = True
            self.env_lbl.config(text="TestNet", foreground='yellow')
            self.status_var.set("Switched to TestNet")
        else:
            self.is_testnet = False
            self.env_lbl.config(text="LIVE", foreground='red')
            self.status_var.set("⚠️  SWITCHED TO LIVE TRADING ⚠️")


# ==================== Main Application ====================
def main() -> None:
    """Launch the GUI application"""
    root = tk.Tk()
    app = CryptoBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()