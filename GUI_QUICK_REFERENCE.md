# ⚡ CryptoBot GUI - QUICK REFERENCE CARD

## 🎯 MAIN INTERFACE LAYOUT

```
╔════════════════════════════════════════════════════════════════════════╗
║                    CRYPTO SCALPER BOT - ADVANCED DASHBOARD            ║
╠════════════════════════════════════════════════════════════════════════╣
║ ☰ MENU | Balance: $10,000 | Current: SOLUSDT | [TestNet] [LIVE]      ║
║ Environment: ━━━━━━━━ | Symbol: [SOLUSDT ▼] [Switch] [Auto-Switch]   ║
║ [Run Backtest] [Start Live] [Stop Bot] | Auto Mode: ☑ Trading Control║
╠════════════════════════════════════════════════════════════════════════╣
║  📊 Dashboard | 🎛️ Trading Controls | ⚙️ Mode Switcher | 📊 Volatility │
║  🛡️ Risk Controls | 📈 Analytics | 🤖 ML Monitor | 📉 Backtest        │
║  ⚙️ Risk Settings | 📈 Market Analysis | 🔍 Market Tracker            │
╠════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  [TAB CONTENT AREA - Scrollable and Interactive]                     ║
║                                                                        ║
║  Equity Curve | Charts | Controls | Tables | Metrics                 ║
║                                                                        ║
╠════════════════════════════════════════════════════════════════════════╣
║ Status: Ready | Connected: Binance TestNet | Trades: 0 | PnL: $0.00  ║
╚════════════════════════════════════════════════════════════════════════╝
```

---

## 🎛️ CONTROLS REFERENCE

### **HEADER CONTROLS (Always Visible)**

| Element | Function | Hotkey |
|---------|----------|--------|
| **☰ MENU** | Open settings | - |
| **Balance** | Current account balance | - |
| **Symbol Selector** | Choose trading pair | - |
| **Environment** | Switch TestNet/Live | Ctrl+T |
| **Run Backtest** | Start backtest | Ctrl+B |
| **Start Live** | Begin trading | Ctrl+S |
| **Stop Bot** | Emergency stop | Esc |

---

## 📑 TAB REFERENCE

### **Tab 1: 📊 Dashboard**
```
Equity Curve Chart
├─ Real-time balance tracking
├─ Equity growth visualization
└─ Navigation toolbar
```

### **Tab 2: 🎛️ Trading Controls**
```
Trading Interface
├─ Mode selector (Spot/Margin/Futures)
├─ Leverage control (1-10x)
├─ Timeframe selection
├─ Symbol management (Available/Active)
└─ Market info (Gainers/Losers/New)
```

### **Tab 3: ⚙️ Mode Switcher**
```
Live/Test Toggle
├─ Mode selection (Test/Live)
├─ API key input
├─ Mock data toggle
├─ Delay simulation
├─ Connection status
└─ Reconnect button
```

### **Tab 4: 📊 Volatility Analysis**
```
Volatility Metrics
├─ Current volatility (std dev)
├─ Volatility regime (Low/Normal/High/Extreme)
├─ High volatility hours (optimal trading)
├─ Low volatility hours (avoid)
└─ Trading recommendation (0-100 score)
```

### **Tab 5: 🛡️ Risk Controls**
```
Position Sizing
├─ Risk per trade (0.1-5%)
├─ Stop loss ATR multiplier (0.5-4x)
├─ Take profit ratio (1:1 to 5:1)
├─ Max drawdown (5-30%)
├─ Daily loss limit ($)
├─ Trailing stop (%)
├─ Position timeout (hours)
├─ Min volatility (ATR)
└─ Emergency: [Close All] [Cancel All] [Reset]
```

### **Tab 6: 📈 Analytics**
```
Performance Metrics
├─ Return, Win Rate, Sharpe Ratio
├─ Max Drawdown, Profit Factor
├─ Trade history table
│  ├─ Entry/Exit prices
│  ├─ P&L tracking
│  └─ Return percentage
└─ Cumulative P&L chart
```

