"""
Universal gui_help.py
Compatible with all CryptoBot GUI versions.
This module guarantees all help constants and utility functions exist.
"""

import tkinter as tk
from tkinter import ttk
import webbrowser
from typing import Optional

# ---------- Generic fallback help text ----------
_DEFAULT_TEXT = "Help topic under development. Check documentation for updates."

# ---------- Help constants ----------
TRADING_MODE_HELP = """TRADING MODE — TEST VS LIVE

Test Mode:
• Uses mock data and simulated trading
• No real funds at risk
• Great for learning and strategy testing
• Automatically simulates order fills and slippage
• Useful for backtesting strategies before live trading

Live Trading:
• Real funds connected to your exchange account
• Requires valid API key configuration
• Enable with caution - always test first
• Monitor positions carefully
• Use risk controls to limit exposure

HOW TO SWITCH:
1. Go to "Mode Switcher" tab
2. Select either "Test Mode" or "Live Trading"
3. For live mode, ensure API key is configured
4. Save settings before starting trades"""

TIMEFRAME_HELP = """CHART TIMEFRAMES

Available Timeframes:
• Scalp (1m): Ultra-fast trades, high frequency, tight stops
• Short (5m): Day trading focused, quick entries and exits
• Medium (1h): Swing trading, hold positions hours to days
• Long (1d): Position trading, hold for days to weeks

TIMEFRAME SELECTION TIPS:
• Choose timeframe matching your trading style
• Shorter timeframes = more trades but higher slippage
• Longer timeframes = fewer trades but better trends
• Combine multiple timeframes for confirmation
• Scalping needs tight risk management
• Position trading needs wider stops

CHANGING TIMEFRAMES:
1. Go to Trading Controls tab
2. Select desired timeframe under "Timeframe" section
3. Changes apply immediately to new candles
4. Historical data reloads when switching"""

INDICATORS_HELP = """INDICATORS AND TECHNICAL TOOLS

Available Indicators:
• RSI (Relative Strength Index): Overbought/oversold
• MACD: Momentum and trend confirmation
• Bollinger Bands: Volatility measurement and reversals
• Moving Averages: Trend direction (SMA/EMA)
• Volume: Strength of price movements
• ATR (Average True Range): Volatility levels

USING INDICATORS:
1. Add indicators from "Market Analysis" tab
2. Adjust parameters in settings
3. Monitor for confirmation signals
4. Combine 2-3 indicators for better accuracy

SIGNAL RELIABILITY:
• Most reliable: Multiple indicators confirming
• Avoid: Single indicator signals
• Best: Combine price action + indicators
• Remember: Past performance ≠ future results"""

SETTINGS_HELP = """SETTINGS CONFIGURATION

Main Settings:
• Trading Mode: Choose test or live trading
• Leverage: Position multiplier (if enabled)
• Timeframe: Selected chart period
• Auto Mode Switch: Automatic trading mode changes
• API Keys: Exchange authentication (live mode only)

CONFIGURATION OPTIONS:
1. Click hamburger menu (☰) for settings access
2. Adjust theme (dark/light)
3. Configure keyboard shortcuts
4. Set default trading pairs
5. Customize risk parameters

SAVING SETTINGS:
• Click "Save" button after changes
• Settings persist across sessions
• Backup important configurations
• Reset to defaults available in advanced options"""

RISK_CONTROLS_HELP = """RISK MANAGEMENT

Essential Risk Controls:
• Position Size: Limit trade size to % of account
• Stop Loss: Automatic loss exit price
• Take Profit: Automatic profit target
• Max Drawdown: Halt trading if losses exceed limit
• Daily Loss Limit: Stop after X% daily loss
• Emergency Stop: Manual override button

RECOMMENDED SETTINGS:
• Max Position: 5% of account per trade
• Stop Loss: 2% below entry
• Take Profit: 3-5% above entry
• Max Drawdown: 10% before pausing
• Risk/Reward Ratio: Minimum 1:2

USING RISK CONTROLS:
1. Go to "Risk Controls" tab
2. Set position sizing rules
3. Enable emergency stop
4. Monitor limits in status bar
5. Adjust based on performance"""

