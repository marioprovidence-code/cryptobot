"""
Advanced risk management interface with real-time adjustments
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RiskControlPanel:
    """Interactive risk management controls"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize risk panel"""
        self.parent = parent
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        
        # Create sections
        self._create_position_controls()
        self._create_risk_limits()
        self._create_auto_rules()
        self._create_emergency()
        
    def _create_position_controls(self) -> None:
        """Create position sizing controls"""
        pos = ttk.LabelFrame(
            self.frame,
            text="Position Sizing",
            padding=10
        )
        pos.pack(fill='x', padx=5, pady=5)
        
        # Risk per trade
        ttk.Label(
            pos,
            text="Risk Per Trade (%):"
        ).grid(row=0, column=0, padx=5)
        
        self.risk_var = tk.DoubleVar(value=2.0)
        risk_scale = ttk.Scale(
            pos,
            from_=0.1,
            to=5.0,
            variable=self.risk_var,
            command=self._on_risk_change
        )
        risk_scale.grid(row=0, column=1, sticky='ew')
        
        ttk.Label(
            pos,
            textvariable=tk.StringVar(
                value=lambda: f"{self.risk_var.get():.1f}%"
            )
        ).grid(row=0, column=2, padx=5)
        
        # Stop loss multiplier
        ttk.Label(
            pos,
            text="Stop Loss (ATR):"
        ).grid(row=1, column=0, padx=5)
        
        self.stop_var = tk.DoubleVar(value=2.0)
        stop_scale = ttk.Scale(
            pos,
            from_=0.5,
            to=4.0,
            variable=self.stop_var,
            command=self._on_stop_change
        )
        stop_scale.grid(row=1, column=1, sticky='ew')
        
        ttk.Label(
            pos,
            textvariable=tk.StringVar(
                value=lambda: f"{self.stop_var.get():.1f}x"
            )
        ).grid(row=1, column=2, padx=5)
        
        # Take profit ratio
        ttk.Label(
            pos,
            text="Take Profit (R:R):"
        ).grid(row=2, column=0, padx=5)
        
        self.tp_var = tk.DoubleVar(value=2.0)
        tp_scale = ttk.Scale(
            pos,
            from_=1.0,
            to=5.0,
            variable=self.tp_var,
            command=self._on_tp_change
        )
        tp_scale.grid(row=2, column=1, sticky='ew')
        
        ttk.Label(
            pos,
            textvariable=tk.StringVar(
                value=lambda: f"{self.tp_var.get():.1f}:1"
            )
        ).grid(row=2, column=2, padx=5)
        
        pos.columnconfigure(1, weight=1)
        
    def _create_risk_limits(self) -> None:
        """Create risk limit controls"""
        limits = ttk.LabelFrame(
            self.frame,
            text="Risk Limits",
            padding=10
        )
        limits.pack(fill='x', padx=5, pady=5)
        
        # Max drawdown
        ttk.Label(
            limits,
            text="Max Drawdown (%):"
        ).grid(row=0, column=0, padx=5)
        
        self.dd_var = tk.DoubleVar(value=15.0)
        dd_scale = ttk.Scale(
            limits,
            from_=5.0,
            to=30.0,
            variable=self.dd_var,
            command=self._on_dd_change
        )
        dd_scale.grid(row=0, column=1, sticky='ew')
        
        ttk.Label(
            limits,
            textvariable=tk.StringVar(
                value=lambda: f"{self.dd_var.get():.1f}%"
            )
        ).grid(row=0, column=2, padx=5)
        
        # Daily loss limit
        ttk.Label(
            limits,
            text="Daily Loss ($):"
        ).grid(row=1, column=0, padx=5)
        
        self.loss_var = tk.DoubleVar(value=500.0)
        loss_scale = ttk.Scale(
            limits,
            from_=100.0,
            to=2000.0,
            variable=self.loss_var,
            command=self._on_loss_change
        )
        loss_scale.grid(row=1, column=1, sticky='ew')
        
        ttk.Label(
            limits,
            textvariable=tk.StringVar(
                value=lambda: f"${self.loss_var.get():.0f}"
            )
        ).grid(row=1, column=2, padx=5)
        
        limits.columnconfigure(1, weight=1)
        
    def _create_auto_rules(self) -> None:
        """Create automated rule controls"""
        rules = ttk.LabelFrame(
            self.frame,
            text="Auto Rules",
            padding=10
        )
        rules.pack(fill='x', padx=5, pady=5)
        
        # Trailing stop
        ttk.Label(
            rules,
            text="Trailing Stop (%):"
        ).grid(row=0, column=0, padx=5)
        
        self.trail_var = tk.DoubleVar(value=1.5)
        trail_scale = ttk.Scale(
            rules,
            from_=0.5,
            to=5.0,
            variable=self.trail_var,
            command=self._on_trail_change
        )
        trail_scale.grid(row=0, column=1, sticky='ew')
        
        ttk.Label(
            rules,
            textvariable=tk.StringVar(
                value=lambda: f"{self.trail_var.get():.1f}%"
            )
        ).grid(row=0, column=2, padx=5)
        
        # Position timeout
        ttk.Label(
            rules,
            text="Position Timeout (h):"
        ).grid(row=1, column=0, padx=5)
        
        self.timeout_var = tk.IntVar(value=6)
        timeout_scale = ttk.Scale(
            rules,
            from_=1,
            to=24,
            variable=self.timeout_var,
            command=self._on_timeout_change
        )
        timeout_scale.grid(row=1, column=1, sticky='ew')
        
        ttk.Label(
            rules,
            textvariable=tk.StringVar(
                value=lambda: f"{self.timeout_var.get()}h"
            )
        ).grid(row=1, column=2, padx=5)
        
        # Min volatility
        ttk.Label(
            rules,
            text="Min Volatility (ATR):"
        ).grid(row=2, column=0, padx=5)
        
        self.vol_var = tk.DoubleVar(value=0.5)
        vol_scale = ttk.Scale(
            rules,
            from_=0.1,
            to=2.0,
            variable=self.vol_var,
            command=self._on_vol_change
        )
        vol_scale.grid(row=2, column=1, sticky='ew')
        
        ttk.Label(
            rules,
            textvariable=tk.StringVar(
                value=lambda: f"{self.vol_var.get():.1f}"
            )
        ).grid(row=2, column=2, padx=5)
        
        rules.columnconfigure(1, weight=1)
        
    def _create_emergency(self) -> None:
        """Create emergency controls"""
        emergency = ttk.LabelFrame(
            self.frame,
            text="Emergency",
            padding=10
        )
        emergency.pack(fill='x', padx=5, pady=5)
        
        # Close all button
        ttk.Button(
            emergency,
            text="Close All Positions",
            style='Emergency.TButton',
            command=self._close_all
        ).pack(side='left', padx=5)
        
        # Cancel all button
        ttk.Button(
            emergency,
            text="Cancel All Orders",
            style='Emergency.TButton',
            command=self._cancel_all
        ).pack(side='left', padx=5)
        
        # Reset button
        ttk.Button(
            emergency,
            text="Reset Risk Settings",
            command=self._reset_settings
        ).pack(side='right', padx=5)
        
    def _on_risk_change(self, *args) -> None:
        """Handle risk per trade change"""
        if hasattr(self, 'on_update'):
            self.on_update({
                'risk_per_trade': self.risk_var.get() / 100.0
            })
            
    def _on_stop_change(self, *args) -> None:
        """Handle stop loss change"""
        if hasattr(self, 'on_update'):
            self.on_update({
                'stop_loss_mult': self.stop_var.get()
            })
            
    def _on_tp_change(self, *args) -> None:
        """Handle take profit change"""
        if hasattr(self, 'on_update'):
            self.on_update({
                'take_profit_rr': self.tp_var.get()
            })
            
    def _on_dd_change(self, *args) -> None:
        """Handle max drawdown change"""
        if hasattr(self, 'on_update'):
            self.on_update({
                'max_dd': self.dd_var.get() / 100.0
            })
            
    def _on_loss_change(self, *args) -> None:
        """Handle daily loss change"""
        if hasattr(self, 'on_update'):
            self.on_update({
                'daily_loss': self.loss_var.get()
            })
            
    def _on_trail_change(self, *args) -> None:
        """Handle trailing stop change"""
        if hasattr(self, 'on_update'):
            self.on_update({
                'trailing_pct': self.trail_var.get() / 100.0
            })
            
    def _on_timeout_change(self, *args) -> None:
        """Handle timeout change"""
        if hasattr(self, 'on_update'):
            self.on_update({
                'timeout_hours': self.timeout_var.get()
            })
            
    def _on_vol_change(self, *args) -> None:
        """Handle min volatility change"""
        if hasattr(self, 'on_update'):
            self.on_update({
                'min_vol_atr': self.vol_var.get()
            })
            
    def _close_all(self) -> None:
        """Close all positions"""
        if messagebox.askyesno(
            "Confirm",
            "Close all open positions?"
        ):
            if hasattr(self, 'on_close_all'):
                self.on_close_all()
                
    def _cancel_all(self) -> None:
        """Cancel all orders"""
        if messagebox.askyesno(
            "Confirm",
            "Cancel all pending orders?"
        ):
            if hasattr(self, 'on_cancel_all'):
                self.on_cancel_all()
                
    def _reset_settings(self) -> None:
        """Reset risk settings"""
        if messagebox.askyesno(
            "Confirm",
            "Reset all risk settings to default?"
        ):
            # Reset variables
            self.risk_var.set(2.0)
            self.stop_var.set(2.0)
            self.tp_var.set(2.0)
            self.dd_var.set(15.0)
            self.loss_var.set(500.0)
            self.trail_var.set(1.5)
            self.timeout_var.set(6)
            self.vol_var.set(0.5)
            
            # Update all
            if hasattr(self, 'on_update'):
                self.on_update({
                    'risk_per_trade': 0.02,
                    'stop_loss_mult': 2.0,
                    'take_profit_rr': 2.0,
                    'max_dd': 0.15,
                    'daily_loss': 500.0,
                    'trailing_pct': 0.015,
                    'timeout_hours': 6,
                    'min_vol_atr': 0.5
                })
                
    def update_stats(self, stats: Dict[str, float]) -> None:
        """Update risk statistics display"""
        pass  # Placeholder for stats display


def main():
    """Test risk control panel"""
    root = tk.Tk()
    root.title("Risk Controls Test")
    
    def on_update(params):
        print(f"Risk update: {params}")
        
    def on_close():
        print("Close all positions")
        
    def on_cancel():
        print("Cancel all orders")
        
    # Create panel
    panel = RiskControlPanel(root)
    panel.on_update = on_update
    panel.on_close_all = on_close
    panel.on_cancel_all = on_cancel
    
    root.mainloop()


if __name__ == '__main__':
    main()