"""
CryptoBot Backtesting Interface
Interactive backtesting and strategy optimization.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, Optional, List
import threading
import json
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_BACKTEST = True
except ImportError:
    HAS_BACKTEST = False
    
# Import core bot features with fallbacks
try:
    from crypto_engine import (
        run_backtest,
        MLModel,
        get_historical_data_with_indicators
    )
    from config import SYMBOLS
except ImportError:
    def run_backtest(*args, **kwargs): return None
    class MLModel: pass
    def get_historical_data_with_indicators(*args, **kwargs): 
        return None
    SYMBOLS = ["SOLUSDT", "BTCUSDT"]


class BacktestPanel:
    """Interactive backtesting interface"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize backtest panel"""
        self.parent = parent
        self.has_backtest = HAS_BACKTEST
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        
        if not self.has_backtest:
            self._show_fallback()
            return
            
        # Create notebook
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
        # Create tabs
        self._create_setup_tab()
        self._create_results_tab()
        self._create_compare_tab()
        
        # Running state
        self.is_running = False
        self.current_test = None
        self.results_history = []
        
    def _show_fallback(self) -> None:
        """Show message when deps not available"""
        msg = "Backtesting requires pandas & matplotlib"
        ttk.Label(
            self.frame,
            text=msg,
            style='Fallback.TLabel'
        ).pack(expand=True)
        
    def _create_setup_tab(self) -> None:
        """Create backtest setup tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Setup")
        
        # Parameters frame
        params = ttk.LabelFrame(
            tab,
            text="Test Parameters",
            padding=10
        )
        params.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        # Symbol selector
        ttk.Label(
            params,
            text="Symbol:"
        ).grid(row=0, column=0, padx=5, pady=2)
        
        self.symbol_var = tk.StringVar(
            value=SYMBOLS[0]
        )
        ttk.Combobox(
            params,
            textvariable=self.symbol_var,
            values=SYMBOLS,
            state='readonly'
        ).grid(row=0, column=1, padx=5, pady=2)
        
        # Date range
        ttk.Label(
            params,
            text="Date Range:"
        ).grid(row=1, column=0, padx=5, pady=2)
        
        dates = ttk.Frame(params)
        dates.grid(row=1, column=1, sticky='ew')
        
        self.start_var = tk.StringVar(
            value=(
                datetime.now() -
                timedelta(days=30)
            ).strftime('%Y-%m-%d')
        )
        ttk.Entry(
            dates,
            textvariable=self.start_var,
            width=10
        ).pack(side='left', padx=2)
        
        ttk.Label(
            dates,
            text="to"
        ).pack(side='left', padx=2)
        
        self.end_var = tk.StringVar(
            value=datetime.now().strftime('%Y-%m-%d')
        )
        ttk.Entry(
            dates,
            textvariable=self.end_var,
            width=10
        ).pack(side='left', padx=2)
        
        # Initial balance
        ttk.Label(
            params,
            text="Initial Balance:"
        ).grid(row=2, column=0, padx=5, pady=2)
        
        self.balance_var = tk.StringVar(value="10000")
        ttk.Entry(
            params,
            textvariable=self.balance_var,
            width=10
        ).grid(row=2, column=1, padx=5, pady=2)
        
        # Risk per trade
        ttk.Label(
            params,
            text="Risk Per Trade:"
        ).grid(row=3, column=0, padx=5, pady=2)
        
        self.risk_var = tk.StringVar(value="1.0")
        ttk.Entry(
            params,
            textvariable=self.risk_var,
            width=10
        ).grid(row=3, column=1, padx=5, pady=2)
        
        # Strategy frame
        strategy = ttk.LabelFrame(
            tab,
            text="Strategy Settings",
            padding=10
        )
        strategy.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        # Model parameters
        self.param_vars = {}
        row = 0
        for name, value in {
            'ml_threshold': 0.55,
            'atr_multiplier': 2.0,
            'profit_target': 0.03,
            'max_bars_back': 20
        }.items():
            ttk.Label(
                strategy,
                text=name.replace('_', ' ').title()
            ).grid(row=row, column=0, padx=5, pady=2)
            
            var = tk.StringVar(value=str(value))
            self.param_vars[name] = var
            ttk.Entry(
                strategy,
                textvariable=var,
                width=10
            ).grid(row=row, column=1, padx=5, pady=2)
            
            row += 1
            
        # Load/save params
        buttons = ttk.Frame(strategy)
        buttons.grid(
            row=row, column=0,
            columnspan=2, pady=10
        )
        
        ttk.Button(
            buttons,
            text="Load Params",
            command=self._load_params
        ).pack(side='left', padx=5)
        
        ttk.Button(
            buttons,
            text="Save Params",
            command=self._save_params
        ).pack(side='left', padx=5)
        
        # Run buttons
        run_frame = ttk.Frame(tab)
        run_frame.pack(
            fill='x', expand=False,
            padx=5, pady=10
        )
        
        self.run_btn = ttk.Button(
            run_frame,
            text="Run Backtest",
            command=self._run_backtest
        )
        self.run_btn.pack(expand=True)
        
    def _create_results_tab(self) -> None:
        """Create results display tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Results")
        
        # Metrics frame
        metrics = ttk.LabelFrame(
            tab,
            text="Performance Metrics",
            padding=10
        )
        metrics.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        self.metrics = {
            'Total Return': tk.StringVar(value='0.00%'),
            'Win Rate': tk.StringVar(value='0.00%'),
            'Profit Factor': tk.StringVar(value='0.00'),
            'Max Drawdown': tk.StringVar(value='0.00%'),
            'Sharpe Ratio': tk.StringVar(value='0.00'),
            'Total Trades': tk.StringVar(value='0')
        }
        
        row = 0
        for name, var in self.metrics.items():
            ttk.Label(
                metrics,
                text=name
            ).grid(
                row=row, column=0,
                sticky='w', padx=5, pady=2
            )
            ttk.Label(
                metrics,
                textvariable=var
            ).grid(
                row=row, column=1,
                sticky='e', padx=5, pady=2
            )
            row += 1
            
        # Charts
        charts = ttk.Frame(tab)
        charts.pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
        # Equity curve
        fig = Figure(figsize=(8, 6))
        self.ax1 = fig.add_subplot(211)
        self.ax2 = fig.add_subplot(212)
        
        self.canvas = FigureCanvasTkAgg(fig, charts)
        self.canvas.get_tk_widget().pack(
            fill='both', expand=True
        )
        
        # Export button
        ttk.Button(
            tab,
            text="Export Results",
            command=self._export_results
        ).pack(pady=10)
        
    def _create_compare_tab(self) -> None:
        """Create strategy comparison tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Compare")
        
        # Results table
        cols = [
            'Symbol',
            'Dates',
            'Return',
            'Win Rate',
            'Drawdown'
        ]
        
        self.compare_tree = ttk.Treeview(
            tab,
            columns=cols,
            show='headings'
        )
        
        # Configure columns
        for col in cols:
            self.compare_tree.heading(
                col,
                text=col,
                command=lambda c=col: self._sort_results(c)
            )
            width = 100 if col in ['Symbol', 'Return'] else 150
            self.compare_tree.column(
                col,
                width=width,
                anchor='center'
            )
            
        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            tab,
            orient='vertical',
            command=self.compare_tree.yview
        )
        self.compare_tree.configure(
            yscrollcommand=scrollbar.set
        )
        
        # Pack
        self.compare_tree.pack(
            side='left',
            fill='both',
            expand=True
        )
        scrollbar.pack(
            side='right',
            fill='y'
        )
        
    def _load_params(self) -> None:
        """Load parameters from file"""
        try:
            filepath = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")]
            )
            if not filepath:
                return
                
            with open(filepath, 'r') as f:
                params = json.load(f)
                
            for name, value in params.items():
                if name in self.param_vars:
                    self.param_vars[name].set(str(value))
                    
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load parameters: {e}"
            )
            
    def _save_params(self) -> None:
        """Save parameters to file"""
        try:
            params = {
                name: float(var.get())
                for name, var in self.param_vars.items()
            }
            
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
            if not filepath:
                return
                
            with open(filepath, 'w') as f:
                json.dump(params, f, indent=2)
                
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to save parameters: {e}"
            )
            
    def _run_backtest(self) -> None:
        """Run backtest with current settings"""
        if self.is_running:
            return
            
        try:
            # Get parameters
            params = {
                name: float(var.get())
                for name, var in self.param_vars.items()
            }
            
            # Create model
            model = MLModel(params)
            
            # Get test settings
            symbol = self.symbol_var.get()
            balance = float(self.balance_var.get())
            risk = float(self.risk_var.get()) / 100
            
            # Run in thread
            self.is_running = True
            self.run_btn.configure(
                text="Running...",
                state='disabled'
            )
            
            def run():
                try:
                    results = run_backtest(
                        model,
                        symbol=symbol,
                        initial_balance=balance,
                        risk_pct=risk
                    )
                    
                    if results:
                        self._update_results(results)
                        self._add_to_compare(results)
                        
                except Exception as e:
                    messagebox.showerror(
                        "Backtest Error",
                        str(e)
                    )
                finally:
                    self.is_running = False
                    self.run_btn.configure(
                        text="Run Backtest",
                        state='normal'
                    )
                    
            thread = threading.Thread(target=run)
            thread.daemon = True
            thread.start()
            
        except ValueError as e:
            messagebox.showerror(
                "Input Error",
                str(e)
            )
            
    def _update_results(self, results: Dict[str, Any]) -> None:
        """Update results display"""
        # Update metrics
        for name, value in results.items():
            if name in self.metrics:
                if isinstance(value, float):
                    if value < 1:
                        self.metrics[name].set(
                            f'{value*100:.2f}%'
                        )
                    else:
                        self.metrics[name].set(
                            f'{value:.2f}'
                        )
                else:
                    self.metrics[name].set(str(value))
                    
        # Update charts
        self.ax1.clear()
        self.ax2.clear()
        
        # Equity curve
        if 'equity_curve' in results:
            self.ax1.plot(
                results['equity_curve'],
                color='g'
            )
            self.ax1.set_title('Equity Curve')
            self.ax1.grid(True)
            
        # Drawdown
        if 'drawdown' in results:
            self.ax2.plot(
                results['drawdown'],
                color='r'
            )
            self.ax2.set_title('Drawdown')
            self.ax2.grid(True)
            
        self.canvas.draw()
        
        # Store results
        self.current_test = results
        self.results_history.append(results)
        
    def _add_to_compare(self, results: Dict[str, Any]) -> None:
        """Add results to comparison table"""
        self.compare_tree.insert(
            '',
            'end',
            values=(
                results.get('symbol', ''),
                f"{results.get('start_date', '')} to "
                f"{results.get('end_date', '')}",
                f"{results.get('total_return', 0)*100:.2f}%",
                f"{results.get('win_rate', 0)*100:.2f}%",
                f"{results.get('max_drawdown', 0)*100:.2f}%"
            )
        )
        
    def _sort_results(self, column: str) -> None:
        """Sort comparison table by column"""
        items = [(
            self.compare_tree.set(k, column), k
        ) for k in self.compare_tree.get_children('')]
        
        items.sort(reverse=True)
        
        for index, (_, k) in enumerate(items):
            self.compare_tree.move(k, '', index)
            
    def _export_results(self) -> None:
        """Export results to file"""
        if not self.current_test:
            messagebox.showwarning(
                "Warning",
                "No results to export"
            )
            return
            
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[
                    ("JSON files", "*.json"),
                    ("CSV files", "*.csv")
                ]
            )
            if not filepath:
                return
                
            ext = os.path.splitext(filepath)[1]
            
            if ext == '.json':
                with open(filepath, 'w') as f:
                    json.dump(
                        self.current_test,
                        f,
                        indent=2,
                        default=str
                    )
            else:
                pd.DataFrame(
                    self.current_test['trades']
                ).to_csv(filepath, index=False)
                
        except Exception as e:
            messagebox.showerror(
                "Export Error",
                str(e)
            )


def main():
    """Test backtest panel"""
    root = tk.Tk()
    root.title("Backtest")
    root.geometry("1000x800")
    
    panel = BacktestPanel(root)
    
    root.mainloop()


if __name__ == '__main__':
    main()