MARKET_TOOLS_HELP = """MARKET ANALYSIS TOOLS

Available Tools:
• Gainers: Top 24h gainers
• Losers: Top 24h losers
• New Listings: Recently listed pairs
• Market Trends: Overall market direction
• Volume Analysis: Trading volume patterns

MARKET SIGNALS:
• Gainers: Potential momentum trades
• Losers: Recovery opportunities
• New Listings: High volatility, risky
• Volume Surge: Confirmation of moves
• Market Correlation: Asset relationships

USING MARKET TOOLS:
1. Monitor "Market Tracker" tab regularly
2. Check trending pairs
3. Watch volume for confirmation
4. Cross-reference with technical indicators
5. Set alerts for significant moves"""

QUICK_COMMANDS = """KEYBOARD SHORTCUTS

Trading Commands:
• Ctrl+S: Start/Stop trading
• Ctrl+T: Toggle Test/Live mode
• Ctrl+B: Run backtest
• Ctrl+R: Reconnect to API
• Ctrl+W: Save settings

Navigation:
• F5: Refresh data
• F1: Show this help
• Ctrl+Q: Quit application
• Escape: Emergency stop

Pro Tips:
• Memorize shortcuts for faster trading
• Emergency stop works even if trading is frozen
• Use Ctrl+S to quickly toggle trading state
• F5 refreshes all open charts and data"""

STRATEGY_HELP = """TRADING STRATEGY GUIDE

Strategy Framework:
1. Entry: Confirmation of trend + technical setup
2. Management: Monitor position, adjust stops
3. Exit: Hit target or stop loss
4. Analysis: Review trade for learning

ENTRY SIGNALS:
• Trend confirmed by moving averages
• RSI showing momentum (> 50 bullish, < 50 bearish)
• MACD cross confirming direction
• Volume supporting move
• Multiple timeframe alignment

POSITION MANAGEMENT:
• Trail stops as trade moves favorably
• Take partial profits at first target
• Move stops to breakeven after profit
• Scale into winning positions
• Exit on price action divergence

RISK MANAGEMENT:
• Risk only 1-2% per trade
• Maintain 1:2 risk/reward minimum
• Use tight stops on breakeven trades
• Protect capital above profits
• Focus on consistent small wins"""

AI_MODEL_HELP = """MACHINE LEARNING MODEL

Model Overview:
• Trained on 2+ years of historical data
• Uses 50+ technical indicators
• Continuously learns from new data
• Provides entry/exit predictions

MODEL COMPONENTS:
• Feature Engineering: 50+ indicator combinations
• Pattern Recognition: Detects repeating setups
• Probability Scoring: Confidence levels for signals
• Risk Assessment: Position sizing recommendations

MONITORING:
1. Go to "ML Monitor" tab
2. Check model accuracy metrics
3. Review feature importance
4. Monitor prediction confidence
5. Retrain if accuracy drops below threshold

USING PREDICTIONS:
• Don't rely solely on AI predictions
• Confirm with technical analysis
• Monitor feature importance for relevance
• Adjust strategy if model accuracy declines
• Periodically retrain with latest data"""

BACKTEST_HELP = """BACKTESTING AND OPTIMIZATION

Backtest Process:
1. Select historical date range
2. Choose trading pairs
3. Configure risk parameters
4. Run simulation
5. Analyze results

INTERPRETING RESULTS:
• Win Rate: % of winning trades
• Profit Factor: Gross profit / gross loss
• Drawdown: Peak-to-trough loss
• Sharpe Ratio: Risk-adjusted returns
• Total Return: Overall P&L

OPTIMIZATION:
• Test different parameter combinations
• Optimize for max Sharpe ratio
• Verify results on out-of-sample data
• Beware overfitting to historical data
• Paper trade before live implementation

BEST PRACTICES:
• Always backtest before live trading
• Test across different market conditions
• Include slippage/commission estimates
• Test on recent data too
• Optimize for consistency, not just profit"""

