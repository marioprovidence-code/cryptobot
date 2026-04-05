# CryptoBot GUI Enhancement Plan

## 1. Advanced Charting Module (`gui_charts.py`)
```python
class TradingChart:
    def __init__(self, frame: tk.Frame):
        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, frame)
        self.candlesticks = []
        self.indicators = {}

    def update_candlesticks(self, df: pd.DataFrame) -> None:
        # Plot OHLC data with volume
        mpf.plot(df, type='candle', style='charles',
                volume=True, panel_ratios=(3,1))
        
    def add_indicator(self, name: str, data: pd.Series) -> None:
        # Overlay technical indicator
        self.indicators[name] = self.ax.plot(
            data.index, data.values, 
            label=name
        )

    def mark_trade(self, timestamp, price, type_: str) -> None:
        # Add buy/sell markers
        color = 'g' if type_ == 'buy' else 'r'
        self.ax.scatter(timestamp, price, c=color, marker='^')
```

## 2. Risk Management Panel (`gui_risk.py`)
```python
class RiskPanel:
    def __init__(self, frame: tk.Frame):
        self.frame = frame
        self.risk_pct = tk.DoubleVar(value=1.0)
        self.stop_atr = tk.DoubleVar(value=2.0)
        self.max_drawdown = tk.DoubleVar(value=10.0)
        
        self._create_widgets()
        self._bind_updates()

    def _create_widgets(self) -> None:
        # Risk per trade
        risk_frame = ttk.LabelFrame(self.frame, text="Risk Settings")
        ttk.Scale(risk_frame, from_=0.1, to=5.0,
                 variable=self.risk_pct).pack()
                 
        # Stop loss multiplier
        stop_frame = ttk.LabelFrame(self.frame, text="Stop Loss")
        ttk.Scale(stop_frame, from_=1.0, to=4.0,
                 variable=self.stop_atr).pack()

    def update_config(self) -> None:
        update_risk_config({
            'risk_per_trade': self.risk_pct.get() / 100,
            'stop_loss_mult': self.stop_atr.get(),
            'max_drawdown': self.max_drawdown.get() / 100
        })
```

## 3. Performance Analytics (`gui_analytics.py`)
```python
class PerformanceMetrics:
    def __init__(self, frame: tk.Frame):
        self.frame = frame
        self._setup_metrics()
        
    def _setup_metrics(self) -> None:
        metrics = [
            ("Win Rate", "win_rate"),
            ("Profit Factor", "profit_factor"),
            ("Max Drawdown", "max_dd"),
            ("Sharpe Ratio", "sharpe")
        ]
        for label, key in metrics:
            ttk.Label(self.frame, text=f"{label}:").pack()
            self.__dict__[f"{key}_var"] = tk.StringVar()
            ttk.Label(
                self.frame,
                textvariable=self.__dict__[f"{key}_var"]
            ).pack()

    def update_metrics(self, trades_df: pd.DataFrame) -> None:
        # Calculate and update performance metrics
        metrics = calculate_performance_metrics(trades_df)
        for key, value in metrics.items():
            if f"{key}_var" in self.__dict__:
                self.__dict__[f"{key}_var"].set(f"{value:.2f}")
```

## 4. Enhanced Main GUI (`gui_advanced.py`)

The enhanced GUI will:
1. Import all component modules
2. Create tabbed interface for different views
3. Handle real-time updates via async bridge
4. Maintain mock-first design pattern

### Implementation Steps:

1. Create component modules
2. Test each component individually
3. Build main integration GUI
4. Add real-time data handling
5. Implement save/load settings

### Timeline:

Phase 1 (Week 1):
- Basic charting module
- Risk management panel
- Component tests

Phase 2 (Week 2):
- Performance analytics
- Settings persistence
- Integration testing

Phase 3 (Week 3):
- Real-time data handling
- UI polish
- Documentation

## Dependencies:

Required:
- tkinter
- threading
- datetime

Optional (with fallbacks):
- matplotlib
- mplfinance
- pandas

## Architecture:

```
gui_advanced/
├── __init__.py
├── components/
│   ├── charts.py
│   ├── risk.py
│   └── analytics.py
├── utils/
│   ├── async_bridge.py
│   └── settings.py
└── main.py
```