"""
CryptoBot Risk Management Component
Provides configurable risk parameters and trade restrictions.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, Callable
from decimal import Decimal


class RiskManager:
    """Trade risk configuration and validation"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize risk manager"""
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        
        # Risk parameters
        self.params = {
            'max_position_size': 100.0,  # in quote currency
            'max_drawdown': 0.02,        # 2% max drawdown
            'trailing_stop': 0.01,       # 1% trailing stop
            'profit_target': 0.03,       # 3% take profit
            'max_trades_per_day': 10,    # trade frequency limit
            'cooldown_minutes': 5        # min time between trades
        }
        
        # Create controls
        self._create_widgets()
        
        # Validation callback
        self.on_update: Optional[Callable] = None
        
    def _create_widgets(self) -> None:
        """Create risk parameter controls"""
        # Parameters frame
        params_frame = ttk.LabelFrame(
            self.frame, text="Risk Parameters",
            padding=10
        )
        params_frame.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        # Create spinboxes for each param
        row = 0
        for name, value in self.params.items():
            # Label
            label = ttk.Label(
                params_frame,
                text=name.replace('_', ' ').title()
            )
            label.grid(
                row=row, column=0,
                sticky='w', padx=5, pady=2
            )
            
            # Spinbox
            var = tk.StringVar(value=str(value))
            spinbox = ttk.Spinbox(
                params_frame,
                from_=0.0, to=1000.0,
                increment=0.01 if value < 1 else 1.0,
                textvariable=var,
                width=10
            )
            spinbox.grid(
                row=row, column=1,
                sticky='e', padx=5, pady=2
            )
            
            # Store reference
            self.params[name] = var
            
            row += 1
            
        # Add update button
        ttk.Button(
            params_frame,
            text="Apply Changes",
            command=self._on_update
        ).grid(
            row=row, column=0,
            columnspan=2, pady=10
        )
        
        # Stats frame
        stats_frame = ttk.LabelFrame(
            self.frame, text="Risk Stats",
            padding=10
        )
        stats_frame.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        # Trade stats
        self.stats = {
            'Current DD': tk.StringVar(value='0.00%'),
            'Max DD': tk.StringVar(value='0.00%'),
            'Win Rate': tk.StringVar(value='0.00%'),
            'Profit Factor': tk.StringVar(value='0.00'),
            'Trades Today': tk.StringVar(value='0')
        }
        
        row = 0
        for name, var in self.stats.items():
            ttk.Label(
                stats_frame,
                text=name
            ).grid(
                row=row, column=0,
                sticky='w', padx=5, pady=2
            )
            ttk.Label(
                stats_frame,
                textvariable=var
            ).grid(
                row=row, column=1,
                sticky='e', padx=5, pady=2
            )
            row += 1
            
    def _on_update(self) -> None:
        """Update risk parameters"""
        # Get values
        new_params = {}
        for name, var in self.params.items():
            try:
                value = float(var.get())
                new_params[name] = value
            except ValueError:
                # Reset invalid value
                var.set(str(self.params[name]))
                
        # Call update callback if set
        if self.on_update:
            self.on_update(new_params)
            
    def update_stats(self, stats: Dict[str, Any]) -> None:
        """Update risk statistics display"""
        for name, value in stats.items():
            if name in self.stats:
                if isinstance(value, float):
                    if value < 1:
                        # Format as percentage
                        self.stats[name].set(
                            f'{value*100:.2f}%'
                        )
                    else:
                        self.stats[name].set(
                            f'{value:.2f}'
                        )
                else:
                    self.stats[name].set(str(value))
                    
    def get_params(self) -> Dict[str, float]:
        """Get current risk parameters"""
        return {
            name: float(var.get())
            for name, var in self.params.items()
        }
        

def main():
    """Test risk manager component"""
    root = tk.Tk()
    root.title("Risk Manager Test")
    root.geometry("400x500")
    
    # Create risk manager
    risk = RiskManager(root)
    
    # Add test callback
    def on_update(params):
        print("Risk params updated:", params)
    risk.on_update = on_update
    
    # Add test stats
    test_stats = {
        'Current DD': 0.015,
        'Max DD': 0.025,
        'Win Rate': 0.65,
        'Profit Factor': 1.45,
        'Trades Today': 5
    }
    risk.update_stats(test_stats)
    
    root.mainloop()


if __name__ == '__main__':
    main()