### **Tab 7: 🤖 ML Monitor**
```
Model Performance
├─ Accuracy (87.5%)
├─ Precision (85.2%)
├─ Recall (88.9%)
├─ F1 Score (0.869)
├─ ROC AUC (0.925)
├─ Predictions table
│  ├─ Time, Prediction, Confidence
│  ├─ Actual vs Predicted
│  └─ Feature importance
└─ Export predictions
```

### **Tab 8: 📉 Backtest**
```
Backtest Configuration
├─ Symbol selector
├─ Lookback period
├─ [Run Backtest] [Export Results]
└─ Results display
   ├─ Total trades, Wins, Losses
   ├─ Return %, Win rate
   ├─ Profit factor
   ├─ Max drawdown
   └─ Sharpe ratio
```

### **Tab 9: ⚙️ Risk Settings** (Advanced)
```
Risk Configuration
├─ Risk per trade (slider)
├─ Stop-loss ATR mult (slider)
├─ Take profit ratio (slider)
├─ Max drawdown (slider)
├─ Daily loss limit (entry)
└─ [Apply Settings]
```

### **Tab 10: 📈 Market Analysis**
```
Volatility Analysis
├─ Current volatility metrics
├─ Garman-Klass estimator
├─ Parkinson volatility
├─ Trading windows
└─ Market recommendation
```

### **Tab 11: 🔍 Market Tracker**
```
Market Data
├─ Top 5 Gainers
├─ Top 5 Losers
├─ New listings
└─ [Refresh]
```

---

## ⌨️ KEYBOARD SHORTCUTS

```
╔═══════════════════════════════════════════════════════════╗
║           KEYBOARD SHORTCUTS REFERENCE                  ║
╠═══════════════════════════════════════════════════════════╣
║  Ctrl+S  → Start/Stop Trading                           ║
║  Ctrl+B  → Run Backtest                                 ║
║  Ctrl+R  → Reconnect to API                             ║
║  Ctrl+T  → Toggle Test/Live Mode                        ║
║  Ctrl+W  → Save Settings                                ║
║  Ctrl+Q  → Quit Application                             ║
║  F5      → Refresh Market Data                          ║
║  F1      → Show Help                                    ║
║  Escape  → STOP ALL TRADING (Emergency)                ║
╚═══════════════════════════════════════════════════════════╝
```

---

## 🎨 THEME COLORS

### **Dark Theme (Default)**
```
Background:     #1a1a1a (Very Dark Gray)
Frame BG:       #262626 (Dark Gray)
Text:           #ffffff (White)
Accent:         #007acc (Blue)
Success:        #4CAF50 (Green)
Warning:        #FF9800 (Orange)
Error:          #f44336 (Red)
```

### **Light Theme**
```
Background:     #ffffff (White)
Frame BG:       #f5f5f5 (Light Gray)
Text:           #000000 (Black)
Accent:         #0078d7 (Blue)
Success:        #107C10 (Green)
Warning:        #FFB900 (Orange)
Error:          #E81123 (Red)
```

---

## 💾 SETTINGS (Hamburger Menu)

### **☰ MENU Button Features**

Click the **☰ MENU** button to access:

**General Tab**
- ☑ Auto-start on launch
- ☑ Auto-reconnect enabled
- Default symbol: [SOLUSDT]
- Theme: [Dark ▼]
- Chart style: [Candle ▼]

**Backtest Tab**
- Initial capital: [$10,000]
- Test period: [30 days]
- Test symbols: [SOLUSDT, BTCUSDT]
- Train/test split: [70/30 slider]
- Tuning trials: [100]

**Alerts Tab**
- ☑ Trade notifications
- ☑ Risk notifications
- ☑ Error notifications
- Custom price alerts: [textarea]

**Data Tab**
- ☑ Cache historical data
- Cache time: [24 hours]
- Data directory: [./data]
- Trades directory: [./trades]

---

## 🚀 TRADING WORKFLOW

### **Step 1: Configure Settings**
```
1. Click ☰ MENU
2. Set risk parameters
3. Configure alerts
4. Click [Save]
```

### **Step 2: Select Trading Mode**
```
1. Click ⚙️ Mode Switcher
2. Choose Test Mode or Live Trading
3. If Live: Enter API key
4. Set delays/mock data as needed
```

### **Step 3: Analyze Markets**
```
1. Click 📊 Volatility tab
2. Check trading score
3. Click 📈 Market Analysis
4. Review volatility regime
```

