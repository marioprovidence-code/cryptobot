"""
CryptoBot Strategy Tuning
Interactive parameter tuning and optimization interface.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional
import threading
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_TUNING = True
except ImportError:
    HAS_TUNING = False
    
# Import core bot features with fallbacks
try:
    from crypto_bot import (
        tune_xgboost,
        run_backtest,
        MLModel,
        get_historical_data_with_indicators
    )
except ImportError:
    def tune_xgboost(*args, **kwargs): return {}
    def run_backtest(*args, **kwargs): return None
    class MLModel: pass
    def get_historical_data_with_indicators(*args, **kwargs): return None


class StrategyTuner:
    """Interactive strategy parameter tuning"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize tuning interface"""
        self.parent = parent
        self.has_tuning = HAS_TUNING
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        
        if not self.has_tuning:
            self._show_fallback()
            return
            
        # Parameters to tune
        self.params = {
            'ml_threshold': {
                'min': 0.5,
                'max': 0.9,
                'value': 0.55,
                'step': 0.01
            },
            'atr_multiplier': {
                'min': 1.0,
                'max': 4.0,
                'value': 2.0,
                'step': 0.1
            },
            'profit_target': {
                'min': 0.01,
                'max': 0.1,
                'value': 0.03,
                'step': 0.005
            },
            'max_bars_back': {
                'min': 10,
                'max': 100,
                'value': 20,
                'step': 5
            }
        }
        
        # Create widgets
        self._create_controls()
        self._create_results()
        
    def _show_fallback(self) -> None:
        """Show message when deps not available"""
        msg = "Tuning requires pandas & matplotlib"
        ttk.Label(
            self.frame,
            text=msg,
            style='Fallback.TLabel'
        ).pack(expand=True)
        
    def _create_controls(self) -> None:
        """Create parameter controls"""
        controls = ttk.LabelFrame(
            self.frame,
            text="Strategy Parameters",
            padding=10
        )
        controls.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        # Parameter sliders
        row = 0
        self.param_vars = {}
        for name, config in self.params.items():
            ttk.Label(
                controls,
                text=name.replace('_', ' ').title()
            ).grid(
                row=row, column=0,
                sticky='w', padx=5, pady=2
            )
            
            var = tk.DoubleVar(value=config['value'])
            self.param_vars[name] = var
            
            scale = ttk.Scale(
                controls,
                from_=config['min'],
                to=config['max'],
                value=config['value'],
                variable=var,
                orient='horizontal'
            )
            scale.grid(
                row=row, column=1,
                sticky='ew', padx=5, pady=2
            )
            
            ttk.Label(
                controls,
                textvariable=var
            ).grid(
                row=row, column=2,
                padx=5, pady=2
            )
            
            row += 1
            
        # Control buttons
        buttons = ttk.Frame(controls)
        buttons.grid(
            row=row, column=0,
            columnspan=3, pady=10
        )
        
        ttk.Button(
            buttons,
            text="Run Backtest",
            command=self._run_backtest
        ).pack(side='left', padx=5)
        
        ttk.Button(
            buttons,
            text="Auto-Tune",
            command=self._auto_tune
        ).pack(side='left', padx=5)
        
        ttk.Button(
            buttons,
            text="Save Params",
            command=self._save_params
        ).pack(side='left', padx=5)
        
    def _create_results(self) -> None:
        """Create results display"""
        results = ttk.LabelFrame(
            self.frame,
            text="Backtest Results",
            padding=10
        )
        results.pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
        # Metrics
        metrics_frame = ttk.Frame(results)
        metrics_frame.pack(fill='x', expand=False)
        
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
                metrics_frame,
                text=name
            ).grid(
                row=row, column=0,
                sticky='w', padx=5, pady=2
            )
            ttk.Label(
                metrics_frame,
                textvariable=var
            ).grid(
                row=row, column=1,
                sticky='e', padx=5, pady=2
            )
            row += 1
            
        # Results chart
        fig = Figure(figsize=(8, 4))
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(fig, results)
        self.canvas.get_tk_widget().pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
    def _run_backtest(self) -> None:
        """Run backtest with current parameters"""
        if not self.has_tuning:
            return
            
        try:
            # Get parameters
            params = {
                name: var.get()
                for name, var in self.param_vars.items()
            }
            
            # Create model
            model = MLModel(params)
            
            # Run backtest
            results = run_backtest(
                model,
                symbol='BTCUSDT',
                risk_pct=0.01
            )
            
            if results is not None:
                self._update_results(results)
                
        except Exception as e:
            messagebox.showerror(
                "Backtest Error",
                str(e)
            )
            
    def _auto_tune(self) -> None:
        """Run auto-tuning optimization"""
        if not self.has_tuning:
            return
            
        try:
            # Run tuning
            best_params = tune_xgboost(
                symbol='BTCUSDT',
                n_trials=10  # Quick test
            )
            
            # Update sliders
            for name, value in best_params.items():
                if name in self.param_vars:
                    self.param_vars[name].set(value)
                    
            # Run backtest with best params
            self._run_backtest()
            
        except Exception as e:
            messagebox.showerror(
                "Tuning Error",
                str(e)
            )
            
    def _save_params(self) -> None:
        """Save parameters to file"""
        if not self.has_tuning:
            return
            
        try:
            params = {
                name: var.get()
                for name, var in self.param_vars.items()
            }
            
            with open('best_params.json', 'w') as f:
                json.dump(params, f, indent=2)
                
            messagebox.showinfo(
                "Success",
                "Parameters saved to best_params.json"
            )
            
        except Exception as e:
            messagebox.showerror(
                "Save Error",
                str(e)
            )
            
    def _update_results(self, results: Dict[str, Any]) -> None:
        """Update results display"""
        if not self.has_tuning:
            return
            
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
                    
        # Update chart
        if 'equity_curve' in results:
            self.ax.clear()
            self.ax.plot(
                results['equity_curve'],
                color='g'
            )
            self.ax.set_title('Equity Curve')
            self.ax.grid(True)
            self.canvas.draw()


def main():
    """Test tuning interface"""
    root = tk.Tk()
    root.title("Strategy Tuner")
    root.geometry("800x600")
    
    tuner = StrategyTuner(root)
    
    root.mainloop()


if __name__ == '__main__':
    main()