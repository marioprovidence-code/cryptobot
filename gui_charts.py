"""
CryptoBot Trading Chart Component
Provides real-time candlestick charts with indicators and trade markers.
Safe to import with fallbacks when matplotlib is not available.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any
from datetime import datetime
import threading
import json
import logging

logger = logging.getLogger(__name__)

# Safely import optional visualization deps
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import mplfinance as mpf
    import pandas as pd
    import numpy as np
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False

# Import core bot features with fallbacks
try:
    from crypto_bot import (
        get_historical_data_with_indicators,
        SYMBOLS
    )
except ImportError:
    def get_historical_data_with_indicators(*args, **kwargs):
        return None
    SYMBOLS = ["SOLUSDT", "BTCUSDT"]


class TradingChart:
    """Candlestick chart with indicators and trade markers"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize chart in parent widget"""
        self.parent = parent
        self.has_charts = HAS_CHARTS
        self.last_update = None
        self.trades = []
        self.layout = {
            'show_volume': True,
            'indicators': ['SMA_20', 'RSI_14'],
            'colors': {
                'up': '#26a69a',
                'down': '#ef5350',
                'volume': '#607d8b',
                'grid': '#404040'
            },
            'styles': {
                'gridstyle': '--',
                'gridwidth': 0.5,
                'volume_alpha': 0.5
            }
        }
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        
        if not self.has_charts:
            self._show_fallback()
            return
            
        # Setup matplotlib
        self.fig, self.ax = plt.subplots(
            figsize=(10, 6),
            facecolor='#1a1a1a'
        )
        self.ax.set_facecolor('#2d2d2d')
        self.canvas = FigureCanvasTkAgg(
            self.fig, self.frame
        )
        self.canvas.get_tk_widget().pack(
            fill='both', expand=True
        )
        
        # Initial empty plot
        self._plot_empty()
        
    def _show_fallback(self) -> None:
        """Show message when matplotlib not available"""
        msg = "Charts require matplotlib & mplfinance"
        ttk.Label(
            self.frame,
            text=msg,
            style='Fallback.TLabel'
        ).pack(expand=True)
        
    def _plot_empty(self) -> None:
        """Show empty chart with instructions"""
        if not self.has_charts:
            return
            
        self.ax.clear()
        self.ax.text(
            0.5, 0.5,
            'No data - start bot to see chart',
            ha='center', va='center',
            transform=self.ax.transAxes,
            color='white', fontsize=12
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()
        
    def save_layout(self, filepath: str) -> None:
        """Save chart layout to JSON file"""
        if not self.has_charts:
            return
        try:
            with open(filepath, 'w') as f:
                json.dump(self.layout, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save layout: {e}")
            
    def load_layout(self, filepath: str) -> None:
        """Load chart layout from JSON file"""
        if not self.has_charts:
            return
        try:
            with open(filepath, 'r') as f:
                self.layout = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load layout: {e}")
            
    def add_indicator(self, name: str, color: str = None) -> None:
        """Add technical indicator to chart"""
        if not self.has_charts:
            return
        if name not in self.layout['indicators']:
            self.layout['indicators'].append(name)
            if color:
                self.layout['colors'][name] = color
        
    def update(self, df: pd.DataFrame) -> None:
        """Update chart with new OHLCV data"""
        if not self.has_charts or df is None:
            return
            
        # Skip if too soon
        now = datetime.now()
        if (self.last_update and
            (now - self.last_update).seconds < 1):
            return
            
        self.last_update = now
        
        # Clear old data
        self.ax.clear()
        
        # Plot candlesticks
        mpf.plot(
            df,
            type='candle',
            style='charles',
            ax=self.ax,
            volume=True,
            ylabel='Price',
            ylabel_lower='Volume'
        )
        
        # Add trades
        self._plot_trades()
        
        # Style
        self.ax.set_facecolor('#2d2d2d')
        self.ax.tick_params(colors='white')
        self.ax.grid(True, alpha=0.2)
        
        # Update canvas
        self.canvas.draw()
        
    def add_trade(self, price: float, type_: str) -> None:
        """Add trade marker to chart"""
        if not self.has_charts:
            return
            
        self.trades.append({
            'timestamp': datetime.now(),
            'price': price,
            'type': type_
        })
        
    def _plot_trades(self) -> None:
        """Plot trade markers on chart"""
        if not self.has_charts:
            return
            
        for trade in self.trades:
            marker = '^' if trade['type'] == 'buy' else 'v'
            color = 'g' if trade['type'] == 'buy' else 'r'
            self.ax.scatter(
                trade['timestamp'],
                trade['price'],
                c=color,
                marker=marker,
                s=100
            )


def main():
    """Test chart component"""
    root = tk.Tk()
    root.title("Chart Test")
    root.geometry("800x600")
    
    # Create chart
    chart = TradingChart(root)
    
    # Add test data
    if HAS_CHARTS:
        dates = pd.date_range('2023-01-01', periods=100)
        data = {
            'Open': np.random.randn(100).cumsum() + 100,
            'High': np.random.randn(100).cumsum() + 102,
            'Low': np.random.randn(100).cumsum() + 98,
            'Close': np.random.randn(100).cumsum() + 100,
            'Volume': np.random.randint(100000, 1000000, 100)
        }
        df = pd.DataFrame(data, index=dates)
        chart.update(df)
        
        # Add test trades
        chart.add_trade(101.5, 'buy')
        chart.add_trade(103.2, 'sell')
    
    root.mainloop()


if __name__ == '__main__':
    main()