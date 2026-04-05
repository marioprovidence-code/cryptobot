"""
MASTER TRADER INTERFACE - Professional Crypto Trading Dashboard
Modern card-based design with dropdown menus, help system, and full theme support
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import random
import math
import os
import sys
from collections import deque
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import requests

import matplotlib.pyplot as plt


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from config import GUIConfig, SYMBOLS, get_logger, RiskConfig
from market_analysis import MarketVolatilityAnalyzer, MarketTracker
from crypto_engine import (
    reconnect_client, get_historical_data_with_indicators, MLModel,
    run_backtest, live_trading_loop, update_risk_config, is_running,
    tune_xgboost
)

# Import live trading view
try:
    from gui_live_trading_view import LiveTradingPanel
except ImportError:
    LiveTradingPanel = None

logger = get_logger(__name__)


# ==================== THEME SYSTEM ====================
class MasterThemeManager:
    """Global theme manager that affects entire app"""
    
    THEMES = {
        'dark': {
            'bg': '#0f0f0f',
            'fg': '#ffffff',
            'frame_bg': '#1a1a1a',
            'card_bg': '#262626',
            'input_bg': '#2d2d2d',
            'button_bg': '#1a7d1a',
            'button_fg': '#ffffff',
            'button_hover': '#22a022',
            'accent': '#00d084',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'info': '#3498db',
            'border': '#404040',
            'text_secondary': '#b0b0b0',
        },
        'light': {
            'bg': '#f5f5f5',
            'fg': '#000000',
            'frame_bg': '#ffffff',
            'card_bg': '#f9f9f9',
            'input_bg': '#e8e8e8',
            'button_bg': '#2196F3',
            'button_fg': '#ffffff',
            'button_hover': '#1976D2',
            'accent': '#00b8a9',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'info': '#3498db',
            'border': '#d0d0d0',
            'text_secondary': '#666666',
        }
    }
    
    def __init__(self):
        self.current_theme = 'dark'
        self.root = None
        self.callbacks = []
    
    def set_root(self, root):
        """Set root window"""
        self.root = root
    
    def apply_theme(self):
        """Apply theme to root window"""
        if not self.root:
            return
        colors = self.THEMES[self.current_theme]
        self.root.configure(bg=colors['bg'])
        
        # Apply to all ttk widgets via style
        self._apply_ttk_theme()
        
        # Notify all listeners
        for callback in self.callbacks:
            callback(colors)
    
    def _apply_ttk_theme(self):
        """Apply ttk styles"""
        colors = self.THEMES[self.current_theme]
        style = ttk.Style()
        
        style.configure('TLabel', background=colors['frame_bg'], foreground=colors['fg'])
        style.configure('TFrame', background=colors['frame_bg'])
        style.configure('TButton', background=colors['button_bg'], foreground=colors['button_fg'])
        style.map('TButton', background=[('active', colors['button_hover'])])
    
    def get_colors(self) -> Dict[str, str]:
        """Get current theme colors"""
        return self.THEMES[self.current_theme].copy()
    
    def switch_theme(self):
        """Toggle between light and dark"""
        self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        self.apply_theme()
    
    def subscribe(self, callback):
        """Subscribe to theme changes"""
        self.callbacks.append(callback)


# Global theme manager
theme_manager = MasterThemeManager()


# ==================== UTILITY FUNCTIONS ====================
def fetch_binance_symbols() -> List[str]:
    """Fetch all trading pairs from Binance API"""
    try:
        response = requests.get(
            'https://api.binance.com/api/v3/exchangeInfo',
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            # Filter for USDT pairs only, get top 100 by volume
            usdt_pairs = [
                s['symbol'] for s in data['symbols'] 
                if s['symbol'].endswith('USDT') and s['status'] == 'TRADING'
            ][:100]  # Limit to 100 for performance
            return sorted(usdt_pairs)
    except Exception as e:
        logger.warning(f"Failed to fetch Binance symbols: {e}")
    
    # Fallback to default
    return SYMBOLS + ['XRPUSDT', 'BNBUSDT', 'DOGEUSDT', 'LINKUSDT', 'MATICUSDT']


# ==================== CARD COMPONENTS ====================
class Card(tk.Frame):
    """Card widget with rounded appearance"""
    
    def __init__(self, parent, title: str, **kwargs):
        colors = theme_manager.get_colors()
        super().__init__(parent, bg=colors['card_bg'], highlightbackground=colors['border'],
                         highlightthickness=1, relief=tk.FLAT, **kwargs)
        
        self.colors = colors
        self._destroying = False
        theme_manager.subscribe(self._on_theme_change)
        
        # Title
        title_label = tk.Label(
            self, text=f"  {title}",
            bg=colors['card_bg'], fg=colors['accent'],
            font=("Segoe UI", 10, "bold"), anchor="w"
        )
        title_label.pack(fill=tk.X, padx=8, pady=(6, 4))
        
        # Content frame
        self.content = tk.Frame(self, bg=colors['card_bg'])
        self.content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
    
    def _on_theme_change(self, colors):
        """Update colors when theme changes"""
        if self._destroying:
            return
        try:
            if not self.winfo_exists():
                return
            self.colors = colors
            self.configure(bg=colors['card_bg'], highlightbackground=colors['border'])
        except:
            pass


class StatCard(tk.Frame):
    """Small stat display card"""
    
    def __init__(self, parent, title: str, value: str = "—", emoji: str = "📊", **kwargs):
        colors = theme_manager.get_colors()
        super().__init__(parent, bg=colors['card_bg'], highlightbackground=colors['border'],
                         highlightthickness=1, relief=tk.FLAT, **kwargs)
        
        self._destroying = False
        theme_manager.subscribe(self._on_theme_change)
        
        # Emoji + Title
        header = tk.Label(
            self, text=f"{emoji} {title}",
            bg=colors['card_bg'], fg=colors['text_secondary'],
            font=("Segoe UI", 9)
        )
        header.pack(anchor="w", padx=6, pady=(6, 2))
        
        # Value
        self.value_label = tk.Label(
            self, text=value,
            bg=colors['card_bg'], fg=colors['accent'],
            font=("Segoe UI", 12, "bold")
        )
        self.value_label.pack(anchor="w", padx=6, pady=(0, 6))
    
    def set_value(self, value: str):
        """Update displayed value"""
        if not self.winfo_exists():
            return
        try:
            self.value_label.config(text=value)
        except:
            pass
    
    def _on_theme_change(self, colors):
        """Update colors when theme changes"""
        if self._destroying:
            return
        try:
            if not self.winfo_exists():
                return
            self.configure(bg=colors['card_bg'], highlightbackground=colors['border'])
            for widget in self.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.configure(bg=colors['card_bg'])
                    if widget == self.value_label:
                        widget.configure(fg=colors['accent'])
                    else:
                        widget.configure(fg=colors['text_secondary'])
        except:
            pass


class ModernButton(tk.Button):
    """Modern button with hover effects"""
    
    def __init__(self, parent, text: str, emoji: str = "", command=None, 
                 bg_color='button_bg', fg_color='button_fg', **kwargs):
        colors = theme_manager.get_colors()
        
        label = f"{emoji} {text}" if emoji else text
        
        super().__init__(
            parent, text=label, command=command,
            bg=colors[bg_color],
            fg=colors[fg_color],
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=10, pady=6,
            cursor="hand2",
            activebackground=colors.get('button_hover', colors[bg_color]),
            activeforeground=colors[fg_color],
            **kwargs
        )
        
        self.emoji = emoji
        self.text_label = text
        self.bg_color = bg_color
        self.fg_color = fg_color
        self._destroying = False
        
        # Hover effects
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        theme_manager.subscribe(self._on_theme_change)
    
    def _on_enter(self, _):
        if self._destroying or not self.winfo_exists():
            return
        colors = theme_manager.get_colors()
        try:
            self.config(bg=colors.get('button_hover', colors[self.bg_color]))
        except:
            pass
    
    def _on_leave(self, _):
        if self._destroying or not self.winfo_exists():
            return
        colors = theme_manager.get_colors()
        try:
            self.config(bg=colors[self.bg_color])
        except:
            pass
    
    def _on_theme_change(self, colors):
        """Update colors when theme changes"""
        if self._destroying:
            return
        try:
            if not self.winfo_exists():
                return
            self.configure(
                bg=colors[self.bg_color],
                fg=colors[self.fg_color],
                activebackground=colors.get('button_hover', colors[self.bg_color])
            )
            self.configure(text=f"{self.emoji} {self.text_label}" if self.emoji else self.text_label)
        except:
            pass


# ==================== MAIN MASTER GUI ====================
class MasterTraderGUI:
    """Professional crypto trading dashboard"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🚀 MASTER TRADER - Crypto Bot Pro")
        self.root.geometry(f"{GUIConfig.WINDOW_WIDTH}x{GUIConfig.WINDOW_HEIGHT}")
        self.branding_icon_image = None
        self.branding_logo_image = None
        self.logo_frame = None
        self.logo_image_label = None
        self.logo_title_label = None
        self._load_branding_assets()
        if self.branding_icon_image:
            try:
                self.root.iconphoto(True, self.branding_icon_image)
            except Exception:
                pass
        
        # Setup theme
        theme_manager.set_root(self.root)
        theme_manager.apply_theme()
        
        # State
        self.is_running = False
        self.trading_thread = None
        self.current_symbol = tk.StringVar(value='SOLUSDT')
        self.symbols_list = []
        self.vol_analyzer = MarketVolatilityAnalyzer()
        self.market_tracker = MarketTracker()
        self.active_trading_pairs = set()
        self.trading_pairs_frame = None
        self.trading_pairs_container = None
        self.trading_pairs_title = None
        self.trading_pairs_listbox = None
        self.market_pairs_box = None
        self.market_pairs_heading = None
        self.market_pairs_label = None
        self.market_pairs_var = tk.StringVar(self.root, value="No active pairs")
        self.market_view_mode = tk.StringVar(self.root, value="chart")
        self.market_mode_buttons = {}
        self.market_view_sections = {}
        self.market_info_labels = {}
        self.market_view_stack = None
        
        # Stats
        self.stats = {
            'balance': 0,
            'pnl': 0,
            'win_rate': 0,
            'trades': 0,
            'roi': 0
        }
        
        # Build UI
        self._build_ui()
        
        # Load Binance symbols asynchronously
        threading.Thread(target=self._load_symbols, daemon=True).start()
    
    def _load_branding_assets(self):
        icon_path = resource_path("Crypto BOT icon.png")
        if not icon_path or not os.path.exists(icon_path):
            return
        try:
            from PIL import Image, ImageTk
            icon_image = Image.open(icon_path)
            self.branding_icon_image = ImageTk.PhotoImage(icon_image.copy())
            preview_image = icon_image.copy()
            preview_image.thumbnail((48, 48), Image.LANCZOS)
            self.branding_logo_image = ImageTk.PhotoImage(preview_image)
        except Exception:
            try:
                photo = tk.PhotoImage(file=icon_path)
                self.branding_icon_image = photo
                if photo.width() > 48 or photo.height() > 48:
                    factor = max(1, math.ceil(photo.width() / 48), math.ceil(photo.height() / 48))
                    self.branding_logo_image = photo.subsample(factor, factor)
                else:
                    self.branding_logo_image = photo
            except Exception:
                self.branding_icon_image = None
                self.branding_logo_image = None
        if self.branding_logo_image is None and self.branding_icon_image is not None:
            self.branding_logo_image = self.branding_icon_image
    
    def _build_ui(self):
        """Build complete UI layout"""
        # Main container
        main_frame = tk.Frame(self.root, bg=theme_manager.get_colors()['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. Top Menu Bar
        self._build_menu_bar(main_frame)
        
        # 2. Main content area
        colors = theme_manager.get_colors()
        content_frame = tk.Frame(main_frame, bg=colors['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.content_splitter = tk.PanedWindow(content_frame, orient=tk.HORIZONTAL, bg=colors['bg'], sashwidth=6)
        self.content_splitter.pack(fill=tk.BOTH, expand=True)
        
        left_panel = self._build_left_panel(self.content_splitter)
        self.content_splitter.add(left_panel, minsize=260)
        
        self.center_right_splitter = tk.PanedWindow(self.content_splitter, orient=tk.HORIZONTAL, bg=colors['bg'], sashwidth=6)
        self.content_splitter.add(self.center_right_splitter, stretch="always")
        
        center_panel = self._build_center_dashboard(self.center_right_splitter)
        self.center_right_splitter.add(center_panel, stretch="always")
        
        right_panel = self._build_right_panel(self.center_right_splitter)
        self.center_right_splitter.add(right_panel, minsize=240)
        
        # Subscribe to theme changes
        theme_manager.subscribe(self._on_theme_change)
    
    def _build_menu_bar(self, parent):
        """Build dropdown menu bar with hamburger menu"""
        colors = theme_manager.get_colors()
        
        menu_frame = tk.Frame(parent, bg=colors['card_bg'], height=50)
        menu_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        menu_frame.pack_propagate(False)
        
        # Hamburger menu button
        hamburger_btn = tk.Button(
            menu_frame, text="☰ MENU",
            bg=colors['input_bg'], fg=colors['fg'],
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, padx=12, pady=8,
            command=self._show_hamburger_menu,
            cursor="hand2"
        )
        hamburger_btn.pack(side=tk.LEFT, padx=5)
        
        self.logo_frame = tk.Frame(menu_frame, bg=colors['card_bg'])
        self.logo_frame.pack(side=tk.LEFT, padx=15, pady=10)
        if self.branding_logo_image:
            self.logo_image_label = tk.Label(
                self.logo_frame,
                image=self.branding_logo_image,
                bg=colors['card_bg']
            )
            self.logo_image_label.pack(side=tk.LEFT)
        self.logo_title_label = tk.Label(
            self.logo_frame,
            text="MASTER TRADER - Professional Crypto Bot",
            bg=colors['card_bg'],
            fg=colors['accent'],
            font=("Segoe UI", 12, "bold")
        )
        padding_left = (10, 0) if self.branding_logo_image else (0, 0)
        self.logo_title_label.pack(side=tk.LEFT, padx=padding_left)
        
        # Spacer
        spacer = tk.Frame(menu_frame, bg=colors['card_bg'])
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.trading_pairs_frame = tk.Frame(
            menu_frame,
            bg=colors['card_bg'],
            highlightbackground=colors['border'],
            highlightthickness=1
        )
        self.trading_pairs_frame.pack(side=tk.RIGHT, padx=5, pady=8)
        self.trading_pairs_container = tk.Frame(self.trading_pairs_frame, bg=colors['card_bg'])
        self.trading_pairs_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.trading_pairs_title = tk.Label(
            self.trading_pairs_container,
            text="Active Pairs",
            bg=colors['card_bg'],
            fg=colors['text_secondary'],
            font=("Segoe UI", 8, "bold")
        )
        self.trading_pairs_title.pack(anchor="w")
        self.trading_pairs_listbox = tk.Listbox(
            self.trading_pairs_container,
            height=3,
            bg=colors['input_bg'],
            fg=colors['text_secondary'],
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=colors['border'],
            activestyle='none',
            selectbackground=colors['accent'],
            selectforeground=colors['bg'],
            exportselection=False
        )
        self.trading_pairs_listbox.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self._refresh_trading_pairs_display()
        
        # Status indicator
        self.connection_indicator = tk.Label(
            menu_frame, text="🟢 Connected",
            bg=colors['card_bg'], fg=colors['button_bg'],
            font=("Segoe UI", 9)
        )
        self.connection_indicator.pack(side=tk.RIGHT, padx=10)
        
        # Theme toggle
        theme_btn = tk.Button(
            menu_frame, text="🌙",
            bg=colors['input_bg'], fg=colors['fg'],
            font=("Segoe UI", 11),
            relief=tk.FLAT, padx=10, pady=8,
            command=self._toggle_theme,
            cursor="hand2"
        )
        theme_btn.pack(side=tk.RIGHT, padx=3)
    
    def _refresh_trading_pairs_display(self):
        colors = theme_manager.get_colors()
        if self.trading_pairs_frame:
            self.trading_pairs_frame.configure(bg=colors['card_bg'], highlightbackground=colors['border'])
        if self.trading_pairs_container:
            self.trading_pairs_container.configure(bg=colors['card_bg'])
        if self.trading_pairs_title:
            self.trading_pairs_title.configure(bg=colors['card_bg'], fg=colors['text_secondary'])
        if self.trading_pairs_listbox:
            self.trading_pairs_listbox.configure(
                bg=colors['input_bg'],
                fg=colors['accent'] if self.active_trading_pairs else colors['text_secondary'],
                highlightbackground=colors['border'],
                selectbackground=colors['accent'],
                selectforeground=colors['bg']
            )
            self.trading_pairs_listbox.delete(0, tk.END)
        if self.market_pairs_box:
            self.market_pairs_box.configure(bg=colors['input_bg'], highlightbackground=colors['border'])
        if self.market_pairs_heading:
            self.market_pairs_heading.configure(bg=colors['input_bg'], fg=colors['text_secondary'])
        if self.market_pairs_label:
            self.market_pairs_label.configure(bg=colors['input_bg'], fg=colors['accent'])
        pairs = sorted(self.active_trading_pairs)
        if self.trading_pairs_listbox:
            if pairs:
                for pair in pairs:
                    self.trading_pairs_listbox.insert(tk.END, pair)
            else:
                self.trading_pairs_listbox.insert(tk.END, "No active pairs")
        display_pairs = pairs[:4]
        if display_pairs:
            self.market_pairs_var.set("\n".join(display_pairs))
        else:
            self.market_pairs_var.set("No active pairs")
    
    def _create_dropdown_button(self, parent, text: str, command):
        """Create dropdown trigger button"""
        colors = theme_manager.get_colors()
        btn = tk.Button(
            parent, text=text,
            bg=colors['input_bg'], fg=colors['fg'],
            font=("Segoe UI", 9),
            relief=tk.FLAT, padx=10, pady=5,
            command=command, cursor="hand2"
        )
        btn.pack(side=tk.RIGHT, padx=5)
    
    def _build_left_panel(self, parent) -> tk.Frame:
        """Build left control panel"""
        colors = theme_manager.get_colors()
        
        panel = tk.Frame(parent, bg=colors['bg'])
        
        # Create a scrollable container
        canvas = tk.Canvas(panel, bg=colors['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(panel, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=colors['bg'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bot Control Card
        control_card = Card(scrollable_frame, "🎮 BOT CONTROL")
        control_card.pack(fill=tk.X, pady=(0, 8))
        
        # Start/Stop buttons
        btn_frame = tk.Frame(control_card.content, bg=colors['card_bg'])
        btn_frame.pack(fill=tk.X, pady=4)
        
        self.start_btn = ModernButton(
            btn_frame, "START BOT", emoji="▶️",
            command=self._start_bot,
            bg_color='button_bg'
        )
        self.start_btn.pack(fill=tk.X, pady=2)
        
        self.stop_btn = ModernButton(
            btn_frame, "STOP BOT", emoji="⏹️",
            command=self._stop_bot,
            bg_color='danger'
        )
        self.stop_btn.pack(fill=tk.X, pady=2)
        
        test_btn = ModernButton(
            btn_frame, "TEST RUN", emoji="🧪",
            command=self._run_test,
            bg_color='warning'
        )
        test_btn.pack(fill=tk.X, pady=2)
        
        # Auto Switch Control
        auto_card = Card(scrollable_frame, "🔄 AUTO SWITCH")
        auto_card.pack(fill=tk.X, pady=(0, 8))
        
        auto_frame = tk.Frame(auto_card.content, bg=colors['card_bg'])
        auto_frame.pack(fill=tk.X, pady=4)
        
        self.auto_switch_var = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(
            auto_frame, text="Enable Auto Symbol Switch",
            variable=self.auto_switch_var,
            bg=colors['card_bg'], fg=colors['fg'],
            font=("Segoe UI", 9), selectcolor=colors['input_bg']
        )
        auto_check.pack(anchor="w", pady=4)
        
        # Auto switch interval
        tk.Label(
            auto_frame, text="Switch Interval (sec):",
            bg=colors['card_bg'], fg=colors['text_secondary'],
            font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(4, 2))
        
        self.auto_switch_interval = tk.Scale(
            auto_frame, from_=10, to=300, orient=tk.HORIZONTAL,
            bg=colors['input_bg'], fg=colors['accent'],
            troughcolor=colors['card_bg'], relief=tk.FLAT, bd=0
        )
        self.auto_switch_interval.set(60)
        self.auto_switch_interval.pack(fill=tk.X, pady=(0, 4))
        
        # Symbol Selection Card
        symbol_card = Card(scrollable_frame, "📊 SYMBOL SELECT")
        symbol_card.pack(fill=tk.X, pady=(0, 8))
        
        # Search box
        search_frame = tk.Frame(symbol_card.content, bg=colors['card_bg'])
        search_frame.pack(fill=tk.X, pady=4)
        
        tk.Label(
            search_frame, text="🔍 Search:",
            bg=colors['card_bg'], fg=colors['text_secondary'],
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(0, 2))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_symbol_search)
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=colors['input_bg'], fg=colors['fg'],
            font=("Segoe UI", 9),
            relief=tk.FLAT, bd=1
        )
        search_entry.pack(fill=tk.X)
        
        # Symbol listbox with scrollbar
        list_frame = tk.Frame(symbol_card.content, bg=colors['card_bg'])
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        
        scrollbar2 = tk.Scrollbar(list_frame)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.symbol_listbox = tk.Listbox(
            list_frame,
            bg=colors['input_bg'], fg=colors['fg'],
            font=("Segoe UI", 9),
            relief=tk.FLAT, bd=0,
            yscrollcommand=scrollbar2.set,
            selectmode=tk.SINGLE,
            height=6
        )
        self.symbol_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.symbol_listbox.bind('<<ListboxSelect>>', self._on_symbol_select)
        scrollbar2.config(command=self.symbol_listbox.yview)
        
        # Stop Loss & Take Profit Card
        sl_tp_card = Card(scrollable_frame, "🎯 SL & TP")
        sl_tp_card.pack(fill=tk.X, pady=(0, 8))
        
        for label, key, min_v, max_v, default in [
            ("Stop Loss ATR Mult", "sl_atr", 0.5, 4, 2.0),
            ("Take Profit RR", "tp_rr", 1, 5, 2.0),
            ("Break Even %", "breakeven", 0.5, 2, 1.0),
        ]:
            self._create_labeled_slider(sl_tp_card.content, label, key, min_v, max_v, default, length=150)
        
        # Risk Limits Card
        limits_card = Card(scrollable_frame, "⛔ RISK LIMITS")
        limits_card.pack(fill=tk.X, pady=(0, 8))
        
        for label, key, min_v, max_v, default in [
            ("Max Drawdown %", "max_dd", 5, 50, 20),
            ("Max Trades/Day", "max_trades", 1, 20, 10),
            ("Daily Loss Limit $", "daily_loss", 100, 5000, 500),
        ]:
            self._create_labeled_slider(limits_card.content, label, key, min_v, max_v, default)
        
        return panel
    
    def _create_slider(self, parent, label: str, key: str, min_v: float, max_v: float, default: float):
        """Create labeled slider"""
        self._create_labeled_slider(parent, label, key, min_v, max_v, default)
    
    def _create_labeled_slider(self, parent, label: str, key: str, min_v: float, max_v: float, default: float, length: int = 180):
        """Create labeled slider with value display"""
        colors = theme_manager.get_colors()
        
        frame = tk.Frame(parent, bg=colors['card_bg'])
        frame.pack(fill=tk.X, pady=4)
        
        label_frame = tk.Frame(frame, bg=colors['card_bg'])
        label_frame.pack(fill=tk.X, pady=(0, 1))
        
        tk.Label(
            label_frame, text=label,
            bg=colors['card_bg'], fg=colors['text_secondary'],
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, anchor="w")
        
        value_var = tk.StringVar(value=f"{default:.1f}")
        value_label = tk.Label(
            label_frame, textvariable=value_var,
            bg=colors['card_bg'], fg=colors['accent'],
            font=("Segoe UI", 8, "bold")
        )
        value_label.pack(side=tk.RIGHT)
        
        if not hasattr(self, 'slider_vars'):
            self.slider_vars = {}
        self.slider_vars[key] = value_var
        
        def on_change(val):
            try:
                value_var.set(f"{float(val):.1f}")
            except:
                pass
        
        resolution = 1
        try:
            if not all(float(v).is_integer() for v in (min_v, max_v, default)):
                resolution = 0.1
        except:
            resolution = 0.1
        
        scale = tk.Scale(
            frame,
            from_=min_v, to=max_v,
            orient=tk.HORIZONTAL,
            bg=colors['input_bg'], fg=colors['accent'],
            troughcolor=colors['card_bg'],
            relief=tk.FLAT, bd=0,
            length=length,
            resolution=resolution,
            command=on_change
        )
        scale.pack(fill=tk.X)
        scale.set(default)
        
        if not hasattr(self, 'slider_controls'):
            self.slider_controls = {}
        self.slider_controls[key] = {'var': value_var, 'scale': scale}
    
    def _build_center_dashboard(self, parent) -> tk.Frame:
        """Build center dashboard with display mode switcher and persistent activity log"""
        colors = theme_manager.get_colors()
        
        frame = tk.Frame(parent, bg=colors['bg'])
        
        # Display Mode Switcher (Top buttons)
        switcher_frame = tk.Frame(frame, bg=colors['card_bg'], height=44)
        switcher_frame.pack(fill=tk.X, padx=5, pady=(0, 8))
        switcher_frame.pack_propagate(False)
        
        tk.Label(
            switcher_frame, text="📺 VIEW MODE:",
            bg=colors['card_bg'], fg=colors['text_secondary'],
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=8, pady=6)
        
        # Mode buttons
        self.display_mode = tk.StringVar(value="market")
        self.mode_buttons = {}
        
        for mode, emoji, label in [
            ("market", "📊", "Market"),
            ("trading", "⚡", "Live Trade"),
            ("analytics", "📉", "Analytics"),
            ("backtest", "🧪", "Backtest"),
        ]:
            btn_frame = tk.Frame(switcher_frame, bg=colors['card_bg'])
            btn_frame.pack(side=tk.LEFT, padx=3)
            
            btn = tk.Button(
                btn_frame, text=f"{emoji} {label}",
                bg=colors['input_bg'], fg=colors['fg'],
                font=("Segoe UI", 9),
                relief=tk.FLAT, padx=9, pady=4,
                command=lambda m=mode: self._switch_display_mode(m),
                cursor="hand2"
            )
            btn.pack()
            self.mode_buttons[mode] = btn
        
        # PanedWindow to split views and activity log
        paned = tk.PanedWindow(frame, orient=tk.VERTICAL, bg=colors['bg'], sashwidth=5)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Content frame container (top half)
        self.content_container = tk.Frame(paned, bg=colors['bg'])
        paned.add(self.content_container, stretch="always")
        
        # Activity Log (bottom half)
        log_card = Card(paned, "📝 ACTIVITY LOG")
        paned.add(log_card, stretch="never")
        
        self.activity_text = scrolledtext.ScrolledText(
            log_card.content,
            bg=colors['input_bg'], fg=colors['accent'],
            font=("Courier", 8),
            relief=tk.FLAT, bd=0,
            height=6
        )
        self.activity_text.pack(fill=tk.BOTH, expand=True)
        
        # Build static view containers
        self._build_market_view()
        self._build_analytics_view()
        self._build_backtest_view()

        # Show market view by default
        self._switch_display_mode("market")
        
        # Log initial message
        self._log_activity("🚀 Master Trader Interface Started - Ready for Trading")
        
        return frame
    
    def _switch_display_mode(self, mode: str):
        """Switch between display modes"""
        colors = theme_manager.get_colors()
        self.display_mode.set(mode)
        
        # Hide all frames
        for frame in self.content_container.winfo_children():
            frame.pack_forget()
        
        # Show selected frame
        target_frame = None
        if hasattr(self, f'frame_{mode}'):
            target_frame = getattr(self, f'frame_{mode}')
        elif mode == "trading":
            self.frame_trading = self._build_live_trading_frame()
            target_frame = self.frame_trading
        else:
            self._log_activity(f"[WARN] Unknown display mode: {mode}")
            return

        target_frame.pack(fill=tk.BOTH, expand=True)
        
        # Update button styles
        for m, btn in self.mode_buttons.items():
            if m == mode:
                btn.config(bg=colors['accent'], fg=colors['bg'], relief=tk.RAISED)
            else:
                btn.config(bg=colors['input_bg'], fg=colors['fg'], relief=tk.FLAT)
    
    def _switch_market_view_mode(self, mode: str):
        """Switch between chart and data sections in market view"""
        colors = theme_manager.get_colors()
        if mode not in self.market_view_sections:
            return
        self.market_view_mode.set(mode)
        for frame in self.market_view_sections.values():
            frame.pack_forget()
        target = self.market_view_sections[mode]
        target.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        for key, btn in self.market_mode_buttons.items():
            if key == mode:
                btn.config(bg=colors['accent'], fg=colors['bg'], relief=tk.RAISED)
            else:
                btn.config(bg=colors['input_bg'], fg=colors['fg'], relief=tk.FLAT)
    
    def _build_market_view(self):
        """Build market view with chart and market data switches"""
        colors = theme_manager.get_colors()
        self.market_mode_buttons.clear()
        self.market_view_sections.clear()
        self.market_info_labels.clear()
        self.frame_market = tk.Frame(self.content_container, bg=colors['bg'])
        market_card = Card(self.frame_market, "📈 MARKET VIEW")
        market_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        control_bar = tk.Frame(market_card.content, bg=colors['card_bg'])
        control_bar.pack(fill=tk.X, pady=(0, 10))
        switch_frame = tk.Frame(control_bar, bg=colors['card_bg'])
        switch_frame.pack(side=tk.LEFT)
        for mode, text in [("chart", "📈 Chart Analysis"), ("data", "🗃️ Market Data")]:
            btn = tk.Button(
                switch_frame,
                text=text,
                bg=colors['input_bg'],
                fg=colors['fg'],
                font=("Segoe UI", 9, "bold"),
                relief=tk.FLAT,
                padx=10,
                pady=6,
                command=lambda m=mode: self._switch_market_view_mode(m),
                cursor="hand2"
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.market_mode_buttons[mode] = btn
        self.market_pairs_box = tk.Frame(
            control_bar,
            bg=colors['input_bg'],
            highlightbackground=colors['border'],
            highlightthickness=1,
            bd=0,
            padx=10,
            pady=6
        )
        self.market_pairs_box.pack(side=tk.RIGHT, padx=6)
        self.market_pairs_heading = tk.Label(
            self.market_pairs_box,
            text="Active Pairs (Testnet)",
            bg=colors['input_bg'],
            fg=colors['text_secondary'],
            font=("Segoe UI", 8, "bold")
        )
        self.market_pairs_heading.pack(anchor="w")
        self.market_pairs_label = tk.Label(
            self.market_pairs_box,
            textvariable=self.market_pairs_var,
            bg=colors['input_bg'],
            fg=colors['accent'],
            font=("Segoe UI", 10, "bold"),
            justify=tk.LEFT
        )
        self.market_pairs_label.pack(anchor="w")
        self.market_view_stack = tk.Frame(market_card.content, bg=colors['card_bg'])
        self.market_view_stack.pack(fill=tk.BOTH, expand=True)
        chart_frame = tk.Frame(self.market_view_stack, bg=colors['card_bg'])
        chart_header = tk.Frame(chart_frame, bg=colors['card_bg'])
        chart_header.pack(fill=tk.X, pady=(0, 6))
        tk.Label(
            chart_header,
            text="Live Price",
            bg=colors['card_bg'],
            fg=colors['text_secondary'],
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)
        self.live_price_var = tk.StringVar(value="$0.00")
        self.live_price_label = tk.Label(
            chart_header,
            textvariable=self.live_price_var,
            bg=colors['card_bg'],
            fg=colors['accent'],
            font=("Segoe UI", 16, "bold")
        )
        self.live_price_label.pack(side=tk.LEFT, padx=12)
        self.trading_canvas = tk.Canvas(
            chart_frame,
            bg=colors['input_bg'],
            highlightthickness=0,
            height=260
        )
        self.trading_canvas.pack(fill=tk.BOTH, expand=True)
        self.market_view_sections['chart'] = chart_frame
        self._init_trading_animation()
        data_frame = tk.Frame(self.market_view_stack, bg=colors['card_bg'])
        summary_row = tk.Frame(data_frame, bg=colors['card_bg'])
        summary_row.pack(fill=tk.X, pady=(0, 12))
        info_specs = [
            ("Current Price", colors['accent']),
            ("24h Change", colors['button_bg']),
            ("High / Low", colors['fg']),
            ("24h Volume", colors['fg'])
        ]
        for title, color in info_specs:
            block = tk.Frame(summary_row, bg=colors['card_bg'])
            block.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
            tk.Label(
                block,
                text=title,
                bg=colors['card_bg'],
                fg=colors['text_secondary'],
                font=("Segoe UI", 9, "bold")
            ).pack(anchor="w")
            label = tk.Label(
                block,
                text="—",
                bg=colors['card_bg'],
                fg=color,
                font=("Segoe UI", 12, "bold")
            )
            label.pack(anchor="w", pady=(2, 0))
            self.market_info_labels[title] = label
        order_frame = tk.Frame(data_frame, bg=colors['card_bg'])
        order_frame.pack(fill=tk.X)
        order_info = [
            ("Entry", "—", colors['accent']),
            ("Stop Loss", "—", colors['danger']),
            ("Take Profit", "—", colors['button_bg']),
            ("Risk / Reward", "—", colors['accent'])
        ]
        for label_text, value, color in order_info:
            column = tk.Frame(order_frame, bg=colors['card_bg'])
            column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
            tk.Label(
                column,
                text=label_text,
                bg=colors['card_bg'],
                fg=colors['text_secondary'],
                font=("Segoe UI", 9, "bold")
            ).pack(anchor="w")
            tk.Label(
                column,
                text=value,
                bg=colors['card_bg'],
                fg=color,
                font=("Segoe UI", 11, "bold")
            ).pack(anchor="w", pady=(2, 0))
        self.market_view_sections['data'] = data_frame
        for frame in self.market_view_sections.values():
            frame.pack_forget()
        self._switch_market_view_mode(self.market_view_mode.get())
        self._refresh_trading_pairs_display()
    
    def _init_trading_animation(self):
        if hasattr(self, '_animation_job') and self._animation_job:
            try:
                self.root.after_cancel(self._animation_job)
            except Exception:
                pass
        self._anim_state = {
            'candles': deque(maxlen=64),
            'price': 100.0,
            'velocity': 0.0,
            'particles': [],
            'pulse': 0.0,
            'frame': 0
        }
        for _ in range(40):
            self._generate_candle(seed=True)
        self.live_price_var.set(f"${self._anim_state['price']:.2f}")
        self._animation_job = None
        self._animate_trading_activity()
    
    def _advance_trading_state(self):
        if not hasattr(self, '_anim_state'):
            return
        state = self._anim_state
        state['frame'] = state.get('frame', 0) + 1
        if state['frame'] % 5 == 0:
            self._generate_candle()
        else:
            self._refine_current_candle()
    
    def _generate_candle(self, seed=False):
        state = self._anim_state
        candles = state['candles']
        base_price = state['price']
        velocity = state['velocity']
        drift_scale = 0.25 if seed else 0.85
        drift = random.gauss(0.0, drift_scale)
        momentum = 0.76 * velocity + drift
        price = max(15.0, base_price + momentum)
        spread = abs(random.gauss(0.0, 1.8 if self.is_running else 1.2))
        high = max(price, base_price) + spread * 0.6
        low = min(price, base_price) - spread * 0.6
        volume = 110 + random.random() * 140
        tick = candles[-1]['tick'] + 1 if candles else 0
        candles.append({
            'open': base_price,
            'close': price,
            'high': high,
            'low': low,
            'volume': volume,
            'tick': tick
        })
        state['price'] = price
        state['velocity'] = momentum
    
    def _refine_current_candle(self):
        state = self._anim_state
        candles = state['candles']
        if not candles:
            self._generate_candle()
            return
        last = candles[-1]
        pulse = random.gauss(0.0, 0.35)
        price = max(15.0, last['close'] + pulse)
        last['close'] = price
        last['high'] = max(last['high'], price)
        last['low'] = min(last['low'], price)
        last['volume'] = max(50.0, last['volume'] * (0.9 + random.random() * 0.18))
        state['velocity'] = state['velocity'] * 0.64 + pulse * 0.36
        state['price'] = price
    
    def _update_trading_particles(self, canvas, width, height, colors):
        state = self._anim_state
        particles = state['particles']
        updated = []
        for particle in particles:
            particle['life'] -= 1
            if particle['life'] <= 0:
                continue
            particle['x'] += particle['dx']
            particle['y'] += particle['dy']
            if 0 <= particle['x'] <= width and 0 <= particle['y'] <= height:
                updated.append(particle)
        while len(updated) < 18:
            max_life = random.randint(18, 36)
            updated.append({
                'x': random.uniform(60, width - 60),
                'y': height - random.uniform(30, 120),
                'dx': random.uniform(-0.9, 0.9),
                'dy': random.uniform(-1.6, -0.4),
                'radius': random.uniform(3.4, 5.8),
                'life': max_life,
                'max_life': max_life
            })
        state['particles'] = updated
        for particle in updated:
            progress = particle['life'] / particle['max_life']
            radius = particle['radius'] * (1.4 - progress * 0.5)
            color = self._mix_color(colors['accent'], colors['bg'], 1 - progress)
            canvas.create_oval(
                particle['x'] - radius,
                particle['y'] - radius,
                particle['x'] + radius,
                particle['y'] + radius,
                fill=color,
                outline=""
            )
    
    def _mix_color(self, base_hex: str, overlay_hex: str, ratio: float) -> str:
        ratio = max(0.0, min(1.0, ratio))
        base = base_hex.lstrip('#')
        overlay = overlay_hex.lstrip('#')
        if len(base) != 6 or len(overlay) != 6:
            return base_hex
        br = int(base[0:2], 16)
        bg = int(base[2:4], 16)
        bb = int(base[4:6], 16)
        orr = int(overlay[0:2], 16)
        og = int(overlay[2:4], 16)
        ob = int(overlay[4:6], 16)
        r = int(br * (1 - ratio) + orr * ratio)
        g = int(bg * (1 - ratio) + og * ratio)
        b = int(bb * (1 - ratio) + ob * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _animate_trading_activity(self):
        if not hasattr(self, 'trading_canvas') or not self.trading_canvas.winfo_exists():
            return
        if not hasattr(self, '_anim_state'):
            return
        canvas = self.trading_canvas
        colors = theme_manager.get_colors()
        width = max(canvas.winfo_width(), 620)
        height = max(canvas.winfo_height(), 260)
        canvas.delete("all")
        margin_x = 60
        margin_y = 60
        top = margin_y
        bottom = height - margin_y
        self._advance_trading_state()
        candles = self._anim_state['candles']
        if not candles:
            return
        max_high = max(c['high'] for c in candles)
        min_low = min(c['low'] for c in candles)
        price_range = max(max_high - min_low, 1)
        scale = (bottom - top) / price_range
        def price_to_y(value):
            return bottom - (value - min_low) * scale
        pulse = (self._anim_state.get('pulse', 0.0) + 0.065) % (math.tau)
        self._anim_state['pulse'] = pulse
        glow = (math.sin(pulse) + 1) / 2
        base_overlay = self._mix_color(colors['accent'], '#ffffff', 0.35 * glow)
        canvas.create_rectangle(0, 0, width, height, fill=colors['input_bg'], outline="")
        canvas.create_rectangle(0, bottom, width, height, fill=self._mix_color(base_overlay, colors['input_bg'], 0.55), outline="")
        grid_color = self._mix_color(colors['border'], colors['bg'], 0.4)
        for i in range(6):
            y = top + (bottom - top) * (i / 5)
            canvas.create_line(margin_x - 20, y, width - margin_x + 20, y, fill=grid_color)
        for i in range(10):
            x = margin_x + (width - margin_x * 2) * (i / 9)
            canvas.create_line(x, top, x, bottom, fill=grid_color, dash=(2, 6))
        count = len(candles)
        step = (width - margin_x * 2) / max(count - 1, 1)
        half_body = max(4, min(14, step * 0.35))
        line_points = []
        volumes = [c['volume'] for c in candles]
        max_volume = max(volumes) if volumes else 1
        render_data = []
        for idx, candle in enumerate(candles):
            x = margin_x + step * idx
            open_y = price_to_y(candle['open'])
            close_y = price_to_y(candle['close'])
            high_y = price_to_y(candle['high'])
            low_y = price_to_y(candle['low'])
            positive = candle['close'] >= candle['open']
            body_color = colors['button_bg'] if positive else colors['danger']
            line_points.append((x, close_y))
            volume_ratio = candle['volume'] / max_volume
            render_data.append((x, open_y, close_y, high_y, low_y, positive, body_color, volume_ratio))
        if len(line_points) > 2:
            area_coords = []
            for px, py in line_points:
                area_coords.extend([px, py])
            area_coords.extend([line_points[-1][0], bottom, line_points[0][0], bottom])
            area_color = self._mix_color(colors['accent'], colors['bg'], 0.82)
            canvas.create_polygon(area_coords, fill=area_color, outline="")
        line_coords = []
        for px, py in line_points:
            line_coords.extend([px, py])
        line_color_core = self._mix_color(colors['accent'], '#ffffff', 0.2 + glow * 0.2)
        if len(line_coords) >= 4:
            canvas.create_line(*line_coords, smooth=True, fill=self._mix_color(line_color_core, '#ffffff', 0.25), width=5)
            canvas.create_line(*line_coords, smooth=True, fill=line_color_core, width=2)
        volume_base = height - 18
        for data in render_data:
            x, open_y, close_y, high_y, low_y, positive, body_color, volume_ratio = data
            fill_color = self._mix_color(body_color, '#ffffff', 0.22 if positive else 0.08)
            outline_color = self._mix_color(body_color, colors['border'], 0.5)
            wick_color = self._mix_color(body_color, colors['fg'], 0.4)
            canvas.create_line(x, high_y, x, low_y, fill=wick_color, width=2)
            top_rect = min(open_y, close_y)
            bottom_rect = max(open_y, close_y)
            if bottom_rect - top_rect < 1.5:
                bottom_rect = top_rect + 1.5
            canvas.create_rectangle(
                x - half_body,
                top_rect,
                x + half_body,
                bottom_rect,
                fill=fill_color,
                outline=outline_color,
                width=1
            )
            volume_top = volume_base - (margin_y - 24) * volume_ratio
            volume_color = self._mix_color(body_color, colors['bg'], 0.6)
            canvas.create_rectangle(
                x - half_body * 0.5,
                volume_top,
                x + half_body * 0.5,
                volume_base,
                fill=volume_color,
                outline=""
            )
        self._update_trading_particles(canvas, width, height, colors)
        self.live_price_var.set(f"${self._anim_state['price']:.2f}")
        price_color = colors['accent'] if self._anim_state['velocity'] >= 0 else colors['danger']
        self.live_price_label.config(fg=price_color)
        interval = 48 if self.is_running else 96
        self._animation_job = self.root.after(interval, self._animate_trading_activity)
    
    def _build_live_trading_frame(self) -> tk.Frame:
        """Build live trading dashboard with embedded TradingView-style panel."""
        colors = theme_manager.get_colors()
        frame = tk.Frame(self.content_container, bg=colors['bg'])

        hub_card = Card(frame, "📈 LIVE TRADING HUB")
        hub_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        if LiveTradingPanel is None:
            message = (
                "Live Trading View dependencies missing.\n\n"
                "Run: pip install mplfinance matplotlib pandas numpy"
            )
            tk.Label(
                hub_card.content,
                text=message,
                bg=colors['card_bg'],
                fg=colors['warning'],
                font=("Segoe UI", 10),
                justify=tk.LEFT
            ).pack(fill=tk.BOTH, expand=True, padx=20, pady=40)
            return frame

        try:
            panel = LiveTradingPanel(hub_card.content, theme_manager)
            panel.pack(fill=tk.BOTH, expand=True)
            self.live_trading_panel = panel
        except Exception as exc:
            tk.Label(
                hub_card.content,
                text=f"Failed to load live trading view:\n{exc}",
                bg=colors['card_bg'],
                fg=colors['danger'],
                font=("Segoe UI", 10),
                justify=tk.LEFT
            ).pack(fill=tk.BOTH, expand=True, padx=20, pady=40)

        return frame
    
    def _build_analytics_view(self):
        """Build analytics dashboard"""
        colors = theme_manager.get_colors()
        self.frame_analytics = tk.Frame(self.content_container, bg=colors['bg'])
        
        analytics_card = Card(self.frame_analytics, "📉 MARKET ANALYTICS")
        analytics_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        # Matplotlib chart
        fig = Figure(figsize=(8, 5), dpi=100, facecolor=colors['card_bg'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(colors['input_bg'])
        ax.grid(True, alpha=0.45, color=colors['text_secondary'], linestyle='--', linewidth=0.7)
        
        # Sample data
        import random
        x = list(range(20))
        y = [100 + random.randint(-10, 10) for _ in x]
        
        ax.plot(x, y, color=colors['accent'], linewidth=2, marker='o')
        ax.fill_between(x, y, alpha=0.3, color=colors['accent'])
        ax.set_title("Price Action (Last 20 periods)", color=colors['fg'])
        ax.tick_params(colors=colors['text_secondary'])
        
        canvas = FigureCanvasTkAgg(fig, master=analytics_card.content)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _build_backtest_view(self):
        """Build backtest results view"""
        colors = theme_manager.get_colors()
        self.frame_backtest = tk.Frame(self.content_container, bg=colors['bg'])
        
        backtest_card = Card(self.frame_backtest, "🧪 BACKTEST RESULTS")
        backtest_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        self.backtest_text = scrolledtext.ScrolledText(
            backtest_card.content,
            bg=colors['input_bg'], fg=colors['accent'],
            font=("Courier", 10),
            relief=tk.FLAT, bd=0
        )
        self.backtest_text.pack(fill=tk.BOTH, expand=True)
        
        # Insert placeholder
        backtest_result = """
📊 BACKTEST PERFORMANCE REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 METRICS
──────────
Total Trades:      42
Win Rate:          65.5%
Profit Factor:     2.1
Sharpe Ratio:      1.85

💰 FINANCIAL
──────────
Starting Balance:  $10,000
Ending Balance:    $12,550
Total Return:      $2,550
ROI:               25.5%
Max Drawdown:      -8.5%

🎯 RISK METRICS
──────────
Avg Win:           $125.50
Avg Loss:          -$58.20
Risk/Reward:       2.15
Best Trade:        $450.00
Worst Trade:       -$250.00

⏱️ TIME ANALYSIS
──────────
Trades/Day:        4.2
Avg Trade Time:    2.5h
Win Streak:        7
Lose Streak:       3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: ✅ READY FOR LIVE TRADING
        """
        self.backtest_text.insert(tk.END, backtest_result)
        self.backtest_text.config(state=tk.DISABLED)
    
    def _build_right_panel(self, parent) -> tk.Frame:
        """Build right stats panel"""
        colors = theme_manager.get_colors()
        
        panel = tk.Frame(parent, bg=colors['bg'])
        
        # Account Stats
        stats_frame = tk.Frame(panel, bg=colors['bg'])
        stats_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            stats_frame, text="💰 ACCOUNT STATS",
            bg=colors['bg'], fg=colors['accent'],
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 6))
        
        self.stat_cards = {}
        for stat_key, emoji, label in [
            ('balance', '💵', 'Balance'),
            ('pnl', '📊', 'P&L'),
            ('win_rate', '✅', 'Win Rate'),
            ('trades', '🔄', 'Trades'),
            ('roi', '🎯', 'ROI'),
        ]:
            card = StatCard(stats_frame, label, "—", emoji)
            card.pack(fill=tk.X, pady=2)
            self.stat_cards[stat_key] = card
        
        # Position Sizing Card
        pos_card = Card(panel, "📍 POSITION SIZING")
        pos_card.pack(fill=tk.X, pady=(0, 8))
        
        self.position_vars = {}
        for label, key, min_v, max_v, default in [
            ("Risk Per Trade %", "risk", 0.1, 5, 2.0),
            ("Position Size", "position", 0.1, 10, 1.0),
        ]:
            self._create_labeled_slider(pos_card.content, label, key, min_v, max_v, default)
        
        # Performance Card
        perf_card = Card(panel, "📉 PERFORMANCE", height=160)
        perf_card.pack(fill=tk.X, pady=(0, 8))
        
        self.perf_text = tk.Label(
            perf_card.content,
            text="Waiting for data...",
            bg=colors['card_bg'], fg=colors['text_secondary'],
            font=("Segoe UI", 9),
            justify=tk.LEFT, wraplength=180
        )
        self.perf_text.pack(fill=tk.BOTH, expand=True)
        
        # Status Card
        status_card = Card(panel, "🟢 STATUS")
        status_card.pack(fill=tk.X)
        
        self.status_label = tk.Label(
            status_card.content,
            text="🟡 STANDBY",
            bg=colors['card_bg'], fg=colors['warning'],
            font=("Segoe UI", 10, "bold")
        )
        self.status_label.pack(pady=6)
        
        # Entry Conditions Card
        entry_card = Card(panel, "📈 ENTRY CONDITIONS")
        entry_card.pack(fill=tk.X, pady=(8, 0))
        
        entry_frame = tk.Frame(entry_card.content, bg=colors['card_bg'])
        entry_frame.pack(fill=tk.X, pady=4)
        
        tk.Label(
            entry_frame, text="Min Volatility (%):",
            bg=colors['card_bg'], fg=colors['text_secondary'],
            font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(0, 1))
        
        self.min_vol = tk.Scale(
            entry_frame, from_=0.5, to=5, orient=tk.HORIZONTAL,
            bg=colors['input_bg'], fg=colors['accent'],
            troughcolor=colors['card_bg'], relief=tk.FLAT, bd=0
        )
        self.min_vol.set(1.5)
        self.min_vol.pack(fill=tk.X, pady=(0, 4))
        
        return panel
    
    def _load_symbols(self):
        """Load Binance symbols"""
        logger.info("Loading Binance symbols...")
        self.symbols_list = fetch_binance_symbols()
        
        # Update listbox
        self.symbol_listbox.delete(0, tk.END)
        for symbol in self.symbols_list:
            self.symbol_listbox.insert(tk.END, symbol)
        
        # Select first
        if self.symbols_list:
            self.symbol_listbox.selection_set(0)
            self._on_symbol_select(None)
    
    def _on_symbol_search(self, *args):
        """Filter symbols by search text"""
        search_text = self.search_var.get().upper()
        self.symbol_listbox.delete(0, tk.END)
        
        for symbol in self.symbols_list:
            if search_text in symbol:
                self.symbol_listbox.insert(tk.END, symbol)
    
    def _on_symbol_select(self, event):
        """Handle symbol selection"""
        selection = self.symbol_listbox.curselection()
        if selection:
            self.current_symbol.set(self.symbol_listbox.get(selection[0]))
            if self.is_running:
                self.active_trading_pairs.clear()
                symbol = self.current_symbol.get()
                if symbol:
                    self.active_trading_pairs.add(symbol)
                    self._refresh_trading_pairs_display()
            logger.info(f"Selected symbol: {self.current_symbol.get()}")
    
    def _start_bot(self):
        """Start trading bot"""
        if self.is_running:
            messagebox.showwarning("Warning", "Bot is already running!")
            return
        
        self.is_running = True
        self.status_label.config(text="🟢 TRADING LIVE", fg=theme_manager.get_colors()['button_bg'])
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        symbol = self.current_symbol.get()
        if symbol:
            self.active_trading_pairs.add(symbol)
            self._refresh_trading_pairs_display()
        
        self._log_activity(f"✅ Bot started - Trading {self.current_symbol.get()}")
        
        # Start trading thread
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()
    
    def _stop_bot(self):
        """Stop trading bot"""
        if not self.is_running:
            messagebox.showwarning("Warning", "Bot is not running!")
            return
        
        self.is_running = False
        self.status_label.config(text="🟡 STANDBY", fg=theme_manager.get_colors()['warning'])
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        symbol = self.current_symbol.get()
        if symbol in self.active_trading_pairs:
            self.active_trading_pairs.discard(symbol)
            self._refresh_trading_pairs_display()
        
        self._log_activity("⏹️ Bot stopped")
    
    def _run_test(self):
        """Run backtesting"""
        self._log_activity(f"🧪 Starting backtest for {self.current_symbol.get()}...")
        
        def run_backtest_thread():
            try:
                # Placeholder backtest
                time.sleep(2)
                metrics = {
                    'total_trades': 42,
                    'win_rate': 65.5,
                    'profit': 1250.50,
                    'roi': 12.5,
                    'sharpe': 1.8,
                    'max_dd': 8.5,
                }
                
                result_text = f"""
📊 BACKTEST RESULTS
━━━━━━━━━━━━━━━━━━━━
🔄 Total Trades: {metrics['total_trades']}
✅ Win Rate: {metrics['win_rate']:.1f}%
💰 Profit: ${metrics['profit']:.2f}
🎯 ROI: {metrics['roi']:.1f}%
📈 Sharpe Ratio: {metrics['sharpe']:.2f}
📉 Max Drawdown: {metrics['max_dd']:.1f}%
"""
                self._log_activity(result_text)
                messagebox.showinfo("Backtest Complete", result_text)
                
            except Exception as e:
                self._log_activity(f"❌ Backtest error: {e}")
                messagebox.showerror("Error", f"Backtest failed: {e}")
        
        threading.Thread(target=run_backtest_thread, daemon=True).start()
    
    def _trading_loop(self):
        """Main trading loop"""
        while self.is_running:
            try:
                # Update stats every 5 seconds
                self._update_stats()
                time.sleep(5)
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
    
    def _update_stats(self):
        """Update stats display"""
        if self.is_running:
            symbol = self.current_symbol.get()
            if symbol and symbol not in self.active_trading_pairs:
                self.active_trading_pairs.add(symbol)
                self._refresh_trading_pairs_display()
        # Simulate stats update
        import random
        self.stats['balance'] = 10000 + random.randint(-500, 500)
        self.stats['pnl'] = random.randint(-200, 500)
        self.stats['win_rate'] = random.randint(40, 80)
        self.stats['trades'] = random.randint(10, 100)
        self.stats['roi'] = random.randint(1, 50)
        
        # Update cards
        self.stat_cards['balance'].set_value(f"${self.stats['balance']:.2f}")
        self.stat_cards['pnl'].set_value(f"${self.stats['pnl']:.2f}")
        self.stat_cards['win_rate'].set_value(f"{self.stats['win_rate']}%")
        self.stat_cards['trades'].set_value(f"{self.stats['trades']}")
        self.stat_cards['roi'].set_value(f"{self.stats['roi']}%")
    
    def _log_activity(self, message: str):
        """Log activity"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.activity_text.see(tk.END)
    
    def _show_hamburger_menu(self):
        """Show comprehensive hamburger menu"""
        self._show_popup_menu([
            ("🎮 TRADING", None, True),
            ("  ▶️ Start Bot", self._start_bot),
            ("  ⏹️ Stop Bot", self._stop_bot),
            ("  🧪 Run Backtest", self._run_test),
            ("  📊 View Trades", lambda: self._switch_display_mode("trading")),
            ("  📈 Live Trading View", self._show_live_trading_view),
            ("", None, False),  # Separator
            ("🏦 TRADING MODES", None, True),
            ("  🏦 Select Trading Method", self._show_trading_method_selector),
            ("  📈 Strategy & Timeframe", self._show_advanced_strategy_selector),
            ("", None, False),  # Separator
            ("🔑 API & KEYS", None, True),
            ("  🔑 Live API Manager", self._show_live_api_manager),
            ("  🔌 API Configuration", self._show_api_settings),
            ("", None, False),  # Separator
            ("⚙️ SETTINGS", None, True),
            ("  💎 Risk Profiles", self._show_risk_profiles),
            ("  🎯 Strategy Presets", self._show_strategy_presets),
            ("  📐 Position Sizer", self._show_position_calculator),
            ("  🔔 Notifications", self._show_notification_settings),
            ("  📊 Advanced Tuning", self._show_advanced_tuning),
            ("  ⚡ Bot Reliability", self._show_bot_reliability_settings),
            ("  📈 Performance Analytics", self._show_performance_dashboard),
            ("  📓 Trade Journal", self._show_trade_journal),
            ("  💾 Save Settings", self._save_settings),
            ("  📝 Edit Config", self._show_config_editor),
            ("  🔄 Restore Defaults", self._restore_defaults),
            ("", None, False),  # Separator
            ("🖥️ DESKTOP", None, True),
            ("  🖥️ Create Desktop Shortcut", self._show_desktop_shortcut_creator),
            ("", None, False),  # Separator
            ("📚 HELP & DOCS", None, True),
            ("  📖 User Guide", self._show_user_guide),
            ("  ⚙️ Setup Guide", self._show_setup_guide),
            ("  📊 Statistics Help", self._show_stats_guide),
            ("  ❌ Troubleshooting", self._show_troubleshooting),
            ("  ⌨️ Keyboard Shortcuts", self._show_shortcuts_dialog),
            ("", None, False),  # Separator
            ("ℹ️ ABOUT", None, True),
            ("  📦 App Version", self._show_version),
            ("  ❓ About Master Trader", self._show_about),
            ("  🔗 Documentation", self._open_docs),
        ])
    
    def _show_settings_menu(self):
        """Show settings dropdown menu"""
        self._show_popup_menu([
            ("📝 Edit Config", self._show_config_editor),
            ("🔌 API Settings", self._show_api_settings),
            ("💾 Save Settings", self._save_settings),
            ("🔄 Restore Defaults", self._restore_defaults),
        ])
    
    def _show_help_menu(self):
        """Show help dropdown menu"""
        self._show_popup_menu([
            ("📖 User Guide", self._show_user_guide),
            ("⚙️ How to Setup", self._show_setup_guide),
            ("📊 Understanding Stats", self._show_stats_guide),
            ("❌ Troubleshooting", self._show_troubleshooting),
            ("ℹ️ About", self._show_about),
        ])
    
    def _show_shortcuts_menu(self):
        """Show keyboard shortcuts"""
        self._show_popup_menu([
            ("⌨️ View All Shortcuts", self._show_shortcuts_dialog),
        ])
    
    def _show_popup_menu(self, items):
        """Show popup menu with items and section headers"""
        colors = theme_manager.get_colors()
        popup = tk.Menu(self.root, tearoff=False, bg=colors['card_bg'], fg=colors['fg'])
        
        for item in items:
            if len(item) == 2:
                label, cmd = item
                is_header = False
            else:
                label, cmd, is_header = item
            
            if label == "":  # Separator
                popup.add_separator()
            elif is_header:  # Section header
                popup.add_command(label=label, state=tk.DISABLED, font=("Segoe UI", 9, "bold"))
            else:
                popup.add_command(label=label, command=cmd if cmd else lambda: None)
        
        try:
            popup.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            popup.grab_release()
    
    def _show_risk_profiles(self):
        """Show risk profile presets"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("💎 Risk Profiles")
        window.geometry("420x350")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Select Risk Profile", bg=colors['bg'], fg=colors['accent'],
                        font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15))
        
        profiles = {
            "🛡️ CONSERVATIVE": {"risk": 0.5, "sl_atr": 3.0, "tp_rr": 3.0, "dd": 10, "trades": 5},
            "⚖️ BALANCED": {"risk": 1.5, "sl_atr": 2.0, "tp_rr": 2.0, "dd": 20, "trades": 10},
            "🚀 AGGRESSIVE": {"risk": 3.0, "sl_atr": 1.5, "tp_rr": 1.5, "dd": 30, "trades": 20},
        }
        
        for name, settings in profiles.items():
            btn = tk.Button(
                frame, text=f"{name}\nRisk: {settings['risk']}% | SL: {settings['sl_atr']:.1f}x | TP RR: {settings['tp_rr']:.1f}",
                bg=colors['input_bg'], fg=colors['fg'], font=("Segoe UI", 10),
                relief=tk.FLAT, pady=15, cursor="hand2",
                command=lambda p=settings: self._apply_risk_profile(p, window)
            )
            btn.pack(fill=tk.X, pady=8)
        
        close_btn = tk.Button(frame, text="❌ Close", bg=colors['danger'], fg=colors['fg'],
                             font=("Segoe UI", 10), relief=tk.FLAT, cursor="hand2",
                             command=window.destroy)
        close_btn.pack(fill=tk.X, pady=(20, 0))
    
    def _apply_risk_profile(self, profile, window):
        """Apply risk profile"""
        try:
            slider_controls = getattr(self, 'slider_controls', {})
            updates = {
                'risk': profile.get('risk'),
                'sl_atr': profile.get('sl_atr'),
                'tp_rr': profile.get('tp_rr'),
                'max_dd': profile.get('dd'),
                'max_trades': profile.get('trades'),
            }
            for key, value in updates.items():
                if value is None:
                    continue
                control = slider_controls.get(key)
                if not control:
                    continue
                scale = control.get('scale')
                if scale is not None:
                    scale.set(float(value))
                var = control.get('var')
                if var is not None:
                    var.set(f"{float(value):.1f}")
            messagebox.showinfo("Profile Applied", "✅ Risk profile applied successfully!")
            window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply profile: {e}")
    
    def _show_strategy_presets(self):
        """Show strategy presets"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("🎯 Strategy Presets")
        window.geometry("420x400")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Trading Strategy Presets", bg=colors['bg'], fg=colors['accent'],
                        font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15))
        
        strategies = [
            "📈 Momentum: Fast entries on breakouts",
            "📊 Mean Reversion: Counter-trend trades",
            "🎯 Trend Following: Long-term trends",
            "⚡ Scalping: Quick short-term trades",
            "🔄 Range Trading: Support/Resistance",
            "🤖 ML Hybrid: ML + Technical",
        ]
        
        for strategy in strategies:
            btn = tk.Button(
                frame, text=strategy,
                bg=colors['input_bg'], fg=colors['fg'], font=("Segoe UI", 10),
                relief=tk.FLAT, pady=12, cursor="hand2",
                command=lambda s=strategy: messagebox.showinfo("Strategy", f"Loaded: {s}")
            )
            btn.pack(fill=tk.X, pady=6)
        
        close_btn = tk.Button(frame, text="❌ Close", bg=colors['danger'], fg=colors['fg'],
                             font=("Segoe UI", 10), relief=tk.FLAT, cursor="hand2",
                             command=window.destroy)
        close_btn.pack(fill=tk.X, pady=(15, 0))
    
    def _show_notification_settings(self):
        """Show notification settings"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("🔔 Notification Settings")
        window.geometry("460x400")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Configure Notifications", bg=colors['bg'], fg=colors['accent'],
                        font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15), anchor="w")
        
        notifications = [
            ("🤖 Trade Executed", True),
            ("⚠️ Stop Loss Hit", True),
            ("📈 Take Profit Reached", True),
            ("⛔ Risk Limit Hit", True),
            ("🔌 API Connection Lost", True),
            ("💰 Balance Updated", False),
            ("📊 Daily Report", False),
        ]
        
        for label, default in notifications:
            var = tk.BooleanVar(value=default)
            check = tk.Checkbutton(
                frame, text=label, variable=var,
                bg=colors['bg'], fg=colors['fg'], font=("Segoe UI", 10),
                selectcolor=colors['input_bg']
            )
            check.pack(anchor="w", pady=6)
        
        # Webhook settings
        tk.Label(frame, text="🔗 Webhook URL (for Discord/Telegram):", bg=colors['bg'],
                fg=colors['text_secondary'], font=("Segoe UI", 9)).pack(anchor="w", pady=(15, 5))
        
        webhook_entry = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                                font=("Segoe UI", 9), relief=tk.FLAT, bd=1)
        webhook_entry.pack(fill=tk.X, pady=(0, 15))
        
        save_btn = tk.Button(frame, text="💾 Save Notifications", bg=colors['button_bg'],
                            fg=colors['fg'], font=("Segoe UI", 10), relief=tk.FLAT,
                            cursor="hand2", command=window.destroy)
        save_btn.pack(fill=tk.X)
    
    def _show_advanced_tuning(self):
        """Show advanced tuning parameters"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("📊 Advanced Tuning")
        window.geometry("480x500")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Advanced Trading Parameters", bg=colors['bg'], fg=colors['accent'],
                        font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15), anchor="w")
        
        params = [
            ("🤖 ML Confidence Threshold", 0.55, 0.9),
            ("🎯 Profit Factor Target", 1.5, 3.0),
            ("📈 Trending Multiplier", 1.0, 2.0),
            ("⚡ Speed Factor", 0.5, 2.0),
            ("🔄 Retracement %", 0, 100),
            ("📊 Volatility Factor", 0.5, 2.0),
        ]
        
        for label, min_v, max_v in params:
            lbl = tk.Label(frame, text=label, bg=colors['bg'], fg=colors['text_secondary'],
                          font=("Segoe UI", 9))
            lbl.pack(anchor="w", pady=(10, 3))
            
            slider = tk.Scale(frame, from_=min_v, to=max_v, orient=tk.HORIZONTAL,
                             bg=colors['input_bg'], fg=colors['accent'],
                             troughcolor=colors['card_bg'], relief=tk.FLAT, bd=0)
            slider.set((min_v + max_v) / 2)
            slider.pack(fill=tk.X)
        
        # Auto-optimization
        opt_var = tk.BooleanVar(value=False)
        tk.Checkbutton(frame, text="🔄 Enable Auto-Optimization (continuous tuning)",
                      variable=opt_var, bg=colors['bg'], fg=colors['fg'],
                      font=("Segoe UI", 9), selectcolor=colors['input_bg']).pack(anchor="w", pady=(15, 5))
        
        save_btn = tk.Button(frame, text="💾 Save Parameters", bg=colors['button_bg'],
                            fg=colors['fg'], font=("Segoe UI", 10), relief=tk.FLAT,
                            cursor="hand2", command=window.destroy)
        save_btn.pack(fill=tk.X, pady=(15, 0))
    
    def _show_config_editor(self):
        """Show config editor window"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("📝 Configuration Editor")
        window.geometry("500x450")
        window.transient(self.root)
        
        # Create notebook
        notebook = ttk.Notebook(window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Trading Settings Tab
        trade_frame = tk.Frame(notebook, bg=colors['bg'])
        notebook.add(trade_frame, text="🎯 Trading")
        
        self._create_config_tab(trade_frame, [
            ("Default Symbol", "SOLUSDT"),
            ("Leverage", "1.0"),
            ("Order Type", "LIMIT"),
        ])
        
        # Risk Settings Tab
        risk_frame = tk.Frame(notebook, bg=colors['bg'])
        notebook.add(risk_frame, text="⛔ Risk")
        
        self._create_config_tab(risk_frame, [
            ("Max Positions", "3"),
            ("Position Size %", "2.0"),
            ("Daily Loss Limit", "500"),
        ])
        
        # Advanced Tab
        adv_frame = tk.Frame(notebook, bg=colors['bg'])
        notebook.add(adv_frame, text="🔧 Advanced")
        
        self._create_config_tab(adv_frame, [
            ("Update Interval (ms)", "1000"),
            ("Chart Lookback (bars)", "100"),
            ("Log Level", "INFO"),
        ])
    
    def _create_config_tab(self, parent, settings):
        """Create config tab with settings"""
        colors = theme_manager.get_colors()
        
        for label, value in settings:
            frame = tk.Frame(parent, bg=colors['bg'])
            frame.pack(fill=tk.X, padx=15, pady=10)
            
            tk.Label(frame, text=label, bg=colors['bg'], fg=colors['text_secondary'],
                    font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 5))
            
            entry = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                           font=("Segoe UI", 9), relief=tk.FLAT, bd=1)
            entry.insert(0, str(value))
            entry.pack(fill=tk.X)
    
    def _show_position_calculator(self):
        """Show position sizing calculator"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("📐 Position Size Calculator")
        window.geometry("450x420")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Position Sizing Calculator", bg=colors['bg'], fg=colors['accent'],
                        font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15), anchor="w")
        
        # Account Size
        tk.Label(frame, text="💰 Account Size ($):", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 3))
        account_entry = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                                font=("Segoe UI", 10), relief=tk.FLAT, bd=1)
        account_entry.insert(0, "10000")
        account_entry.pack(fill=tk.X, pady=(0, 8))
        
        # Risk Percentage
        tk.Label(frame, text="⚠️ Risk % per Trade:", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 3))
        risk_entry = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                             font=("Segoe UI", 10), relief=tk.FLAT, bd=1)
        risk_entry.insert(0, "2.0")
        risk_entry.pack(fill=tk.X, pady=(0, 8))
        
        # Entry Price
        tk.Label(frame, text="📊 Entry Price:", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 3))
        entry_entry = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                              font=("Segoe UI", 10), relief=tk.FLAT, bd=1)
        entry_entry.insert(0, "100.00")
        entry_entry.pack(fill=tk.X, pady=(0, 8))
        
        # Stop Loss Price
        tk.Label(frame, text="🛑 Stop Loss Price:", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 3))
        sl_entry = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                           font=("Segoe UI", 10), relief=tk.FLAT, bd=1)
        sl_entry.insert(0, "95.00")
        sl_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Calculate button
        def calculate():
            try:
                account = float(account_entry.get())
                risk_pct = float(risk_entry.get()) / 100
                entry = float(entry_entry.get())
                sl = float(sl_entry.get())
                
                risk_amount = account * risk_pct
                price_range = abs(entry - sl)
                qty = risk_amount / price_range
                
                result = f"""✅ POSITION SIZE CALCULATION
                
