"""
CryptoBot GUI Theme Support
Provides dark/light themes and custom styles.
"""

from tkinter import ttk
import tkinter as tk
from typing import Dict, Any

# Theme definitions
THEMES = {
    'dark': {
        'bg': '#1a1a1a',
        'fg': '#ffffff',
        'select_bg': '#404040',
        'select_fg': '#ffffff',
        'button_bg': '#2d2d2d',
        'button_fg': '#ffffff',
        'frame_bg': '#262626',
        'accent': '#007acc'
    },
    'light': {
        'bg': '#ffffff',
        'fg': '#000000',
        'select_bg': '#0078d7',
        'select_fg': '#ffffff',
        'button_bg': '#f0f0f0',
        'button_fg': '#000000',
        'frame_bg': '#f5f5f5',
        'accent': '#0078d7'
    }
}

class ThemeManager:
    """Manages GUI themes and styles"""
    
    def __init__(self):
        """Initialize with default theme"""
        self.current_theme = 'dark'
        self._setup_styles()
        
    def _setup_styles(self) -> None:
        """Configure ttk styles"""
        style = ttk.Style()
        
        # Get theme colors
        colors = THEMES[self.current_theme]
        
        # Configure styles
        style.configure(
            'TFrame',
            background=colors['frame_bg']
        )
        
        style.configure(
            'TLabel',
            background=colors['frame_bg'],
            foreground=colors['fg']
        )
        
        style.configure(
            'TButton',
            background=colors['button_bg'],
            foreground=colors['button_fg']
        )
        
        style.configure(
            'Accent.TButton',
            background=colors['accent'],
            foreground=colors['select_fg']
        )
        
        style.configure(
            'TNotebook',
            background=colors['bg'],
            tabmargins=[2, 5, 2, 0]
        )
        
        style.configure(
            'TNotebook.Tab',
            background=colors['button_bg'],
            foreground=colors['button_fg'],
            padding=[10, 2]
        )
        
        style.map('TNotebook.Tab',
            background=[('selected', colors['select_bg'])],
            foreground=[('selected', colors['select_fg'])]
        )
        
        # Custom styles
        style.configure(
            'Title.TLabel',
            font=('Helvetica', 14, 'bold'),
            foreground=colors['accent']
        )
        
        style.configure(
            'Fallback.TLabel',
            font=('Helvetica', 12),
            foreground='#888888'
        )
        
        style.configure(
            'Risk.TLabel',
            foreground='#ff4444'
        )
        
        style.configure(
            'Success.TLabel',
            foreground='#44ff44'
        )
        
    def apply_theme(self, theme_name: str) -> None:
        """Switch to a different theme"""
        if theme_name in THEMES:
            self.current_theme = theme_name
            self._setup_styles()
            
    def get_colors(self) -> Dict[str, str]:
        """Get current theme colors"""
        return THEMES[self.current_theme]
        
    def configure_root(self, root: tk.Tk) -> None:
        """Apply theme to root window"""
        colors = self.get_colors()
        root.configure(bg=colors['bg'])
        
        # Configure all frames
        for child in root.winfo_children():
            if isinstance(child, (ttk.Frame, ttk.LabelFrame)):
                child.configure(style='TFrame')
            elif isinstance(child, ttk.Label):
                child.configure(style='TLabel')


# Global theme manager instance
theme_manager = ThemeManager()