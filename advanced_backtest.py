"""
Advanced Backtesting System
Provides comprehensive backtesting with realistic simulation
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
import logging
from logging_utils import get_logger
import json
import matplotlib.pyplot as plt
import seaborn as sns

logger = get_logger(__name__)

class BacktestEngine:
    """Advanced backtesting engine with realistic simulation"""
    
    def __init__(self,
                 initial_capital: float = 10000.0,
                 commission_rate: float = 0.001,
                 slippage_model: str = "basic"):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_model = slippage_model
        
        # Performance tracking
        self.trades = []
        self.equity_curve = []
        self.positions = {}
        self.metrics = {}
        
        # Market impact simulation
        self._market_impact = self._create_market_impact_model()
        
    def run_backtest(self,
                    strategy: Callable,
                    data: Dict[str, pd.DataFrame],
                    params: Dict = None,
                    constraints: Dict = None) -> Dict:
        """
        Run full backtest with market impact and constraints
        """
        try:
            # Reset state
            self._reset_state()
            
            # Setup tracking
            results = {
                symbol: {
                    'trades': [],
                    'equity': [],
                    'drawdown': [],
                    'exposure': []
                }
                for symbol in data.keys()
            }
            
            # Align timestamps across symbols
            aligned_data = self._align_data(data)
            
            # Run simulation
            for timestamp in aligned_data.index:
                # Get current market state
                market_state = {
                    symbol: df.loc[timestamp]
                    for symbol, df in aligned_data.items()
                }
                
                # Apply strategy
                signals = strategy(market_state, self.positions, params)
                
                # Execute trades with constraints
                self._execute_trades(signals, market_state, constraints)
                
                # Update metrics
                self._update_metrics(timestamp, market_state)
                
                # Record state
                self._record_state(timestamp, results)
                
            # Calculate final metrics
            self.metrics = self._calculate_metrics(results)
            
            return {
                'metrics': self.metrics,
                'trades': self.trades,
                'equity_curve': self.equity_curve,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return {}
            
    def _reset_state(self):
        """Reset backtest state"""
        self.trades = []
        self.equity_curve = []
        self.positions = {}
        self.metrics = {}
        self.current_capital = self.initial_capital
        
    def _align_data(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Align data across symbols to common timestamp"""
        try:
            # Convert all dataframes to common index
            aligned = {}
            for symbol, df in data.items():
                df = df.copy()
                df.index = pd.to_datetime(df.index)
                aligned[symbol] = df
                
            # Find common timestamps
            common_index = None
            for df in aligned.values():
                if common_index is None:
                    common_index = df.index
                else:
                    common_index = common_index.intersection(df.index)
                    
            # Reindex all dataframes
            return {
                symbol: df.reindex(common_index)
                for symbol, df in aligned.items()
            }
            
        except Exception as e:
            logger.error(f"Data alignment error: {e}")
            return data
            
    def _execute_trades(self,
                       signals: Dict[str, float],
                       market_state: Dict[str, pd.Series],
                       constraints: Dict) -> None:
        """Execute trades with market impact and constraints"""
        try:
            for symbol, signal in signals.items():
                if symbol not in market_state:
                    continue
                    
                current_price = market_state[symbol]['close']
                
                # Apply position constraints
                max_position = constraints.get('max_position_size', float('inf'))
                
                # Calculate position size
                size = self._calculate_position_size(
                    signal,
                    current_price,
                    max_position
                )
                
                # Check if trade is valid
                if not self._validate_trade(size, current_price, constraints):
                    continue
                    
                # Calculate market impact
                impact_price = self._calculate_market_impact(
                    symbol,
                    size,
                    current_price,
                    market_state[symbol]
                )
                
                # Execute trade
                self._execute_trade(
                    symbol,
                    size,
                    impact_price,
                    market_state[symbol].name
                )
                
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            
    def _calculate_position_size(self,
                               signal: float,
                               price: float,
                               max_position: float) -> float:
        """Calculate position size with constraints"""
        try:
            # Base size on portfolio value
            portfolio_value = self.current_capital + sum(
                pos['size'] * price
                for pos in self.positions.values()
            )
            
            # Risk-based sizing
            risk_amount = portfolio_value * 0.02  # 2% risk per trade
            size = risk_amount / price
            
            # Apply constraints
            size = min(size, max_position)
            
            # Scale by signal strength (-1 to 1)
            size *= abs(signal)
            
            # Round to appropriate precision
            return round(size, 8)
            
        except Exception as e:
            logger.error(f"Position size calculation error: {e}")
            return 0.0
            
    def _validate_trade(self,
                       size: float,
                       price: float,
                       constraints: Dict) -> bool:
        """Validate trade against constraints"""
        try:
            # Check minimum size
            if abs(size) < constraints.get('min_position_size', 0.0001):
                return False
                
            # Check capital requirements
            cost = size * price
            if cost > self.current_capital:
                return False
                
            # Check maximum drawdown
            if constraints.get('max_drawdown'):
                current_dd = self._calculate_drawdown()
                if current_dd > constraints['max_drawdown']:
                    return False
                    
            # Check daily loss limit
            if constraints.get('daily_loss_limit'):
                today_pnl = self._calculate_daily_pnl()
                if today_pnl < -constraints['daily_loss_limit']:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Trade validation error: {e}")
            return False
            
    def _calculate_market_impact(self,
                               symbol: str,
                               size: float,
                               price: float,
                               market_data: pd.Series) -> float:
        """Calculate price impact of trade"""
        try:
            if self.slippage_model == "basic":
                # Simple percentage slippage
                impact = price * 0.0001 * abs(size)  # 1bp per unit
                return price + (impact if size > 0 else -impact)
                
            elif self.slippage_model == "volume":
                # Volume-based impact
                avg_volume = market_data.get('volume', 1000)
                volume_ratio = abs(size) / avg_volume
                impact = price * 0.0001 * (volume_ratio ** 0.5)
                return price + (impact if size > 0 else -impact)
                
            elif self.slippage_model == "advanced":
                # Use market impact model
                return self._market_impact(symbol, size, price, market_data)
                
            return price
            
        except Exception as e:
            logger.error(f"Market impact calculation error: {e}")
            return price
            
    def _execute_trade(self,
                      symbol: str,
                      size: float,
                      price: float,
                      timestamp: datetime) -> None:
        """Execute trade and update state"""
        try:
            # Calculate costs
            commission = abs(size * price * self.commission_rate)
            total_cost = (size * price) + commission
            
            # Update capital
            self.current_capital -= total_cost
            
            # Update position
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'size': 0,
                    'cost_basis': 0
                }
                
            old_position = self.positions[symbol]['size']
            old_cost = self.positions[symbol]['cost_basis']
            
            # Update position
            new_size = old_position + size
            if new_size == 0:
                del self.positions[symbol]
            else:
                self.positions[symbol] = {
                    'size': new_size,
                    'cost_basis': ((old_cost * old_position) + (price * size)) / new_size
                }
                
            # Record trade
            self.trades.append({
                'timestamp': timestamp,
                'symbol': symbol,
                'size': size,
                'price': price,
                'commission': commission,
                'total_cost': total_cost
            })
            
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            
    def _update_metrics(self,
                       timestamp: datetime,
                       market_state: Dict[str, pd.Series]) -> None:
        """Update performance metrics"""
        try:
            # Calculate portfolio value
            portfolio_value = self.current_capital
            for symbol, position in self.positions.items():
                if symbol in market_state:
                    current_price = market_state[symbol]['close']
                    portfolio_value += position['size'] * current_price
                    
            # Update equity curve
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': portfolio_value,
                'cash': self.current_capital,
                'positions': len(self.positions)
            })
            
        except Exception as e:
            logger.error(f"Metrics update error: {e}")
            
    def _record_state(self,
                     timestamp: datetime,
                     results: Dict) -> None:
        """Record current state to results"""
        try:
            equity = self.equity_curve[-1]['equity']
            
            for symbol in results.keys():
                results[symbol]['equity'].append(equity)
                
                # Calculate drawdown
                peak = max(results[symbol]['equity'])
                dd = (peak - equity) / peak if peak > 0 else 0
                results[symbol]['drawdown'].append(dd)
                
                # Calculate exposure
                exposure = 0
                if symbol in self.positions:
                    exposure = abs(self.positions[symbol]['size'])
                results[symbol]['exposure'].append(exposure)
                
        except Exception as e:
            logger.error(f"State recording error: {e}")
            
    def _calculate_metrics(self, results: Dict) -> Dict:
        """Calculate comprehensive performance metrics"""
        try:
            metrics = {}
            
            for symbol, data in results.items():
                equity = pd.Series(data['equity'])
                returns = equity.pct_change()
                
                metrics[symbol] = {
                    'total_return': (equity.iloc[-1] / equity.iloc[0]) - 1,
                    'annualized_return': ((equity.iloc[-1] / equity.iloc[0]) ** (252 / len(equity)) - 1),
                    'max_drawdown': max(data['drawdown']),
                    'sharpe_ratio': np.sqrt(252) * returns.mean() / returns.std() if len(returns) > 1 else 0,
                    'sortino_ratio': self._calculate_sortino(returns),
                    'win_rate': self._calculate_win_rate(symbol),
                    'profit_factor': self._calculate_profit_factor(symbol),
                    'avg_trade': self._calculate_avg_trade(symbol),
                    'num_trades': len([t for t in self.trades if t['symbol'] == symbol])
                }
                
            return metrics
            
        except Exception as e:
            logger.error(f"Metrics calculation error: {e}")
            return {}
            
    def _calculate_sortino(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio"""
        try:
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                downside_std = np.sqrt(252) * negative_returns.std()
                return returns.mean() * 252 / downside_std if downside_std > 0 else 0
            return 0
            
        except Exception as e:
            logger.error(f"Sortino calculation error: {e}")
            return 0
            
    def _calculate_win_rate(self, symbol: str) -> float:
        """Calculate win rate for symbol"""
        try:
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            if not symbol_trades:
                return 0
                
            wins = sum(1 for t in symbol_trades if t['total_cost'] > 0)
            return wins / len(symbol_trades)
            
        except Exception as e:
            logger.error(f"Win rate calculation error: {e}")
            return 0
            
    def _calculate_profit_factor(self, symbol: str) -> float:
        """Calculate profit factor for symbol"""
        try:
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            if not symbol_trades:
                return 0
                
            gains = sum(t['total_cost'] for t in symbol_trades if t['total_cost'] > 0)
            losses = abs(sum(t['total_cost'] for t in symbol_trades if t['total_cost'] < 0))
            
            return gains / losses if losses > 0 else float('inf')
            
        except Exception as e:
            logger.error(f"Profit factor calculation error: {e}")
            return 0
            
    def _calculate_avg_trade(self, symbol: str) -> float:
        """Calculate average trade profit for symbol"""
        try:
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            if not symbol_trades:
                return 0
                
            return sum(t['total_cost'] for t in symbol_trades) / len(symbol_trades)
            
        except Exception as e:
            logger.error(f"Average trade calculation error: {e}")
            return 0
            
    def generate_report(self, output_path: str = None) -> None:
        """Generate detailed backtest report"""
        try:
            report = {
                'summary': self.metrics,
                'trades': [t for t in self.trades],
                'equity_curve': [e for e in self.equity_curve]
            }
            
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                    
            # Generate plots
            self._plot_results()
            
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            
    def _plot_results(self) -> None:
        """Generate performance visualization"""
        try:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 16))
            
            # Equity curve
            equity = pd.DataFrame(self.equity_curve)
            equity.set_index('timestamp', inplace=True)
            
            ax1.plot(equity.index, equity['equity'], 'b-', label='Portfolio Value')
            ax1.set_title('Equity Curve')
            ax1.grid(True)
            ax1.legend()
            
            # Drawdown
            rolling_max = equity['equity'].expanding().max()
            drawdown = (rolling_max - equity['equity']) / rolling_max
            
            ax2.fill_between(equity.index, drawdown, 0, color='r', alpha=0.3)
            ax2.set_title('Drawdown')
            ax2.grid(True)
            
            # Trade distribution
            trades_df = pd.DataFrame(self.trades)
            if not trades_df.empty:
                sns.histplot(data=trades_df, x='total_cost', bins=50, ax=ax3)
                ax3.set_title('Trade P&L Distribution')
                
            plt.tight_layout()
            
        except Exception as e:
            logger.error(f"Plot generation error: {e}")
            
    def _create_market_impact_model(self) -> Callable:
        """Create advanced market impact model"""
        def impact_model(symbol: str,
                        size: float,
                        price: float,
                        market_data: pd.Series) -> float:
            try:
                # Get market metrics
                volume = market_data.get('volume', 1000)
                volatility = market_data.get('volatility', 0.01)
                
                # Calculate impact components
                temporary_impact = price * 0.0001 * (abs(size) / volume) ** 0.5
                permanent_impact = price * 0.0001 * volatility * (abs(size) / volume)
                
                # Combine impacts
                total_impact = temporary_impact + permanent_impact
                return price + (total_impact if size > 0 else -total_impact)
                
            except Exception as e:
                logger.error(f"Market impact model error: {e}")
                return price
                
        return impact_model