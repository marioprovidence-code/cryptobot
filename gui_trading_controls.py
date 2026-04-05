import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Callable, Dict, List
import json
import os
import time
import random

# Try to import crypto_bot components, fallback to mock objects if not available
try:
    from crypto_bot import (
        TradingMode, TimeFrame, RiskConfig, 
        market_tracker, MLModel, run_live_in_thread
    )
except (ImportError, ModuleNotFoundError):
    # Fallback mock objects
    class TradingMode:
        SPOT = "Spot"
        MARGIN = "Margin"
        FUTURES = "Futures"
    
    class TimeFrame:
        SCALP = "Scalp (1m)"
        SHORT = "Short (5m)"
        MEDIUM = "Medium (1h)"
        LONG = "Long (1d)"
    
    class RiskConfig:
        TRADING_MODE = "Spot"
        LEVERAGE = 1.0
        MAX_LEVERAGE = 10.0
        TIMEFRAME = "Medium (1h)"
        AUTO_MODE_SWITCH = False
    
    class MockMarketTracker:
        def __init__(self):
            self.gainers = []
            self.losers = []
            self.new_listings = []
            self.mode_metrics = {}
            self.available_pairs = [
                "BTCUSDT",
                "ETHUSDT",
                "SOLUSDT",
                "ADAUSDT",
                "XRPUSDT",
                "DOGEUSDT",
                "BNBUSDT",
            ]

        def update_market_data(self):
            timestamp = time.time()
            self.gainers = [
                {
                    "symbol": symbol,
                    "change": random.uniform(0.5, 8.0),
                    "volume": random.uniform(5_000, 50_000),
                    "price": random.uniform(0.5, 250.0),
                }
                for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT")
            ]
            self.losers = [
                {
                    "symbol": symbol,
                    "change": -random.uniform(0.5, 6.0),
                    "volume": random.uniform(3_000, 40_000),
                    "price": random.uniform(0.05, 120.0),
                }
                for symbol in ("ADAUSDT", "XRPUSDT", "DOGEUSDT")
            ]
            self.new_listings = [
                {
                    "symbol": f"NEW{i}USDT",
                    "time": timestamp,
                    "price": random.uniform(0.01, 10.0),
                    "volume": random.uniform(1_000, 15_000),
                }
                for i in range(1, 4)
            ]
            self.mode_metrics = {
                "Spot": {
                    "trades": random.randint(5, 25),
                    "profit": random.uniform(-250.0, 750.0),
                    "max_drawdown": random.uniform(2.0, 12.0),
                }
            }

        def search_pairs(self, text):
            query = (text or "").upper()
            return [symbol for symbol in self.available_pairs if query in symbol]
    
    market_tracker = MockMarketTracker()
    MLModel = None
    run_live_in_thread = None

