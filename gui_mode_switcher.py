"""
Mode switcher panel for live/testnet trading
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

class TradingModeSwitcher:
    """Controls for switching between live and test trading"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize mode switcher"""
        self.parent = parent
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='x', padx=5, pady=5)
        
        # Mode selector
        self._create_mode_selector()
        
        # Settings
        self._create_settings()
        
        # Status
        self._create_status()
        
    def _create_mode_selector(self) -> None:
        """Create mode selection controls"""
        # Mode frame
        mode_frame = ttk.LabelFrame(
            self.frame,
            text="Trading Mode",
            padding=5
        )
        mode_frame.pack(
            side='left',
            fill='x',
            expand=True,
            padx=5
        )
        
        # Mode buttons
        self.mode_var = tk.StringVar(value='test')
        
        ttk.Radiobutton(
            mode_frame,
            text="Test Mode",
            variable=self.mode_var,
            value='test',
            command=self._mode_changed
        ).pack(side='left', padx=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="Live Trading",
            variable=self.mode_var,
            value='live',
            command=self._mode_changed
        ).pack(side='left', padx=5)
        
        # Warning label
        self.warning_var = tk.StringVar()
        ttk.Label(
            mode_frame,
            textvariable=self.warning_var,
            style='Warning.TLabel'
        ).pack(side='left', padx=10)
        
    def _create_settings(self) -> None:
        """Create mode-specific settings"""
        # Settings frame
        settings = ttk.LabelFrame(
            self.frame,
            text="Settings",
            padding=5
        )
        settings.pack(
            side='left',
            fill='x',
            expand=True,
            padx=5
        )
        
        # Test mode settings
        self.mock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings,
            text="Use Mock Data",
            variable=self.mock_var,
            command=self._settings_changed
        ).pack(side='left', padx=5)
        
        self.delay_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings,
            text="Simulate Delays",
            variable=self.delay_var,
            command=self._settings_changed
        ).pack(side='left', padx=5)
        
        # Live mode settings
        ttk.Label(
            settings,
            text="API Key:"
        ).pack(side='left', padx=5)
        
        self.api_var = tk.StringVar()
        self.api_entry = ttk.Entry(
            settings,
            textvariable=self.api_var,
            width=20,
            show='*'
        )
        self.api_entry.pack(side='left', padx=5)
        
        # Save button
        ttk.Button(
            settings,
            text="Save",
            command=self._save_settings
        ).pack(side='left', padx=10)
        
    def _create_status(self) -> None:
        """Create status display"""
        # Status frame
        status = ttk.LabelFrame(
            self.frame,
            text="Status",
            padding=5
        )
        status.pack(
            side='left',
            fill='x',
            expand=True,
            padx=5
        )
        
        # Connection status
        self.conn_var = tk.StringVar(
            value="Not Connected"
        )
        ttk.Label(
            status,
            textvariable=self.conn_var,
            style='Status.TLabel'
        ).pack(side='left', padx=5)
        
        # Test indicator
        self.test_label = ttk.Label(
            status,
            text="TEST MODE",
            style='TestMode.TLabel'
        )
        self.test_label.pack(side='left', padx=10)
        
        # Reconnect button
        self.reconn_btn = ttk.Button(
            status,
            text="Reconnect",
            command=self._reconnect,
            state='disabled'
        )
        self.reconn_btn.pack(side='right', padx=5)
        
    def _mode_changed(self) -> None:
        """Handle mode change"""
        mode = self.mode_var.get()
        
        if mode == 'live':
            self.warning_var.set(
                "⚠️ Live trading uses real funds"
            )
            self.test_label.pack_forget()
            self.reconn_btn.configure(state='normal')
            
            # Check API key
            if not self.api_var.get():
                self.conn_var.set("Need API Key")
                return
                
        else:
            self.warning_var.set("")
            self.test_label.pack(side='left', padx=10)
            self.reconn_btn.configure(state='disabled')
            self.conn_var.set("Mock Mode")
            
        # Notify listeners
        if hasattr(self, 'on_mode_change'):
            self.on_mode_change(
                mode,
                self.mock_var.get(),
                self.delay_var.get()
            )
            
    def _settings_changed(self) -> None:
        """Handle settings changes"""
        if hasattr(self, 'on_settings_change'):
            self.on_settings_change({
                'mock': self.mock_var.get(),
                'delay': self.delay_var.get()
            })
            
    def _save_settings(self) -> None:
        """Save current settings"""
        if hasattr(self, 'on_save_settings'):
            self.on_save_settings({
                'mode': self.mode_var.get(),
                'mock': self.mock_var.get(),
                'delay': self.delay_var.get(),
                'api_key': self.api_var.get()
            })
            
    def _reconnect(self) -> None:
        """Attempt reconnection"""
        if hasattr(self, 'on_reconnect'):
            self.on_reconnect()
            
    def update_status(
        self,
        connected: bool,
        message: Optional[str] = None
    ) -> None:
        """Update connection status"""
        if connected:
            self.conn_var.set(
                "Connected" if not message
                else message
            )
        else:
            self.conn_var.set(
                "Disconnected" if not message
                else message
            )
            
    def set_mode(self, mode: str) -> None:
        """Set trading mode"""
        self.mode_var.set(mode)
        self._mode_changed()
        
    def get_mode(self) -> str:
        """Get current trading mode"""
        return self.mode_var.get()
        
    def is_live(self) -> bool:
        """Check if in live mode"""
        return self.mode_var.get() == 'live'
        
    def is_mock(self) -> bool:
        """Check if using mock data"""
        return (
            self.mode_var.get() == 'test' or
            self.mock_var.get()
        )


def main():
    """Test mode switcher"""
    root = tk.Tk()
    root.title("Mode Switcher Test")
    
    def on_mode_change(mode, mock, delay):
        print(f"Mode: {mode}, Mock: {mock}, Delay: {delay}")
        
    def on_save(settings):
        print(f"Save settings: {settings}")
        
    def on_reconnect():
        print("Reconnect requested")
        
    # Create switcher
    switcher = TradingModeSwitcher(root)
    switcher.on_mode_change = on_mode_change
    switcher.on_save_settings = on_save
    switcher.on_reconnect = on_reconnect
    
    # Test status updates
    root.after(2000, lambda: switcher.update_status(True, "Connected to Binance"))
    root.after(4000, lambda: switcher.update_status(False, "Connection lost"))
    
    root.mainloop()


if __name__ == '__main__':
    main()