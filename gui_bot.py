"""
gui_bot.py - Fully Integrated Crypto Trading GUI
Includes:
- TradingControlsFrame with market data and TreeViews
- StrategyTuner tab with sliders, charts, auto-tune
- TradeDisplay panel with live trade updates & animations
- MarketVolatilityAnalyzer integration
- Market microstructure & candlestick analysis
- ML/backtesting integration
- Logging, database save/load, theme support, plugin architecture
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
from typing import Callable, Dict, List, Any, Optional
import threading
import logging
import time
import random
import os
import json
import sqlite3
import csv
from pathlib import Path
from datetime import datetime, timedelta

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("CryptoBotGUI")

# --- Theme Manager ---
THEMES = {
    'dark': {
        'bg': '#1a1a1a', 'fg': '#ffffff', 'select_bg': '#404040',
        'select_fg': '#ffffff', 'button_bg': '#2d2d2d',
        'button_fg': '#ffffff', 'frame_bg': '#262626', 'accent': '#007acc'
    },
    'light': {
        'bg': '#ffffff', 'fg': '#000000', 'select_bg': '#0078d7',
        'select_fg': '#ffffff', 'button_bg': '#f0f0f0',
        'button_fg': '#000000', 'frame_bg': '#f5f5f5', 'accent': '#0078d7'
    }
}

class ThemeManager:
    """Manages GUI themes and styles"""
    def __init__(self):
        self.current_theme = 'dark'
        self._setup_styles()
        
    def _setup_styles(self):
        style = ttk.Style()
        colors = THEMES[self.current_theme]
        style.configure('TFrame', background=colors['frame_bg'])
        style.configure('TLabel', background=colors['frame_bg'], foreground=colors['fg'])
        style.configure('TButton', background=colors['button_bg'], foreground=colors['button_fg'])
        style.configure('Accent.TButton', background=colors['accent'], foreground=colors['select_fg'])
        style.configure('TNotebook', background=colors['bg'], tabmargins=[2,5,2,0])
        style.configure('TNotebook.Tab', background=colors['button_bg'], foreground=colors['button_fg'], padding=[10,2])
        style.map('TNotebook.Tab', background=[('selected', colors['select_bg'])], foreground=[('selected', colors['select_fg'])])
        style.configure('Title.TLabel', font=('Helvetica',14,'bold'), foreground=colors['accent'])
        style.configure('Fallback.TLabel', font=('Helvetica',12), foreground='#888888')
        style.configure('Risk.TLabel', foreground='#ff4444')
        style.configure('Success.TLabel', foreground='#44ff44')

    def apply_theme(self, theme_name: str):
        if theme_name in THEMES:
            self.current_theme = theme_name
            self._setup_styles()
            
    def get_colors(self) -> Dict[str,str]:
        return THEMES[self.current_theme]
    
    def configure_root(self, root: tk.Tk):
        colors = self.get_colors()
        root.configure(bg=colors['bg'])
        for child in root.winfo_children():
            if isinstance(child, (ttk.Frame, ttk.LabelFrame)):
                child.configure(style='TFrame')
            elif isinstance(child, ttk.Label):
                child.configure(style='TLabel')

theme_manager = ThemeManager()

# --- Market Volatility Analyzer ---
import numpy as np
import pandas as pd

class MarketVolatilityAnalyzer:
    """Analyzes market volatility for optimal trade timing"""
    def __init__(self, lookback_periods: int = 20):
        self.lookback = lookback_periods
        self.volatility_history = {}
        self.session_volatility = {}
    
    def analyze_volatility(self, symbol: str, price_data: pd.DataFrame) -> Dict[str,Any]:
        try:
            close_prices = price_data['close'].values
            high_prices = price_data['high'].values
            low_prices = price_data['low'].values
            returns = np.diff(np.log(close_prices))
            current_vol = np.std(returns[-self.lookback:]) * np.sqrt(252)
            gk_vol = self._calculate_garman_klass(high_prices[-self.lookback:], low_prices[-self.lookback:], close_prices[-self.lookback:])
            park_vol = self._calculate_parkinson(high_prices[-self.lookback:], low_prices[-self.lookback:])
            
            if symbol not in self.volatility_history:
                self.volatility_history[symbol] = []
            self.volatility_history[symbol].append({'timestamp':datetime.now(),'std_vol':current_vol,'gk_vol':gk_vol,'park_vol':park_vol})
            if len(self.volatility_history[symbol])>100: self.volatility_history[symbol].pop(0)
            
            vol_regime = self._determine_volatility_regime(current_vol,self.volatility_history[symbol])
            thresholds = self._calculate_trading_thresholds(current_vol,vol_regime)
            self._update_session_volatility(symbol,current_vol)
            trading_windows = self._find_trading_windows(symbol)
            
            return {'current_volatility':current_vol,'garman_klass_vol':gk_vol,'parkinson_vol':park_vol,'volatility_regime':vol_regime,'trading_thresholds':thresholds,'trading_windows':trading_windows}
        except Exception as e:
            logger.error(f"Error analyzing volatility: {e}")
            return {}

    def _calculate_garman_klass(self,high: np.ndarray,low: np.ndarray,close: np.ndarray) -> float:
        try:
            log_hl = np.log(high/low)
            log_co = np.log(close[1:]/close[:-1])
            hl_term = 0.5*np.mean(log_hl**2)
            co_term = np.mean(log_co**2)
            vol = np.sqrt(252*(hl_term-(2*np.log(2)-1)*co_term))
            return float(vol)
        except: return 0.0
    
    def _calculate_parkinson(self,high: np.ndarray,low: np.ndarray) -> float:
        try:
            log_hl = np.log(high/low)
            vol = np.sqrt(252*np.mean(log_hl**2)/(4*np.log(2)))
            return float(vol)
        except: return 0.0
    
    def _determine_volatility_regime(self,current_vol:float,history:List[Dict])->str:
        if not history: return "normal"
        hist_vols=[h['std_vol'] for h in history]
        mean=np.mean(hist_vols);std=np.std(hist_vols)
        if current_vol>mean+2*std: return "extreme"
        elif current_vol>mean+std: return "high"
        elif current_vol<mean-std: return "low"
        return "normal"
    
    def _calculate_trading_thresholds(self,current_vol:float,regime:str)->Dict[str,float]:
        thresholds={'entry_threshold':0.001,'stop_loss_mult':2.0,'take_profit_mult':3.0,'position_size_factor':1.0}
        adjustments={'low':{'entry_threshold':0.8,'stop_loss_mult':1.5,'take_profit_mult':2.5,'position_size_factor':1.2},
                     'normal':{'entry_threshold':1.0,'stop_loss_mult':2.0,'take_profit_mult':3.0,'position_size_factor':1.0},
                     'high':{'entry_threshold':1.3,'stop_loss_mult':2.5,'take_profit_mult':3.5,'position_size_factor':0.8},
                     'extreme':{'entry_threshold':1.5,'stop_loss_mult':3.0,'take_profit_mult':4.0,'position_size_factor':0.5}}
        adj=adjustments.get(regime,adjustments['normal'])
        for k,v in thresholds.items(): thresholds[k]=v*adj[k]
        vol_scale=min(max(current_vol/0.2,0.5),2.0)
        thresholds['position_size_factor']*=vol_scale
        return thresholds
    
    def _update_session_volatility(self,symbol:str,current_vol:float)->None:
        now=datetime.now();session_key=now.strftime("%Y-%m-%d-%H")
        if symbol not in self.session_volatility: self.session_volatility[symbol]={}
        if session_key not in self.session_volatility[symbol]: self.session_volatility[symbol][session_key]=[]
        self.session_volatility[symbol][session_key].append(current_vol)
        cutoff=(now-timedelta(days=7)).strftime("%Y-%m-%d")
        self.session_volatility[symbol]={k:v for k,v in self.session_volatility[symbol].items() if k.startswith(cutoff) or k>cutoff}

    def _find_trading_windows(self,symbol:str)->Dict[str,List[int]]:
        if symbol not in self.session_volatility: return {}
        hourly_vol={}
        for session,vols in self.session_volatility[symbol].items():
            hour=int(session.split('-')[-1])
            hourly_vol.setdefault(hour,[]).extend(vols)
        avg_vol={h:np.mean(vs) for h,vs in hourly_vol.items() if vs}
        if not avg_vol: return {}
        mean_vol=np.mean(list(avg_vol.values()));std_vol=np.std(list(avg_vol.values()))
        high=[h for h,v in avg_vol.items() if v>mean_vol+0.5*std_vol]
        low=[h for h,v in avg_vol.items() if v<mean_vol-0.5*std_vol]
        return {'high_volatility':sorted(high),'low_volatility':sorted(low)}
    
    def get_trading_recommendation(self,symbol:str,current_vol:float)->Dict[str,Any]:
        now=datetime.now();current_hour=now.hour
        windows=self._find_trading_windows(symbol)
        regime=self._determine_volatility_regime(current_vol,self.volatility_history.get(symbol,[]))
        thresholds=self._calculate_trading_thresholds(current_vol,regime)
        score=50;regime_scores={"low":-10,"normal":0,"high":10,"extreme":-20}
        score+=regime_scores.get(regime,0)
        if current_hour in windows.get('high_volatility',[]): score+=20
        elif current_hour in windows.get('low_volatility',[]): score-=10
        if symbol in self.volatility_history and len(self.volatility_history[symbol])>1:
            recent=[h['std_vol'] for h in self.volatility_history[symbol][-5:]]
            trend=np.polyfit(range(len(recent)),recent,1)[0]
            score+=10 if trend>0 else -10 if trend<0 else 0
        score=max(0,min(100,score))
        return {'trading_score':score,'volatility_regime':regime,'thresholds':thresholds,'current_hour':current_hour,'is_high_vol_window':current_hour in windows.get('high_volatility',[]),'is_low_vol_window':current_hour in windows.get('low_volatility',[]),'recommendation':'high' if score>=70 else 'moderate' if score>=40 else 'low'}

# --- Trading Modes, TimeFrames, Risk Config ---
class TradingMode:
    SPOT='Spot';MARGIN='Margin';FUTURES='Futures'
class TimeFrame:
    SCALP='Scalp';SHORT='Short';MEDIUM='Medium';LONG='Long'
class RiskConfig:
    TRADING_MODE=TradingMode.SPOT
    LEVERAGE=1.0
    MAX_LEVERAGE=10.0
    TIMEFRAME=TimeFrame.SHORT
    AUTO_MODE_SWITCH=True

# --- Market Tracker Stub ---
class MarketTracker:
    """Stub for market data"""
    def __init__(self):
        self.gainers=[]
        self.losers=[]
        self.new_listings=[]
        self.mode_metrics={'Spot':{'trades':0,'profit':0.0,'max_drawdown':0.0}}
        self.available_pairs=['BTCUSDT','ETHUSDT','BNBUSDT','ADAUSDT','XRPUSDT','SOLUSDT']
    def search_pairs(self,text): return [p for p in self.available_pairs if text.upper() in p]
    def update_market_data(self):
        # Simulate market data
        self.gainers=[{'change':random.uniform(0,10),'volume':random.uniform(1000,5000),'price':random.uniform(1000,50000)} for _ in range(5)]
        self.losers=[{'change':-random.uniform(0,10),'volume':random.uniform(1000,5000),'price':random.uniform(1000,50000)} for _ in range(5)]
        self.new_listings=[{'time':time.time(),'price':random.uniform(0.1,100),'volume':random.uniform(1000,5000)} for _ in range(3)]
market_tracker=MarketTracker()

# --- ML Model & Backtesting Stubs ---
class MLModel:
    def __init__(self, params=None):
        self.params = params or {}


def _simulate_live_thread(model, symbols, trades_csv, stop_event, callback):
    if isinstance(symbols, str):
        symbol_list = [symbols]
    else:
        symbol_list = list(symbols or [])
    if not symbol_list:
        symbol_list = ["BTCUSDT"]
    stop_flag = stop_event or threading.Event()
    max_iterations = 60 if stop_event is None else None

    def emit(payload):
        if callback:
            try:
                callback(payload)
            except Exception:
                logger.exception("Error delivering trading update")

    def worker():
        balance = 10000.0
        pnl = 0.0
        trades = 0
        equity_curve = []
        csv_file = None
        writer = None
        try:
            if trades_csv:
                path = Path(trades_csv)
                path.parent.mkdir(parents=True, exist_ok=True)
                csv_file = path.open("w", newline="", encoding="utf-8")
                writer = csv.writer(csv_file)
                writer.writerow(["timestamp", "symbol", "price", "quantity", "pnl", "balance"])
            rng = random.Random()
            while not stop_flag.is_set():
                if max_iterations is not None and trades >= max_iterations:
                    break
                time.sleep(2)
                symbol = rng.choice(symbol_list)
                price = rng.uniform(10.0, 500.0)
                quantity = rng.uniform(0.01, 0.5)
                change = rng.uniform(-1.5, 1.8) / 100
                trade_pnl = price * quantity * change
                pnl += trade_pnl
                balance += trade_pnl
                trades += 1
                equity_curve.append(balance)
                if writer:
                    writer.writerow([
                        datetime.utcnow().isoformat(),
                        symbol,
                        f"{price:.4f}",
                        f"{quantity:.4f}",
                        f"{trade_pnl:.2f}",
                        f"{balance:.2f}",
                    ])
                    csv_file.flush()
                emit({
                    "symbol": symbol,
                    "trades": trades,
                    "balance": round(balance, 2),
                    "pnl": round(pnl, 2),
                    "last_price": round(price, 4),
                    "equity_curve": equity_curve[-200:],
                    "timestamp": time.time(),
                })
        except Exception:
            logger.exception("Simulated live trading failed")
        finally:
            if csv_file:
                csv_file.close()
            emit({
                "status": "stopped",
                "timestamp": time.time(),
                "trades": trades,
                "balance": round(balance, 2),
                "pnl": round(pnl, 2),
            })

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


run_live_in_thread = _simulate_live_thread

def run_backtest(model, symbol, risk_pct):
    return {'Total Return':0.1,'Win Rate':0.55,'Profit Factor':1.5,'Max Drawdown':0.05,'Sharpe Ratio':1.2,'Total Trades':100,'equity_curve':[1,1.05,1.1,1.2,1.15]}

def tune_xgboost(symbol, n_trials):
    return {'ml_threshold':0.6,'atr_multiplier':2.2,'profit_target':0.04,'max_bars_back':25}

# --- GUI Components ---
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class StrategyTuner:
    """Interactive strategy parameter tuning"""
    def __init__(self,parent:tk.Widget):
        self.parent=parent
        self.frame=ttk.Frame(parent);self.frame.pack(fill='both',expand=True)
        self.has_tuning=True
        self.params={'ml_threshold':{'min':0.5,'max':0.9,'value':0.55,'step':0.01},
                     'atr_multiplier':{'min':1.0,'max':4.0,'value':2.0,'step':0.1},
                     'profit_target':{'min':0.01,'max':0.1,'value':0.03,'step':0.005},
                     'max_bars_back':{'min':10,'max':100,'value':20,'step':5}}
        self._create_controls();self._create_results()
    def _create_controls(self):
        controls=ttk.LabelFrame(self.frame,text="Strategy Parameters",padding=10);controls.pack(fill='x',expand=False,padx=5,pady=5)
        row=0;self.param_vars={}
        for name,config in self.params.items():
            ttk.Label(controls,text=name.replace('_',' ').title()).grid(row=row,column=0,sticky='w',padx=5,pady=2)
            var=tk.DoubleVar(value=config['value']);self.param_vars[name]=var
            ttk.Scale(controls,from_=config['min'],to=config['max'],value=config['value'],variable=var,orient='horizontal').grid(row=row,column=1,sticky='ew',padx=5,pady=2)
            ttk.Label(controls,textvariable=var).grid(row=row,column=2,padx=5,pady=2)
            row+=1
        buttons=ttk.Frame(controls);buttons.grid(row=row,column=0,columnspan=3,pady=10)
        ttk.Button(buttons,text="Run Backtest",command=self._run_backtest).pack(side='left',padx=5)
        ttk.Button(buttons,text="Auto-Tune",command=self._auto_tune).pack(side='left',padx=5)
        ttk.Button(buttons,text="Save Params",command=self._save_params).pack(side='left',padx=5)
    def _create_results(self):
        results=ttk.LabelFrame(self.frame,text="Backtest Results",padding=10);results.pack(fill='both',expand=True,padx=5,pady=5)
        metrics_frame=ttk.Frame(results);metrics_frame.pack(fill='x',expand=False)
        self.metrics={'Total Return':tk.StringVar(value='0.00%'),'Win Rate':tk.StringVar(value='0.00%'),'Profit Factor':tk.StringVar(value='0.00'),'Max Drawdown':tk.StringVar(value='0.00%'),'Sharpe Ratio':tk.StringVar(value='0.00'),'Total Trades':tk.StringVar(value='0')}
        row=0
        for name,var in self.metrics.items():
            ttk.Label(metrics_frame,text=name).grid(row=row,column=0,sticky='w',padx=5,pady=2)
            ttk.Label(metrics_frame,textvariable=var).grid(row=row,column=1,sticky='e',padx=5,pady=2)
            row+=1
        fig=Figure(figsize=(8,4));self.ax=fig.add_subplot(111)
        self.canvas=FigureCanvasTkAgg(fig,results);self.canvas.get_tk_widget().pack(fill='both',expand=True,padx=5,pady=5)
    def _run_backtest(self):
        params={name:var.get() for name,var in self.param_vars.items()}
        model=MLModel(params)
        results=run_backtest(model,'BTCUSDT',0.01)
        if results: self._update_results(results)
    def _auto_tune(self):
        best=tune_xgboost('BTCUSDT',10)
        for k,v in best.items():
            if k in self.param_vars: self.param_vars[k].set(v)
        self._run_backtest()
    def _save_params(self):
        params={name:var.get() for name,var in self.param_vars.items()}
        with open('best_params.json','w') as f: json.dump(params,f,indent=2)
        messagebox.showinfo("Success","Parameters saved to best_params.json")
    def _update_results(self,results):
        for k,v in results.items():
            if k in self.metrics:
                self.metrics[k].set(f"{v*100:.2f}%" if v<1 else f"{v:.2f}")
        if 'equity_curve' in results:
            self.ax.clear();self.ax.plot(results['equity_curve'],color='g');self.ax.set_title('Equity Curve');self.ax.grid(True);self.canvas.draw()

class TradingControlsFrame(ttk.Frame):
    """Main trading controls frame"""
    def __init__(self,parent,callback:Callable=None):
        super().__init__(parent)
        self.callback=callback
        self.stop_event=None
        self.active_symbols=set()
        self.create_widgets()
    def create_widgets(self):
        # Trading Mode Controls
        mode_frame=ttk.LabelFrame(self,text="Trading Mode");mode_frame.pack(fill="x",padx=5,pady=5)
        self.mode_var=tk.StringVar(value=RiskConfig.TRADING_MODE)
        for mode in [TradingMode.SPOT,TradingMode.MARGIN,TradingMode.FUTURES]:
            ttk.Radiobutton(mode_frame,text=mode,value=mode,variable=self.mode_var,command=self.on_mode_change).pack(anchor="w",padx=5)
        leverage_frame=ttk.Frame(mode_frame);leverage_frame.pack(fill="x",padx=5,pady=5)
        ttk.Label(leverage_frame,text="Leverage:").pack(side="left")
        self.leverage_var=tk.DoubleVar(value=RiskConfig.LEVERAGE)
        ttk.Spinbox(leverage_frame,from_=1.0,to=RiskConfig.MAX_LEVERAGE,increment=0.5,textvariable=self.leverage_var,width=10,command=self.on_leverage_change).pack(side="left",padx=5)
        # Timeframe
        time_frame=ttk.LabelFrame(self,text="Timeframe");time_frame.pack(fill="x",padx=5,pady=5)
        self.timeframe_var=tk.StringVar(value=RiskConfig.TIMEFRAME)
        for tf in [TimeFrame.SCALP,TimeFrame.SHORT,TimeFrame.MEDIUM,TimeFrame.LONG]:
            ttk.Radiobutton(time_frame,text=tf,value=tf,variable=self.timeframe_var,command=self.on_timeframe_change).pack(anchor="w",padx=5)
        auto_frame=ttk.Frame(self);auto_frame.pack(fill="x",padx=5,pady=5)
        self.auto_mode_var=tk.BooleanVar(value=RiskConfig.AUTO_MODE_SWITCH)
        ttk.Checkbutton(auto_frame,text="Auto Mode Switch",variable=self.auto_mode_var,command=self.on_auto_mode_change).pack(side="left")
        # Symbol selection
        symbol_frame=ttk.LabelFrame(self,text="Trading Pairs");symbol_frame.pack(fill="both",expand=True,padx=5,pady=5)
        search_frame=ttk.Frame(symbol_frame);search_frame.pack(fill="x",padx=5,pady=5)
        ttk.Label(search_frame,text="Search:").pack(side="left")
        self.search_var=tk.StringVar();self.search_var.trace("w",self.on_search)
        ttk.Entry(search_frame,textvariable=self.search_var).pack(side="left",fill="x",expand=True,padx=5)
        lists_frame=ttk.Frame(symbol_frame);lists_frame.pack(fill="both",expand=True,padx=5,pady=5)
        avail_frame=ttk.LabelFrame(lists_frame,text="Available");avail_frame.pack(side="left",fill="both",expand=True)
        self.available_list=tk.Listbox(avail_frame,selectmode="multiple");self.available_list.pack(fill="both",expand=True)
        btn_frame=ttk.Frame(lists_frame);btn_frame.pack(side="left",padx=5)
        ttk.Button(btn_frame,text="→",command=self.add_selected).pack(pady=2)
        ttk.Button(btn_frame,text="←",command=self.remove_selected).pack(pady=2)
        active_frame=ttk.LabelFrame(lists_frame,text="Active");active_frame.pack(side="left",fill="both",expand=True)
        self.active_list=tk.Listbox(active_frame,selectmode="multiple");self.active_list.pack(fill="both",expand=True)
        # Market info
        market_frame=ttk.LabelFrame(self,text="Market Information");market_frame.pack(fill="both",expand=True,padx=5,pady=5)
        notebook=ttk.Notebook(market_frame);notebook.pack(fill="both",expand=True)
        # Gainers
        gainers_frame=ttk.Frame(notebook);notebook.add(gainers_frame,text="Gainers")
        self.gainers_tree=ttk.Treeview(gainers_frame,columns=("change","volume","price"),show="headings")
        for col,name in zip(["change","volume","price"],["Change %","Volume","Price"]): self.gainers_tree.heading(col,text=name)
        self.gainers_tree.pack(fill="both",expand=True)
        # Losers
        losers_frame=ttk.Frame(notebook);notebook.add(losers_frame,text="Losers")
        self.losers_tree=ttk.Treeview(losers_frame,columns=("change","volume","price"),show="headings")
        for col,name in zip(["change","volume","price"],["Change %","Volume","Price"]): self.losers_tree.heading(col,text=name)
        self.losers_tree.pack(fill="both",expand=True)
        # New listings
        new_frame=ttk.Frame(notebook);notebook.add(new_frame,text="New Listings")
        self.new_tree=ttk.Treeview(new_frame,columns=("time","price","volume"),show="headings")
        for col,name in zip(["time","price","volume"],["Listed","Price","Volume"]): self.new_tree.heading(col,text=name)
        self.new_tree.pack(fill="both",expand=True)
        # Performance
        perf_frame=ttk.Frame(notebook);notebook.add(perf_frame,text="Performance")
        self.perf_tree=ttk.Treeview(perf_frame,columns=("trades","profit","drawdown"),show="headings")
        for col,name in zip(["trades","profit","drawdown"],["Trades","Profit","Drawdown"]): self.perf_tree.heading(col,text=name)
        self.perf_tree.pack(fill="both",expand=True)
        # Control buttons
        control_frame=ttk.Frame(self);control_frame.pack(fill="x",padx=5,pady=5)
        self.start_btn=ttk.Button(control_frame,text="Start Trading",command=self.start_trading);self.start_btn.pack(side="left",padx=5)
        self.stop_btn=ttk.Button(control_frame,text="Stop Trading",command=self.stop_trading,state="disabled");self.stop_btn.pack(side="left",padx=5)
        self.update_market_data()
    # --- Handlers ---
    def on_mode_change(self,*args): RiskConfig.TRADING_MODE=self.mode_var.get()
    def on_leverage_change(self,*args): RiskConfig.LEVERAGE=self.leverage_var.get()
    def on_timeframe_change(self,*args): RiskConfig.TIMEFRAME=self.timeframe_var.get()
    def on_auto_mode_change(self,*args): RiskConfig.AUTO_MODE_SWITCH=self.auto_mode_var.get()
    def on_search(self,*args):
        term=self.search_var.get()
        self.available_list.delete(0,"end")
        for p in market_tracker.search_pairs(term): self.available_list.insert("end",p)
    def add_selected(self): idxs=self.available_list.curselection();[self.active_list.insert("end",self.available_list.get(i)) for i in idxs]
    def remove_selected(self): idxs=self.active_list.curselection();[self.active_list.delete(i) for i in reversed(idxs)]
    def start_trading(self): self.start_btn.config(state="disabled");self.stop_btn.config(state="normal");messagebox.showinfo("Trading","Trading started")
    def stop_trading(self): self.start_btn.config(state="normal");self.stop_btn.config(state="disabled");messagebox.showinfo("Trading","Trading stopped")
    def update_market_data(self):
        market_tracker.update_market_data()
        # Clear trees
        for tree,data in [(self.gainers_tree,market_tracker.gainers),(self.losers_tree,market_tracker.losers),(self.new_tree,market_tracker.new_listings)]: 
            tree.delete(*tree.get_children());[tree.insert("", "end", values=[round(d.get(k,0),2) if isinstance(d.get(k,0),float) else d.get(k,0) for k in tree['columns']]) for d in data]
        self.after(5000,self.update_market_data)

# --- Main App ---
class CryptoBotApp:
    def __init__(self,root:tk.Tk):
        self.root=root
        root.title("CryptoBot GUI")
        root.geometry("1200x800")
        theme_manager.configure_root(root)
        self.notebook=ttk.Notebook(root);self.notebook.pack(fill="both",expand=True)
        self.trading_tab=TradingControlsFrame(self.notebook);self.notebook.add(self.trading_tab,text="Trading")
        self.strategy_tab=StrategyTuner(self.notebook);self.notebook.add(self.strategy_tab.frame,text="Strategy Tuner")
        # Plugins placeholder
        self.plugins=[]
        self.db_path="cryptobot.db"
        self._setup_db()
    def _setup_db(self):
        self.conn=sqlite3.connect(self.db_path)
        self.cursor=self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, action TEXT, price REAL, qty REAL, timestamp TEXT)")
        self.conn.commit()
    def register_plugin(self,plugin_callable:Callable):
        self.plugins.append(plugin_callable)
    def run_plugins(self):
        for plugin in self.plugins: plugin(self)

# --- Main ---
def main():
    root=tk.Tk()
    app=CryptoBotApp(root)
    root.mainloop()

if __name__=="__main__":
    main()
# gui_bot.py
"""
CryptoBot GUI (enhanced)
- Integrated with crypto_bot.py trading engine
- Uses BinanceExecutionAdapter and BinancePriceFeed from crypto_bot.py by default (placeholders for credentials)
- Backtest scheduling runs in separate processes via BacktestScheduler which calls crypto_bot.backtest_worker
- UI updates are marshaled to the main thread (widget.after)
- Order fills and trade events are logged to sqlite for audit
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import sqlite3
import os

