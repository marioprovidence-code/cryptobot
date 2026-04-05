"""
Advanced candlestick chart with real-time updates and customization
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

try:
    import pandas as pd
    import numpy as np
    import mplfinance as mpf
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False

logger = logging.getLogger(__name__)

class CandlestickChart:
    """Interactive candlestick chart with real-time updates"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize candlestick chart"""
        self.parent = parent
        self.has_charts = HAS_CHARTS
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        
        if not self.has_charts:
            self._show_fallback()
            return
            
        # Chart settings
        self._create_settings()
        
        # Create chart
        self._create_chart()
        
        # Initialize data
        self.df = None
        self.last_update = None
        self.indicators = {}
        self.auto_update = True
        
    def _show_fallback(self) -> None:
        """Show message when deps not available"""
        msg = "Charts require mplfinance"
        ttk.Label(
            self.frame,
            text=msg,
            style='Fallback.TLabel'
        ).pack(expand=True)
        
    def _create_settings(self) -> None:
        """Create chart settings panel"""
        settings = ttk.Frame(self.frame)
        settings.pack(fill='x', padx=5, pady=5)
        
        # Auto-update toggle
        self.auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings,
            text="Auto Update",
            variable=self.auto_var,
            command=self._toggle_auto
        ).pack(side='left', padx=5)
        
        # Timeframe selector
        ttk.Label(
            settings,
            text="Timeframe:"
        ).pack(side='left', padx=5)
        
        self.tf_var = tk.StringVar(value='1h')
        tf_cb = ttk.Combobox(
            settings,
            textvariable=self.tf_var,
            values=['1m', '5m', '15m', '1h', '4h', '1d'],
            width=5,
            state='readonly'
        )
        tf_cb.pack(side='left', padx=5)
        tf_cb.bind('<<ComboboxSelected>>', self._change_timeframe)
        
        # Style selector
        ttk.Label(
            settings,
            text="Style:"
        ).pack(side='left', padx=5)
        
        self.style_var = tk.StringVar(value='candle')
        style_cb = ttk.Combobox(
            settings,
            textvariable=self.style_var,
            values=['candle', 'line', 'renko', 'pnf'],
            width=8,
            state='readonly'
        )
        style_cb.pack(side='left', padx=5)
        style_cb.bind('<<ComboboxSelected>>', self._change_style)
        
        # Indicators
        ttk.Label(
            settings,
            text="Indicators:"
        ).pack(side='left', padx=5)
        
        self.sma_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings,
            text="SMA",
            variable=self.sma_var,
            command=self._toggle_sma
        ).pack(side='left')
        
        self.bb_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings,
            text="BB",
            variable=self.bb_var,
            command=self._toggle_bb
        ).pack(side='left')
        
        self.vol_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings,
            text="Volume",
            variable=self.vol_var,
            command=self._toggle_volume
        ).pack(side='left')
        
        # Update button
        ttk.Button(
            settings,
            text="Update",
            command=self._manual_update
        ).pack(side='right', padx=5)
        
    def _create_chart(self) -> None:
        """Create candlestick chart"""
        # Figure
        self.fig = Figure(figsize=(10, 6))
        self.ax1 = self.fig.add_subplot(111)
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(
            self.fig, self.frame
        )
        self.canvas.get_tk_widget().pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
    def update(self, df: pd.DataFrame) -> None:
        """Update chart with new data"""
        if not self.has_charts or df is None:
            return
            
        try:
            # Store data
            self.df = df.copy()
            self.last_update = datetime.now()
            
            # Only update if auto-update is on
            if self.auto_var.get():
                self._update_chart()
                
        except Exception as e:
            logger.error(f"Chart update error: {e}")
            
    def _update_chart(self) -> None:
        """Redraw chart with current settings"""
        if not self.has_charts or self.df is None:
            return
            
        try:
            # Clear
            self.ax1.clear()
            
            # Prepare data
            df = self.df.copy()
            df.set_index('open_time', inplace=True)
            
            # Style
            style = self.style_var.get()
            
            # Plot candlesticks
            if style == 'candle':
                mpf.plot(
                    df,
                    type='candle',
                    style='charles',
                    ax=self.ax1,
                    volume=self.vol_var.get(),
                    show_nontrading=True
                )
            elif style == 'line':
                self.ax1.plot(df.index, df['close'])
            elif style in ['renko', 'pnf']:
                mpf.plot(
                    df,
                    type=style,
                    ax=self.ax1,
                    volume=self.vol_var.get()
                )
                
            # Add indicators
            if self.sma_var.get():
                self._add_sma()
            if self.bb_var.get():
                self._add_bollinger()
                
            # Format
            self.ax1.set_title(
                f"Last Update: {self.last_update:%H:%M:%S}"
            )
            self.ax1.tick_params(axis='x', rotation=45)
            self.fig.tight_layout()
            
            # Draw
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Chart redraw error: {e}")
            
    def _add_sma(self, periods: List[int] = [20, 50, 200]) -> None:
        """Add SMA lines"""
        if self.df is None:
            return
            
        for p in periods:
            sma = self.df['close'].rolling(p).mean()
            self.ax1.plot(
                self.df.index,
                sma,
                label=f'SMA {p}'
            )
        self.ax1.legend()
        
    def _add_bollinger(self, period: int = 20, std: float = 2.0) -> None:
        """Add Bollinger Bands"""
        if self.df is None:
            return
            
        # Calculate bands
        sma = self.df['close'].rolling(period).mean()
        std_dev = self.df['close'].rolling(period).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        # Plot
        self.ax1.plot(
            self.df.index, upper,
            'b--', label='Upper BB'
        )
        self.ax1.plot(
            self.df.index, sma,
            'g--', label='Middle BB'
        )
        self.ax1.plot(
            self.df.index, lower,
            'b--', label='Lower BB'
        )
        self.ax1.legend()
        
    def _toggle_auto(self) -> None:
        """Toggle auto-updates"""
        self.auto_update = self.auto_var.get()
        if self.auto_update:
            self._update_chart()
            
    def _change_timeframe(self, event=None) -> None:
        """Handle timeframe change"""
        if hasattr(self, 'on_timeframe_change'):
            self.on_timeframe_change(
                self.tf_var.get()
            )
            
    def _change_style(self, event=None) -> None:
        """Handle style change"""
        self._update_chart()
        
    def _toggle_sma(self) -> None:
        """Toggle SMA display"""
        self._update_chart()
        
    def _toggle_bb(self) -> None:
        """Toggle Bollinger Bands"""
        self._update_chart()
        
    def _toggle_volume(self) -> None:
        """Toggle volume display"""
        self._update_chart()
        
    def _manual_update(self) -> None:
        """Manual chart update"""
        self._update_chart()
        
    def add_trade(self, price: float, trade_type: str) -> None:
        """Add trade marker to chart"""
        if not self.has_charts or self.df is None:
            return
            
        try:
            color = 'g' if trade_type == 'buy' else 'r'
            marker = '^' if trade_type == 'buy' else 'v'
            self.ax1.plot(
                self.df.index[-1],
                price,
                marker=marker,
                color=color,
                markersize=10
            )
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Trade marker error: {e}")


def main():
    """Test candlestick chart"""
    root = tk.Tk()
    root.title("Candlestick Test")
    root.geometry("1000x800")
    
    chart = CandlestickChart(root)
    
    if HAS_CHARTS:
        # Create test data
        dates = pd.date_range('2023-01-01', periods=100)
        data = pd.DataFrame({
            'open_time': dates,
            'open': np.random.randn(100).cumsum() + 100,
            'high': np.random.randn(100).cumsum() + 102,
            'low': np.random.randn(100).cumsum() + 98,
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 5000, 100)
        })
        
        # Update chart
        chart.update(data)
        
        # Add test trade
        chart.add_trade(101.5, 'buy')
        
    root.mainloop()


if __name__ == '__main__':
    main()