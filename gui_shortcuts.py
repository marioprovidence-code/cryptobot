"""
CryptoBot keyboard shortcuts handler
"""
from typing import Dict, Callable, Any
import tkinter as tk

class ShortcutManager:
    """Manage keyboard shortcuts"""
    
    DEFAULT_SHORTCUTS = {
        '<Control-s>': ('start_stop', 'Start/Stop Trading'),
        '<Control-r>': ('reconnect', 'Reconnect'),
        '<Control-b>': ('run_backtest', 'Run Backtest'),
        '<Control-t>': ('toggle_test', 'Toggle Test Mode'),
        '<Control-w>': ('save_settings', 'Save Settings'),
        '<Escape>': ('close_all', 'Close All Positions'),
        'F5': ('refresh', 'Refresh Charts'),
        'F1': ('show_help', 'Show Help'),
        '<Control-q>': ('quit', 'Quit Application')
    }
    
    def __init__(self):
        """Initialize shortcuts"""
        self.shortcuts = self.DEFAULT_SHORTCUTS.copy()
        
    def bind_all(self, root: tk.Tk, callbacks: Dict[str, Callable]) -> None:
        """Bind all shortcuts to root window"""
        for key, (action, _) in self.shortcuts.items():
            if action in callbacks:
                root.bind(key, callbacks[action])
                
    def get_help(self) -> str:
        """Get help text showing all shortcuts"""
        lines = ["Keyboard Shortcuts:"]
        for key, (_, desc) in self.shortcuts.items():
            lines.append(f"{key}: {desc}")
        return "\n".join(lines)