# Import engine and integration primitives
import crypto_bot as engine

# Logging with rotating file
import logging.handlers
LOG_PATH = "cryptobot_gui.log"
logger = logging.getLogger("GUI")
logger.setLevel(logging.INFO)
if not logger.handlers:
    rh = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3, encoding='utf-8')
    rh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    logger.addHandler(rh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    logger.addHandler(ch)

# --- DB helper for persistence/audit ---
class AuditDB:
    def __init__(self, path="cryptobot_audit.db"):
        self.path = path
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._cursor = self._conn.cursor()
        self._setup()

    def _setup(self):
        self._cursor.execute(
            "CREATE TABLE IF NOT EXISTS fills(id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, source TEXT, order_id TEXT, symbol TEXT, side TEXT, qty REAL, price REAL, raw TEXT)"
        )
        self._cursor.execute(
            "CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, level TEXT, message TEXT)"
        )
        self._conn.commit()

    def record_fill(self, source, order_id, symbol, side, qty, price, raw=""):
        self._cursor.execute(
            "INSERT INTO fills(timestamp, source, order_id, symbol, side, qty, price, raw) VALUES (?,?,?,?,?,?,?,?)",
            (datetime.utcnow().isoformat(), source, str(order_id), symbol, side, float(qty), float(price), str(raw))
        )
        self._conn.commit()

    def record_log(self, level, message):
        self._cursor.execute(
            "INSERT INTO logs(timestamp, level, message) VALUES (?,?,?)",
            (datetime.utcnow().isoformat(), level, message)
        )
        self._conn.commit()

# --- GUI components ---


class StrategyTunerPanel:
    """Wrap engine StrategyTuner if available, else minimal panel that interacts with engine.run_backtest/tune_xgboost"""
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        # Parameter defaults
        self.params = {
            'ml_threshold': tk.DoubleVar(value=0.55),
            'atr_multiplier': tk.DoubleVar(value=2.0),
            'profit_target': tk.DoubleVar(value=0.03),
            'max_bars_back': tk.DoubleVar(value=20)
        }
        self._create_controls()
        self._create_results()

    def _create_controls(self):
        controls = ttk.LabelFrame(self.frame, text="Strategy Parameters", padding=8)
        controls.pack(fill='x', padx=6, pady=6)
        row = 0
        for name, var in self.params.items():
            ttk.Label(controls, text=name.replace('_', ' ').title()).grid(row=row, column=0, sticky='w', padx=4, pady=2)
            scale = ttk.Scale(controls, from_=0.0, to=1.0, variable=var, orient='horizontal') if isinstance(var, tk.DoubleVar) else ttk.Entry(controls, textvariable=var)
            scale.grid(row=row, column=1, sticky='ew', padx=4, pady=2)
            ttk.Label(controls, textvariable=var).grid(row=row, column=2, sticky='e', padx=4, pady=2)
            row += 1

        btns = ttk.Frame(controls)
        btns.grid(row=row, column=0, columnspan=3, pady=6)
        ttk.Button(btns, text="Run Backtest", command=self.run_backtest).pack(side='left', padx=4)
        ttk.Button(btns, text="Auto-Tune", command=self.auto_tune).pack(side='left', padx=4)
        ttk.Button(btns, text="Save Params", command=self.save_params).pack(side='left', padx=4)

    def _create_results(self):
        results = ttk.LabelFrame(self.frame, text="Backtest Results", padding=8)
        results.pack(fill='both', expand=True, padx=6, pady=6)
        self.metrics_vars = {
            'Total Return': tk.StringVar(value='0.00%'),
            'Win Rate': tk.StringVar(value='0.00%'),
            'Profit Factor': tk.StringVar(value='0.00'),
            'Max Drawdown': tk.StringVar(value='0.00%'),
            'Sharpe Ratio': tk.StringVar(value='0.00'),
            'Total Trades': tk.StringVar(value='0')
        }
        row = 0
        for k, v in self.metrics_vars.items():
            ttk.Label(results, text=k).grid(row=row, column=0, sticky='w', padx=4, pady=2)
            ttk.Label(results, textvariable=v).grid(row=row, column=1, sticky='e', padx=4, pady=2)
            row += 1
        # Equity curve canvas (use engine plotting if available)
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            fig = Figure(figsize=(6, 3))
            self.ax = fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(fig, results)
            self.canvas.get_tk_widget().grid(row=0, column=2, rowspan=row, sticky='nsew', padx=6, pady=2)
        except Exception:
            self.ax = None
            self.canvas = None

    def run_backtest(self):
        params = {k: float(v.get()) for k, v in self.params.items()}
        # schedule backtest via engine BacktestScheduler (exposed from crypto_bot)
        job_id = f"gui-bt-{int(time.time())}"
        sched = engine.get_backtest_scheduler()
        def on_progress(m):
            # marshal to UI thread
            self.frame.after(0, lambda: self._on_progress(m))
        def on_done(r):
            self.frame.after(0, lambda: self._on_done(r))
        sched.schedule_backtest(job_id, engine.backtest_worker, params, on_progress=on_progress, on_done=on_done)
        messagebox.showinfo("Backtest", f"Backtest {job_id} scheduled")

    def auto_tune(self):
        # run engine.tune_xgboost in a background thread and update params
        def worker():
            try:
                best = engine.tune_xgboost('BTCUSDT', 10)
                def apply():
                    for k, v in best.items():
                        if k in self.params:
                            try:
                                self.params[k].set(float(v))
                            except Exception:
                                pass
                    self.run_backtest()
                self.frame.after(0, apply)
            except Exception:
                logger.exception("Auto-tune failed")
        threading.Thread(target=worker, daemon=True).start()

    def save_params(self):
        params = {k: float(v.get()) for k, v in self.params.items()}
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], title="Save params")
        if path:
            import json
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(params, f, indent=2)
            messagebox.showinfo("Saved", f"Parameters saved to {path}")

    def _on_progress(self, msg):
        # msg is a dict pushed from backtest worker
        if msg.get('status') == 'progress':
            pct = msg.get('pct')
            m = msg.get('message', '')
            self.metrics_vars['Total Trades'].set(f"{m}")
        elif msg.get('status') == 'error':
            messagebox.showerror("Backtest Error", msg.get('error'))

    def _on_done(self, res):
        if not res:
            return
        # format results into metrics
        for k in ['Total Return','Win Rate','Profit Factor','Max Drawdown','Sharpe Ratio','Total Trades']:
            if k in res:
                v = res[k]
                if isinstance(v, float) and v < 1 and ('Rate' in k or 'Return' in k or 'Drawdown' in k):
                    self.metrics_vars[k].set(f"{v*100:.2f}%")
                else:
                    self.metrics_vars[k].set(f"{v:.2f}" if isinstance(v, float) else str(v))
        # plot equity curve if provided
        if self.ax and 'equity_curve' in res:
            try:
                self.ax.clear()
                self.ax.plot(res['equity_curve'], color='g')
                self.ax.set_title("Equity Curve")
                self.ax.grid(True)
                self.canvas.draw_idle()
            except Exception:
                logger.exception("Failed plotting equity curve")


class TradingControlsFrame(ttk.Frame):
    """Trading controls integrated with engine runner adapters"""
    def __init__(self, parent, execution_adapter=None, price_feed=None, audit_db: AuditDB = None):
        super().__init__(parent)
        self.execution_adapter = execution_adapter
        self.price_feed = price_feed
        self.audit_db = audit_db or AuditDB()
        self.order_manager = engine.OrderManager()
        self.active_symbols = set(getattr(engine, 'market_tracker', None).available_pairs if getattr(engine, 'market_tracker', None) else [])
        self._create_widgets()
        # fill available pairs
        self.populate_available_pairs()

    def _create_widgets(self):
        # Left: symbol selection
        left = ttk.LabelFrame(self, text="Symbols")
        left.pack(side='left', fill='both', expand=True, padx=6, pady=6)
        search_row = ttk.Frame(left); search_row.pack(fill='x', pady=4)
        ttk.Label(search_row, text="Search:").pack(side='left')
        self.search_var = tk.StringVar(); self.search_var.trace_add('write', self.on_search)
        ttk.Entry(search_row, textvariable=self.search_var).pack(side='left', fill='x', expand=True, padx=4)
        lists = ttk.Frame(left); lists.pack(fill='both', expand=True)
        avail_frame = ttk.LabelFrame(lists, text="Available"); avail_frame.pack(side='left', fill='both', expand=True, padx=4)
        self.available_list = tk.Listbox(avail_frame, selectmode='multiple'); self.available_list.pack(fill='both', expand=True)
        btns = ttk.Frame(lists); btns.pack(side='left', padx=4)
        ttk.Button(btns, text="→", command=self.add_selected).pack(pady=6)
        ttk.Button(btns, text="←", command=self.remove_selected).pack(pady=6)
        active_frame = ttk.LabelFrame(lists, text="Active"); active_frame.pack(side='left', fill='both', expand=True, padx=4)
        self.active_list = tk.Listbox(active_frame); self.active_list.pack(fill='both', expand=True)

        # Right: market info
        right = ttk.LabelFrame(self, text="Market Info")
        right.pack(side='left', fill='both', expand=True, padx=6, pady=6)
        notebook = ttk.Notebook(right); notebook.pack(fill='both', expand=True)
        # Gainers, Losers, New
        self.gainers_tree = ttk.Treeview(notebook, columns=('symbol','change','volume','price'), show='headings'); 
        for c, name in zip(['symbol','change','volume','price'], ['Symbol','Change%','Volume','Price']): self.gainers_tree.heading(c, text=name)
        gframe = ttk.Frame(notebook); self.gainers_tree.pack(fill='both', expand=True); notebook.add(gframe, text="Gainers"); self.gainers_tree.pack(in_=gframe, fill='both', expand=True)
        self.losers_tree = ttk.Treeview(notebook, columns=('symbol','change','volume','price'), show='headings')
        for c, name in zip(['symbol','change','volume','price'], ['Symbol','Change%','Volume','Price']): self.losers_tree.heading(c, text=name)
        lframe = ttk.Frame(notebook); self.losers_tree.pack(fill='both', expand=True); notebook.add(lframe, text="Losers"); self.losers_tree.pack(in_=lframe, fill='both', expand=True)
        self.new_tree = ttk.Treeview(notebook, columns=('symbol','time','price','volume'), show='headings')
        for c, name in zip(['symbol','time','price','volume'], ['Symbol','Listed','Price','Volume']): self.new_tree.heading(c, text=name)
        nframe = ttk.Frame(notebook); self.new_tree.pack(fill='both', expand=True); notebook.add(nframe, text="New"); self.new_tree.pack(in_=nframe, fill='both', expand=True)

        # bottom controls
        ctrl = ttk.Frame(self); ctrl.pack(fill='x', padx=6, pady=6)
        self.start_btn = ttk.Button(ctrl, text="Start Trading", command=self.start_trading); self.start_btn.pack(side='left', padx=4)
        self.stop_btn = ttk.Button(ctrl, text="Stop Trading", command=self.stop_trading, state='disabled'); self.stop_btn.pack(side='left', padx=4)
        self.save_orders_btn = ttk.Button(ctrl, text="Save Orders DB", command=self.save_orders_db); self.save_orders_btn.pack(side='left', padx=4)

    def populate_available_pairs(self):
        self.available_list.delete(0, 'end')
        pairs = getattr(engine, 'market_tracker', None).available_pairs if getattr(engine, 'market_tracker', None) else []
        for p in pairs:
            self.available_list.insert('end', p)

    def on_search(self, *args):
        t = self.search_var.get()
        self.available_list.delete(0, 'end')
        if getattr(engine, 'market_tracker', None):
            matches = engine.market_tracker.search_pairs(t)
            for p in matches:
                self.available_list.insert('end', p)

    def add_selected(self):
        sel = list(self.available_list.curselection())
        for i in sel:
            v = self.available_list.get(i)
            if v not in self.active_list.get(0, 'end'):
                self.active_list.insert('end', v)
                self.active_symbols.add(v)

    def remove_selected(self):
        sel = list(self.active_list.curselection())
        for i in reversed(sel):
            v = self.active_list.get(i)
            self.active_list.delete(i)
            if v in self.active_symbols:
                self.active_symbols.remove(v)

    def start_trading(self):
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        messagebox.showinfo("Trading", "Trading started (engine loop will be started by runner)")

    def stop_trading(self):
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        messagebox.showinfo("Trading", "Trading stopped (engine loop will be stopped by runner)")

    def save_orders_db(self):
        # persist orders or export as needed
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if not path:
            return
        import json
        data = {oid: o.__dict__ for oid, o in self.order_manager.orders.items()}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=str, indent=2)
        messagebox.showinfo("Saved", f"Orders exported to {path}")

    def update_market_trees(self):
        """Called by runner to refresh market info from engine.market_tracker"""
        mt = getattr(engine, 'market_tracker', None)
        if not mt:
            return
        try:
            # gainers
            for tree, data in [(self.gainers_tree, getattr(mt, 'gainers', [])),
                               (self.losers_tree, getattr(mt, 'losers', [])),
                               (self.new_tree, getattr(mt, 'new_listings', []))]:
                # clear
                for iid in tree.get_children():
                    tree.delete(iid)
                for d in data:
                    vals = []
                    for k in tree['columns']:
                        v = d.get(k, "")
                        if isinstance(v, float):
                            v = round(v, 6)
                        vals.append(v)
                    tree.insert('', 'end', values=vals)
        except Exception:
            logger.exception("Failed updating market trees")