PERFORMANCE_HELP = """PERFORMANCE METRICS

Key Metrics:
• Total Return: Overall profit/loss
• Win Rate: % of winning trades
• Average Win/Loss: Typical trade outcomes
• Max Drawdown: Worst peak-to-trough loss
• Sharpe Ratio: Risk-adjusted returns

ANALYZING PERFORMANCE:
1. Go to "Analytics" tab
2. Review trade history
3. Check equity curve
4. Analyze monthly/weekly returns
5. Identify patterns

INTERPRETING STATISTICS:
• Win rate above 50% is good
• Profit factor > 1.5 is strong
• Max drawdown < 20% is acceptable
• Sharpe ratio > 1.0 is solid
• Consistency matters more than profit

IMPROVING RESULTS:
• Increase win rate through better entries
• Improve exits to protect profits
• Reduce drawdown with better risk control
• Diversify trading pairs and timeframes
• Track and adjust underperforming strategies"""

GENERAL_HELP = """GETTING STARTED

Initial Setup:
1. Configure API keys (for live mode)
2. Set risk parameters
3. Choose trading pairs
4. Select timeframe
5. Start with test mode

FIRST TRADE:
1. Enable "Test Mode"
2. Select 1-2 trading pairs
3. Run backtest first
4. Check Risk Controls settings
5. Click "Start Trading"

MONITORING:
• Watch trade entry/exit points
• Monitor P&L in real-time
• Check for emergency stop triggers
• Review closed trades regularly
• Adjust strategy if needed

COMMON ISSUES:
• API Connection: Check keys and network
• No Trades: Adjust signal parameters
• Slippage: May vary by market conditions
• Drawdown: Review risk settings
• For help: Check documentation or forum"""

OTHER_HELP = """MISCELLANEOUS TOPICS

Performance Optimization:
• Disable animations if CPU usage high
• Reduce chart update frequency
• Limit number of indicators
• Close unused tabs
• Monitor system resources

Troubleshooting:
• Check internet connection
• Verify API keys are correct
• Ensure sufficient balance
• Review error logs
• Restart application if frozen

Advanced Features:
• Multi-symbol trading enabled
• Automated rebalancing available
• Custom indicator creation
• Strategy parameter optimization
• Data export to CSV

Support Resources:
• GitHub: project documentation
• Discord: community support
• Email: technical support
• Documentation: full guides
• Video Tutorials: YouTube channel"""

# ---------- Tooltip helpers ----------
def create_tooltip(widget: tk.Widget, text: str):
    """Attach a tooltip to any widget."""
    tooltip = tk.Toplevel(widget)
    tooltip.withdraw()
    tooltip.overrideredirect(True)
    label = tk.Label(tooltip, text=text, bg="#333", fg="white",
                     padx=6, pady=3, relief="solid", borderwidth=1)
    label.pack()

    def enter(event):
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 20
        tooltip.geometry(f"+{x}+{y}")
        tooltip.deiconify()

    def leave(event):
        tooltip.withdraw()

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)
    return tooltip


def get_quick_tooltip(widget: tk.Widget, text: str):
    """Alias for create_tooltip (compatibility)."""
    return create_tooltip(widget, text)