class TradingControlsFrame(ttk.Frame):
    def __init__(self, parent, callback: Callable = None):
        super().__init__(parent)
        self.callback = callback
        self.stop_event = None
        self.active_symbols = set()
        self.create_widgets()
        
    def create_widgets(self):
        # Trading Mode Controls
        mode_frame = ttk.LabelFrame(self, text="Trading Mode")
        mode_frame.pack(fill="x", padx=5, pady=5)
        
        self.mode_var = tk.StringVar(value=RiskConfig.TRADING_MODE)
        for mode in [TradingMode.SPOT, TradingMode.MARGIN, TradingMode.FUTURES]:
            ttk.Radiobutton(mode_frame, text=mode, value=mode, 
                          variable=self.mode_var,
                          command=self.on_mode_change).pack(anchor="w", padx=5)
                          
        # Leverage Control
        leverage_frame = ttk.Frame(mode_frame)
        leverage_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(leverage_frame, text="Leverage:").pack(side="left")
        self.leverage_var = tk.DoubleVar(value=RiskConfig.LEVERAGE)
        leverage_spin = ttk.Spinbox(leverage_frame, from_=1.0, to=RiskConfig.MAX_LEVERAGE,
                                  increment=0.5, textvariable=self.leverage_var,
                                  width=10, command=self.on_leverage_change)
        leverage_spin.pack(side="left", padx=5)
        
        # Timeframe Controls
        time_frame = ttk.LabelFrame(self, text="Timeframe")
        time_frame.pack(fill="x", padx=5, pady=5)
        
        self.timeframe_var = tk.StringVar(value=RiskConfig.TIMEFRAME)
        for tf in [TimeFrame.SCALP, TimeFrame.SHORT, TimeFrame.MEDIUM, TimeFrame.LONG]:
            ttk.Radiobutton(time_frame, text=tf, value=tf,
                          variable=self.timeframe_var,
                          command=self.on_timeframe_change).pack(anchor="w", padx=5)
        
        # Auto Mode Switch
        auto_frame = ttk.Frame(self)
        auto_frame.pack(fill="x", padx=5, pady=5)
        self.auto_mode_var = tk.BooleanVar(value=RiskConfig.AUTO_MODE_SWITCH)
        ttk.Checkbutton(auto_frame, text="Auto Mode Switch",
                       variable=self.auto_mode_var,
                       command=self.on_auto_mode_change).pack(side="left")
        
        # Symbol Selection
        symbol_frame = ttk.LabelFrame(self, text="Trading Pairs")
        symbol_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Search bar
        search_frame = ttk.Frame(symbol_frame)
        search_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Symbol lists
        lists_frame = ttk.Frame(symbol_frame)
        lists_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Available pairs
        avail_frame = ttk.LabelFrame(lists_frame, text="Available")
        avail_frame.pack(side="left", fill="both", expand=True)
        self.available_list = tk.Listbox(avail_frame, selectmode="multiple")
        self.available_list.pack(fill="both", expand=True)
        
        # Buttons frame
        btn_frame = ttk.Frame(lists_frame)
        btn_frame.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="→",
                  command=self.add_selected).pack(pady=2)
        ttk.Button(btn_frame, text="←",
                  command=self.remove_selected).pack(pady=2)
        
        # Active pairs
        active_frame = ttk.LabelFrame(lists_frame, text="Active")
        active_frame.pack(side="left", fill="both", expand=True)
        self.active_list = tk.Listbox(active_frame, selectmode="multiple")
        self.active_list.pack(fill="both", expand=True)
        
        # Market Info
        market_frame = ttk.LabelFrame(self, text="Market Information")
        market_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tabs for different views
        notebook = ttk.Notebook(market_frame)
        notebook.pack(fill="both", expand=True)
        
        # Gainers tab
        gainers_frame = ttk.Frame(notebook)
        notebook.add(gainers_frame, text="Gainers")
        self.gainers_tree = ttk.Treeview(gainers_frame, columns=("change", "volume", "price"),
                                       show="headings")
        self.gainers_tree.heading("change", text="Change %")
        self.gainers_tree.heading("volume", text="Volume")
        self.gainers_tree.heading("price", text="Price")
        self.gainers_tree.pack(fill="both", expand=True)
        
        # Losers tab
        losers_frame = ttk.Frame(notebook)
        notebook.add(losers_frame, text="Losers")
        self.losers_tree = ttk.Treeview(losers_frame, columns=("change", "volume", "price"),
                                      show="headings")
        self.losers_tree.heading("change", text="Change %")
        self.losers_tree.heading("volume", text="Volume")
        self.losers_tree.heading("price", text="Price")
        self.losers_tree.pack(fill="both", expand=True)
        
        # New Listings tab
        new_frame = ttk.Frame(notebook)
        notebook.add(new_frame, text="New Listings")
        self.new_tree = ttk.Treeview(new_frame, columns=("time", "price", "volume"),
                                   show="headings")
        self.new_tree.heading("time", text="Listed")
        self.new_tree.heading("price", text="Price")
        self.new_tree.heading("volume", text="Volume")
        self.new_tree.pack(fill="both", expand=True)
        
        # Performance tab
        perf_frame = ttk.Frame(notebook)
        notebook.add(perf_frame, text="Performance")
        self.perf_tree = ttk.Treeview(perf_frame, columns=("trades", "profit", "drawdown"),
                                    show="headings")
        self.perf_tree.heading("trades", text="Trades")
        self.perf_tree.heading("profit", text="Profit")
        self.perf_tree.heading("drawdown", text="Drawdown")
        self.perf_tree.pack(fill="both", expand=True)
        
        # Control buttons
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        self.start_btn = ttk.Button(control_frame, text="Start Trading",
                                  command=self.start_trading)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Trading",
                                 command=self.stop_trading, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        # Start update loop
        self.update_market_data()
        
    def on_mode_change(self, *args):
        """Handle trading mode change"""
        new_mode = self.mode_var.get()
        RiskConfig.TRADING_MODE = new_mode
        # Enable/disable leverage control
        if new_mode == TradingMode.SPOT:
            self.leverage_var.set(1.0)
        if self.callback:
            self.callback({"type": "mode_change", "mode": new_mode})
            
    def on_leverage_change(self, *args):
        """Handle leverage change"""
        new_leverage = min(self.leverage_var.get(), RiskConfig.MAX_LEVERAGE)
        RiskConfig.LEVERAGE = new_leverage
        if self.callback:
            self.callback({"type": "leverage_change", "leverage": new_leverage})
            
    def on_timeframe_change(self, *args):
        """Handle timeframe change"""
        new_tf = self.timeframe_var.get()
        RiskConfig.TIMEFRAME = new_tf
        if self.callback:
            self.callback({"type": "timeframe_change", "timeframe": new_tf})
            
    def on_auto_mode_change(self, *args):
        """Handle auto mode switch change"""
        auto_mode = self.auto_mode_var.get()
        RiskConfig.AUTO_MODE_SWITCH = auto_mode
        if self.callback:
            self.callback({"type": "auto_mode_change", "enabled": auto_mode})
            
    def on_search(self, *args):
        """Filter available symbols based on search"""
        search_text = self.search_var.get().upper()
        self.available_list.delete(0, tk.END)
        for symbol in market_tracker.search_pairs(search_text):
            if symbol not in self.active_symbols:
                self.available_list.insert(tk.END, symbol)
                
    def add_selected(self):
        """Add selected symbols to active list"""
        selected = self.available_list.curselection()
        for idx in selected:
            symbol = self.available_list.get(idx)
            self.active_symbols.add(symbol)
            self.active_list.insert(tk.END, symbol)
        self.refresh_available_list()
        
    def remove_selected(self):
        """Remove selected symbols from active list"""
        selected = self.active_list.curselection()
        for idx in reversed(selected):
            symbol = self.active_list.get(idx)
            self.active_symbols.remove(symbol)
            self.active_list.delete(idx)
        self.refresh_available_list()
        
    def refresh_available_list(self):
        """Refresh available symbols list"""
        self.available_list.delete(0, tk.END)
        search_text = self.search_var.get().upper()
        for symbol in market_tracker.search_pairs(search_text):
            if symbol not in self.active_symbols:
                self.available_list.insert(tk.END, symbol)
                
    def update_market_data(self):
        """Update market data displays"""
        try:
            market_tracker.update_market_data()
            
            # Update gainers
            self.gainers_tree.delete(*self.gainers_tree.get_children())
            for g in market_tracker.gainers:
                self.gainers_tree.insert("", "end", values=(
                    f"{g['change']:.2f}%",
                    f"{g['volume']:,.0f}",
                    f"{g['price']:.8f}"
                ))
                
            # Update losers
            self.losers_tree.delete(*self.losers_tree.get_children())
            for l in market_tracker.losers:
                self.losers_tree.insert("", "end", values=(
                    f"{l['change']:.2f}%",
                    f"{l['volume']:,.0f}",
                    f"{l['price']:.8f}"
                ))
                
            # Update new listings
            self.new_tree.delete(*self.new_tree.get_children())
            for n in market_tracker.new_listings:
                self.new_tree.insert("", "end", values=(
                    f"{n['time']:.0f}",
                    f"{n['price']:.8f}",
                    f"{n['volume']:,.0f}"
                ))
                
            # Update performance metrics
            self.perf_tree.delete(*self.perf_tree.get_children())
            for mode, metrics in market_tracker.mode_metrics.items():
                self.perf_tree.insert("", "end", text=mode, values=(
                    metrics['trades'],
                    f"{metrics['profit']:.2f}",
                    f"{metrics.get('max_drawdown', 0):.2f}%"
                ))
                
        except Exception as e:
            print(f"Error updating market data: {e}")
            
        # Schedule next update
        self.after(5000, self.update_market_data)
        
    def start_trading(self):
        """Start trading with selected configuration"""
        if not self.active_symbols:
            messagebox.showwarning("Warning", "Please select at least one trading pair")
            return
        
        if MLModel is None or run_live_in_thread is None:
            messagebox.showerror("Error", "Trading functions not available. Check dependencies.")
            return
            
        try:
            # Initialize model and strategy
            model = MLModel()
            
            # Create stop event
            self.stop_event = threading.Event()
            
            # Start trading thread
            trading_thread = threading.Thread(
                target=run_live_in_thread,
                kwargs={
                    "model": model,
                    "symbols": list(self.active_symbols),
                    "trades_csv": os.path.join("trades", f"multi_trades_{int(time.time())}.csv"),
                    "stop_event": self.stop_event,
                    "callback": self.on_trading_update
                }
            )
            trading_thread.daemon = True
            trading_thread.start()
            
            # Update button states
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start trading: {e}")
            
    def stop_trading(self):
        """Stop trading"""
        if self.stop_event:
            self.stop_event.set()
            self.stop_event = None
            
        # Update button states
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        
    def on_trading_update(self, metrics: Dict):
        """Handle trading updates"""
        try:
            if self.callback:
                self.callback({"type": "trading_update", "metrics": metrics})
        except Exception as e:
            print(f"Error handling trading update: {e}")

def main():
    root = tk.Tk()
    root.title("Trading Controls")
    app = TradingControlsFrame(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    main()