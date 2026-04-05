"""
Bot settings menu and control panel
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any
import json
import logging
import os

logger = logging.getLogger(__name__)

class BotSettingsMenu:
    """Dropdown menu for bot settings"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize settings menu"""
        self.parent = parent
        
        # Create menu button
        self._create_menu_button()
        
        # Load settings
        self.settings = self._load_settings()
        
        # Create settings window
        self._create_settings_window()
        
    def _create_menu_button(self) -> None:
        """Create hamburger menu button"""
        self.menu_btn = ttk.Button(
            self.parent,
            text="☰",
            width=3,
            command=self._toggle_menu
        )
        self.menu_btn.pack(
            side='right',
            padx=5,
            pady=5
        )
        
    def _create_settings_window(self) -> None:
        """Create settings popup window"""
        self.window = None
        
    def _toggle_menu(self) -> None:
        """Show/hide settings window"""
        if self.window is None:
            self._show_settings()
        else:
            self._hide_settings()
            
    def _show_settings(self) -> None:
        """Show settings window"""
        # Create window
        self.window = tk.Toplevel(self.parent)
        self.window.title("Bot Settings")
        self.window.geometry("400x600")
        self.window.transient(self.parent)
        self.window.protocol(
            "WM_DELETE_WINDOW",
            self._hide_settings
        )
        
        # Create notebook
        nb = ttk.Notebook(self.window)
        nb.pack(fill='both', expand=True)
        
        # Create tabs
        self._create_general_tab(nb)
        self._create_backtest_tab(nb)
        self._create_alerts_tab(nb)
        self._create_data_tab(nb)
        
    def _create_general_tab(self, nb: ttk.Notebook) -> None:
        """Create general settings tab"""
        tab = ttk.Frame(nb)
        nb.add(tab, text="General")
        
        # Trading settings
        trading = ttk.LabelFrame(
            tab,
            text="Trading",
            padding=10
        )
        trading.pack(fill='x', padx=5, pady=5)
        
        # Auto start
        self.auto_start = tk.BooleanVar(
            value=self.settings.get(
                'auto_start', False
            )
        )
        ttk.Checkbutton(
            trading,
            text="Auto-start on launch",
            variable=self.auto_start
        ).pack(anchor='w')
        
        # Auto reconnect
        self.auto_reconn = tk.BooleanVar(
            value=self.settings.get(
                'auto_reconnect', True
            )
        )
        ttk.Checkbutton(
            trading,
            text="Auto-reconnect",
            variable=self.auto_reconn
        ).pack(anchor='w')
        
        # Default symbol
        ttk.Label(
            trading,
            text="Default Symbol:"
        ).pack(anchor='w')
        
        self.symbol_var = tk.StringVar(
            value=self.settings.get(
                'default_symbol', 'BTCUSDT'
            )
        )
        ttk.Entry(
            trading,
            textvariable=self.symbol_var
        ).pack(fill='x')
        
        # UI settings
        ui = ttk.LabelFrame(
            tab,
            text="Interface",
            padding=10
        )
        ui.pack(fill='x', padx=5, pady=5)
        
        # Theme
        ttk.Label(
            ui,
            text="Theme:"
        ).pack(anchor='w')
        
        self.theme_var = tk.StringVar(
            value=self.settings.get(
                'theme', 'dark'
            )
        )
        ttk.Combobox(
            ui,
            textvariable=self.theme_var,
            values=['light', 'dark'],
            state='readonly'
        ).pack(fill='x')
        
        # Chart style
        ttk.Label(
            ui,
            text="Chart Style:"
        ).pack(anchor='w')
        
        self.chart_var = tk.StringVar(
            value=self.settings.get(
                'chart_style', 'candle'
            )
        )
        ttk.Combobox(
            ui,
            textvariable=self.chart_var,
            values=['candle', 'line', 'renko'],
            state='readonly'
        ).pack(fill='x')
        
    def _create_backtest_tab(self, nb: ttk.Notebook) -> None:
        """Create backtesting settings tab"""
        tab = ttk.Frame(nb)
        nb.add(tab, text="Backtest")
        
        # Test settings
        test = ttk.LabelFrame(
            tab,
            text="Test Settings",
            padding=10
        )
        test.pack(fill='x', padx=5, pady=5)
        
        # Initial capital
        ttk.Label(
            test,
            text="Initial Capital ($):"
        ).pack(anchor='w')
        
        self.capital_var = tk.StringVar(
            value=str(self.settings.get(
                'initial_capital', 10000
            ))
        )
        ttk.Entry(
            test,
            textvariable=self.capital_var
        ).pack(fill='x')
        
        # Date range
        ttk.Label(
            test,
            text="Test Period (days):"
        ).pack(anchor='w')
        
        self.period_var = tk.StringVar(
            value=str(self.settings.get(
                'test_period', 360
            ))
        )
        ttk.Entry(
            test,
            textvariable=self.period_var
        ).pack(fill='x')
        
        # Symbols
        ttk.Label(
            test,
            text="Test Symbols:"
        ).pack(anchor='w')
        
        self.symbols_var = tk.StringVar(
            value=','.join(self.settings.get(
                'test_symbols',
                ['BTCUSDT', 'ETHUSDT']
            ))
        )
        ttk.Entry(
            test,
            textvariable=self.symbols_var
        ).pack(fill='x')
        
        # ML settings
        ml = ttk.LabelFrame(
            tab,
            text="ML Settings",
            padding=10
        )
        ml.pack(fill='x', padx=5, pady=5)
        
        # Training split
        ttk.Label(
            ml,
            text="Train/Test Split:"
        ).pack(anchor='w')
        
        self.split_var = tk.DoubleVar(
            value=self.settings.get(
                'train_split', 0.8
            )
        )
        ttk.Scale(
            ml,
            from_=0.5,
            to=0.9,
            variable=self.split_var
        ).pack(fill='x')
        
        # Trials
        ttk.Label(
            ml,
            text="Tuning Trials:"
        ).pack(anchor='w')
        
        self.trials_var = tk.StringVar(
            value=str(self.settings.get(
                'n_trials', 30
            ))
        )
        ttk.Entry(
            ml,
            textvariable=self.trials_var
        ).pack(fill='x')
        
    def _create_alerts_tab(self, nb: ttk.Notebook) -> None:
        """Create alerts settings tab"""
        tab = ttk.Frame(nb)
        nb.add(tab, text="Alerts")
        
        # Notification settings
        notif = ttk.LabelFrame(
            tab,
            text="Notifications",
            padding=10
        )
        notif.pack(fill='x', padx=5, pady=5)
        
        # Trade alerts
        self.trade_alerts = tk.BooleanVar(
            value=self.settings.get(
                'trade_alerts', True
            )
        )
        ttk.Checkbutton(
            notif,
            text="Trade notifications",
            variable=self.trade_alerts
        ).pack(anchor='w')
        
        # Risk alerts
        self.risk_alerts = tk.BooleanVar(
            value=self.settings.get(
                'risk_alerts', True
            )
        )
        ttk.Checkbutton(
            notif,
            text="Risk notifications",
            variable=self.risk_alerts
        ).pack(anchor='w')
        
        # Error alerts
        self.error_alerts = tk.BooleanVar(
            value=self.settings.get(
                'error_alerts', True
            )
        )
        ttk.Checkbutton(
            notif,
            text="Error notifications",
            variable=self.error_alerts
        ).pack(anchor='w')
        
        # Custom alerts
        alerts = ttk.LabelFrame(
            tab,
            text="Custom Alerts",
            padding=10
        )
        alerts.pack(fill='x', padx=5, pady=5)
        
        # Price alerts
        ttk.Label(
            alerts,
            text="Price Alerts:"
        ).pack(anchor='w')
        
        self.price_alerts = self._load_price_alerts()
        self.price_text = tk.Text(
            alerts,
            height=5,
            width=30
        )
        self.price_text.pack(fill='both')
        self.price_text.insert(
            '1.0',
            '\n'.join(self.price_alerts)
        )
        
    def _create_data_tab(self, nb: ttk.Notebook) -> None:
        """Create data settings tab"""
        tab = ttk.Frame(nb)
        nb.add(tab, text="Data")
        
        # Data settings
        data = ttk.LabelFrame(
            tab,
            text="Data Settings",
            padding=10
        )
        data.pack(fill='x', padx=5, pady=5)
        
        # Cache data
        self.use_cache = tk.BooleanVar(
            value=self.settings.get(
                'use_cache', True
            )
        )
        ttk.Checkbutton(
            data,
            text="Cache historical data",
            variable=self.use_cache
        ).pack(anchor='w')
        
        # Cache time
        ttk.Label(
            data,
            text="Cache Time (hours):"
        ).pack(anchor='w')
        
        self.cache_time = tk.StringVar(
            value=str(self.settings.get(
                'cache_hours', 24
            ))
        )
        ttk.Entry(
            data,
            textvariable=self.cache_time
        ).pack(fill='x')
        
        # Paths
        paths = ttk.LabelFrame(
            tab,
            text="Data Paths",
            padding=10
        )
        paths.pack(fill='x', padx=5, pady=5)
        
        # Data directory
        ttk.Label(
            paths,
            text="Data Directory:"
        ).pack(anchor='w')
        
        self.data_dir = tk.StringVar(
            value=self.settings.get(
                'data_dir', 'data'
            )
        )
        ttk.Entry(
            paths,
            textvariable=self.data_dir
        ).pack(fill='x')
        
        # Logs directory
        ttk.Label(
            paths,
            text="Logs Directory:"
        ).pack(anchor='w')
        
        self.logs_dir = tk.StringVar(
            value=self.settings.get(
                'logs_dir', 'logs'
            )
        )
        ttk.Entry(
            paths,
            textvariable=self.logs_dir
        ).pack(fill='x')
        
        # Trades directory
        ttk.Label(
            paths,
            text="Trades Directory:"
        ).pack(anchor='w')
        
        self.trades_dir = tk.StringVar(
            value=self.settings.get(
                'trades_dir', 'trades'
            )
        )
        ttk.Entry(
            paths,
            textvariable=self.trades_dir
        ).pack(fill='x')
        
        # Add buttons
        buttons = ttk.Frame(self.window)
        buttons.pack(
            fill='x',
            padx=5,
            pady=10
        )
        
        ttk.Button(
            buttons,
            text="Save",
            command=self._save_settings
        ).pack(side='right', padx=5)
        
        ttk.Button(
            buttons,
            text="Cancel",
            command=self._hide_settings
        ).pack(side='right', padx=5)
        
        ttk.Button(
            buttons,
            text="Reset All",
            command=self._reset_settings
        ).pack(side='left', padx=5)
        
    def _hide_settings(self) -> None:
        """Hide settings window"""
        if self.window:
            self.window.destroy()
            self.window = None
            
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file"""
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except:
            return {}
            
    def _save_settings(self) -> None:
        """Save settings to file"""
        try:
            settings = {
                # General
                'auto_start': self.auto_start.get(),
                'auto_reconnect': self.auto_reconn.get(),
                'default_symbol': self.symbol_var.get(),
                'theme': self.theme_var.get(),
                'chart_style': self.chart_var.get(),
                
                # Backtest
                'initial_capital': float(
                    self.capital_var.get()
                ),
                'test_period': int(
                    self.period_var.get()
                ),
                'test_symbols': [
                    s.strip() for s in
                    self.symbols_var.get().split(',')
                ],
                'train_split': self.split_var.get(),
                'n_trials': int(
                    self.trials_var.get()
                ),
                
                # Alerts
                'trade_alerts': self.trade_alerts.get(),
                'risk_alerts': self.risk_alerts.get(),
                'error_alerts': self.error_alerts.get(),
                'price_alerts': self._get_price_alerts(),
                
                # Data
                'use_cache': self.use_cache.get(),
                'cache_hours': int(
                    self.cache_time.get()
                ),
                'data_dir': self.data_dir.get(),
                'logs_dir': self.logs_dir.get(),
                'trades_dir': self.trades_dir.get()
            }
            
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
                
            # Notify callback
            if hasattr(self, 'on_settings_update'):
                self.on_settings_update(settings)
                
            self._hide_settings()
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to save settings: {e}"
            )
            
    def _reset_settings(self) -> None:
        """Reset settings to defaults"""
        if messagebox.askyesno(
            "Confirm Reset",
            "Reset all settings to default values?"
        ):
            # Delete settings file
            try:
                os.remove('settings.json')
            except:
                pass
                
            # Reload defaults
            self.settings = {}
            
            # Close window
            self._hide_settings()
            
    def _load_price_alerts(self) -> List[str]:
        """Load price alerts"""
        alerts = self.settings.get(
            'price_alerts', []
        )
        return alerts if isinstance(alerts, list) else []
        
    def _get_price_alerts(self) -> List[str]:
        """Get price alerts from text"""
        text = self.price_text.get('1.0', 'end')
        alerts = [
            line.strip() for line in text.split('\n')
            if line.strip()
        ]
        return alerts


def main():
    """Test settings menu"""
    root = tk.Tk()
    root.title("Settings Test")
    
    def on_update(settings):
        print(f"Settings updated: {settings}")
        
    # Create menu
    menu = BotSettingsMenu(root)
    menu.on_settings_update = on_update
    
    root.mainloop()


if __name__ == '__main__':
    main()