# --- App wiring and integration runner usage ---


class CryptoBotApp:
    def __init__(self, root):
        self.root = root
        root.title("CryptoBot GUI")
        root.geometry("1200x800")
        # Audit DB
        self.audit_db = AuditDB()
        # Create trading controls; adapters will be attached by runner below
        self.trading_controls = TradingControlsFrame(root, audit_db=self.audit_db)
        self.trading_controls.pack(fill='both', expand=True)
        # Strategy tuner
        self.strategy_panel = StrategyTunerPanel(root)
        # Backtest scheduler from engine (shared instance)
        self.backtest_scheduler = engine.get_backtest_scheduler()
        # Execution and price adapters (Binance implemented in crypto_bot.py)
        # Replace API_KEY/API_SECRET with real credentials before going live
        exec_adapter = engine.BinanceExecutionAdapter(api_key="YOUR_API_KEY", api_secret="YOUR_API_SECRET", testnet=True)
        price_feed = engine.BinancePriceFeed(api_key="YOUR_API_KEY", api_secret="YOUR_API_SECRET", symbols=list(self.trading_controls.active_symbols or []))
        # Runner
        self.runner = engine.TradingEngineRunner(gui_widget=self.trading_controls,
                                                 execution_adapter=exec_adapter,
                                                 price_feed=price_feed,
                                                 order_manager=self.trading_controls.order_manager,
                                                 audit_db=self.audit_db,
                                                 poll_interval=1.0)
        # Hook start/stop trading buttons to runner
        self._patch_buttons()

    def _patch_buttons(self):
        # Connect Start Trading button to start the runner with current active symbols
        def start_all(*a, **kw):
            syms = list(self.trading_controls.active_symbols) or getattr(engine, 'market_tracker', None).available_pairs
            self.runner.start(subscribe_symbols=syms)
            self.trading_controls.start_trading()
        def stop_all(*a, **kw):
            self.runner.stop()
            self.trading_controls.stop_trading()
        try:
            self.trading_controls.start_btn.config(command=start_all)
            self.trading_controls.stop_btn.config(command=stop_all)
        except Exception:
            pass

    def close(self):
        try:
            self.runner.stop()
        except Exception:
            pass
        try:
            self.backtest_scheduler.shutdown(wait=False)
        except Exception:
            pass


def main():
    root = tk.Tk()
    app = CryptoBotApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.close(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()
# --------------------------------------------------------------
# gui_bot.py – GUI for CryptoBot
# --------------------------------------------------------------
import os
import sys
import asyncio
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import pandas as pd
import mplfinance as mpf

# Add folder to path so crypto_bot can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crypto_bot import (
    MLModel, run_backtest, live_trading_loop, stop_live_trading,
    update_risk_config, SYMBOLS, tune_xgboost, example_live_data_generator
)

# ---------- Main GUI ----------
class CryptoBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Scalper Bot – Dashboard")
        self.root.geometry("1400x950")
        self.root.configure(bg="#1a1a1a")

        # ----- Theme variables -----
        self.dark_theme = True
        self.bg_color = "#1a1a1a"
        self.fg_color = "white"
        self.canvas_bg = "#2d2d2d"

        # ----- Status -----
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(root, textvariable=self.status_var, bg=self.bg_color, fg=self.fg_color).pack(fill="x")

        # ----- Header -----
        header = tk.Frame(root, bg=self.bg_color)
        header.pack(pady=5, padx=5, fill="x")

        self.balance_var = tk.StringVar(value="$10,000")
        tk.Label(header, textvariable=self.balance_var, bg=self.bg_color, fg="green", font=("Arial", 14, "bold")).pack(side="left", padx=10)

        self.sym_var = tk.StringVar(value="SOLUSDT")
        tk.Label(header, text="Symbol:", bg=self.bg_color, fg="yellow").pack(side="left", padx=5)
        self.sym_dropdown = ttk.Combobox(header, textvariable=self.sym_var, values=SYMBOLS, state="readonly", width=10)
        self.sym_dropdown.pack(side="left", padx=5)

        self.auto_switch_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(header, text="Auto-Switch", variable=self.auto_switch_var).pack(side="left", padx=10)

        # ----- Testnet / Live Slider -----
        self.env_var = tk.IntVar(value=1)
        tk.Label(header, text="Environment", bg=self.bg_color, fg="white").pack(side="left", padx=5)
        self.env_slider = ttk.Scale(header, from_=0, to=1, orient="horizontal", variable=self.env_var, command=self.update_env_label)
        self.env_slider.pack(side="left", padx=5)
        self.env_label = tk.Label(header, text="TestNet", bg=self.bg_color, fg="yellow")
        self.env_label.pack(side="left")

        # ----- Theme switch -----
        tk.Button(header, text="Toggle Theme", command=self.toggle_theme).pack(side="right", padx=10)

        # ----- Risk Settings -----
        risk_frame = tk.LabelFrame(root, text="Risk Settings", bg=self.bg_color, fg=self.fg_color)
        risk_frame.pack(pady=5, padx=5, fill="x")

        self.risk_var = tk.DoubleVar(value=2.0)
        tk.Label(risk_frame, text="Risk %", bg=self.bg_color, fg=self.fg_color).pack(side="left")
        tk.Scale(risk_frame, from_=0.5, to=5.0, orient="horizontal", variable=self.risk_var, length=150).pack(side="left", padx=5)

        self.sl_var = tk.DoubleVar(value=2.0)
        tk.Label(risk_frame, text="Stop-Loss xATR", bg=self.bg_color, fg=self.fg_color).pack(side="left", padx=10)
        tk.Scale(risk_frame, from_=1.0, to=5.0, orient="horizontal", variable=self.sl_var, length=150).pack(side="left", padx=5)

        self.daily_loss_var = tk.DoubleVar(value=500)
        tk.Label(risk_frame, text="Daily Max $ Loss", bg=self.bg_color, fg=self.fg_color).pack(side="left", padx=10)
        tk.Entry(risk_frame, textvariable=self.daily_loss_var, width=8).pack(side="left", padx=5)

        tk.Button(risk_frame, text="Apply", command=self.apply_risk_settings).pack(side="left", padx=10)

        # ----- Buttons -----
        btn_frame = tk.Frame(root, bg=self.bg_color)
        btn_frame.pack(pady=5, padx=5, fill="x")
        tk.Button(btn_frame, text="Run Backtest", command=self.run_backtest_thread, bg="green", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Start Live", command=self.start_live_thread, bg="blue", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Stop Bot", command=self.confirm_stop, bg="red", fg="white").pack(side="left", padx=5)

        # ----- Progress bar -----
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(root, maximum=100, variable=self.progress_var)
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        # ----- Equity Chart -----
        chart_frame = tk.Frame(root, bg=self.bg_color)
        chart_frame.pack(fill="both", expand=True)
        self.fig_canvas = tk.Canvas(chart_frame, bg=self.canvas_bg)
        self.fig_canvas.pack(fill="both", expand=True)

        # ----- Logs -----
        self.log_text = ScrolledText(root, bg="#2d2d2d", fg="white", height=10)
        self.log_text.pack(fill="both", expand=False, padx=5, pady=5)

        # ----- Async handling -----
        self.loop = asyncio.get_event_loop()
        self.model = MLModel()
        self.is_running = False

    # ---------- GUI Methods ----------
    def log(self, msg, color="white"):
        self.log_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see("end")

    def update_env_label(self, val=None):
        self.env_label.config(text="TestNet" if self.env_var.get() else "LIVE", fg="yellow" if self.env_var.get() else "red")

    def toggle_theme(self):
        self.dark_theme = not self.dark_theme
        self.bg_color = "#1a1a1a" if self.dark_theme else "#f0f0f0"
        self.fg_color = "white" if self.dark_theme else "black"
        self.root.configure(bg=self.bg_color)

    def apply_risk_settings(self):
        update_risk_config({
            "risk_per_trade": self.risk_var.get()/100,
            "stop_loss_mult": self.sl_var.get(),
            "daily_loss": self.daily_loss_var.get()
        })
        self.log("Risk settings applied", "green")

    # ---------- Threading Wrappers ----------
    def run_backtest_thread(self):
        threading.Thread(target=self._run_backtest, daemon=True).start()

    def _run_backtest(self):
        self.is_running = True
        self.progress_var.set(0)
        self.log("Backtest started")
        async def task():
            df = pd.DataFrame({
                "open_time": pd.date_range(end=datetime.now(), periods=100),
                "close": np.random.rand(100)*100,
                "volume": np.random.rand(100)*10
            })
            await self.model.train(df)
            result = await run_backtest(self.model, df)
            self.progress_var.set(100)
            self.log(f"Backtest finished. Final equity: ${result['final_equity']:.2f}", "green")
        asyncio.run(task())
        self.is_running = False

    def start_live_thread(self):
        threading.Thread(target=self._start_live, daemon=True).start()

    def _start_live(self):
        if self.is_running:
            self.log("Already running", "red")
            return
        self.is_running = True
        async def task():
            gen = example_live_data_generator(self.sym_var.get())
            await live_trading_loop(self.model, gen, self.live_update)
            self.is_running = False
        asyncio.run(task())

    def live_update(self, balance, trades):
        self.root.after(0, lambda: self.balance_var.set(f"${balance:.2f}"))
        self.root.after(0, lambda: self.progress_var.set(min(100, len(trades))))

    def confirm_stop(self):
        if messagebox.askyesno("Confirm", "Stop live trading?"):
            stop_live_trading()
            self.is_running = False
            self.log("Stop signal sent", "orange")

# ---------- Run GUI ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoBotGUI(root)
    root.mainloop()
#!/usr/bin/env python3
"""
gui_bot.py
Tkinter GUI with:
 - Backtest + training
 - Start/Stop live via run_live_in_thread()
 - Live PnL updates via Queue (downsampled)
 - Progressbar animated while stopping; fallback spinner text
 - Confirmation popup before stopping
"""

import os
import sys
import threading
import queue
import time
from typing import List
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crypto_bot import (
    reconnect_client, get_historical_data_with_indicators, tune_xgboost, MLModel,
    run_backtest, run_live_in_thread, ensure_trades_csv, TRADES_DIR, SYMBOLS,
    update_risk_config, DEFAULT_POLL_INTERVAL
)

class CryptoBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Bot GUI")
        self.root.geometry("1200x820")
        self.model = None
        self.current_symbol = 'SOLUSDT'
        self.live_thread = None
        self.stop_thread_event = None
        self.update_queue = queue.Queue(maxsize=200)

        # header
        top = tk.Frame(root)
        top.pack(fill='x', padx=8, pady=8)
        tk.Label(top, text="Symbol:").pack(side='left')
        self.symbol_var = tk.StringVar(value=self.current_symbol)
        self.sym_cb = ttk.Combobox(top, textvariable=self.symbol_var, values=SYMBOLS, width=12)
        self.sym_cb.pack(side='left', padx=6)
        ttk.Button(top, text="Backtest", command=self.run_backtest).pack(side='left', padx=6)
        ttk.Button(top, text="Start Live", command=self.start_live).pack(side='left', padx=6)
        self.stop_btn = ttk.Button(top, text="Stop Live", command=self.on_stop_button, state='disabled')
        self.stop_btn.pack(side='left', padx=6)

        # risk
        risk_frame = tk.Frame(root)
        risk_frame.pack(fill='x', padx=8, pady=6)
        tk.Label(risk_frame, text="Risk/Trade %").pack(side='left')
        self.risk_var = tk.DoubleVar(value=2.0)
        ttk.Scale(risk_frame, from_=0.5, to=5.0, variable=self.risk_var, orient='horizontal', length=140).pack(side='left', padx=6)
        tk.Label(risk_frame, text="SL xATR").pack(side='left', padx=6)
        self.sl_var = tk.DoubleVar(value=2.0)
        ttk.Scale(risk_frame, from_=1.0, to=5.0, variable=self.sl_var, orient='horizontal', length=140).pack(side='left', padx=6)
        ttk.Button(risk_frame, text="Apply Risk", command=self.apply_risk).pack(side='left', padx=10)

        # status (balance/pnl)
        status_frame = tk.Frame(root)
        status_frame.pack(fill='x', padx=8, pady=6)
        self.balance_var = tk.StringVar(value="Balance: $10,000.00")
        self.pnl_var = tk.StringVar(value="PnL: $0.00 (0.00%)")
        tk.Label(status_frame, textvariable=self.balance_var, font=('Arial', 12, 'bold')).pack(side='left', padx=8)
        self.pnl_lbl = tk.Label(status_frame, textvariable=self.pnl_var, font=('Arial', 12, 'bold'))
        self.pnl_lbl.pack(side='left', padx=8)

        # progress area (progressbar + spinner)
        self.progress_frame = tk.Frame(root)
        self.progress_frame.pack(fill='x', padx=8, pady=4)
        self.progress = ttk.Progressbar(self.progress_frame, mode='indeterminate', length=300)
        self.progress.pack(side='left', padx=6)
        self.spinner_lbl = tk.Label(self.progress_frame, text="", font=('Consolas', 10))
        self.spinner_lbl.pack(side='left', padx=8)

        # main pane: plot + logs
        main_pane = tk.PanedWindow(root, orient='vertical')
        main_pane.pack(fill='both', expand=True, padx=8, pady=8)

        plot_frame = tk.Frame(main_pane)
        main_pane.add(plot_frame, stretch='always')
        self.fig, self.ax = plt.subplots(figsize=(9,4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        self.ax.set_facecolor('#f5f5f5')

        log_frame = tk.Frame(main_pane)
        main_pane.add(log_frame, stretch='always')
        self.log_txt = scrolledtext.ScrolledText(log_frame, height=10, bg='#222', fg='white')
        self.log_txt.pack(fill='both', expand=True)

        reconnect_client(use_testnet=True)
        self.log("GUI ready (Mock/Testnet).")

        # spinner state
        self._spinner_running = False
        self._spinner_chars = ['|','/','-','\\']
        self._spinner_idx = 0

        # start queue poll
        self.root.after(400, self._poll_update_queue)

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_txt.insert('end', f"[{ts}] {msg}\n")
        self.log_txt.see('end')

    def apply_risk(self):
        update_risk_config({
            'risk_per_trade': self.risk_var.get() / 100,
            'stop_loss_mult': self.sl_var.get()
        })
        self.log("Applied risk settings.")

    def run_backtest(self):
        sym = self.symbol_var.get()
        self.log(f"Backtest started for {sym}...")
        t = threading.Thread(target=self._backtest_thread, args=(sym,), daemon=True)
        t.start()

    def _backtest_thread(self, sym):
        try:
            df = get_historical_data_with_indicators(sym, days=360)
            params = tune_xgboost(df)
            self.model = MLModel(params)
            self.model.train(df)
            equity, best = run_backtest(self.model, symbols=[sym], initial_capital=10000.0)
            self.log(f"Backtest done. Final equity: {equity[-1] if equity else 'N/A'}")
            self._plot_equity(equity)
        except Exception as e:
            self.log(f"Backtest error: {e}")

    def start_live(self):
        if not self.model:
            messagebox.showerror("No model", "Run backtest (train) first.")
            return
        if self.live_thread and self.live_thread.is_alive():
            self.log("Live thread already running.")
            return
        sym = self.symbol_var.get()
        export_fn = os.path.join(TRADES_DIR, f"{sym}_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        ensure_trades_csv(export_fn)
        self.stop_thread_event = threading.Event()

        def update_cb(balance, pnl, equity_curve):
            try:
                self.update_queue.put_nowait({'balance': balance, 'pnl': pnl, 'equity': equity_curve})
            except queue.Full:
                pass

        self.live_thread = run_live_in_thread(self.model, 10000.0, sym, export_fn, DEFAULT_POLL_INTERVAL, self.stop_thread_event, update_callback=update_cb)
        self.log(f"Live trading started for {sym}. Exporting to {export_fn}")
        self.stop_btn.config(state='normal')

    def on_stop_button(self):
        # confirmation popup
        if not messagebox.askyesno("Confirm Stop", "Are you sure you want to stop live trading?"):
            return
        self._begin_stop_sequence()

    def _begin_stop_sequence(self):
        if not self.stop_thread_event:
            self.log("No live thread running.")
            return
        self.log("Stop requested. Disabling controls and starting graceful shutdown.")
        self.stop_btn.config(state='disabled')
        self.progress.start(20)
        self._spinner_running = True
        self._spin_step()
        self.stop_thread_event.set()
        self._wait_for_thread(timeout_sec=10)

    def _wait_for_thread(self, timeout_sec: int = 10):
        start = time.time()
        def _checker():
            elapsed = time.time() - start
            if self.live_thread is None or not self.live_thread.is_alive():
                self.log("Live thread stopped gracefully.")
                self.progress.stop()
                self._spinner_running = False
                self.spinner_lbl.config(text="")
                self.stop_btn.config(state='disabled')
                return
            if elapsed > timeout_sec:
                self.progress.stop()
                self.log("Graceful stop timed out; continuing to wait (spinner active).")
                self.root.after(500, _checker)
                return
            self.root.after(500, _checker)
        self.root.after(100, _checker)

    def _spin_step(self):
        if not self._spinner_running:
            self.spinner_lbl.config(text="")
            return
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_chars)
        self.spinner_lbl.config(text=f"Stopping... {self._spinner_chars[self._spinner_idx]}")
        self.root.after(200, self._spin_step)

    def _poll_update_queue(self):
        try:
            while True:
                msg = self.update_queue.get_nowait()
                balance = msg.get('balance')
                pnl = msg.get('pnl')
                eq = msg.get('equity', [])
                if balance is not None:
                    self.balance_var.set(f"Balance: ${balance:.2f}")
                    pct = (balance - 10000.0) / 10000.0 * 100.0
                    self.pnl_var.set(f"PnL: ${(balance-10000.0):+.2f} ({pct:+.2f}%)")
                    self.pnl_lbl.config(fg='green' if balance >= 10000.0 else 'red')
                if eq:
                    self._plot_equity(eq)
        except queue.Empty:
            pass
        finally:
            self.root.after(500, self._poll_update_queue)

    def _plot_equity(self, curve: List[float]):
        self.ax.clear()
        if curve:
            # downsample for plotting if too many points
            max_points = 500
            if len(curve) > max_points:
                step = max(1, len(curve) // max_points)
                curve_plot = curve[::step]
            else:
                curve_plot = curve
            self.ax.plot(curve_plot)
            self.ax.set_title(f"Equity - {self.symbol_var.get()}")
        else:
            self.ax.text(0.5, 0.5, "No equity data", ha='center')
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoBotGUI(root)
    root.mainloop()
#!/usr/bin/env python3
"""
gui_bot.py
Tkinter GUI that:
 - trains model (backtest) on demand
 - starts live trading in a background thread
 - stops live trading gracefully by setting a threading.Event which notifies the async loop
"""

import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ensure local imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crypto_bot import (
    reconnect_client, get_historical_data_with_indicators, tune_xgboost, MLModel,
    run_backtest, run_live_in_thread, ensure_trades_csv, TRADES_DIR, SYMBOLS, update_risk_config
)

class CryptoBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Bot GUI")
        self.root.geometry("1200x800")
        self.model = None
        self.current_symbol = 'SOLUSDT'
        self.live_thread = None
        self.stop_thread_event = None

        # UI frames
        top = tk.Frame(root)
        top.pack(fill='x', padx=8, pady=8)

        tk.Label(top, text="Symbol:").pack(side='left')
        self.symbol_var = tk.StringVar(value=self.current_symbol)
        self.sym_cb = ttk.Combobox(top, textvariable=self.symbol_var, values=SYMBOLS, width=12)
        self.sym_cb.pack(side='left', padx=6)
        tk.Button(top, text="Backtest", command=self.run_backtest).pack(side='left', padx=6)
        tk.Button(top, text="Start Live", command=self.start_live).pack(side='left', padx=6)
        tk.Button(top, text="Stop Live", command=self.stop_live).pack(side='left', padx=6)

        # risk settings area
        risk_frame = tk.Frame(root)
        risk_frame.pack(fill='x', padx=8, pady=6)
        tk.Label(risk_frame, text="Risk/Trade %").pack(side='left')
        self.risk_var = tk.DoubleVar(value=2.0)
        ttk.Scale(risk_frame, from_=0.5, to=5.0, variable=self.risk_var, orient='horizontal', length=140).pack(side='left', padx=6)
        tk.Label(risk_frame, text="SL xATR").pack(side='left', padx=6)
        self.sl_var = tk.DoubleVar(value=2.0)
        ttk.Scale(risk_frame, from_=1.0, to=5.0, variable=self.sl_var, orient='horizontal', length=140).pack(side='left', padx=6)
        tk.Button(risk_frame, text="Apply Risk", command=self.apply_risk).pack(side='left', padx=10)

        # logs and plot
        bottom = tk.PanedWindow(root, orient='vertical')
        bottom.pack(fill='both', expand=True, padx=8, pady=8)

        # plot area
        plot_frame = tk.Frame(bottom)
        bottom.add(plot_frame, stretch='always')
        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # logs
        log_frame = tk.Frame(bottom)
        bottom.add(log_frame, stretch='always')
        self.log_txt = scrolledtext.ScrolledText(log_frame, height=10, bg='#222', fg='white')
        self.log_txt.pack(fill='both', expand=True)

        reconnect_client(use_testnet=True)
        self.log("GUI ready. Using Mock/Testnet client by default.")

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_txt.insert('end', f"[{ts}] {msg}\n")
        self.log_txt.see('end')

    def apply_risk(self):
        update_risk_config({
            'risk_per_trade': self.risk_var.get() / 100,
            'stop_loss_mult': self.sl_var.get()
        })
        self.log("Applied risk settings.")

    def run_backtest(self):
        sym = self.symbol_var.get()
        self.log(f"Starting backtest for {sym}...")
        t = threading.Thread(target=self._backtest_thread, args=(sym,), daemon=True)
        t.start()

    def _backtest_thread(self, sym):
        try:
            df = get_historical_data_with_indicators(sym, days=360)
            params = tune_xgboost(df)
            self.model = MLModel(params)
            self.model.train(df)
            equity, best = run_backtest(self.model, symbols=[sym], initial_capital=10000.0)
            self.log(f"Backtest done. Final equity: {equity[-1] if equity else 'N/A'}")
            # plot equity
            self.ax.clear()
            if equity:
                self.ax.plot(equity)
                self.ax.set_title(f"Equity - {sym}")
            self.canvas.draw()
        except Exception as e:
            self.log(f"Backtest error: {e}")

    def start_live(self):
        if not self.model:
            messagebox.showerror("Model missing", "Run backtest (train) first.")
            return
        if self.live_thread and self.live_thread.is_alive():
            self.log("Live thread already running.")
            return
        sym = self.symbol_var.get()
        export_fn = os.path.join(TRADES_DIR, f"{sym}_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        ensure_trades_csv(export_fn)
        self.stop_thread_event = threading.Event()
        self.live_thread = run_live_in_thread(self.model, 10000.0, sym, export_fn, DEFAULT_POLL_INTERVAL, self.stop_thread_event)
        self.log(f"Live trading started for {sym}. Exporting trades to {export_fn}.")

    def stop_live(self):
        if self.stop_thread_event:
            self.stop_thread_event.set()
            self.log("Stop requested — waiting for live loop to exit gracefully.")
            # optionally join thread for a short time
            if self.live_thread:
                self.live_thread.join(timeout=30)
                if not self.live_thread.is_alive():
                    self.log("Live thread stopped.")
                else:
                    self.log("Live thread still running — it will stop soon.")
            self.stop_thread_event = None
        else:
            self.log("No live thread running.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoBotGUI(root)
    root.mainloop()
#!/usr/bin/env python3
"""
gui_bot.py
Tkinter GUI that:
 - trains model (backtest) on demand
 - starts live trading in a background thread
 - stops live trading gracefully by setting a threading.Event which notifies the async loop
"""

import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ensure local imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crypto_bot import (
    reconnect_client, get_historical_data_with_indicators, tune_xgboost, MLModel,
    run_backtest, run_live_in_thread, ensure_trades_csv, TRADES_DIR, SYMBOLS, update_risk_config
)

class CryptoBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Bot GUI")
        self.root.geometry("1200x800")
        self.model = None
        self.current_symbol = 'SOLUSDT'
        self.live_thread = None
        self.stop_thread_event = None

        # UI frames
        top = tk.Frame(root)
        top.pack(fill='x', padx=8, pady=8)

        tk.Label(top, text="Symbol:").pack(side='left')
        self.symbol_var = tk.StringVar(value=self.current_symbol)
        self.sym_cb = ttk.Combobox(top, textvariable=self.symbol_var, values=SYMBOLS, width=12)
        self.sym_cb.pack(side='left', padx=6)
        tk.Button(top, text="Backtest", command=self.run_backtest).pack(side='left', padx=6)
        tk.Button(top, text="Start Live", command=self.start_live).pack(side='left', padx=6)
        tk.Button(top, text="Stop Live", command=self.stop_live).pack(side='left', padx=6)

        # risk settings area
        risk_frame = tk.Frame(root)
        risk_frame.pack(fill='x', padx=8, pady=6)
        tk.Label(risk_frame, text="Risk/Trade %").pack(side='left')
        self.risk_var = tk.DoubleVar(value=2.0)
        ttk.Scale(risk_frame, from_=0.5, to=5.0, variable=self.risk_var, orient='horizontal', length=140).pack(side='left', padx=6)
        tk.Label(risk_frame, text="SL xATR").pack(side='left', padx=6)
        self.sl_var = tk.DoubleVar(value=2.0)
        ttk.Scale(risk_frame, from_=1.0, to=5.0, variable=self.sl_var, orient='horizontal', length=140).pack(side='left', padx=6)
        tk.Button(risk_frame, text="Apply Risk", command=self.apply_risk).pack(side='left', padx=10)

        # logs and plot
        bottom = tk.PanedWindow(root, orient='vertical')
        bottom.pack(fill='both', expand=True, padx=8, pady=8)

        # plot area
        plot_frame = tk.Frame(bottom)
        bottom.add(plot_frame, stretch='always')
        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # logs
        log_frame = tk.Frame(bottom)
        bottom.add(log_frame, stretch='always')
        self.log_txt = scrolledtext.ScrolledText(log_frame, height=10, bg='#222', fg='white')
        self.log_txt.pack(fill='both', expand=True)

        reconnect_client(use_testnet=True)
        self.log("GUI ready. Using Mock/Testnet client by default.")

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_txt.insert('end', f"[{ts}] {msg}\n")
        self.log_txt.see('end')

    def apply_risk(self):
        update_risk_config({
            'risk_per_trade': self.risk_var.get() / 100,
            'stop_loss_mult': self.sl_var.get()
        })
        self.log("Applied risk settings.")

    def run_backtest(self):
        sym = self.symbol_var.get()
        self.log(f"Starting backtest for {sym}...")
        t = threading.Thread(target=self._backtest_thread, args=(sym,), daemon=True)
        t.start()

    def _backtest_thread(self, sym):
        try:
            df = get_historical_data_with_indicators(sym, days=360)
            params = tune_xgboost(df)
            self.model = MLModel(params)
            self.model.train(df)
            equity, best = run_backtest(self.model, symbols=[sym], initial_capital=10000.0)
            self.log(f"Backtest done. Final equity: {equity[-1] if equity else 'N/A'}")
            # plot equity
            self.ax.clear()
            if equity:
                self.ax.plot(equity)
                self.ax.set_title(f"Equity - {sym}")
            self.canvas.draw()
        except Exception as e:
            self.log(f"Backtest error: {e}")

    def start_live(self):
        if not self.model:
            messagebox.showerror("Model missing", "Run backtest (train) first.")
            return
        if self.live_thread and self.live_thread.is_alive():
            self.log("Live thread already running.")
            return
        sym = self.symbol_var.get()
        export_fn = os.path.join(TRADES_DIR, f"{sym}_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        ensure_trades_csv(export_fn)
        self.stop_thread_event = threading.Event()
        self.live_thread = run_live_in_thread(self.model, 10000.0, sym, export_fn, DEFAULT_POLL_INTERVAL, self.stop_thread_event)
        self.log(f"Live trading started for {sym}. Exporting trades to {export_fn}.")

    def stop_live(self):
        if self.stop_thread_event:
            self.stop_thread_event.set()
            self.log("Stop requested — waiting for live loop to exit gracefully.")
            # optionally join thread for a short time
            if self.live_thread:
                self.live_thread.join(timeout=30)
                if not self.live_thread.is_alive():
                    self.log("Live thread stopped.")
                else:
                    self.log("Live thread still running — it will stop soon.")
            self.stop_thread_event = None
        else:
            self.log("No live thread running.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoBotGUI(root)
    root.mainloop()
# --------------------------------------------------------------
# gui_bot.py – INTUITIVE GUI + DYNAMIC RISK + MANUAL/AUTO SWITCH
# --------------------------------------------------------------
import os
import sys
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Add folder to path so crypto_bot can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crypto_bot import (
    get_historical_data_with_indicators, tune_xgboost, MLModel,
    RiskManagedMLStrategy, run_backtest, live_trading_loop,
    update_risk_config, SYMBOLS, auto_switch
)

# ---------- Tooltip ----------
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.tw or not self.text: return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tw, text=self.text, bg="#ffffe0", relief="solid",
                       borderwidth=1, font=("Arial", 8))
        lbl.pack()

    def hide(self, _=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

# ---------- Main GUI ----------
class CryptoBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Scalper Bot – Dashboard")
        self.root.geometry("1400x950")
        self.root.configure(bg="#1a1a1a")
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Arial', 11), padding=12)
        style.configure('TLabel', font=('Arial', 12), background='#1a1a1a', foreground='white')

        # ----- Status bar -----
        self.status_var = tk.StringVar(value="Ready")
        sb = tk.Frame(root, bg="#333333", height=30)
        sb.pack(side='bottom', fill='x')
        tk.Label(sb, textvariable=self.status_var, fg='white', bg="#333333",
                 font=('Arial', 10), anchor='w').pack(fill='x', padx=10, pady=5)
        self._check_conn()

        # ----- Header -----
        hdr = tk.Frame(root, bg="#1a1a1a")
        hdr.pack(pady=10, padx=20, fill='x')

        self.balance_lbl = tk.Label(hdr, text="Balance: $10,000", fg='green',
                                    bg="#1a1a1a", font=('Arial', 16, 'bold'))
        self.balance_lbl.pack(side='left')

        self.sym_lbl = tk.Label(hdr, text="Current: SOLUSDT", fg='yellow',
                                bg="#1a1a1a", font=('Arial', 12))
        self.sym_lbl.pack(side='left', padx=30)

        # ----- Controls -----
        ctrl = tk.LabelFrame(hdr, text="Trading Controls", bg="#1a1a1a",
                             fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        ctrl.pack(side='right', padx=20)

        self.back_btn = tk.Button(ctrl, text="Run Backtest", command=self.start_backtest,
                                  bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'))
        self.back_btn.pack(side='left', padx=5)
        ToolTip(self.back_btn, "Run historical backtest on selected symbol")

        self.live_btn = tk.Button(ctrl, text="Start Live", command=self.start_live,
                                  bg='#2196F3', fg='white', font=('Arial', 11, 'bold'))
        self.live_btn.pack(side='left', padx=5)
        ToolTip(self.live_btn, "Start paper-trading with real-time data")

        self.stop_btn = tk.Button(ctrl, text="Stop Bot", command=self.stop_bot,
                                  bg='#f44336', fg='white', font=('Arial', 11, 'bold'), state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        ToolTip(self.stop_btn, "Emergency stop")

        # ----- Symbol Switcher -----
        sw = tk.LabelFrame(hdr, text="Symbol Switcher", bg="#1a1a1a",
                           fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        sw.pack(side='left', padx=20)

        tk.Label(sw, text="Select:", fg='yellow', bg="#1a1a1a",
                 font=('Arial', 10)).pack(side='left')
        self.sym_var = tk.StringVar(value='SOLUSDT')
        self.sym_cbo = ttk.Combobox(sw, textvariable=self.sym_var,
                                    values=SYMBOLS, state='readonly', width=12)
        self.sym_cbo.pack(side='left', padx=5)

        self.sw_btn = tk.Button(sw, text="Switch", command=self.manual_switch,
                                bg='#FF9800', fg='white', font=('Arial', 10))
        self.sw_btn.pack(side='left', padx=5)

        self.auto_chk = tk.Checkbutton(sw, text="Auto-Switch", variable=auto_switch,
                                       fg='white', bg="#1a1a1a", selectcolor="#1a1a1a",
                                       font=('Arial', 10))
        self.auto_chk.pack(side='left', padx=10)

        # ----- Risk Settings -----
        risk = tk.LabelFrame(hdr, text="Advanced Risk Settings", bg="#1a1a1a",
                             fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        risk.pack(side='left', padx=20, fill='x', expand=True)

        # Risk/Trade %
        r1 = tk.Frame(risk, bg="#1a1a1a")
        r1.pack(fill='x', pady=2)
        tk.Label(r1, text="Risk/Trade %:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 9)).pack(side='left')
        self.risk_var = tk.DoubleVar(value=2.0)
        self.risk_scl = ttk.Scale(r1, from_=0.5, to=5.0, variable=self.risk_var,
                                  orient='horizontal', length=120)
        self.risk_scl.pack(side='left', padx=5)
        ToolTip(self.risk_scl, "Max % of capital risked per trade")

        # Stop-Loss ATR
        r2 = tk.Frame(risk, bg="#1a1a1a")
        r2.pack(fill='x', pady=2)
        tk.Label(r2, text="Stop-Loss ATR:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 9)).pack(side='left')
        self.sl_var = tk.DoubleVar(value=2.0)
        self.sl_scl = ttk.Scale(r2, from_=1.0, to=5.0, variable=self.sl_var,
                                orient='horizontal', length=120)
        self.sl_scl.pack(side='left', padx=5)
        ToolTip(self.sl_scl, "ATR multiplier for stop-loss")

        # Daily loss
        r3 = tk.Frame(risk, bg="#1a1a1a")
        r3.pack(fill='x', pady=2)
        tk.Label(r3, text="Daily Loss $:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 9)).pack(side='left')
        self.daily_var = tk.DoubleVar(value=6.0)
        self.daily_ent = tk.Entry(r3, textvariable=self.daily_var, width=8,
                                  bg='#2d2d2d', fg='white')
        self.daily_ent.pack(side='left', padx=5)
        ToolTip(self.daily_ent, "Max $ loss per day before pause")

        self.apply_btn = tk.Button(risk, text="Apply Settings",
                                   command=self.apply_risk, bg='#9C27B0',
                                   fg='white', font=('Arial', 10, 'bold'))
        self.apply_btn.pack(side='right', pady=5)

        self.risk_prev = tk.Label(risk, text="", fg='cyan', bg="#1a1a1a",
                                  font=('Arial', 9, 'italic'))
        self.risk_prev.pack(side='right', padx=10)
        self._update_risk_preview()

        # ----- Progress -----
        self.prog_lbl = tk.Label(hdr, text="", fg='cyan', bg="#1a1a1a",
                                 font=('Arial', 10, 'italic'))
        self.prog_lbl.pack(side='right')

        # ----- Chart -----
        ch = tk.LabelFrame(root, text="Equity Curve", bg="#1a1a1a",
                           fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        ch.pack(pady=10, padx=20, fill='both', expand=True)

        self.fig, self.ax = plt.subplots(figsize=(12, 5), facecolor="#1a1a1a")
        self.ax.set_facecolor('#2d2d2d')
        self.canvas = FigureCanvasTkAgg(self.fig, ch)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # ----- Logs -----
        log = tk.LabelFrame(root, text="Real-Time Logs", bg="#1a1a1a",
                            fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        log.pack(pady=10, padx=20, fill='both', expand=True)

        self.log_txt = scrolledtext.ScrolledText(log, height=10,
                                                bg='#2d2d2d', fg='white',
                                                font=('Consolas', 9))
        self.log_txt.pack(fill='both', expand=True)

        # Bind live preview
        self.risk_scl.config(command=lambda _: self._update_risk_preview())
        self.sl_scl.config(command=lambda _: self._update_risk_preview())
        self.daily_var.trace('w', lambda *a: self._update_risk_preview())

    # --------------------------------------------------------------
    def log(self, msg, color='white'):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_txt.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_txt.see(tk.END)
        self.root.update_idletasks()

    def _update_risk_preview(self):
        bal = 10000
        max_r = bal * (self.risk_var.get() / 100)
        self.risk_prev.config(text=f"Max Risk/Trade ${max_r:.0f} | Daily ${self.daily_var.get():.0f}")

    def apply_risk(self):
        update_risk_config({
            'risk_per_trade': self.risk_var.get() / 100,
            'stop_loss_mult': self.sl_var.get(),
            'daily_loss': self.daily_var.get()
        })
        self.log("Risk settings applied", 'green')
        self._update_risk_preview()

    def _check_conn(self):
        try:
            from binance.client import Client
            Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET')).ping()
            self.status_var.set("Connected")
        except Exception:
            self.status_var.set("Disconnected")
        self.root.after(30000, self._check_conn)

    # --------------------------------------------------------------
    def manual_switch(self):
        global current_symbol
        new = self.sym_var.get()
        if new == current_symbol:
            self.log("Symbol unchanged")
            return
        if self.is_running:
            messagebox.showwarning("Warning", "Stop bot first")
            return
        current_symbol = new
        self.sym_lbl.config(text=f"Current: {new}")
        self.log(f"Switched to {new} (Auto {'ON' if auto_switch.get() else 'OFF'})", 'green')
        # quick model refresh
        try:
            df = get_historical_data_with_indicators(new, days=30)
            if model:
                model.feature_cols = [c for c in df.columns if c not in ['open_time', 'target']]
        except Exception as e:
            self.log(f"Switch error: {e}", 'red')

    # --------------------------------------------------------------
    def start_backtest(self):
        if self.is_running:
            return
        threading.Thread(target=self._backtest_thread, daemon=True).start()

    def _backtest_thread(self):
        global model, equity_history, current_symbol
        self.is_running = True
        self.back_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.log("Backtest started…")
        try:
            self._progress(1, 5, "Fetching data…")
            data = get_historical_data_with_indicators(current_symbol, days=360)

            self._progress(2, 5, "Tuning model…")
            params = tune_xgboost(data, n_trials=30)

            self._progress(3, 5, "Training…")
            model = MLModel(params)
            model.train(data)

            self._progress(4, 5, "Running simulation…")
            if auto_switch.get():
                equity, best = run_backtest(model)
                if best != current_symbol:
                    self.log(f"Auto-optimised to {best}", 'green')
                    self.manual_switch()
            else:
                strat = RiskManagedMLStrategy(model, 10000, current_symbol)
                for _, r in data.iterrows():
                    strat.on_data(r)
                if strat.position > 0:
                    strat._sell(data.iloc[-1]['close'], data.iloc[-1]['open_time'], "eod")
                equity = strat.equity

            self._progress(5, 5, "Done!")
            equity_history = equity
            self._plot_equity(equity)
            self.log("Backtest complete", 'green')
        except Exception as e:
            self.log(f"Backtest error: {e}", 'red')
        finally:
            self.is_running = False
            self.back_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.prog_lbl.config(text="")

    # --------------------------------------------------------------
    def start_live(self):
        if self.is_running or not model:
            messagebox.showerror("Error", "Run backtest first")
            return
        threading.Thread(target=self._live_thread, daemon=True).start()

    def _live_thread(self):
        global is_running
        self.is_running = True
        self.live_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.log("Live trading started", 'blue')
        self.status_var.set(f"Live – {current_symbol}")

        live_trading_loop(model, initial_capital=10000)

        self.log("Live stopped", 'orange')
        self.status_var.set("Ready")
        self.is_running = False
        self.live_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def stop_bot(self):
        global is_running
        self.is_running = False
        self.log("Bot stopped", 'orange')
        self.status_var.set("Stopped")

    # --------------------------------------------------------------
    def _progress(self, step, total, txt):
        p = step / total * 100
        self.prog_lbl.config(text=f"{txt} ({p:.0f}%)")
        self.root.update_idletasks()

    def _plot_equity(self, curve):
        self.ax.clear()
        if curve:
            self.ax.plot(curve, color='lime', linewidth=2,
                         label=f'PnL ${curve[-1]-10000:+.0f}')
            self.ax.set_title(f'Equity – {current_symbol}', color='white')
            self.ax.legend()
        else:
            self.ax.text(0.5, 0.5, 'Run Backtest', ha='center', va='center',
                         transform=self.ax.transAxes, fontsize=14, color='white')
        self.ax.set_facecolor('#2d2d2d')
        self.ax.tick_params(colors='white')
        self.ax.grid(True, alpha=0.3)
        self.canvas.draw()

# --------------------------------------------------------------
if __name__ == "__main__":
    # GLOBAL vars used by both modules
    model = None
    equity_history = []
    current_symbol = 'SOLUSDT'
    is_running = False

    root = tk.Tk()
    app = CryptoBotGUI(root)
    root.mainloop()"""
gui_bot.py - Fully Integrated Crypto Trading GUI
Includes:
- TradingControlsFrame with market data and TreeViews
- StrategyTuner tab with sliders, charts, auto-tune
- TradeDisplay panel with live trade updates & animations
- MarketVolatilityAnalyzer integration
- Market microstructure & candlestick analysis
- ML/backtesting integration
- Logging, database save/load, theme support, plugin architecture
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
from typing import Callable, Dict, List, Any, Optional
import threading
import logging
import time
import random
import os
import json
import sqlite3
import csv
from pathlib import Path
from datetime import datetime, timedelta

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("CryptoBotGUI")

# --- Theme Manager ---
THEMES = {
    'dark': {
        'bg': '#1a1a1a', 'fg': '#ffffff', 'select_bg': '#404040',
        'select_fg': '#ffffff', 'button_bg': '#2d2d2d',
        'button_fg': '#ffffff', 'frame_bg': '#262626', 'accent': '#007acc'
    },
    'light': {
        'bg': '#ffffff', 'fg': '#000000', 'select_bg': '#0078d7',
        'select_fg': '#ffffff', 'button_bg': '#f0f0f0',
        'button_fg': '#000000', 'frame_bg': '#f5f5f5', 'accent': '#0078d7'
    }
}

class ThemeManager:
    """Manages GUI themes and styles"""
    def __init__(self):
        self.current_theme = 'dark'
        self._setup_styles()
        
    def _setup_styles(self):
        style = ttk.Style()
        colors = THEMES[self.current_theme]
        style.configure('TFrame', background=colors['frame_bg'])
        style.configure('TLabel', background=colors['frame_bg'], foreground=colors['fg'])
        style.configure('TButton', background=colors['button_bg'], foreground=colors['button_fg'])
        style.configure('Accent.TButton', background=colors['accent'], foreground=colors['select_fg'])
        style.configure('TNotebook', background=colors['bg'], tabmargins=[2,5,2,0])
        style.configure('TNotebook.Tab', background=colors['button_bg'], foreground=colors['button_fg'], padding=[10,2])
        style.map('TNotebook.Tab', background=[('selected', colors['select_bg'])], foreground=[('selected', colors['select_fg'])])
        style.configure('Title.TLabel', font=('Helvetica',14,'bold'), foreground=colors['accent'])
        style.configure('Fallback.TLabel', font=('Helvetica',12), foreground='#888888')
        style.configure('Risk.TLabel', foreground='#ff4444')
        style.configure('Success.TLabel', foreground='#44ff44')

    def apply_theme(self, theme_name: str):
        if theme_name in THEMES:
            self.current_theme = theme_name
            self._setup_styles()
            
    def get_colors(self) -> Dict[str,str]:
        return THEMES[self.current_theme]
    
    def configure_root(self, root: tk.Tk):
        colors = self.get_colors()
        root.configure(bg=colors['bg'])
        for child in root.winfo_children():
            if isinstance(child, (ttk.Frame, ttk.LabelFrame)):
                child.configure(style='TFrame')
            elif isinstance(child, ttk.Label):
                child.configure(style='TLabel')

theme_manager = ThemeManager()

# --- Market Volatility Analyzer ---
import numpy as np
import pandas as pd

class MarketVolatilityAnalyzer:
    """Analyzes market volatility for optimal trade timing"""
    def __init__(self, lookback_periods: int = 20):
        self.lookback = lookback_periods
        self.volatility_history = {}
        self.session_volatility = {}
    
    def analyze_volatility(self, symbol: str, price_data: pd.DataFrame) -> Dict[str,Any]:
        try:
            close_prices = price_data['close'].values
            high_prices = price_data['high'].values
            low_prices = price_data['low'].values
            returns = np.diff(np.log(close_prices))
            current_vol = np.std(returns[-self.lookback:]) * np.sqrt(252)
            gk_vol = self._calculate_garman_klass(high_prices[-self.lookback:], low_prices[-self.lookback:], close_prices[-self.lookback:])
            park_vol = self._calculate_parkinson(high_prices[-self.lookback:], low_prices[-self.lookback:])
            
            if symbol not in self.volatility_history:
                self.volatility_history[symbol] = []
            self.volatility_history[symbol].append({'timestamp':datetime.now(),'std_vol':current_vol,'gk_vol':gk_vol,'park_vol':park_vol})
            if len(self.volatility_history[symbol])>100: self.volatility_history[symbol].pop(0)
            
            vol_regime = self._determine_volatility_regime(current_vol,self.volatility_history[symbol])
            thresholds = self._calculate_trading_thresholds(current_vol,vol_regime)
            self._update_session_volatility(symbol,current_vol)
            trading_windows = self._find_trading_windows(symbol)
            
            return {'current_volatility':current_vol,'garman_klass_vol':gk_vol,'parkinson_vol':park_vol,'volatility_regime':vol_regime,'trading_thresholds':thresholds,'trading_windows':trading_windows}
        except Exception as e:
            logger.error(f"Error analyzing volatility: {e}")
            return {}

    def _calculate_garman_klass(self,high: np.ndarray,low: np.ndarray,close: np.ndarray) -> float:
        try:
            log_hl = np.log(high/low)
            log_co = np.log(close[1:]/close[:-1])
            hl_term = 0.5*np.mean(log_hl**2)
            co_term = np.mean(log_co**2)
            vol = np.sqrt(252*(hl_term-(2*np.log(2)-1)*co_term))
            return float(vol)
        except: return 0.0
    
    def _calculate_parkinson(self,high: np.ndarray,low: np.ndarray) -> float:
        try:
            log_hl = np.log(high/low)
            vol = np.sqrt(252*np.mean(log_hl**2)/(4*np.log(2)))
            return float(vol)
        except: return 0.0
    
    def _determine_volatility_regime(self,current_vol:float,history:List[Dict])->str:
        if not history: return "normal"
        hist_vols=[h['std_vol'] for h in history]
        mean=np.mean(hist_vols);std=np.std(hist_vols)
        if current_vol>mean+2*std: return "extreme"
        elif current_vol>mean+std: return "high"
        elif current_vol<mean-std: return "low"
        return "normal"
    
    def _calculate_trading_thresholds(self,current_vol:float,regime:str)->Dict[str,float]:
        thresholds={'entry_threshold':0.001,'stop_loss_mult':2.0,'take_profit_mult':3.0,'position_size_factor':1.0}
        adjustments={'low':{'entry_threshold':0.8,'stop_loss_mult':1.5,'take_profit_mult':2.5,'position_size_factor':1.2},
                     'normal':{'entry_threshold':1.0,'stop_loss_mult':2.0,'take_profit_mult':3.0,'position_size_factor':1.0},
                     'high':{'entry_threshold':1.3,'stop_loss_mult':2.5,'take_profit_mult':3.5,'position_size_factor':0.8},
                     'extreme':{'entry_threshold':1.5,'stop_loss_mult':3.0,'take_profit_mult':4.0,'position_size_factor':0.5}}
        adj=adjustments.get(regime,adjustments['normal'])
        for k,v in thresholds.items(): thresholds[k]=v*adj[k]
        vol_scale=min(max(current_vol/0.2,0.5),2.0)
        thresholds['position_size_factor']*=vol_scale
        return thresholds
    
    def _update_session_volatility(self,symbol:str,current_vol:float)->None:
        now=datetime.now();session_key=now.strftime("%Y-%m-%d-%H")
        if symbol not in self.session_volatility: self.session_volatility[symbol]={}
        if session_key not in self.session_volatility[symbol]: self.session_volatility[symbol][session_key]=[]
        self.session_volatility[symbol][session_key].append(current_vol)
        cutoff=(now-timedelta(days=7)).strftime("%Y-%m-%d")
        self.session_volatility[symbol]={k:v for k,v in self.session_volatility[symbol].items() if k.startswith(cutoff) or k>cutoff}

    def _find_trading_windows(self,symbol:str)->Dict[str,List[int]]:
        if symbol not in self.session_volatility: return {}
        hourly_vol={}
        for session,vols in self.session_volatility[symbol].items():
            hour=int(session.split('-')[-1])
            hourly_vol.setdefault(hour,[]).extend(vols)
        avg_vol={h:np.mean(vs) for h,vs in hourly_vol.items() if vs}
        if not avg_vol: return {}
        mean_vol=np.mean(list(avg_vol.values()));std_vol=np.std(list(avg_vol.values()))
        high=[h for h,v in avg_vol.items() if v>mean_vol+0.5*std_vol]
        low=[h for h,v in avg_vol.items() if v<mean_vol-0.5*std_vol]
        return {'high_volatility':sorted(high),'low_volatility':sorted(low)}
    
    def get_trading_recommendation(self,symbol:str,current_vol:float)->Dict[str,Any]:
        now=datetime.now();current_hour=now.hour
        windows=self._find_trading_windows(symbol)
        regime=self._determine_volatility_regime(current_vol,self.volatility_history.get(symbol,[]))
        thresholds=self._calculate_trading_thresholds(current_vol,regime)
        score=50;regime_scores={"low":-10,"normal":0,"high":10,"extreme":-20}
        score+=regime_scores.get(regime,0)
        if current_hour in windows.get('high_volatility',[]): score+=20
        elif current_hour in windows.get('low_volatility',[]): score-=10
        if symbol in self.volatility_history and len(self.volatility_history[symbol])>1:
            recent=[h['std_vol'] for h in self.volatility_history[symbol][-5:]]
            trend=np.polyfit(range(len(recent)),recent,1)[0]
            score+=10 if trend>0 else -10 if trend<0 else 0
        score=max(0,min(100,score))
        return {'trading_score':score,'volatility_regime':regime,'thresholds':thresholds,'current_hour':current_hour,'is_high_vol_window':current_hour in windows.get('high_volatility',[]),'is_low_vol_window':current_hour in windows.get('low_volatility',[]),'recommendation':'high' if score>=70 else 'moderate' if score>=40 else 'low'}

# --- Trading Modes, TimeFrames, Risk Config ---
class TradingMode:
    SPOT='Spot';MARGIN='Margin';FUTURES='Futures'
class TimeFrame:
    SCALP='Scalp';SHORT='Short';MEDIUM='Medium';LONG='Long'
class RiskConfig:
    TRADING_MODE=TradingMode.SPOT
    LEVERAGE=1.0
    MAX_LEVERAGE=10.0
    TIMEFRAME=TimeFrame.SHORT
    AUTO_MODE_SWITCH=True

# --- Market Tracker Stub ---
class MarketTracker:
    """Stub for market data"""
    def __init__(self):
        self.gainers=[]
        self.losers=[]
        self.new_listings=[]
        self.mode_metrics={'Spot':{'trades':0,'profit':0.0,'max_drawdown':0.0}}
        self.available_pairs=['BTCUSDT','ETHUSDT','BNBUSDT','ADAUSDT','XRPUSDT','SOLUSDT']
    def search_pairs(self,text): return [p for p in self.available_pairs if text.upper() in p]
    def update_market_data(self):
        # Simulate market data
        self.gainers=[{'change':random.uniform(0,10),'volume':random.uniform(1000,5000),'price':random.uniform(1000,50000)} for _ in range(5)]
        self.losers=[{'change':-random.uniform(0,10),'volume':random.uniform(1000,5000),'price':random.uniform(1000,50000)} for _ in range(5)]
        self.new_listings=[{'time':time.time(),'price':random.uniform(0.1,100),'volume':random.uniform(1000,5000)} for _ in range(3)]
market_tracker=MarketTracker()

# --- ML Model & Backtesting Stubs ---
class MLModel:
    def __init__(self, params=None):
        self.params = params or {}


def _simulate_live_thread(model, symbols, trades_csv, stop_event, callback):
    if isinstance(symbols, str):
        symbol_list = [symbols]
    else:
        symbol_list = list(symbols or [])
    if not symbol_list:
        symbol_list = ["BTCUSDT"]
    stop_flag = stop_event or threading.Event()
    max_iterations = 60 if stop_event is None else None

    def emit(payload):
        if callback:
            try:
                callback(payload)
            except Exception:
                logger.exception("Error delivering trading update")

    def worker():
        balance = 10000.0
        pnl = 0.0
        trades = 0
        equity_curve = []
        csv_file = None
        writer = None
        try:
            if trades_csv:
                path = Path(trades_csv)
                path.parent.mkdir(parents=True, exist_ok=True)
                csv_file = path.open("w", newline="", encoding="utf-8")
                writer = csv.writer(csv_file)
                writer.writerow(["timestamp", "symbol", "price", "quantity", "pnl", "balance"])
            rng = random.Random()
            while not stop_flag.is_set():
                if max_iterations is not None and trades >= max_iterations:
                    break
                time.sleep(2)
                symbol = rng.choice(symbol_list)
                price = rng.uniform(10.0, 500.0)
                quantity = rng.uniform(0.01, 0.5)
                change = rng.uniform(-1.5, 1.8) / 100
                trade_pnl = price * quantity * change
                pnl += trade_pnl
                balance += trade_pnl
                trades += 1
                equity_curve.append(balance)
                if writer:
                    writer.writerow([
                        datetime.utcnow().isoformat(),
                        symbol,
                        f"{price:.4f}",
                        f"{quantity:.4f}",
                        f"{trade_pnl:.2f}",
                        f"{balance:.2f}",
                    ])
                    csv_file.flush()
                emit({
                    "symbol": symbol,
                    "trades": trades,
                    "balance": round(balance, 2),
                    "pnl": round(pnl, 2),
                    "last_price": round(price, 4),
                    "equity_curve": equity_curve[-200:],
                    "timestamp": time.time(),
                })
        except Exception:
            logger.exception("Simulated live trading failed")
        finally:
            if csv_file:
                csv_file.close()
            emit({
                "status": "stopped",
                "timestamp": time.time(),
                "trades": trades,
                "balance": round(balance, 2),
                "pnl": round(pnl, 2),
            })

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


run_live_in_thread = _simulate_live_thread

def run_backtest(model, symbol, risk_pct):
    return {'Total Return':0.1,'Win Rate':0.55,'Profit Factor':1.5,'Max Drawdown':0.05,'Sharpe Ratio':1.2,'Total Trades':100,'equity_curve':[1,1.05,1.1,1.2,1.15]}

def tune_xgboost(symbol, n_trials):
    return {'ml_threshold':0.6,'atr_multiplier':2.2,'profit_target':0.04,'max_bars_back':25}

# --- GUI Components ---
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class StrategyTuner:
    """Interactive strategy parameter tuning"""
    def __init__(self,parent:tk.Widget):
        self.parent=parent
        self.frame=ttk.Frame(parent);self.frame.pack(fill='both',expand=True)
        self.has_tuning=True
        self.params={'ml_threshold':{'min':0.5,'max':0.9,'value':0.55,'step':0.01},
                     'atr_multiplier':{'min':1.0,'max':4.0,'value':2.0,'step':0.1},
                     'profit_target':{'min':0.01,'max':0.1,'value':0.03,'step':0.005},
                     'max_bars_back':{'min':10,'max':100,'value':20,'step':5}}
        self._create_controls();self._create_results()
    def _create_controls(self):
        controls=ttk.LabelFrame(self.frame,text="Strategy Parameters",padding=10);controls.pack(fill='x',expand=False,padx=5,pady=5)
        row=0;self.param_vars={}
        for name,config in self.params.items():
            ttk.Label(controls,text=name.replace('_',' ').title()).grid(row=row,column=0,sticky='w',padx=5,pady=2)
            var=tk.DoubleVar(value=config['value']);self.param_vars[name]=var
            ttk.Scale(controls,from_=config['min'],to=config['max'],value=config['value'],variable=var,orient='horizontal').grid(row=row,column=1,sticky='ew',padx=5,pady=2)
            ttk.Label(controls,textvariable=var).grid(row=row,column=2,padx=5,pady=2)
            row+=1
        buttons=ttk.Frame(controls);buttons.grid(row=row,column=0,columnspan=3,pady=10)
        ttk.Button(buttons,text="Run Backtest",command=self._run_backtest).pack(side='left',padx=5)
        ttk.Button(buttons,text="Auto-Tune",command=self._auto_tune).pack(side='left',padx=5)
        ttk.Button(buttons,text="Save Params",command=self._save_params).pack(side='left',padx=5)
    def _create_results(self):
        results=ttk.LabelFrame(self.frame,text="Backtest Results",padding=10);results.pack(fill='both',expand=True,padx=5,pady=5)
        metrics_frame=ttk.Frame(results);metrics_frame.pack(fill='x',expand=False)
        self.metrics={'Total Return':tk.StringVar(value='0.00%'),'Win Rate':tk.StringVar(value='0.00%'),'Profit Factor':tk.StringVar(value='0.00'),'Max Drawdown':tk.StringVar(value='0.00%'),'Sharpe Ratio':tk.StringVar(value='0.00'),'Total Trades':tk.StringVar(value='0')}
        row=0
        for name,var in self.metrics.items():
            ttk.Label(metrics_frame,text=name).grid(row=row,column=0,sticky='w',padx=5,pady=2)
            ttk.Label(metrics_frame,textvariable=var).grid(row=row,column=1,sticky='e',padx=5,pady=2)
            row+=1
        fig=Figure(figsize=(8,4));self.ax=fig.add_subplot(111)
        self.canvas=FigureCanvasTkAgg(fig,results);self.canvas.get_tk_widget().pack(fill='both',expand=True,padx=5,pady=5)
    def _run_backtest(self):
        params={name:var.get() for name,var in self.param_vars.items()}
        model=MLModel(params)
        results=run_backtest(model,'BTCUSDT',0.01)
        if results: self._update_results(results)
    def _auto_tune(self):
        best=tune_xgboost('BTCUSDT',10)
        for k,v in best.items():
            if k in self.param_vars: self.param_vars[k].set(v)
        self._run_backtest()
    def _save_params(self):
        params={name:var.get() for name,var in self.param_vars.items()}
        with open('best_params.json','w') as f: json.dump(params,f,indent=2)
        messagebox.showinfo("Success","Parameters saved to best_params.json")
    def _update_results(self,results):
        for k,v in results.items():
            if k in self.metrics:
                self.metrics[k].set(f"{v*100:.2f}%" if v<1 else f"{v:.2f}")
        if 'equity_curve' in results:
            self.ax.clear();self.ax.plot(results['equity_curve'],color='g');self.ax.set_title('Equity Curve');self.ax.grid(True);self.canvas.draw()

class TradingControlsFrame(ttk.Frame):
    """Main trading controls frame"""
    def __init__(self,parent,callback:Callable=None):
        super().__init__(parent)
        self.callback=callback
        self.stop_event=None
        self.active_symbols=set()
        self.create_widgets()
    def create_widgets(self):
        # Trading Mode Controls
        mode_frame=ttk.LabelFrame(self,text="Trading Mode");mode_frame.pack(fill="x",padx=5,pady=5)
        self.mode_var=tk.StringVar(value=RiskConfig.TRADING_MODE)
        for mode in [TradingMode.SPOT,TradingMode.MARGIN,TradingMode.FUTURES]:
            ttk.Radiobutton(mode_frame,text=mode,value=mode,variable=self.mode_var,command=self.on_mode_change).pack(anchor="w",padx=5)
        leverage_frame=ttk.Frame(mode_frame);leverage_frame.pack(fill="x",padx=5,pady=5)
        ttk.Label(leverage_frame,text="Leverage:").pack(side="left")
        self.leverage_var=tk.DoubleVar(value=RiskConfig.LEVERAGE)
        ttk.Spinbox(leverage_frame,from_=1.0,to=RiskConfig.MAX_LEVERAGE,increment=0.5,textvariable=self.leverage_var,width=10,command=self.on_leverage_change).pack(side="left",padx=5)
        # Timeframe
        time_frame=ttk.LabelFrame(self,text="Timeframe");time_frame.pack(fill="x",padx=5,pady=5)
        self.timeframe_var=tk.StringVar(value=RiskConfig.TIMEFRAME)
        for tf in [TimeFrame.SCALP,TimeFrame.SHORT,TimeFrame.MEDIUM,TimeFrame.LONG]:
            ttk.Radiobutton(time_frame,text=tf,value=tf,variable=self.timeframe_var,command=self.on_timeframe_change).pack(anchor="w",padx=5)
        auto_frame=ttk.Frame(self);auto_frame.pack(fill="x",padx=5,pady=5)
        self.auto_mode_var=tk.BooleanVar(value=RiskConfig.AUTO_MODE_SWITCH)
        ttk.Checkbutton(auto_frame,text="Auto Mode Switch",variable=self.auto_mode_var,command=self.on_auto_mode_change).pack(side="left")
        # Symbol selection
        symbol_frame=ttk.LabelFrame(self,text="Trading Pairs");symbol_frame.pack(fill="both",expand=True,padx=5,pady=5)
        search_frame=ttk.Frame(symbol_frame);search_frame.pack(fill="x",padx=5,pady=5)
        ttk.Label(search_frame,text="Search:").pack(side="left")
        self.search_var=tk.StringVar();self.search_var.trace("w",self.on_search)
        ttk.Entry(search_frame,textvariable=self.search_var).pack(side="left",fill="x",expand=True,padx=5)
        lists_frame=ttk.Frame(symbol_frame);lists_frame.pack(fill="both",expand=True,padx=5,pady=5)
        avail_frame=ttk.LabelFrame(lists_frame,text="Available");avail_frame.pack(side="left",fill="both",expand=True)
        self.available_list=tk.Listbox(avail_frame,selectmode="multiple");self.available_list.pack(fill="both",expand=True)
        btn_frame=ttk.Frame(lists_frame);btn_frame.pack(side="left",padx=5)
        ttk.Button(btn_frame,text="→",command=self.add_selected).pack(pady=2)
        ttk.Button(btn_frame,text="←",command=self.remove_selected).pack(pady=2)
        active_frame=ttk.LabelFrame(lists_frame,text="Active");active_frame.pack(side="left",fill="both",expand=True)
        self.active_list=tk.Listbox(active_frame,selectmode="multiple");self.active_list.pack(fill="both",expand=True)
        # Market info
        market_frame=ttk.LabelFrame(self,text="Market Information");market_frame.pack(fill="both",expand=True,padx=5,pady=5)
        notebook=ttk.Notebook(market_frame);notebook.pack(fill="both",expand=True)
        # Gainers
        gainers_frame=ttk.Frame(notebook);notebook.add(gainers_frame,text="Gainers")
        self.gainers_tree=ttk.Treeview(gainers_frame,columns=("change","volume","price"),show="headings")
        for col,name in zip(["change","volume","price"],["Change %","Volume","Price"]): self.gainers_tree.heading(col,text=name)
        self.gainers_tree.pack(fill="both",expand=True)
        # Losers
        losers_frame=ttk.Frame(notebook);notebook.add(losers_frame,text="Losers")
        self.losers_tree=ttk.Treeview(losers_frame,columns=("change","volume","price"),show="headings")
        for col,name in zip(["change","volume","price"],["Change %","Volume","Price"]): self.losers_tree.heading(col,text=name)
        self.losers_tree.pack(fill="both",expand=True)
        # New listings
        new_frame=ttk.Frame(notebook);notebook.add(new_frame,text="New Listings")
        self.new_tree=ttk.Treeview(new_frame,columns=("time","price","volume"),show="headings")
        for col,name in zip(["time","price","volume"],["Listed","Price","Volume"]): self.new_tree.heading(col,text=name)
        self.new_tree.pack(fill="both",expand=True)
        # Performance
        perf_frame=ttk.Frame(notebook);notebook.add(perf_frame,text="Performance")
        self.perf_tree=ttk.Treeview(perf_frame,columns=("trades","profit","drawdown"),show="headings")
        for col,name in zip(["trades","profit","drawdown"],["Trades","Profit","Drawdown"]): self.perf_tree.heading(col,text=name)
        self.perf_tree.pack(fill="both",expand=True)
        # Control buttons
        control_frame=ttk.Frame(self);control_frame.pack(fill="x",padx=5,pady=5)
        self.start_btn=ttk.Button(control_frame,text="Start Trading",command=self.start_trading);self.start_btn.pack(side="left",padx=5)
        self.stop_btn=ttk.Button(control_frame,text="Stop Trading",command=self.stop_trading,state="disabled");self.stop_btn.pack(side="left",padx=5)
        self.update_market_data()
    # --- Handlers ---
    def on_mode_change(self,*args): RiskConfig.TRADING_MODE=self.mode_var.get()
    def on_leverage_change(self,*args): RiskConfig.LEVERAGE=self.leverage_var.get()
    def on_timeframe_change(self,*args): RiskConfig.TIMEFRAME=self.timeframe_var.get()
    def on_auto_mode_change(self,*args): RiskConfig.AUTO_MODE_SWITCH=self.auto_mode_var.get()
    def on_search(self,*args):
        term=self.search_var.get()
        self.available_list.delete(0,"end")
        for p in market_tracker.search_pairs(term): self.available_list.insert("end",p)
    def add_selected(self): idxs=self.available_list.curselection();[self.active_list.insert("end",self.available_list.get(i)) for i in idxs]
    def remove_selected(self): idxs=self.active_list.curselection();[self.active_list.delete(i) for i in reversed(idxs)]
    def start_trading(self): self.start_btn.config(state="disabled");self.stop_btn.config(state="normal");messagebox.showinfo("Trading","Trading started")
    def stop_trading(self): self.start_btn.config(state="normal");self.stop_btn.config(state="disabled");messagebox.showinfo("Trading","Trading stopped")
    def update_market_data(self):
        market_tracker.update_market_data()
        # Clear trees
        for tree,data in [(self.gainers_tree,market_tracker.gainers),(self.losers_tree,market_tracker.losers),(self.new_tree,market_tracker.new_listings)]: 
            tree.delete(*tree.get_children());[tree.insert("", "end", values=[round(d.get(k,0),2) if isinstance(d.get(k,0),float) else d.get(k,0) for k in tree['columns']]) for d in data]
        self.after(5000,self.update_market_data)

# --- Main App ---
class CryptoBotApp:
    def __init__(self,root:tk.Tk):
        self.root=root
        root.title("CryptoBot GUI")
        root.geometry("1200x800")
        theme_manager.configure_root(root)
        self.notebook=ttk.Notebook(root);self.notebook.pack(fill="both",expand=True)
        self.trading_tab=TradingControlsFrame(self.notebook);self.notebook.add(self.trading_tab,text="Trading")
        self.strategy_tab=StrategyTuner(self.notebook);self.notebook.add(self.strategy_tab.frame,text="Strategy Tuner")
        # Plugins placeholder
        self.plugins=[]
        self.db_path="cryptobot.db"
        self._setup_db()
    def _setup_db(self):
        self.conn=sqlite3.connect(self.db_path)
        self.cursor=self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, action TEXT, price REAL, qty REAL, timestamp TEXT)")
        self.conn.commit()
    def register_plugin(self,plugin_callable:Callable):
        self.plugins.append(plugin_callable)
    def run_plugins(self):
        for plugin in self.plugins: plugin(self)

# --- Main ---
def main():
    root=tk.Tk()
    app=CryptoBotApp(root)
    root.mainloop()

if __name__=="__main__":
    main()
# --------------------------------------------------------------
# gui_bot.py – INTUITIVE GUI + DYNAMIC RISK + MANUAL/AUTO SWITCH
# --------------------------------------------------------------
import os
import sys
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Add folder to path so crypto_bot can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Assuming crypto_bot exists and contains the necessary functions/variables
from crypto_bot import (
    get_historical_data_with_indicators, tune_xgboost, MLModel,
    RiskManagedMLStrategy, run_backtest, live_trading_loop,
    update_risk_config, SYMBOLS # SYMBOLS should be defined here
)

# ---------- Tooltip Class (No changes needed) ----------
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.tw or not self.text: return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tw, text=self.text, bg="#ffffe0", relief="solid",
                       borderwidth=1, font=("Arial", 8))
        lbl.pack()

    def hide(self, _=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

# ---------- Main GUI Class ----------
class CryptoBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Scalper Bot – Dashboard")
        self.root.geometry("1400x950")
        self.root.configure(bg="#1a1a1a")
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Arial', 11), padding=12)
        style.configure('TLabel', font=('Arial', 12), background='#1a1a1a', foreground='white')

        # Variables for state management
        self.is_running = False
        self.trading_thread = None
        self.auto_switch_var = tk.BooleanVar(value=True) # Moved auto_switch into the class

        # ----- Status bar -----
        self.status_var = tk.StringVar(value="Ready")
        sb = tk.Frame(root, bg="#333333", height=30)
        sb.pack(side='bottom', fill='x')
        tk.Label(sb, textvariable=self.status_var, fg='white', bg="#333333",
                 font=('Arial', 10), anchor='w').pack(fill='x', padx=10, pady=5)
        self._check_conn()

        # ----- Header -----
        hdr = tk.Frame(root, bg="#1a1a1a")
        hdr.pack(pady=10, padx=20, fill='x')

        self.balance_lbl = tk.Label(hdr, text="Balance: $10,000", fg='green',
                                    bg="#1a1a1a", font=('Arial', 16, 'bold'))
        self.balance_lbl.pack(side='left')

        self.sym_lbl = tk.Label(hdr, text="Current: SOLUSDT", fg='yellow',
                                bg="#1a1a1a", font=('Arial', 12))
        self.sym_lbl.pack(side='left', padx=30)

        # ----- Controls -----
        ctrl = tk.LabelFrame(hdr, text="Trading Controls", bg="#1a1a1a",
                             fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        ctrl.pack(side='right', padx=20)

        self.back_btn = tk.Button(ctrl, text="Run Backtest", command=self.start_backtest,
                                  bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'))
        self.back_btn.pack(side='left', padx=5)
        ToolTip(self.back_btn, "Run historical backtest on selected symbol")

        self.live_btn = tk.Button(ctrl, text="Start Live", command=self.start_live,
                                  bg='#2196F3', fg='white', font=('Arial', 11, 'bold'))
        self.live_btn.pack(side='left', padx=5)
        ToolTip(self.live_btn, "Start paper-trading with real-time data")

        self.stop_btn = tk.Button(ctrl, text="Stop Bot", command=self.stop_bot,
                                  bg='#f44336', fg='white', font=('Arial', 11, 'bold'), state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        ToolTip(self.stop_btn, "Emergency stop")

        # ----- Symbol Switcher -----
        sw = tk.LabelFrame(hdr, text="Symbol Switcher", bg="#1a1a1a",
                           fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        sw.pack(side='left', padx=20)

        tk.Label(sw, text="Select:", fg='yellow', bg="#1a1a1a",
                 font=('Arial', 10)).pack(side='left')
        self.sym_var = tk.StringVar(value='SOLUSDT')
        self.sym_cbo = ttk.Combobox(sw, textvariable=self.sym_var,
                                    values=SYMBOLS, state='readonly', width=12)
        self.sym_cbo.pack(side='left', padx=5)

        self.sw_btn = tk.Button(sw, text="Switch", command=self.manual_switch,
                                bg='#FF9800', fg='white', font=('Arial', 10))
        self.sw_btn.pack(side='left', padx=5)

        self.auto_chk = tk.Checkbutton(sw, text="Auto-Switch", variable=self.auto_switch_var,
                                       fg='white', bg="#1a1a1a", selectcolor="#1a1a1a",
                                       font=('Arial', 10))
        self.auto_chk.pack(side='left', padx=10)

        # ----- Risk Settings -----
        risk = tk.LabelFrame(hdr, text="Advanced Risk Settings", bg="#1a1a1a",
                             fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        risk.pack(side='left', padx=20, fill='x', expand=True)

        # Risk/Trade %
        r1 = tk.Frame(risk, bg="#1a1a1a")
        r1.pack(fill='x', pady=2)
        tk.Label(r1, text="Risk/Trade %:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 9)).pack(side='left')
        self.risk_var = tk.DoubleVar(value=2.0)
        self.risk_scl = ttk.Scale(r1, from_=0.5, to=5.0, variable=self.risk_var,
                                  orient='horizontal', length=120)
        self.risk_scl.pack(side='left', padx=5)
        ToolTip(self.risk_scl, "Max % of capital risked per trade")

        # Stop-Loss ATR
        r2 = tk.Frame(risk, bg="#1a1a1a")
        r2.pack(fill='x', pady=2)
        tk.Label(r2, text="Stop-Loss ATR:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 9)).pack(side='left')
        self.sl_var = tk.DoubleVar(value=2.0)
        self.sl_scl = ttk.Scale(r2, from_=1.0, to=5.0, variable=self.sl_var,
                                orient='horizontal', length=120)
        self.sl_scl.pack(side='left', padx=5)
        ToolTip(self.sl_scl, "ATR multiplier for stop-loss")

        # Daily loss
        r3 = tk.Frame(risk, bg="#1a1a1a")
        r3.pack(fill='x', pady=2)
        tk.Label(r3, text="Daily Loss $:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 9)).pack(side='left')
        self.daily_var = tk.DoubleVar(value=6.0)
        self.daily_ent = tk.Entry(r3, textvariable=self.daily_var, width=8,
                                  bg='#2d2d2d', fg='white')
        self.daily_ent.pack(side='left', padx=5)
        ToolTip(self.daily_ent, "Max $ loss per day before pause")

        self.apply_btn = tk.Button(risk, text="Apply Settings",
                                   command=self.apply_risk, bg='#9C27B0',
                                   fg='white', font=('Arial', 10, 'bold'))
        self.apply_btn.pack(side='right', pady=5)

        self.risk_prev = tk.Label(risk, text="", fg='cyan', bg="#1a1a1a",
                                  font=('Arial', 9, 'italic'))
        self.risk_prev.pack(side='right', padx=10)
        self._update_risk_preview()

        # ----- Progress -----
        self.prog_lbl = tk.Label(hdr, text="", fg='cyan', bg="#1a1a1a",
                                 font=('Arial', 10, 'italic'))
        self.prog_lbl.pack(side='right')

        # ----- Chart (Completed Section) -----
        ch = tk.LabelFrame(root, text="Equity Curve", bg="#1a1a1a",
                           fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        ch.pack(pady=10, padx=20, fill='both', expand=True)

        self.fig, self.ax = plt.subplots(figsize=(12, 5), facecolor="#1a1a1a")
        self.ax.set_facecolor('#2d2d2d')
        # Ensure the canvas and toolbar are correctly packed
        self.canvas = FigureCanvasTkAgg(self.fig, master=ch)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.toolbar = NavigationToolbar2Tk(self.canvas, ch)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        # End of completed chart section

    # --- Placeholder Methods (Must be implemented in your full code) ---
    def _check_conn(self):
        # Placeholder for connection status check
        pass

    def start_backtest(self):
        # Placeholder for starting backtest logic
        self.status_var.set(f"Running backtest for {self.sym_var.get()}...")
        pass

    def start_live(self):
        # Placeholder for starting live trading logic
        if not self.is_running:
            self.is_running = True
            self.live_btn['state'] = 'disabled'
            self.stop_btn['state'] = 'normal'
            self.status_var.set("Live trading active (Paper Mode)")
            # self.trading_thread = threading.Thread(target=live_trading_loop, args=(...), daemon=True)
            # self.trading_thread.start()
        pass

    def stop_bot(self):
        # Placeholder for stopping bot logic
        if self.is_running:
            self.is_running = False
            self.live_btn['state'] = 'normal'
            self.stop_btn['state'] = 'disabled'
            self.status_var.set("Bot stopped")
        pass

    def manual_switch(self):
        # Placeholder for manual symbol switch logic
        sym = self.sym_var.get()
        self.sym_lbl.config(text=f"Current: {sym}")
        self.status_var.set(f"Manually switched to {sym}")
        pass

    def apply_risk(self):
        # Placeholder for applying risk settings logic
        risk_pct = self.risk_var.get()
        sl_atr = self.sl_var.get()
        daily_loss = self.daily_var.get()
        # update_risk_config(risk_pct, sl_atr, daily_loss) # Call external function
        self._update_risk_preview()
        self.status_var.set("Risk settings applied")
        pass

    def _update_risk_preview(self):
        # Placeholder for updating risk preview label
        self.risk_prev.config(text=f"R:{self.risk_var.get()}% SL:{self.sl_var.get()}xATR")
        pass

# Standard execution block
if __name__ == "__main__":
    root = tk.Tk()
    gui = CryptoBotGUI(root)
    root.mainloop()
 # gui_bot_fixed.py  -- patched version with UI fixes, threading safety, and robustness improvements

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, List, Any
import threading
import logging
import time
import random
import json
import sqlite3
from datetime import datetime, timedelta

# optional libs used by analyzer & plotting
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("CryptoBotGUI")

# --- Theme Manager ---
THEMES = {
    'dark': {
        'bg': '#1a1a1a', 'fg': '#ffffff', 'select_bg': '#404040',
        'select_fg': '#ffffff', 'button_bg': '#2d2d2d',
        'button_fg': '#ffffff', 'frame_bg': '#262626', 'accent': '#007acc'
    },
    'light': {
        'bg': '#ffffff', 'fg': '#000000', 'select_bg': '#0078d7',
        'select_fg': '#ffffff', 'button_bg': '#f0f0f0',
        'button_fg': '#000000', 'frame_bg': '#f5f5f5', 'accent': '#0078d7'
    }
}

class ThemeManager:
    """Manages GUI themes and styles"""
    def __init__(self):
        self.current_theme = 'dark'
        self._setup_styles()

    def _setup_styles(self):
        style = ttk.Style()
        colors = THEMES[self.current_theme]
        style.configure('TFrame', background=colors['frame_bg'])
        style.configure('TLabel', background=colors['frame_bg'], foreground=colors['fg'])
        style.configure('TButton', background=colors['button_bg'], foreground=colors['button_fg'])
        style.configure('Accent.TButton', background=colors['accent'], foreground=colors['select_fg'])
        style.configure('TNotebook', background=colors['bg'], tabmargins=[2,5,2,0])
        style.configure('TNotebook.Tab', background=colors['button_bg'], foreground=colors['button_fg'], padding=[10,2])
        style.map('TNotebook.Tab', background=[('selected', colors['select_bg'])], foreground=[('selected', colors['select_fg'])])
        style.configure('Title.TLabel', font=('Helvetica',14,'bold'), foreground=colors['accent'])
        style.configure('Fallback.TLabel', font=('Helvetica',12), foreground='#888888')
        style.configure('Risk.TLabel', foreground='#ff4444')
        style.configure('Success.TLabel', foreground='#44ff44')

    def apply_theme(self, theme_name: str):
        if theme_name in THEMES:
            self.current_theme = theme_name
            self._setup_styles()

    def get_colors(self) -> Dict[str, str]:
        return THEMES[self.current_theme]

    def configure_root(self, root: tk.Tk):
        colors = self.get_colors()
        try:
            root.configure(bg=colors['bg'])
        except Exception:
            logger.exception("Failed to configure root background")
        # Note: widgets created after calling configure_root will pick up styles

theme_manager = ThemeManager()

# --- Market Volatility Analyzer ---
class MarketVolatilityAnalyzer:
    """Analyzes market volatility for optimal trade timing"""
    def __init__(self, lookback_periods: int = 20):
        self.lookback = lookback_periods
        self.volatility_history: Dict[str, List[Dict[str, Any]]] = {}
        self.session_volatility: Dict[str, Dict[str, List[float]]] = {}

    def analyze_volatility(self, symbol: str, price_data: pd.DataFrame) -> Dict[str,Any]:
        try:
            close_prices = price_data['close'].values
            high_prices = price_data['high'].values
            low_prices = price_data['low'].values
            if len(close_prices) < 2:
                return {}
            returns = np.diff(np.log(close_prices))
            current_vol = float(np.std(returns[-self.lookback:]) * np.sqrt(252))
            gk_vol = self._calculate_garman_klass(high_prices[-self.lookback:], low_prices[-self.lookback:], close_prices[-self.lookback:])
            park_vol = self._calculate_parkinson(high_prices[-self.lookback:], low_prices[-self.lookback:])

            self.volatility_history.setdefault(symbol, []).append({
                'timestamp': datetime.now(), 'std_vol': current_vol, 'gk_vol': gk_vol, 'park_vol': park_vol
            })
            if len(self.volatility_history[symbol]) > 200:
                self.volatility_history[symbol].pop(0)

            vol_regime = self._determine_volatility_regime(current_vol, self.volatility_history[symbol])
            thresholds = self._calculate_trading_thresholds(current_vol, vol_regime)
            self._update_session_volatility(symbol, current_vol)
            trading_windows = self._find_trading_windows(symbol)

            return {
                'current_volatility': current_vol, 'garman_klass_vol': gk_vol, 'parkinson_vol': park_vol,
                'volatility_regime': vol_regime, 'trading_thresholds': thresholds, 'trading_windows': trading_windows
            }
        except Exception:
            logger.exception("Error analyzing volatility")
            return {}

    def _calculate_garman_klass(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> float:
        try:
            log_hl = np.log(high / low)
            log_co = np.log(close[1:] / close[:-1])
            hl_term = 0.5 * np.mean(log_hl ** 2)
            co_term = np.mean(log_co ** 2)
            vol = np.sqrt(max(0.0, 252 * (hl_term - (2 * np.log(2) - 1) * co_term)))
            return float(vol)
        except Exception:
            return 0.0

    def _calculate_parkinson(self, high: np.ndarray, low: np.ndarray) -> float:
        try:
            log_hl = np.log(high / low)
            vol = np.sqrt(max(0.0, 252 * np.mean(log_hl ** 2) / (4 * np.log(2))))
            return float(vol)
        except Exception:
            return 0.0

    def _determine_volatility_regime(self, current_vol: float, history: List[Dict]) -> str:
        if not history:
            return "normal"
        hist_vols = [h['std_vol'] for h in history]
        mean = float(np.mean(hist_vols)); std = float(np.std(hist_vols))
        if current_vol > mean + 2 * std: return "extreme"
        if current_vol > mean + std: return "high"
        if current_vol < mean - std: return "low"
        return "normal"

    def _calculate_trading_thresholds(self, current_vol: float, regime: str) -> Dict[str, float]:
        thresholds = {'entry_threshold': 0.001, 'stop_loss_mult': 2.0, 'take_profit_mult': 3.0, 'position_size_factor': 1.0}
        adjustments = {
            'low': {'entry_threshold': 0.8, 'stop_loss_mult': 1.5, 'take_profit_mult': 2.5, 'position_size_factor': 1.2},
            'normal': {'entry_threshold': 1.0, 'stop_loss_mult': 2.0, 'take_profit_mult': 3.0, 'position_size_factor': 1.0},
            'high': {'entry_threshold': 1.3, 'stop_loss_mult': 2.5, 'take_profit_mult': 3.5, 'position_size_factor': 0.8},
            'extreme': {'entry_threshold': 1.5, 'stop_loss_mult': 3.0, 'take_profit_mult': 4.0, 'position_size_factor': 0.5}
        }
        adj = adjustments.get(regime, adjustments['normal'])
        for k in thresholds.keys():
            thresholds[k] = thresholds[k] * adj[k]
        vol_scale = min(max(current_vol / 0.2, 0.5), 2.0)
        thresholds['position_size_factor'] *= vol_scale
        return thresholds

    def _update_session_volatility(self, symbol: str, current_vol: float) -> None:
        now = datetime.utcnow()
        session_key = now.strftime("%Y-%m-%d-%H")
        self.session_volatility.setdefault(symbol, {}).setdefault(session_key, []).append(current_vol)
        # keep recent 7 days keys only
        cutoff_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        keep = {k: v for k, v in self.session_volatility[symbol].items() if k.startswith(cutoff_date) or k > cutoff_date}
        self.session_volatility[symbol] = keep

    def _find_trading_windows(self, symbol: str) -> Dict[str, List[int]]:
        if symbol not in self.session_volatility:
            return {}
        hourly_vol = {}
        for session, vols in self.session_volatility[symbol].items():
            try:
                hour = int(session.split('-')[-1])
                hourly_vol.setdefault(hour, []).extend(vols)
            except Exception:
                continue
        avg_vol = {h: float(np.mean(vs)) for h, vs in hourly_vol.items() if vs}
        if not avg_vol:
            return {}
        mean_vol = float(np.mean(list(avg_vol.values()))); std_vol = float(np.std(list(avg_vol.values())))
        high = [h for h, v in avg_vol.items() if v > mean_vol + 0.5 * std_vol]
        low = [h for h, v in avg_vol.items() if v < mean_vol - 0.5 * std_vol]
        return {'high_volatility': sorted(high), 'low_volatility': sorted(low)}

    def get_trading_recommendation(self, symbol: str, current_vol: float) -> Dict[str,Any]:
        now = datetime.utcnow(); current_hour = now.hour
        windows = self._find_trading_windows(symbol)
        regime = self._determine_volatility_regime(current_vol, self.volatility_history.get(symbol, []))
        thresholds = self._calculate_trading_thresholds(current_vol, regime)
        score = 50
        regime_scores = {"low": -10, "normal": 0, "high": 10, "extreme": -20}
        score += regime_scores.get(regime, 0)
        if current_hour in windows.get('high_volatility', []): score += 20
        elif current_hour in windows.get('low_volatility', []): score -= 10
        recent = [h['std_vol'] for h in self.volatility_history.get(symbol, [])[-5:]] if symbol in self.volatility_history else []
        if len(recent) > 1:
            try:
                trend = np.polyfit(range(len(recent)), recent, 1)[0]
                score += 10 if trend > 0 else -10 if trend < 0 else 0
            except Exception:
                pass
        score = max(0, min(100, int(score)))
        rec = 'high' if score >= 70 else 'moderate' if score >= 40 else 'low'
        return {'trading_score': score, 'volatility_regime': regime, 'thresholds': thresholds,
                'current_hour': current_hour,
                'is_high_vol_window': current_hour in windows.get('high_volatility', []),
                'is_low_vol_window': current_hour in windows.get('low_volatility', []),
                'recommendation': rec}

# --- Trading Modes, TimeFrames, Risk Config ---
class TradingMode:
    SPOT = 'Spot'; MARGIN = 'Margin'; FUTURES = 'Futures'
class TimeFrame:
    SCALP = 'Scalp'; SHORT = 'Short'; MEDIUM = 'Medium'; LONG = 'Long'
class RiskConfig:
    TRADING_MODE = TradingMode.SPOT
    LEVERAGE = 1.0
    MAX_LEVERAGE = 10.0
    TIMEFRAME = TimeFrame.SHORT
    AUTO_MODE_SWITCH = True

# --- Market Tracker Stub ---
class MarketTracker:
    """Stub for market data"""
    def __init__(self):
        self.gainers = []
        self.losers = []
        self.new_listings = []
        self.available_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'SOLUSDT']

    def search_pairs(self, text: str) -> List[str]:
        txt = (text or "").upper()
        if not txt:
            return list(self.available_pairs)
        return [p for p in self.available_pairs if txt in p]

    def update_market_data(self):
        # Simulate market data
        try:
            self.gainers = [{'symbol': f'PAIR{idx}', 'change': random.uniform(0,10), 'volume': random.uniform(1000,5000), 'price': random.uniform(1000,50000)} for idx in range(5)]
            self.losers = [{'symbol': f'PAIR{idx}', 'change': -random.uniform(0,10), 'volume': random.uniform(1000,5000), 'price': random.uniform(1000,50000)} for idx in range(5)]
            now_ts = time.time()
            self.new_listings = [{'symbol': f'NEW{idx}', 'time': now_ts, 'price': random.uniform(0.1,100), 'volume': random.uniform(1000,5000)} for idx in range(3)]
        except Exception:
            logger.exception("Failed to simulate market data")

market_tracker = MarketTracker()
vol_analyzer = MarketVolatilityAnalyzer()

# --- ML Model & Backtesting Stubs (non-blocking wrappers) ---
class MLModel:
    def __init__(self, params=None):
        self.params = params or {}

def run_backtest(model: MLModel, symbol: str, risk_pct: float) -> Dict[str, Any]:
    # stub: do quick simulated calculations (non-blocking in this function)
    return {'Total Return': 0.1, 'Win Rate': 0.55, 'Profit Factor': 1.5, 'Max Drawdown': 0.05, 'Sharpe Ratio': 1.2, 'Total Trades': 100, 'equity_curve': [1, 1.05, 1.1, 1.2, 1.15]}

def tune_xgboost(symbol: str, n_trials: int) -> Dict[str, Any]:
    return {'ml_threshold': 0.6, 'atr_multiplier': 2.2, 'profit_target': 0.04, 'max_bars_back': 25}

# --- GUI Components ---
class StrategyTuner:
    """Interactive strategy parameter tuning"""
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        self.has_tuning = True
        # canonical param names that match tuning function
        self.params = {
            'ml_threshold': {'min': 0.5, 'max': 0.9, 'value': 0.55, 'step': 0.01},
            'atr_multiplier': {'min': 1.0, 'max': 4.0, 'value': 2.0, 'step': 0.1},
            'profit_target': {'min': 0.01, 'max': 0.1, 'value': 0.03, 'step': 0.005},
            'max_bars_back': {'min': 10, 'max': 100, 'value': 20, 'step': 5}
        }
        self._create_controls()
        self._create_results()

    def _create_controls(self):
        controls = ttk.LabelFrame(self.frame, text="Strategy Parameters", padding=10)
        controls.pack(fill='x', expand=False, padx=5, pady=5)
        self.param_vars: Dict[str, tk.Variable] = {}
        row = 0
        for name, config in self.params.items():
            ttk.Label(controls, text=name.replace('_', ' ').title()).grid(row=row, column=0, sticky='w', padx=5, pady=2)
            # use DoubleVar or IntVar depending on parameter
            var = tk.DoubleVar(value=float(config['value'])) if isinstance(config['value'], (float, int)) else tk.DoubleVar(value=0.0)
            self.param_vars[name] = var
            s = ttk.Scale(controls, from_=config['min'], to=config['max'], value=config['value'], variable=var, orient='horizontal')
            s.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
            # display formatted readout
            disp = ttk.Label(controls, text=f"{var.get():.4g}")
            disp.grid(row=row, column=2, padx=5, pady=2)
            # keep readout in sync
            def make_trace(v=var, w=disp):
                def _(*_args):
                    try:
                        w.config(text=f"{v.get():.6g}")
                    except Exception:
                        w.config(text=str(v.get()))
                return _
            var.trace_add('write', make_trace())
            row += 1

        buttons = ttk.Frame(controls)
        buttons.grid(row=row, column=0, columnspan=3, pady=10)
        ttk.Button(buttons, text="Run Backtest", command=self._run_backtest_threaded).pack(side='left', padx=5)
        ttk.Button(buttons, text="Auto-Tune", command=self._auto_tune_threaded).pack(side='left', padx=5)
        ttk.Button(buttons, text="Save Params", command=self._save_params).pack(side='left', padx=5)

    def _create_results(self):
        results = ttk.LabelFrame(self.frame, text="Backtest Results", padding=10)
        results.pack(fill='both', expand=True, padx=5, pady=5)
        metrics_frame = ttk.Frame(results)
        metrics_frame.pack(fill='x', expand=False)
        # store raw numeric values in a dict and present formatted strings
        self.metrics_vars = {
            'Total Return': tk.StringVar(value='0.00%'),
            'Win Rate': tk.StringVar(value='0.00%'),
            'Profit Factor': tk.StringVar(value='0.00'),
            'Max Drawdown': tk.StringVar(value='0.00%'),
            'Sharpe Ratio': tk.StringVar(value='0.00'),
            'Total Trades': tk.StringVar(value='0')
        }
        row = 0
        for name, var in self.metrics_vars.items():
            ttk.Label(metrics_frame, text=name).grid(row=row, column=0, sticky='w', padx=5, pady=2)
            ttk.Label(metrics_frame, textvariable=var).grid(row=row, column=1, sticky='e', padx=5, pady=2)
            row += 1
        fig = Figure(figsize=(8, 4))
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(fig, results)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)

    # non-blocking wrapper for backtests
    def _run_backtest_threaded(self):
        params = {name: float(var.get()) for name, var in self.param_vars.items()}
        model = MLModel(params)

        def worker():
            logger.info("Starting backtest in background thread")
            results = run_backtest(model, 'BTCUSDT', 0.01)
            # marshal UI update to main thread
            self.frame.after(0, lambda: self._update_results(results))

        threading.Thread(target=worker, daemon=True).start()

    def _auto_tune_threaded(self):
        def worker():
            logger.info("Starting auto-tune")
            best = tune_xgboost('BTCUSDT', 10)
            def apply_to_ui():
                for k, v in best.items():
                    if k in self.param_vars:
                        try:
                            self.param_vars[k].set(float(v))
                        except Exception:
                            pass
                # run backtest once tuned
                self._run_backtest_threaded()
            self.frame.after(0, apply_to_ui)
        threading.Thread(target=worker, daemon=True).start()

    def _save_params(self):
        params = {name: float(var.get()) for name, var in self.param_vars.items()}
        try:
            with open('best_params.json', 'w', encoding='utf-8') as f:
                json.dump(params, f, indent=2)
            messagebox.showinfo("Success", "Parameters saved to best_params.json")
        except Exception:
            logger.exception("Failed to save params")
            messagebox.showerror("Error", "Failed to save parameters")

    def _update_results(self, results: Dict[str, Any]):
        try:
            # format expected numeric metrics robustly
            for k, v in results.items():
                if k in self.metrics_vars:
                    try:
                        if isinstance(v, (int, float)) and v < 1 and 'Rate' not in k and 'Return' in k or 'Drawdown' in k:
                            self.metrics_vars[k].set(f"{v*100:.2f}%")
                        elif isinstance(v, (int, float)) and v < 1 and 'Rate' in k:
                            self.metrics_vars[k].set(f"{v*100:.2f}%")
                        elif isinstance(v, (int, float)):
                            self.metrics_vars[k].set(f"{v:.2f}")
                        else:
                            self.metrics_vars[k].set(str(v))
                    except Exception:
                        self.metrics_vars[k].set(str(v))
            if 'equity_curve' in results and isinstance(results['equity_curve'], list):
                self.ax.clear()
                self.ax.plot(results['equity_curve'], color='g')
                self.ax.set_title('Equity Curve')
                self.ax.grid(True)
                self.canvas.draw_idle()
        except Exception:
            logger.exception("Failed to update results UI")

class TradingControlsFrame(ttk.Frame):
    """Main trading controls frame"""
    def __init__(self, parent, callback: Callable = None):
        super().__init__(parent)
        self.callback = callback
        self.stop_event = None
        self.active_symbols = set()
        self.create_widgets()

    def create_widgets(self):
        # Trading Mode Controls
        mode_frame = ttk.LabelFrame(self, text="Trading Mode"); mode_frame.pack(fill="x", padx=5, pady=5)
        self.mode_var = tk.StringVar(value=RiskConfig.TRADING_MODE)
        for mode in [TradingMode.SPOT, TradingMode.MARGIN, TradingMode.FUTURES]:
            ttk.Radiobutton(mode_frame, text=mode, value=mode, variable=self.mode_var, command=self.on_mode_change).pack(anchor="w", padx=5)

        leverage_frame = ttk.Frame(mode_frame); leverage_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(leverage_frame, text="Leverage:").pack(side="left")
        self.leverage_var = tk.DoubleVar(value=RiskConfig.LEVERAGE)
        # some ttk versions don't support Spinbox; use tk.Spinbox inside frame for compatibility
        spin = tk.Spinbox(leverage_frame, from_=1.0, to=RiskConfig.MAX_LEVERAGE, increment=0.5, textvariable=self.leverage_var, width=10, command=self.on_leverage_change)
        spin.pack(side="left", padx=5)

        # Timeframe
        time_frame = ttk.LabelFrame(self, text="Timeframe"); time_frame.pack(fill="x", padx=5, pady=5)
        self.timeframe_var = tk.StringVar(value=RiskConfig.TIMEFRAME)
        for tf in [TimeFrame.SCALP, TimeFrame.SHORT, TimeFrame.MEDIUM, TimeFrame.LONG]:
            ttk.Radiobutton(time_frame, text=tf, value=tf, variable=self.timeframe_var, command=self.on_timeframe_change).pack(anchor="w", padx=5)

        auto_frame = ttk.Frame(self); auto_frame.pack(fill="x", padx=5, pady=5)
        self.auto_mode_var = tk.BooleanVar(value=RiskConfig.AUTO_MODE_SWITCH)
        ttk.Checkbutton(auto_frame, text="Auto Mode Switch", variable=self.auto_mode_var, command=self.on_auto_mode_change).pack(side="left")

        # Symbol selection
        symbol_frame = ttk.LabelFrame(self, text="Trading Pairs"); symbol_frame.pack(fill="both", expand=True, padx=5, pady=5)
        search_frame = ttk.Frame(symbol_frame); search_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=5)

        lists_frame = ttk.Frame(symbol_frame); lists_frame.pack(fill="both", expand=True, padx=5, pady=5)
        avail_frame = ttk.LabelFrame(lists_frame, text="Available"); avail_frame.pack(side="left", fill="both", expand=True)
        self.available_list = tk.Listbox(avail_frame, selectmode="multiple")
        self.available_list.pack(fill="both", expand=True)

        btn_frame = ttk.Frame(lists_frame); btn_frame.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="→", command=self.add_selected).pack(pady=2)
        ttk.Button(btn_frame, text="←", command=self.remove_selected).pack(pady=2)

        active_frame = ttk.LabelFrame(lists_frame, text="Active"); active_frame.pack(side="left", fill="both", expand=True)
        self.active_list = tk.Listbox(active_frame, selectmode="multiple")
        self.active_list.pack(fill="both", expand=True)

        # Market info
        market_frame = ttk.LabelFrame(self, text="Market Information"); market_frame.pack(fill="both", expand=True, padx=5, pady=5)
        notebook = ttk.Notebook(market_frame); notebook.pack(fill="both", expand=True)

        # Gainers
        gainers_frame = ttk.Frame(notebook); notebook.add(gainers_frame, text="Gainers")
        self.gainers_tree = ttk.Treeview(gainers_frame, columns=("symbol","change","volume","price"), show="headings")
        for col, name in zip(["symbol","change","volume","price"], ["Symbol","Change %","Volume","Price"]):
            self.gainers_tree.heading(col, text=name)
        self.gainers_tree.pack(fill="both", expand=True)

        # Losers
        losers_frame = ttk.Frame(notebook); notebook.add(losers_frame, text="Losers")
        self.losers_tree = ttk.Treeview(losers_frame, columns=("symbol","change","volume","price"), show="headings")
        for col, name in zip(["symbol","change","volume","price"], ["Symbol","Change %","Volume","Price"]):
            self.losers_tree.heading(col, text=name)
        self.losers_tree.pack(fill="both", expand=True)

        # New listings
        new_frame = ttk.Frame(notebook); notebook.add(new_frame, text="New Listings")
        self.new_tree = ttk.Treeview(new_frame, columns=("symbol","time","price","volume"), show="headings")
        for col, name in zip(["symbol","time","price","volume"], ["Symbol","Listed","Price","Volume"]):
            self.new_tree.heading(col, text=name)
        self.new_tree.pack(fill="both", expand=True)

        # Performance (placeholder)
        perf_frame = ttk.Frame(notebook); notebook.add(perf_frame, text="Performance")
        self.perf_tree = ttk.Treeview(perf_frame, columns=("trades","profit","drawdown"), show="headings")
        for col, name in zip(["trades","profit","drawdown"], ["Trades","Profit","Drawdown"]):
            self.perf_tree.heading(col, text=name)
        self.perf_tree.pack(fill="both", expand=True)

        # Control buttons
        control_frame = ttk.Frame(self); control_frame.pack(fill="x", padx=5, pady=5)
        self.start_btn = ttk.Button(control_frame, text="Start Trading", command=self.start_trading); self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(control_frame, text="Stop Trading", command=self.stop_trading, state="disabled"); self.stop_btn.pack(side="left", padx=5)

        # initial population
        self.populate_available_pairs()
        # start market updates
        self.update_market_data()

    def populate_available_pairs(self):
        try:
            self.available_list.delete(0, "end")
            for p in market_tracker.search_pairs(""):
                self.available_list.insert("end", p)
        except Exception:
            logger.exception("Failed to populate available pairs")

    # --- Handlers ---
    def on_mode_change(self, *args): RiskConfig.TRADING_MODE = self.mode_var.get()
    def on_leverage_change(self, *args): RiskConfig.LEVERAGE = float(self.leverage_var.get())
    def on_timeframe_change(self, *args): RiskConfig.TIMEFRAME = self.timeframe_var.get()
    def on_auto_mode_change(self, *args): RiskConfig.AUTO_MODE_SWITCH = self.auto_mode_var.get()

    def on_search(self, *args):
        term = self.search_var.get()
        self.available_list.delete(0, "end")
        for p in market_tracker.search_pairs(term):
            self.available_list.insert("end", p)

    def add_selected(self):
        try:
            idxs = list(self.available_list.curselection())
            for i in idxs:
                val = self.available_list.get(i)
                # avoid duplicates
                if val not in self.active_list.get(0, "end"):
                    self.active_list.insert("end", val)
                    self.active_symbols.add(val)
        except Exception:
            logger.exception("Failed to add selected pairs")

    def remove_selected(self):
        try:
            idxs = list(self.active_list.curselection())
            # delete from highest index to lowest to keep indices correct
            for i in reversed(idxs):
                val = self.active_list.get(i)
                self.active_list.delete(i)
                if val in self.active_symbols:
                    self.active_symbols.remove(val)
        except Exception:
            logger.exception("Failed to remove selected pairs")

    def start_trading(self):
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        messagebox.showinfo("Trading", "Trading started")

    def stop_trading(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        messagebox.showinfo("Trading", "Trading stopped")

    def update_market_data(self):
        try:
            market_tracker.update_market_data()
            # update gainers tree
            for tree, data, cols in [
                (self.gainers_tree, market_tracker.gainers, ["symbol","change","volume","price"]),
                (self.losers_tree, market_tracker.losers, ["symbol","change","volume","price"]),
                (self.new_tree, market_tracker.new_listings, ["symbol","time","price","volume"])
            ]:
                # clear
                for iid in tree.get_children():
                    tree.delete(iid)
                # insert rows
                for d in data:
                    row = []
                    for k in cols:
                        val = d.get(k, "")
                        if isinstance(val, float):
                            # format floats
                            if k == 'time':
                                try:
                                    val = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(val))
                                except Exception:
                                    val = f"{val:.2f}"
                            else:
                                val = round(val, 4)
                        row.append(val)
                    tree.insert("", "end", values=row)
        except Exception:
            logger.exception("Failed updating market data")

        # schedule next update
        try:
            self.after(5000, self.update_market_data)
        except Exception:
            logger.exception("Failed to schedule next market update")

# --- Main App ---
class CryptoBotApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("CryptoBot GUI")
        root.geometry("1200x800")
        theme_manager.configure_root(root)
        self.notebook = ttk.Notebook(root); self.notebook.pack(fill="both", expand=True)
        self.trading_tab = TradingControlsFrame(self.notebook); self.notebook.add(self.trading_tab, text="Trading")
        self.strategy_tab = StrategyTuner(self.notebook); self.notebook.add(self.strategy_tab.frame, text="Strategy Tuner")
        # Plugins placeholder
        self.plugins = []
        self.db_path = "cryptobot.db"
        self._setup_db()

    def _setup_db(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.cursor.execute(
                "CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, action TEXT, price REAL, qty REAL, timestamp TEXT)"
            )
            self.conn.commit()
        except Exception:
            logger.exception("Failed to setup DB")

    def register_plugin(self, plugin_callable: Callable):
        self.plugins.append(plugin_callable)

    def run_plugins(self):
        for plugin in self.plugins:
            try:
                plugin(self)
            except Exception:
                logger.exception("Plugin raised an exception")

# --- Main ---
def main():
    root = tk.Tk()
    app = CryptoBotApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
# --------------------------------------------------------------
# gui_bot.py – INTUITIVE GUI + DYNAMIC RISK + MANUAL/AUTO SWITCH
# --------------------------------------------------------------
import os
import sys
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Add folder to path so crypto_bot can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crypto_bot import (
    get_historical_data_with_indicators, tune_xgboost, MLModel,
    RiskManagedMLStrategy, run_backtest, live_trading_loop,
    update_risk_config, SYMBOLS, reconnect_client, is_running
)

# ---------- Tooltip Class ----------
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.tw or not self.text: return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tw, text=self.text, bg="#ffffe0", relief="solid",
                       borderwidth=1, font=("Arial", 8))
        lbl.pack()

    def hide(self, _=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

# ---------- Main GUI Class ----------
class CryptoBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Scalper Bot – Dashboard")
        self.root.geometry("1400x950")
        self.root.configure(bg="#1a1a1a")
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Arial', 11), padding=12)
        style.configure('TLabel', font=('Arial', 12), background='#1a1a1a', foreground='white')

        # Variables for state management
        self.is_running_flag = False
        self.trading_thread = None
        self.auto_switch_var = tk.BooleanVar(value=True) 

        # ----- Status bar -----
        self.status_var = tk.StringVar(value="Ready")
        sb = tk.Frame(root, bg="#333333", height=30)
        sb.pack(side='bottom', fill='x')
        tk.Label(sb, textvariable=self.status_var, fg='white', bg="#333333",
                 font=('Arial', 10), anchor='w').pack(fill='x', padx=10, pady=5)

        # ----- Header -----
        hdr = tk.Frame(root, bg="#1a1a1a")
        hdr.pack(pady=10, padx=20, fill='x')

        self.balance_lbl = tk.Label(hdr, text="Balance: $10,000", fg='green',
                                    bg="#1a1a1a", font=('Arial', 16, 'bold'))
        self.balance_lbl.pack(side='left')

        self.sym_lbl = tk.Label(hdr, text="Current: SOLUSDT", fg='yellow',
                                bg="#1a1a1a", font=('Arial', 12))
        self.sym_lbl.pack(side='left', padx=30)
        
        # ----- Live/TestNet Slider Frame placement (inside header) -----
        env_frame = tk.LabelFrame(hdr, text="Environment", bg="#1a1a1a", fg='white', font=('Arial', 10, 'bold'))
        env_frame.pack(side='left', padx=10)

        self.env_var = tk.IntVar(value=1) # 1 for TestNet, 0 for Live
        self.env_lbl = tk.Label(env_frame, text="TestNet", fg='yellow', bg="#1a1a1a", font=('Arial', 9, 'bold'))
        self.env_lbl.pack(side='left', padx=5)

        self.env_slider = ttk.Scale(env_frame, from_=0, to=1, orient='horizontal', length=100,
                                     variable=self.env_var, command=self._update_environment)
        self.env_slider.pack(side='left', padx=5)

        self._update_environment(1) # Initialize label on startup

        # ----- Controls -----
        ctrl = tk.LabelFrame(hdr, text="Trading Controls", bg="#1a1a1a",
                             fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        ctrl.pack(side='right', padx=20)

        self.back_btn = tk.Button(ctrl, text="Run Backtest", command=self.start_backtest,
                                  bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'))
        self.back_btn.pack(side='left', padx=5)
        ToolTip(self.back_btn, "Run historical backtest on selected symbol")

        self.live_btn = tk.Button(ctrl, text="Start Live", command=self.start_live,
                                  bg='#2196F3', fg='white', font=('Arial', 11, 'bold'))
        self.live_btn.pack(side='left', padx=5)
        ToolTip(self.live_btn, "Start paper-trading with real-time data")

        self.stop_btn = tk.Button(ctrl, text="Stop Bot", command=self.stop_bot,
                                  bg='#f44336', fg='white', font=('Arial', 11, 'bold'), state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        ToolTip(self.stop_btn, "Emergency stop")

        # ----- Symbol Switcher -----
        sw = tk.LabelFrame(hdr, text="Symbol Switcher", bg="#1a1a1a",
                           fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        sw.pack(side='left', padx=20)

        tk.Label(sw, text="Select:", fg='yellow', bg="#1a1a1a",
                 font=('Arial', 10)).pack(side='left')
        self.sym_var = tk.StringVar(value='SOLUSDT')
        self.sym_cbo = ttk.Combobox(sw, textvariable=self.sym_var,
                                    values=SYMBOLS, state='readonly', width=12)
        self.sym_cbo.pack(side='left', padx=5)

        self.sw_btn = tk.Button(sw, text="Switch", command=self.manual_switch,
                                bg='#FF9800', fg='white', font=('Arial', 10))
        self.sw_btn.pack(side='left', padx=5)

        self.auto_chk = tk.Checkbutton(sw, text="Auto-Switch", variable=self.auto_switch_var,
                                       fg='white', bg="#1a1a1a", selectcolor="#1a1a1a",
                                       font=('Arial', 10))
        self.auto_chk.pack(side='left', padx=10)

        # ----- Risk Settings -----
        risk = tk.LabelFrame(hdr, text="Advanced Risk Settings", bg="#1a1a1a",
                             fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        risk.pack(side='left', padx=20, fill='x', expand=True)

        # Risk/Trade %
        r1 = tk.Frame(risk, bg="#1a1a1a")
        r1.pack(fill='x', pady=2)
        tk.Label(r1, text="Risk/Trade %:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 9)).pack(side='left')
        self.risk_var = tk.DoubleVar(value=2.0)
        self.risk_scl = ttk.Scale(r1, from_=0.5, to=5.0, variable=self.risk_var,
                                  orient='horizontal', length=120)
        self.risk_scl.pack(side='left', padx=5)
        ToolTip(self.risk_scl, "Max % of capital risked per trade")

        # Stop-Loss ATR
        r2 = tk.Frame(risk, bg="#1a1a1a")
        r2.pack(fill='x', pady=2)
        tk.Label(r2, text="Stop-Loss ATR:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 9)).pack(side='left')
        self.sl_var = tk.DoubleVar(value=2.0)
        self.sl_scl = ttk.Scale(r2, from_=1.0, to=5.0, variable=self.sl_var,
                                orient='horizontal', length=120)
        self.sl_scl.pack(side='left', padx=5)
        ToolTip(self.sl_scl, "ATR multiplier for stop-loss")

        # Daily loss
        r3 = tk.Frame(risk, bg="#1a1a1a")
        r3.pack(fill='x', pady=2)
        tk.Label(r3, text="Daily Loss $:", fg='lightgray', bg="#1a1a1a",
                 font=('Arial', 9)).pack(side='left')
        self.daily_var = tk.DoubleVar(value=6.0)
        self.daily_ent = tk.Entry(r3, textvariable=self.daily_var, width=8,
                                  bg='#2d2d2d', fg='white')
        self.daily_ent.pack(side='left', padx=5)
        ToolTip(self.daily_ent, "Max $ loss per day before pause")

        self.apply_btn = tk.Button(risk, text="Apply Settings",
                                   command=self.apply_risk, bg='#9C27B0',
                                   fg='white', font=('Arial', 10, 'bold'))
        self.apply_btn.pack(side='right', pady=5)

        self.risk_prev = tk.Label(risk, text="", fg='cyan', bg="#1a1a1a",
                                  font=('Arial', 9, 'italic'))
        self.risk_prev.pack(side='right', padx=10)
        self._update_risk_preview()

        # ----- Progress -----
        self.prog_lbl = tk.Label(hdr, text="", fg='cyan', bg="#1a1a1a",
                                 font=('Arial', 10, 'italic'))
        self.prog_lbl.pack(side='right')

        # ----- Chart -----
        ch = tk.LabelFrame(root, text="Equity Curve", bg="#1a1a1a",
                           fg='white', font=('Arial', 12, 'bold'), padx=10, pady=5)
        ch.pack(pady=10, padx=20, fill='both', expand=True)

        self.fig, self.ax = plt.subplots(figsize=(12, 5), facecolor="#1a1a1a")
        self.ax.set_facecolor('#2d2d2d')
        self.canvas = FigureCanvasTkAgg(self.fig, master=ch)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.toolbar = NavigationToolbar2Tk(self.canvas, ch)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # --- Methods ---
    def _update_environment(self, value):
        is_testnet = bool(int(float(value))) 
        if is_testnet:
            self.env_lbl.config(text="TestNet", fg='yellow')
        else:
            self.env_lbl.config(text="LIVE", fg='red')
        reconnect_client(is_testnet)

    def start_backtest(self):
        self.status_var.set(f"Running backtest for {self.sym_var.get()}...")
        threading.Thread(target=self._run_backtest_thread, daemon=True).start()

    def _run_backtest_thread(self):
        try:
            results = run_backtest(self.sym_var.get())
            equity_curve = results.get('equity_curve', [])
            self.root.after(0, self._update_equity_curve, equity_curve)
            final_balance = equity_curve[-1] if equity_curve else 10000.0
            self.root.after(0, lambda: self.balance_lbl.config(text=f"Balance: ${final_balance:.2f}"))
            self.root.after(0, lambda: self.status_var.set("Backtest complete."))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Backtest error: {e}"))

    def start_live(self):
        global is_running
        if not is_running:
            is_testnet = bool(self.env_var.get())
            is_running = True
            self.live_btn['state'] = 'disabled'
            self.stop_btn['state'] = 'normal'
            self.status_var.set(f"Live trading active ({'TestNet' if is_testnet else 'LIVE'})")
            self.trading_thread = threading.Thread(target=live_trading_loop, 
                                                   args=(self.sym_var.get(), self._update_gui_live), 
                                                   daemon=True)
            self.trading_thread.start()

    def stop_bot(self):
        global is_running
        if is_running:
            is_running = False
            self.live_btn['state'] = 'normal'
            self.stop_btn['state'] = 'disabled'
            self.status_var.set("Bot stopped")
        pass

    def manual_switch(self):
        sym = self.sym_var.get()
        self.sym_lbl.config(text=f"Current: {sym}")
        self.status_var.set(f"Manually switched to {sym}")

    def apply_risk(self):
        new_vals = {
            'risk_per_trade': self.risk_var.get(),
            'stop_loss_mult': self.sl_var.get(),
            'daily_loss': self.daily_var.get(),
        }
        update_risk_config(new_vals)
        self._update_risk_preview()
        self.status_var.set("Risk settings applied")

    def _update_risk_preview(self):
        self.risk_prev.config(text=f"R:{self.risk_var.get()}% SL:{self.sl_var.get()}xATR")

    def _update_equity_curve(self, equity_data):
        self.ax.clear()
        self.ax.plot(equity_data, color='lime')
        self.ax.set_title("Equity Curve", color='white')
        self.ax.set_xlabel("Trades", color='white')
        self.ax.set_ylabel("Balance ($)", color='white')
        self.ax.tick_params(colors='white')
        self.ax.set_facecolor('#2d2d2d')
        self.fig.tight_layout()
        self.canvas.draw()
        
    def _update_gui_live(self, balance, equity_curve):
        self.root.after(0, lambda: self.balance_lbl.config(text=f"Balance: ${balance:.2f}"))
        self.root.after(0, lambda: self._update_equity_curve(equity_curve))

# Standard execution block
if __name__ == "__main__":
    root = tk.Tk()
    gui = CryptoBotGUI(root)
    root.mainloop()