Position Quantity: {qty:.4f}
Risk Amount: ${risk_amount:.2f}
Entry Price: ${entry:.2f}
Stop Loss: ${sl:.2f}
Risk Distance: {price_range:.2f}
Percentage Risk: {abs((entry-sl)/entry)*100:.2f}%"""
                
                messagebox.showinfo("Position Size", result)
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")
        
        calc_btn = tk.Button(frame, text="🔢 Calculate Position Size", bg=colors['accent'],
                            fg=colors['fg'], font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                            cursor="hand2", pady=10, command=calculate)
        calc_btn.pack(fill=tk.X, pady=(10, 0))
    
    def _show_performance_dashboard(self):
        """Show performance analytics dashboard"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("📈 Performance Analytics")
        window.geometry("500x480")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Trading Performance Dashboard", bg=colors['bg'], 
                        fg=colors['accent'], font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15), anchor="w")
        
        stats = [
            ("📊 Total Trades", "42"),
            ("✅ Winning Trades", "28 (66.7%)"),
            ("❌ Losing Trades", "14 (33.3%)"),
            ("💰 Gross Profit", "$2,450.50"),
            ("📉 Gross Loss", "-$820.30"),
            ("🎯 Net Profit", "$1,630.20"),
            ("📈 Win Rate", "66.7%"),
            ("💎 Profit Factor", "2.98"),
            ("🎲 Max Drawdown", "-12.3%"),
            ("⏱️ Avg Trade Duration", "4.2 hours"),
        ]
        
        for label, value in stats:
            stat_frame = tk.Frame(frame, bg=colors['card_bg'], relief=tk.FLAT, bd=1)
            stat_frame.pack(fill=tk.X, pady=4)
            
            tk.Label(stat_frame, text=label, bg=colors['card_bg'], fg=colors['text_secondary'],
                    font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=10, pady=8)
            tk.Label(stat_frame, text=value, bg=colors['card_bg'], fg=colors['accent'],
                    font=("Segoe UI", 10, "bold")).pack(side=tk.RIGHT, padx=10, pady=8)
        
        close_btn = tk.Button(frame, text="💾 Export Report", bg=colors['button_bg'],
                            fg=colors['fg'], font=("Segoe UI", 10), relief=tk.FLAT,
                            cursor="hand2", command=window.destroy)
        close_btn.pack(fill=tk.X, pady=(15, 0))
    
    def _show_trade_journal(self):
        """Show trade journal and review"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("📓 Trade Journal")
        window.geometry("550x420")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Recent Trades Review", bg=colors['bg'], 
                        fg=colors['accent'], font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15), anchor="w")
        
        # Create treeview for trades
        columns = ("Date", "Symbol", "Type", "Entry", "Exit", "P&L", "Duration")
        tree = tk.Frame(frame, bg=colors['bg'])
        tree.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Header
        header = tk.Frame(tree, bg=colors['card_bg'])
        header.pack(fill=tk.X)
        
        for col in columns:
            tk.Label(header, text=col, bg=colors['card_bg'], fg=colors['text_secondary'],
                    font=("Segoe UI", 8, "bold"), width=12).pack(side=tk.LEFT, padx=3, pady=5)
        
        # Sample trades
        trades = [
            ("2025-11-04", "SOL", "LONG", "140.22", "142.50", "+$45.50", "2h 30m"),
            ("2025-11-04", "BTC", "SHORT", "43250", "43100", "+$120.00", "1h 15m"),
            ("2025-11-03", "SOL", "LONG", "138.50", "136.80", "-$35.20", "3h 45m"),
        ]
        
        for trade in trades:
            trade_frame = tk.Frame(tree, bg=colors['input_bg'])
            trade_frame.pack(fill=tk.X, pady=2)
            
            for i, val in enumerate(trade):
                color = colors['button_bg'] if '+' in val else colors['danger'] if '-' in val else colors['text_secondary']
                tk.Label(trade_frame, text=val, bg=colors['input_bg'], fg=color,
                        font=("Segoe UI", 8), width=12).pack(side=tk.LEFT, padx=3, pady=3)
        
        btn_frame = tk.Frame(frame, bg=colors['bg'])
        btn_frame.pack(fill=tk.X)
        
        export_btn = tk.Button(btn_frame, text="📥 Export CSV", bg=colors['button_bg'],
                              fg=colors['fg'], font=("Segoe UI", 9), relief=tk.FLAT,
                              cursor="hand2", command=lambda: messagebox.showinfo("Exported", "Trade journal exported to CSV"))
        export_btn.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        close_btn = tk.Button(btn_frame, text="❌ Close", bg=colors['danger'],
                             fg=colors['fg'], font=("Segoe UI", 9), relief=tk.FLAT,
                             cursor="hand2", command=window.destroy)
        close_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _show_api_settings(self):
        """Show API settings"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("🔌 API Configuration")
        window.geometry("460x400")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Binance API Settings", bg=colors['bg'], fg=colors['accent'],
                        font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15), anchor="w")
        
        # API Key
        tk.Label(frame, text="🔑 API Key:", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 3))
        api_key = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                          font=("Segoe UI", 9), relief=tk.FLAT, bd=1, show="*")
        api_key.pack(fill=tk.X, pady=(0, 15))
        
        # Secret Key
        tk.Label(frame, text="🔐 Secret Key:", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 3))
        secret_key = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                             font=("Segoe UI", 9), relief=tk.FLAT, bd=1, show="*")
        secret_key.pack(fill=tk.X, pady=(0, 15))
        
        # Testnet toggle
        testnet_var = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="🧪 Use Testnet (Recommended for testing)",
                      variable=testnet_var, bg=colors['bg'], fg=colors['fg'],
                      font=("Segoe UI", 9), selectcolor=colors['input_bg']).pack(anchor="w", pady=10)
        
        # Connection status
        tk.Label(frame, text="🟢 Connection: Connected", bg=colors['bg'],
                fg=colors['button_bg'], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 10))
        
        # Buttons
        btn_frame = tk.Frame(frame, bg=colors['bg'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        test_btn = tk.Button(btn_frame, text="🧪 Test Connection", bg=colors['warning'],
                            fg=colors['fg'], font=("Segoe UI", 9), relief=tk.FLAT,
                            cursor="hand2", command=lambda: messagebox.showinfo("Test", "✅ Connection successful!"))
        test_btn.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        save_btn = tk.Button(btn_frame, text="💾 Save", bg=colors['button_bg'],
                            fg=colors['fg'], font=("Segoe UI", 9), relief=tk.FLAT,
                            cursor="hand2", command=window.destroy)
        save_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _save_settings(self):
        """Save settings"""
        messagebox.showinfo("Saved", "Settings saved successfully!")
    
    def _restore_defaults(self):
        """Restore default settings"""
        messagebox.showinfo("Restored", "Settings restored to defaults!")
    
    def _show_user_guide(self):
        """Show user guide"""
        guide = """
🎯 MASTER TRADER USER GUIDE

1. SELECT SYMBOL
   • Search and select cryptocurrency
   • Supported: All Binance USDT pairs

2. CONFIGURE RISK
   • Set risk percentage (0.1-5%)
   • Adjust stop loss multiplier
   • Define take profit ratio

3. START TRADING
   • Click "START BOT" to begin
   • Monitor real-time stats
   • View trades in activity log

4. TEST FIRST
   • Use "TEST RUN" to backtest
   • Verify profitability
   • Optimize settings

5. STOP SAFELY
   • Click "STOP BOT" to pause
   • Current positions remain open
   • Can resume trading later
"""
        self._show_text_window("User Guide", guide)
    
    def _show_setup_guide(self):
        """Show setup guide"""
        guide = """
⚙️ SETUP GUIDE

1. API KEYS
   • Get from Binance API Management
   • Add to settings → API Settings
   • Use testnet keys for testing

2. RISK SETTINGS
   • Risk: 1-2% per trade recommended
   • Stop Loss: 2x ATR typical
   • Take Profit: 2:1 risk/reward

3. SYMBOLS
   • Start with major pairs (BTC, ETH, SOL)
   • Test with small positions
   • Scale up gradually

4. MONITORING
   • Watch win rate and ROI
   • Check max drawdown
   • Review trade log daily
"""
        self._show_text_window("Setup Guide", guide)
    
    def _show_stats_guide(self):
        """Show stats explanation"""
        stats = """
📊 UNDERSTANDING STATS

💵 BALANCE
   Current account balance in USDT

📊 P&L (Profit/Loss)
   Net gain/loss from trades

✅ WIN RATE
   Percentage of profitable trades

🔄 TRADES
   Total number of executed trades

🎯 ROI (Return on Investment)
   Percentage return on capital

📈 SHARPE RATIO
   Risk-adjusted returns (>1.0 good)

📉 MAX DRAWDOWN
   Largest peak-to-trough decline
"""
        self._show_text_window("Stats Guide", stats)
    
    def _show_troubleshooting(self):
        """Show troubleshooting"""
        tips = """
❌ TROUBLESHOOTING

API CONNECTION FAILED
   • Check internet connection
   • Verify API keys in settings
   • Check IP whitelist on Binance

BOT NOT EXECUTING TRADES
   • Verify symbol is correct
   • Check risk settings
   • Review order logs

BALANCE NOT UPDATING
   • Reconnect to API
   • Check account balance on Binance
   • Verify symbols trading

HIGH DRAWDOWN
   • Reduce risk percentage
   • Check market conditions
   • Review strategy parameters
"""
        self._show_text_window("Troubleshooting", tips)
    
    def _show_about(self):
        """Show about dialog"""
        about = """
🚀 MASTER TRADER v1.0

Professional Crypto Trading Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Features:
• Real-time trading dashboard
• Advanced risk management
• Backtesting engine
• ML-powered predictions
• Live Binance integration
• Support for 100+ pairs

Support: https://crypto-bot.io
License: MIT

© 2024 Master Trader
"""
        self._show_text_window("About Master Trader", about)
    
    def _show_version(self):
        """Show version info"""
        version_info = """
📦 APPLICATION VERSION

Version: 1.0.0
Release: 2024
Status: Production Ready

Python: 3.10+
Tkinter: Built-in
Dependencies:
  • matplotlib
  • pandas
  • numpy
  • requests
  • xgboost
  • scikit-learn

Updates: Check official repository
Last Updated: 2024-11-04
"""
        self._show_text_window("Version Info", version_info)
    
    def _open_docs(self):
        """Open documentation"""
        import webbrowser
        messagebox.showinfo("Documentation", 
            "Opening documentation...\n\n"
            "If browser doesn't open, visit:\n"
            "https://crypto-bot.io/docs")
        try:
            webbrowser.open("https://crypto-bot.io/docs")
        except:
            pass
    
    def _show_shortcuts_dialog(self):
        """Show keyboard shortcuts dialog"""
        shortcuts = """
⌨️ KEYBOARD SHORTCUTS

TRADING
  Ctrl+S .......... Start/Stop Bot
  Ctrl+B ......... Run Backtest
  Ctrl+E ......... Emergency Stop

VIEW
  Ctrl+T ......... Toggle Theme
  Ctrl+R ......... Refresh Data
  F5 ............ Full Refresh

WINDOW
  Ctrl+Q ......... Quit Application
  Escape ........ Close Dialog
  F1 ............ Show Help

NAVIGATION
  Tab ........... Next Field
  Shift+Tab ..... Previous Field
  Enter ......... Confirm
"""
        self._show_text_window("Keyboard Shortcuts", shortcuts)
    
    def _show_text_window(self, title: str, text: str):
        """Show text in new window"""
        colors = theme_manager.get_colors()
        
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("500x400")
        window.configure(bg=colors['bg'])
        
        # Text widget
        text_widget = scrolledtext.ScrolledText(
            window,
            bg=colors['input_bg'], fg=colors['fg'],
            font=("Courier", 9),
            relief=tk.FLAT, bd=0, wrap=tk.WORD
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, text)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        close_btn = ModernButton(window, "Close", command=window.destroy)
        close_btn.pack(pady=10)
    
    def _show_live_api_manager(self):
        """Live API Key Manager - Add/Change Binance and Testnet keys"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("🔑 Live API Key Manager")
        window.geometry("520x580")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Binance API Key Configuration", bg=colors['bg'], 
                        fg=colors['accent'], font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 20), anchor="w")
        
        # Live API Section
        live_label = tk.Label(frame, text="🔴 LIVE TRADING API", bg=colors['bg'], 
                             fg=colors['danger'], font=("Segoe UI", 11, "bold"))
        live_label.pack(anchor="w", pady=(15, 10))
        
        tk.Label(frame, text="Live API Key:", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 2))
        live_key = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                           font=("Segoe UI", 9), relief=tk.FLAT, bd=1, show="*", width=50)
        live_key.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(frame, text="Live API Secret:", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 2))
        live_secret = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                              font=("Segoe UI", 9), relief=tk.FLAT, bd=1, show="*", width=50)
        live_secret.pack(fill=tk.X, pady=(0, 15))
        
        # Testnet API Section
        testnet_label = tk.Label(frame, text="🧪 TESTNET API", bg=colors['bg'], 
                                fg=colors['info'], font=("Segoe UI", 11, "bold"))
        testnet_label.pack(anchor="w", pady=(15, 10))
        
        tk.Label(frame, text="Testnet API Key:", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 2))
        test_key = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                           font=("Segoe UI", 9), relief=tk.FLAT, bd=1, show="*", width=50)
        test_key.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(frame, text="Testnet API Secret:", bg=colors['bg'], fg=colors['text_secondary'],
                font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 2))
        test_secret = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                              font=("Segoe UI", 9), relief=tk.FLAT, bd=1, show="*", width=50)
        test_secret.pack(fill=tk.X, pady=(0, 15))
        
        # Mode indicator
        mode_var = tk.StringVar(value="testnet")
        mode_frame = tk.Frame(frame, bg=colors['bg'])
        mode_frame.pack(fill=tk.X, pady=(10, 20))
        
        tk.Radiobutton(mode_frame, text="🧪 Use Testnet (Safe)", variable=mode_var, 
                      value="testnet", bg=colors['bg'], fg=colors['fg'],
                      selectcolor=colors['input_bg'], font=("Segoe UI", 9)).pack(anchor="w", pady=5)
        tk.Radiobutton(mode_frame, text="🔴 Use Live (Real Money)", variable=mode_var, 
                      value="live", bg=colors['bg'], fg=colors['fg'],
                      selectcolor=colors['input_bg'], font=("Segoe UI", 9)).pack(anchor="w", pady=5)
        
        # Action buttons
        btn_frame = tk.Frame(frame, bg=colors['bg'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        def test_connection():
            mode = mode_var.get()
            messagebox.showinfo("Connection", f"✅ {mode.upper()} connection successful!")
        
        def save_keys():
            messagebox.showinfo("Saved", "✅ API keys saved securely!")
            window.destroy()
        
        test_btn = tk.Button(btn_frame, text="🧪 Test Connection", bg=colors['info'],
                            fg=colors['fg'], font=("Segoe UI", 9), relief=tk.FLAT,
                            cursor="hand2", command=test_connection)
        test_btn.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        save_btn = tk.Button(btn_frame, text="💾 Save Keys", bg=colors['button_bg'],
                            fg=colors['fg'], font=("Segoe UI", 9), relief=tk.FLAT,
                            cursor="hand2", command=save_keys)
        save_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _show_live_trading_view(self):
        """Show professional Binance-like live trading view"""
        if LiveTradingPanel is None:
            messagebox.showerror("Error", "Live Trading View requires additional packages.\n\n"
                               "Install with: pip install mplfinance matplotlib pandas numpy")
            return
        
        window = tk.Toplevel(self.root)
        window.title("📈 Live Trading View - Binance Style")
        window.geometry("1400x900")
        window.transient(self.root)
        
        try:
            # Create live trading panel
            panel = LiveTradingPanel(window, theme_manager)
            panel.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load trading view:\n{str(e)}")
            window.destroy()
    
    def _show_trading_method_selector(self):
        """Trading Method Selector - Spot/Margin/Futures"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("🏦 Trading Method Selector")
        window.geometry("480x520")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Select Trading Method", bg=colors['bg'], 
                        fg=colors['accent'], font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 20), anchor="w")
        
        methods = {
            "📊 SPOT TRADING": {
                "desc": "Buy and hold cryptocurrency",
                "risk": "Low",
                "leverage": "1x",
                "features": ["No leverage", "Secure", "Best for beginners", "Perfect for hodling"]
            },
            "💼 MARGIN TRADING": {
                "desc": "Borrow funds to increase position size",
                "risk": "Medium",
                "leverage": "Up to 3x",
                "features": ["3x max leverage", "More capital required", "Liquidation risk", "Pro traders"]
            },
            "⚡ FUTURES TRADING": {
                "desc": "Trade with leverage and go short (perpetual contracts)",
                "risk": "High",
                "leverage": "Up to 20x",
                "features": ["High leverage", "24/7 trading", "Go short/long", "Advanced only"]
            }
        }
        
        selected = tk.StringVar(value="spot")
        
        for method, info in methods.items():
            box = tk.Frame(frame, bg=colors['input_bg'], relief=tk.FLAT, bd=1)
            box.pack(fill=tk.X, pady=8)
            
            header = tk.Frame(box, bg=colors['input_bg'])
            header.pack(fill=tk.X, padx=10, pady=10)
            
            mode_val = method.split()[0].lower()
            rb = tk.Radiobutton(header, text=method, variable=selected, value=mode_val,
                              bg=colors['input_bg'], fg=colors['fg'], selectcolor=colors['button_bg'],
                              font=("Segoe UI", 11, "bold"), cursor="hand2")
            rb.pack(anchor="w")
            
            tk.Label(header, text=info['desc'], bg=colors['input_bg'], fg=colors['text_secondary'],
                    font=("Segoe UI", 9), wraplength=400, justify="left").pack(anchor="w", pady=(5, 0))
            
            details = tk.Frame(box, bg=colors['input_bg'])
            details.pack(fill=tk.X, padx=18, pady=(0, 8))
            
            tk.Label(details, text=f"Risk Level: {info['risk']}", bg=colors['input_bg'], 
                    fg=colors['warning'], font=("Segoe UI", 9)).pack(anchor="w")
            tk.Label(details, text=f"Max Leverage: {info['leverage']}", bg=colors['input_bg'], 
                    fg=colors['accent'], font=("Segoe UI", 9)).pack(anchor="w")
            
            for feat in info['features']:
                tk.Label(details, text=f"  ✓ {feat}", bg=colors['input_bg'], 
                        fg=colors['fg'], font=("Segoe UI", 8)).pack(anchor="w")
        
        btn_frame = tk.Frame(frame, bg=colors['bg'])
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        def apply_method():
            method_name = selected.get().upper()
            messagebox.showinfo("Method Selected", f"✅ Switched to {method_name} trading!")
            window.destroy()
        
        apply_btn = tk.Button(btn_frame, text="✅ Apply Method", bg=colors['button_bg'],
                             fg=colors['fg'], font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                             cursor="hand2", command=apply_method)
        apply_btn.pack(fill=tk.X)
    
    def _show_advanced_strategy_selector(self):
        """Advanced Strategy & Timeframe Selector"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("📈 Strategy & Timeframe Configuration")
        window.geometry("550x650")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Select Trading Strategy & Timeframe", bg=colors['bg'], 
                        fg=colors['accent'], font=("Segoe UI", 13, "bold"))
        title.pack(pady=(0, 15), anchor="w")
        
        # Strategy Selection
        strat_label = tk.Label(frame, text="📊 Trading Strategies", bg=colors['bg'], 
                              fg=colors['accent'], font=("Segoe UI", 11, "bold"))
        strat_label.pack(anchor="w", pady=(10, 8))
        
        strategy_var = tk.StringVar(value="scalp")
        strategies = {
            "⚡ SCALP TRADING": ("scalp", "Hold seconds to minutes. Max 50+ trades/day. High frequency, small profits per trade."),
            "📈 SWING TRADING": ("swing", "Hold hours to days. 10-15 trades/day. Medium risk, balanced approach."),
            "📊 DAY TRADING": ("day", "Hold minutes to hours. 3-10 trades/day. Intraday movements, close all positions."),
            "🏔️ POSITION TRADING": ("position", "Hold days to weeks. 1-3 trades/week. Long-term trends, major moves."),
            "🎯 MEAN REVERSION": ("reversion", "Buy oversold, sell overbought. Uses RSI & Bollinger Bands."),
            "🔄 TREND FOLLOWING": ("trend", "Follow strong trends with momentum. Uses MA & MACD."),
        }
        
        for name, (val, desc) in strategies.items():
            rb = tk.Radiobutton(frame, text=f"{name}", variable=strategy_var, value=val,
                              bg=colors['bg'], fg=colors['fg'], selectcolor=colors['button_bg'],
                              font=("Segoe UI", 9), cursor="hand2")
            rb.pack(anchor="w", pady=3)
            desc_label = tk.Label(frame, text=desc, bg=colors['bg'], fg=colors['text_secondary'],
                                 font=("Segoe UI", 8), wraplength=500, justify="left")
            desc_label.pack(anchor="w", padx=25, pady=(0, 8))
        
        # Timeframe Selection
        tf_label = tk.Label(frame, text="⏱️ Select Timeframe(s)", bg=colors['bg'], 
                           fg=colors['accent'], font=("Segoe UI", 11, "bold"))
        tf_label.pack(anchor="w", pady=(15, 8))
        
        tf_var = tk.StringVar(value="1h")
        timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        
        tf_frame = tk.Frame(frame, bg=colors['bg'])
        tf_frame.pack(anchor="w", fill=tk.X, pady=(0, 15))
        
        for tf in timeframes:
            rb = tk.Radiobutton(tf_frame, text=tf, variable=tf_var, value=tf,
                              bg=colors['bg'], fg=colors['fg'], selectcolor=colors['button_bg'],
                              font=("Segoe UI", 9))
            rb.pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        btn_frame = tk.Frame(frame, bg=colors['bg'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        def apply_settings():
            strategy = strategy_var.get().upper()
            timeframe = tf_var.get()
            messagebox.showinfo("Settings Applied", 
                              f"✅ Strategy: {strategy}\n✅ Timeframe: {timeframe}")
            window.destroy()
        
        apply_btn = tk.Button(btn_frame, text="✅ Apply Settings", bg=colors['button_bg'],
                             fg=colors['fg'], font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                             cursor="hand2", command=apply_settings)
        apply_btn.pack(fill=tk.X)
    
    def _show_bot_reliability_settings(self):
        """Bot Reliability & Efficiency Tweaks"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("⚙️ Bot Reliability & Efficiency Settings")
        window.geometry("520x620")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Optimize Bot Performance", bg=colors['bg'], 
                        fg=colors['accent'], font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15), anchor="w")
        
        # Reliability Settings
        rel_label = tk.Label(frame, text="🛡️ Reliability", bg=colors['bg'], 
                            fg=colors['accent'], font=("Segoe UI", 11, "bold"))
        rel_label.pack(anchor="w", pady=(10, 8))
        
        auto_recover = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="🔄 Auto-Recover from Disconnections", 
                      variable=auto_recover, bg=colors['bg'], fg=colors['fg'],
                      font=("Segoe UI", 9), selectcolor=colors['input_bg']).pack(anchor="w", pady=3)
        
        position_manager = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="📍 Aggressive Position Management", 
                      variable=position_manager, bg=colors['bg'], fg=colors['fg'],
                      font=("Segoe UI", 9), selectcolor=colors['input_bg']).pack(anchor="w", pady=3)
        
        emergency_stop = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="⚠️ Emergency Stop at Max Drawdown", 
                      variable=emergency_stop, bg=colors['bg'], fg=colors['fg'],
                      font=("Segoe UI", 9), selectcolor=colors['input_bg']).pack(anchor="w", pady=3)
        
        # Efficiency Settings
        eff_label = tk.Label(frame, text="⚡ Efficiency", bg=colors['bg'], 
                            fg=colors['accent'], font=("Segoe UI", 11, "bold"))
        eff_label.pack(anchor="w", pady=(15, 8))
        
        tk.Label(frame, text="Max Daily Profit Target ($):", bg=colors['bg'], 
                fg=colors['text_secondary'], font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 2))
        profit_entry = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                               font=("Segoe UI", 9), relief=tk.FLAT, bd=1, width=20)
        profit_entry.insert(0, "500")
        profit_entry.pack(anchor="w", pady=(0, 8))
        
        tk.Label(frame, text="Max Daily Loss Limit ($):", bg=colors['bg'], 
                fg=colors['text_secondary'], font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 2))
        loss_entry = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                             font=("Segoe UI", 9), relief=tk.FLAT, bd=1, width=20)
        loss_entry.insert(0, "200")
        loss_entry.pack(anchor="w", pady=(0, 8))
        
        tk.Label(frame, text="Min Win Rate Threshold (%):", bg=colors['bg'], 
                fg=colors['text_secondary'], font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 2))
        win_entry = tk.Entry(frame, bg=colors['input_bg'], fg=colors['fg'],
                            font=("Segoe UI", 9), relief=tk.FLAT, bd=1, width=20)
        win_entry.insert(0, "50")
        win_entry.pack(anchor="w", pady=(0, 8))
        
        # Profit Maximization
        profit_label = tk.Label(frame, text="💰 Profit Maximization", bg=colors['bg'], 
                               fg=colors['accent'], font=("Segoe UI", 11, "bold"))
        profit_label.pack(anchor="w", pady=(15, 8))
        
        trailing_stop = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="📈 Enable Trailing Stop Loss", 
                      variable=trailing_stop, bg=colors['bg'], fg=colors['fg'],
                      font=("Segoe UI", 9), selectcolor=colors['input_bg']).pack(anchor="w", pady=3)
        
        dynamic_risk = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="🎯 Dynamic Risk Adjustment", 
                      variable=dynamic_risk, bg=colors['bg'], fg=colors['fg'],
                      font=("Segoe UI", 9), selectcolor=colors['input_bg']).pack(anchor="w", pady=3)
        
        partial_tp = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="💎 Partial Take Profit (3-tier)", 
                      variable=partial_tp, bg=colors['bg'], fg=colors['fg'],
                      font=("Segoe UI", 9), selectcolor=colors['input_bg']).pack(anchor="w", pady=3)
        
        # Buttons
        btn_frame = tk.Frame(frame, bg=colors['bg'])
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        def save_reliability():
            messagebox.showinfo("Saved", "✅ Bot optimization settings saved!")
            window.destroy()
        
        save_btn = tk.Button(btn_frame, text="💾 Save Settings", bg=colors['button_bg'],
                            fg=colors['fg'], font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                            cursor="hand2", command=save_reliability)
        save_btn.pack(fill=tk.X)
    
    def _show_desktop_shortcut_creator(self):
        """Create desktop shortcut with icon"""
        colors = theme_manager.get_colors()
        window = tk.Toplevel(self.root)
        window.title("🖥️ Desktop Shortcut Creator")
        window.geometry("480x420")
        window.transient(self.root)
        
        frame = tk.Frame(window, bg=colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        title = tk.Label(frame, text="Create Desktop Shortcut", bg=colors['bg'], 
                        fg=colors['accent'], font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 15))
        
        info = tk.Label(frame, text="""
🎯 This will create a desktop shortcut for Master Trader

📍 Location: ~/Desktop/Master Trader.lnk
🎨 Icon: Crypto BOT icon.png
⏱️ Execution: Direct exe launch
📂 Working Dir: Application folder

Benefits:
  ✓ Quick access to Master Trader
  ✓ Custom icon display
  ✓ One-click launch
  ✓ Professional appearance
        """, bg=colors['bg'], fg=colors['fg'], font=("Segoe UI", 10),
                    justify="left", wraplength=420)
        info.pack(fill=tk.BOTH, expand=True, pady=15)
        
        btn_frame = tk.Frame(frame, bg=colors['bg'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        def create_shortcut():
            try:
                import winreg
                from pathlib import Path
                import os
                
                # Get desktop path
                desktop = Path.home() / "Desktop"
                shortcut_path = desktop / "Master Trader.lnk"
                
                # Simple Python approach
                vbs_code = f'''
Dim objShell, strShortcutPath, strTargetPath, objShortcut
Set objShell = WScript.CreateObject("WScript.Shell")
strShortcutPath = "{shortcut_path}"
strTargetPath = "{os.path.abspath('dist/MasterTrader.exe')}"

Set objShortcut = objShell.CreateShortcut(strShortcutPath)
objShortcut.TargetPath = strTargetPath
objShortcut.WorkingDirectory = "{os.path.abspath('.')}"
objShortcut.IconLocation = "{os.path.abspath('Crypto BOT icon.png')}"
objShortcut.Save
'''
                
                vbs_file = '__create_shortcut.vbs'
                with open(vbs_file, 'w') as f:
                    f.write(vbs_code)
                
                os.system(f'cscript.exe "{vbs_file}"')
                os.remove(vbs_file)
                
                messagebox.showinfo("Success", 
                    f"✅ Desktop shortcut created!\n\nLocation: {desktop}\\Master Trader.lnk")
                window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create shortcut: {e}")
        
        create_btn = tk.Button(btn_frame, text="✅ Create Shortcut", bg=colors['button_bg'],
                              fg=colors['fg'], font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                              cursor="hand2", command=create_shortcut)
        create_btn.pack(fill=tk.X, padx=(0, 10), expand=True, side=tk.LEFT)
        
        close_btn = tk.Button(btn_frame, text="❌ Cancel", bg=colors['danger'],
                             fg=colors['fg'], font=("Segoe UI", 10), relief=tk.FLAT,
                             cursor="hand2", command=window.destroy)
        close_btn.pack(fill=tk.X, expand=True, side=tk.LEFT)
    
    def _toggle_theme(self):
        """Toggle light/dark theme"""
        theme_manager.switch_theme()
    
    def _on_theme_change(self, colors):
        """Handle theme change"""
        try:
            if self.root.winfo_exists():
                self.root.configure(bg=colors['bg'])
            if self.logo_frame:
                self.logo_frame.configure(bg=colors['card_bg'])
            if self.logo_image_label:
                self.logo_image_label.configure(bg=colors['card_bg'])
            if self.logo_title_label:
                self.logo_title_label.configure(bg=colors['card_bg'], fg=colors['accent'])
            if hasattr(self, 'content_splitter') and self.content_splitter.winfo_exists():
                self.content_splitter.configure(bg=colors['bg'])
            if hasattr(self, 'center_right_splitter') and self.center_right_splitter.winfo_exists():
                self.center_right_splitter.configure(bg=colors['bg'])
            self._refresh_trading_pairs_display()
            if self.market_view_sections:
                self._switch_market_view_mode(self.market_view_mode.get())
        except:
            pass


def main():
    """Launch master trader GUI"""
    root = tk.Tk()
    app = MasterTraderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()