### **Step 4: Set Risk**
```
1. Click 🛡️ Risk Controls
2. Adjust position size
3. Set stop loss & profit target
4. Configure daily limits
```

### **Step 5: Select Symbols**
```
1. Click 🎛️ Trading Controls
2. Search and select symbols
3. Move to active list (→)
4. Review selected pairs
```

### **Step 6: Start Trading**
```
1. Click [Start Trading] button
2. OR press Ctrl+S
3. Monitor 📈 Analytics tab
4. Watch 🤖 ML Monitor for predictions
```

### **Step 7: Monitor & Adjust**
```
1. Track 📊 Dashboard equity curve
2. Review 📈 Analytics performance
3. Check 🤖 ML accuracy
4. Adjust risk in 🛡️ Risk Controls
```

### **Step 8: Stop Trading**
```
1. Click [Stop Bot] button
2. OR press Escape
3. Review results in 📈 Analytics
4. Export 📉 Backtest results
```

---

## 🆘 EMERGENCY PROCEDURES

### **Quick Stop**
- Press **Escape** key immediately
- All trading stops instantly
- All pending orders remain

### **Close All Positions**
1. Go to **🛡️ Risk Controls** tab
2. Click **[Close All Positions]**
3. Confirm dialog
4. Wait for close confirmation

### **Cancel All Orders**
1. Go to **🛡️ Risk Controls** tab
2. Click **[Cancel All Orders]**
3. Confirm dialog
4. Wait for cancellation

### **Reset to Safe Defaults**
1. Go to **🛡️ Risk Controls** tab
2. Click **[Reset Risk Settings]**
3. Confirm dialog
4. All settings reset to defaults

---

## 📊 COMMON TASKS

### **Change Symbol**
```
Header: [SOLUSDT ▼] → Select new symbol → [Switch]
OR click "Auto-Switch" checkbox for automatic switching
```

### **Run Backtest**
```
Click [Run Backtest] button
OR Press Ctrl+B
Results appear in 📉 Backtest tab
```

### **View Performance**
```
Click 📈 Analytics tab
View all metrics and trade history
Export as CSV if needed
```

### **Check Model Accuracy**
```
Click 🤖 ML Monitor tab
View accuracy, precision, recall, F1
Check ROC curve and confusion matrix
```

### **Analyze Volatility**
```
Click 📊 Volatility Analysis tab
View current volatility and regime
See optimal trading windows
Check trading score
```

### **Switch to Live Trading**
```
1. Click ⚙️ Mode Switcher
2. Select "Live Trading"
3. Enter API key
4. Confirm environment is "LIVE" (Red)
5. Click [Start Live]
⚠️  WARNING: Real money will be used!
```

---

## 🎓 PRO TIPS

1. **Use keyboard shortcuts** - Much faster than clicking
2. **Monitor volatility** - Trade more in high vol windows
3. **Watch ML accuracy** - Only trade when accuracy > 80%
4. **Set tight risk limits** - Preserve capital
5. **Use trailing stops** - Lock in profits automatically
6. **Run backtests** - Before live trading
7. **Review analytics** - Daily performance analysis
8. **Adjust on weekends** - When markets are calm

---

## 📱 WINDOW SIZE

Recommended: **1400x900** or larger

For mobile/small screens: GUI is scrollable and responsive

---

## 🔧 TROUBLESHOOTING

| Issue | Solution |
|-------|----------|
| **GUI won't load** | Check Python 3.8+ installed |
| **No charts** | Install matplotlib: `pip install matplotlib` |
| **ML Monitor empty** | Run backtest or trades first |
| **Settings not saved** | Check file permissions on gui_settings.json |
| **API errors** | Check API keys in Mode Switcher |
| **Slow updates** | Reduce chart update interval in settings |

---

## 📞 HELP & SUPPORT

Press **F1** to open help window

Or refer to:
- README.md - Project overview
- QUICKSTART.md - Getting started
- SETUP_AND_RUN.md - Installation guide
- GUI_ENHANCEMENT_COMPLETE.md - This GUI documentation

---

**Happy Trading! 🚀💰**

*Last Updated: 2025-11-05*
*GUI Version: 2.0 - Complete*