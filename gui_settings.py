"""
CryptoBot GUI Settings
Manages persistent settings and keyboard shortcuts.
"""

import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class Settings:
    """Persistent settings manager"""
    
    def __init__(self, filename: str = 'gui_settings.json'):
        """Initialize with settings file"""
        self.filename = filename
        self.defaults = {
            'theme': 'dark',
            'symbol': 'SOLUSDT',
            'risk': {
                'max_position_size': 100.0,
                'max_drawdown': 0.02,
                'trailing_stop': 0.01,
                'profit_target': 0.03,
                'max_trades_per_day': 10,
                'cooldown_minutes': 5
            },
            'chart': {
                'update_interval_ms': 1000,
                'show_volume': True,
                'indicators': ['SMA_20', 'RSI_14']
            }
        }
        self.current = self.load()
        
    def load(self) -> Dict[str, Any]:
        """Load settings from file"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
        return self.defaults.copy()
        
    def save(self) -> None:
        """Save current settings to file"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.current, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value with optional default"""
        return self.current.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Update setting value and save"""
        self.current[key] = value
        self.save()
        
    def get_risk_params(self) -> Dict[str, float]:
        """Get risk management parameters"""
        return self.current.get('risk', self.defaults['risk'])
        
    def update_risk_params(self, params: Dict[str, float]) -> None:
        """Update risk parameters"""
        self.current['risk'] = params
        self.save()


class KeyBindings:
    """Keyboard shortcut manager"""
    
    def __init__(self):
        """Initialize default bindings"""
        self.bindings = {
            '<Control-s>': ('start_stop', 'Start/Stop Trading'),
            '<Control-r>': ('reconnect', 'Reconnect'),
            '<Control-q>': ('quit', 'Quit Application'),
            '<Control-t>': ('toggle_theme', 'Toggle Theme'),
            '<F5>': ('refresh', 'Refresh Data'),
            '<Control-h>': ('show_help', 'Show Help')
        }
        
    def bind_all(self, root, callbacks) -> None:
        """Bind all shortcuts to root window"""
        for key, (action, _) in self.bindings.items():
            if action in callbacks:
                root.bind(key, callbacks[action])
                
    def get_help(self) -> str:
        """Get help text for all shortcuts"""
        help_text = "Keyboard Shortcuts:\n\n"
        for key, (_, desc) in self.bindings.items():
            help_text += f"{key}: {desc}\n"
        return help_text


# Global instances
settings = Settings()
key_bindings = KeyBindings()