# ---------- Help window ----------
class HelpSystem:
    """Unified help dialog system for CryptoBot GUI with comprehensive topics."""

    HELP_TOPICS = {
        "Getting Started": GENERAL_HELP,
        "Trading Mode": TRADING_MODE_HELP,
        "Timeframes": TIMEFRAME_HELP,
        "Strategy": STRATEGY_HELP,
        "Indicators": INDICATORS_HELP,
        "Risk Controls": RISK_CONTROLS_HELP,
        "Settings": SETTINGS_HELP,
        "Market Tools": MARKET_TOOLS_HELP,
        "AI Model": AI_MODEL_HELP,
        "Backtesting": BACKTEST_HELP,
        "Performance": PERFORMANCE_HELP,
        "Quick Commands": QUICK_COMMANDS,
        "Troubleshooting": OTHER_HELP
    }

    def __init__(self, parent: Optional[tk.Widget] = None):
        self.parent = parent or tk._default_root
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("CryptoBot Help System")
        self.dialog.geometry("1000x700")
        self._create_layout()
        # Show "Getting Started" by default
        self._show_topic("Getting Started")

    def _create_layout(self):
        paned = ttk.PanedWindow(self.dialog, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=5, pady=5)

        # Left panel - Navigation
        left = ttk.Frame(paned, padding=8)
        paned.add(left, weight=1)
        
        # Title in left panel
        ttk.Label(left, text="📚 TOPICS", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Search bar
        ttk.Label(left, text="Search:").pack(anchor='w', pady=(0, 2))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(left)
        search_entry.pack(fill='x', pady=(0, 10))
        
        # Topics frame with scrollbar
        topics_frame = ttk.Frame(left)
        topics_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        topics_canvas = tk.Canvas(topics_frame, bg='white', highlightthickness=0)
        topics_canvas.pack(side='left', fill='both', expand=True)
        
        topics_scroll = ttk.Scrollbar(topics_frame, orient='vertical', command=topics_canvas.yview)
        topics_scroll.pack(side='right', fill='y')
        topics_canvas.configure(yscrollcommand=topics_scroll.set)
        
        topics_inner = ttk.Frame(topics_canvas)
        topics_canvas.create_window((0, 0), window=topics_inner, anchor='nw')
        
        # Add topic buttons
        for topic in self.HELP_TOPICS:
            ttk.Button(topics_inner, text=f"▸ {topic}",
                       command=lambda t=topic: self._show_topic(t),
                       width=18).pack(fill='x', padx=2, pady=2)
        
        topics_inner.update_idletasks()
        topics_canvas.config(scrollregion=topics_canvas.bbox('all'))

        # Links section
        links = ttk.LabelFrame(left, text="🔗 Resources", padding=5)
        links.pack(fill='x')
        ttk.Button(links, text="📖 Documentation", 
                   command=lambda: webbrowser.open("https://docs.cryptobot.com"),
                   width=18).pack(fill='x', pady=2)
        ttk.Button(links, text="💬 Community Forum",
                   command=lambda: webbrowser.open("https://forum.cryptobot.com"),
                   width=18).pack(fill='x', pady=2)
        ttk.Button(links, text="▶️ YouTube Tutorials",
                   command=lambda: webbrowser.open("https://youtube.com"),
                   width=18).pack(fill='x', pady=2)

        # Right panel - Content display
        right = ttk.Frame(paned, padding=8)
        paned.add(right, weight=3)

        # Title display
        title_frame = ttk.Frame(right)
        title_frame.pack(fill='x', pady=(0, 10))
        
        self.title_var = tk.StringVar()
        ttk.Label(title_frame, textvariable=self.title_var,
                  font=('Arial', 16, 'bold')).pack(anchor='w')
        
        ttk.Separator(title_frame, orient='horizontal').pack(fill='x', pady=5)

        # Text display with syntax highlighting
        text_frame = ttk.Frame(right)
        text_frame.pack(fill='both', expand=True)
        
        self.text = tk.Text(text_frame, wrap='word', padx=10, pady=8,
                           font=('Courier', 10), bg='#f5f5f5')
        self.text.pack(fill='both', expand=True, side='left')
        
        # Configure text tags for formatting
        self.text.tag_configure('heading', font=('Arial', 12, 'bold'), foreground='#0066cc')
        self.text.tag_configure('bullet', font=('Courier', 10), foreground='#333333')
        self.text.tag_configure('code', font=('Courier', 9), background='#e0e0e0')

        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.text.yview)
        scrollbar.pack(side='right', fill='y')
        self.text.configure(yscrollcommand=scrollbar.set)

    def _show_topic(self, topic: str):
        content = self.HELP_TOPICS.get(topic, _DEFAULT_TEXT)
        self.title_var.set(topic)
        self.text.delete('1.0', tk.END)
        self.text.insert('1.0', content)


def show_help_window(parent=None):
    """Launch the help window."""
    HelpSystem(parent)


# ---------- Export ----------
__all__ = [
    "HelpSystem", "show_help_window", "create_tooltip", "get_quick_tooltip",
    "TRADING_MODE_HELP", "TIMEFRAME_HELP", "INDICATORS_HELP",
    "SETTINGS_HELP", "RISK_CONTROLS_HELP", "MARKET_TOOLS_HELP",
    "QUICK_COMMANDS", "STRATEGY_HELP", "AI_MODEL_HELP",
    "BACKTEST_HELP", "PERFORMANCE_HELP", "GENERAL_HELP", "OTHER_HELP"
]
