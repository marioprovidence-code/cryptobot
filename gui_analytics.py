"""
CryptoBot Analytics Component
Provides trade analytics, performance metrics and reports.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import os
import logging

try:
    import pandas as pd
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_ANALYTICS = True
except ImportError:
    HAS_ANALYTICS = False


class Analytics:
    """Trade analytics and performance metrics"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize analytics component"""
        self.parent = parent
        self.has_analytics = HAS_ANALYTICS
        self.trades_df = None
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        
        if not self.has_analytics:
            self._show_fallback()
            return
            
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Create tabs
        self._create_performance_tab()
        self._create_trades_tab()
        self._create_reports_tab()
        
    def _show_fallback(self) -> None:
        """Show message when deps not available"""
        msg = "Analytics require pandas & matplotlib"
        ttk.Label(
            self.frame,
            text=msg,
            style='Fallback.TLabel'
        ).pack(expand=True)
        
    def _create_performance_tab(self) -> None:
        """Create performance metrics tab"""
        if not self.has_analytics:
            return
            
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Performance')
        
        # Metrics frame
        metrics_frame = ttk.LabelFrame(
            tab, text="Key Metrics",
            padding=10
        )
        metrics_frame.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        # Metrics
        self.metrics = {
            'Total Return': tk.StringVar(value='0.00%'),
            'Win Rate': tk.StringVar(value='0.00%'),
            'Avg Win': tk.StringVar(value='$0.00'),
            'Avg Loss': tk.StringVar(value='$0.00'),
            'Profit Factor': tk.StringVar(value='0.00'),
            'Sharpe Ratio': tk.StringVar(value='0.00'),
            'Max Drawdown': tk.StringVar(value='0.00%'),
            'Total Trades': tk.StringVar(value='0')
        }
        
        row = 0
        for name, var in self.metrics.items():
            ttk.Label(
                metrics_frame,
                text=name
            ).grid(
                row=row, column=0,
                sticky='w', padx=5, pady=2
            )
            ttk.Label(
                metrics_frame,
                textvariable=var
            ).grid(
                row=row, column=1,
                sticky='e', padx=5, pady=2
            )
            row += 1
            
        # Performance chart
        fig = Figure(figsize=(8, 4))
        self.perf_ax = fig.add_subplot(111)
        self.perf_canvas = FigureCanvasTkAgg(fig, tab)
        self.perf_canvas.get_tk_widget().pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
    def _create_trades_tab(self) -> None:
        """Create trades history tab"""
        if not self.has_analytics:
            return
            
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Trades')
        
        # Trades table
        cols = [
            'Time', 'Symbol', 'Type',
            'Price', 'Size', 'PnL'
        ]
        
        self.trades_tree = ttk.Treeview(
            tab, columns=cols,
            show='headings'
        )
        
        # Configure columns
        for col in cols:
            self.trades_tree.heading(
                col, text=col,
                command=lambda c=col: self._sort_trades(c)
            )
            width = 100 if col == 'Time' else 70
            self.trades_tree.column(
                col, width=width, anchor='center'
            )
            
        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            tab, orient='vertical',
            command=self.trades_tree.yview
        )
        self.trades_tree.configure(
            yscrollcommand=scrollbar.set
        )
        
        # Pack
        self.trades_tree.pack(
            side='left', fill='both',
            expand=True
        )
        scrollbar.pack(
            side='right', fill='y'
        )
        
    def _create_reports_tab(self) -> None:
        """Create reports generation tab"""
        if not self.has_analytics:
            return
            
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Reports')
        
        # Report options
        options_frame = ttk.LabelFrame(
            tab, text="Report Options",
            padding=10
        )
        options_frame.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        # Date range
        ttk.Label(
            options_frame,
            text="Date Range"
        ).grid(row=0, column=0, padx=5)
        
        self.date_var = tk.StringVar(
            value='Last 7 Days'
        )
        date_cb = ttk.Combobox(
            options_frame,
            textvariable=self.date_var,
            values=[
                'Today',
                'Last 7 Days',
                'Last 30 Days',
                'All Time'
            ],
            state='readonly'
        )
        date_cb.grid(row=0, column=1, padx=5)
        
        # Report type
        ttk.Label(
            options_frame,
            text="Report Type"
        ).grid(row=1, column=0, padx=5, pady=5)
        
        self.type_var = tk.StringVar(
            value='Summary'
        )
        type_cb = ttk.Combobox(
            options_frame,
            textvariable=self.type_var,
            values=[
                'Summary',
                'Detailed',
                'Risk Analysis',
                'ML Performance'
            ],
            state='readonly'
        )
        type_cb.grid(row=1, column=1, padx=5, pady=5)
        
        # Generate button
        ttk.Button(
            options_frame,
            text="Generate Report",
            command=self._generate_report
        ).grid(
            row=2, column=0,
            columnspan=2, pady=10
        )
        
        # Report preview
        preview_frame = ttk.LabelFrame(
            tab, text="Preview",
            padding=10
        )
        preview_frame.pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
        self.preview_text = tk.Text(
            preview_frame,
            wrap='word',
            height=10
        )
        self.preview_text.pack(
            fill='both', expand=True
        )
        
    def load_trades(self, trades_file: str) -> None:
        """Load trades from CSV file"""
        if not self.has_analytics:
            return
            
        try:
            # Load and ensure required columns
            df = pd.read_csv(trades_file)
            if 'time' in df.columns:
                df = df.rename(columns={'time': 'Time'})
            if 'type' in df.columns:
                df = df.rename(columns={'type': 'Type'})
            if 'price' in df.columns:
                df = df.rename(columns={'price': 'Price'})
            if 'symbol' in df.columns:
                df = df.rename(columns={'symbol': 'Symbol'})
            if 'pnl' in df.columns:
                df = df.rename(columns={'pnl': 'PnL'})

            # Ensure datetime
            df['Time'] = pd.to_datetime(df['Time'])
            
            # Add size if missing
            if 'Size' not in df.columns:
                df['Size'] = 1.0
                
            # Add PnL if missing
            if 'PnL' not in df.columns:
                df['PnL'] = 0.0
                
            self.trades_df = df
            self._update_all()
        except Exception as e:
            print(f"Error loading trades: {e}")
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to load trades from {trades_file}: {e}")
            
    def _update_all(self) -> None:
        """Update all analytics views"""
        if not self.has_analytics:
            return
            
        self._update_metrics()
        self._update_performance_chart()
        self._update_trades_table()
        
    def _update_metrics(self) -> None:
        """Update performance metrics"""
        if not self.has_analytics or self.trades_df is None:
            return
            
        df = self.trades_df
        
        # Calculate metrics
        total_pnl = df['PnL'].sum()
        starting_bal = 1000  # placeholder
        total_return = total_pnl / starting_bal
        
        wins = df[df['PnL'] > 0]
        losses = df[df['PnL'] < 0]
        
        win_rate = len(wins) / len(df)
        avg_win = wins['PnL'].mean() if len(wins) > 0 else 0
        avg_loss = losses['PnL'].mean() if len(losses) > 0 else 0
        
        profit_factor = (
            abs(wins['PnL'].sum()) /
            abs(losses['PnL'].sum())
            if len(losses) > 0 else float('inf')
        )
        
        # Update display
        self.metrics['Total Return'].set(
            f'{total_return*100:.2f}%'
        )
        self.metrics['Win Rate'].set(
            f'{win_rate*100:.2f}%'
        )
        self.metrics['Avg Win'].set(
            f'${avg_win:.2f}'
        )
        self.metrics['Avg Loss'].set(
            f'${avg_loss:.2f}'
        )
        self.metrics['Profit Factor'].set(
            f'{profit_factor:.2f}'
        )
        self.metrics['Total Trades'].set(
            str(len(df))
        )
        
    def _update_performance_chart(self) -> None:
        """Update performance chart"""
        if not self.has_analytics or self.trades_df is None:
            return
            
        df = self.trades_df
        
        # Calculate cumulative returns
        df['Cumulative'] = df['PnL'].cumsum()
        
        # Plot
        self.perf_ax.clear()
        self.perf_ax.plot(
            df['Time'],
            df['Cumulative'],
            color='g'
        )
        self.perf_ax.set_title('Cumulative P&L')
        self.perf_ax.tick_params(axis='x', rotation=45)
        self.perf_canvas.draw()
        
    def _update_trades_table(self) -> None:
        """Update trades table"""
        if not self.has_analytics or self.trades_df is None:
            return
            
        # Clear existing
        for item in self.trades_tree.get_children():
            self.trades_tree.delete(item)
            
        # Add trades
        for _, row in self.trades_df.iterrows():
            values = [
                row['Time'].strftime('%Y-%m-%d %H:%M'),
                row['Symbol'],
                row['Type'],
                f'${row["Price"]:.2f}',
                row['Size'],
                f'${row["PnL"]:.2f}'
            ]
            self.trades_tree.insert('', 'end', values=values)
            
    def _sort_trades(self, col: str) -> None:
        """Sort trades table by column"""
        if not self.has_analytics or self.trades_df is None:
            return
            
        items = [(self.trades_tree.set(k, col), k)
                for k in self.trades_tree.get_children('')]
                
        items.sort(reverse=True)
        
        for index, (_, k) in enumerate(items):
            self.trades_tree.move(k, '', index)
            
    def _generate_report(self) -> None:
        """Generate selected report"""
        if not self.has_analytics or self.trades_df is None:
            return
            
        date_range = self.date_var.get()
        report_type = self.type_var.get()
        
        # Filter data
        df = self.trades_df
        if date_range == 'Today':
            df = df[df['Time'].dt.date == datetime.now().date()]
        elif date_range == 'Last 7 Days':
            cutoff = datetime.now() - timedelta(days=7)
            df = df[df['Time'] >= cutoff]
        elif date_range == 'Last 30 Days':
            cutoff = datetime.now() - timedelta(days=30)
            df = df[df['Time'] >= cutoff]
            
        # Generate report
        report = f"=== {report_type} Report ===\n"
        report += f"Date Range: {date_range}\n\n"
        
        if report_type == 'Summary':
            report += self._generate_summary(df)
        elif report_type == 'Detailed':
            report += self._generate_detailed(df)
        elif report_type == 'Risk Analysis':
            report += self._generate_risk(df)
        else:
            report += self._generate_ml(df)
            
        # Show preview
        self.preview_text.delete('1.0', 'end')
        self.preview_text.insert('1.0', report)
        
    def _generate_summary(self, df: pd.DataFrame) -> str:
        """Generate summary report"""
        report = "Performance Summary:\n"
        report += f"Total Trades: {len(df)}\n"
        report += f"Total P&L: ${df['PnL'].sum():.2f}\n"
        report += f"Win Rate: {len(df[df['PnL']>0])/len(df)*100:.1f}%\n"
        return report
        
    def _generate_detailed(self, df: pd.DataFrame) -> str:
        """Generate detailed report"""
        report = "Detailed Analysis:\n\n"
        report += "By Symbol:\n"
        for symbol in df['Symbol'].unique():
            symbol_df = df[df['Symbol'] == symbol]
            report += f"{symbol}:\n"
            report += f"  Trades: {len(symbol_df)}\n"
            report += f"  P&L: ${symbol_df['PnL'].sum():.2f}\n"
        return report
        
    def _generate_risk(self, df: pd.DataFrame) -> str:
        """Generate risk report"""
        report = "Risk Metrics:\n\n"
        
        # Calculate drawdown
        cumsum = df['PnL'].cumsum()
        roll_max = cumsum.expanding().max()
        drawdowns = cumsum - roll_max
        max_dd = drawdowns.min()
        
        report += f"Max Drawdown: ${abs(max_dd):.2f}\n"
        report += f"Avg Trade Risk: ${abs(df['PnL']).mean():.2f}\n"
        return report
        
    def _generate_ml(self, df: pd.DataFrame) -> str:
        """Generate ML performance report"""
        report = "ML Model Performance:\n\n"
        report += "(Placeholder for ML metrics)\n"
        report += "Model accuracy, precision, etc.\n"
        return report


def main():
    """Test analytics component"""
    root = tk.Tk()
    root.title("Analytics Test")
    root.geometry("800x600")
    
    # Create analytics
    analytics = Analytics(root)
    
    if HAS_ANALYTICS:
        # Create test data
        data = {
            'Time': pd.date_range('2023-01-01', periods=100),
            'Symbol': ['BTCUSDT']*100,
            'Type': ['buy', 'sell']*50,
            'Price': np.random.randn(100).cumsum() + 100,
            'Size': [0.1]*100,
            'PnL': np.random.randn(100)*10
        }
        df = pd.DataFrame(data)
        
        # Save temp file
        temp_file = 'test_trades.csv'
        df.to_csv(temp_file, index=False)
        
        # Load trades
        analytics.load_trades(temp_file)
        
        # Clean up
        os.remove(temp_file)
    
    root.mainloop()


if __name__ == '__main__':
    main()