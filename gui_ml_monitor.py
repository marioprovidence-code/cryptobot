"""
CryptoBot ML Monitoring
Real-time machine learning model monitoring and diagnostics.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Optional, List
import threading
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from sklearn.metrics import (
        confusion_matrix,
        precision_recall_curve,
        roc_curve,
        auc
    )
    HAS_ML = True
except ImportError:
    HAS_ML = False
    
# Import core bot features with fallbacks
try:
    from crypto_bot import (
        MLModel,
        get_historical_data_with_indicators
    )
except ImportError:
    class MLModel: pass
    def get_historical_data_with_indicators(*args, **kwargs): 
        return None


class MLMonitor:
    """Real-time ML model monitoring"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize ML monitor"""
        self.parent = parent
        self.has_ml = HAS_ML
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        
        if not self.has_ml:
            self._show_fallback()
            return
            
        # Create notebook
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
        # Create tabs
        self._create_metrics_tab()
        self._create_predictions_tab()
        self._create_features_tab()
        
        # Initialize data
        self.predictions = []
        self.actuals = []
        self.feature_importance = {}
        
    def _show_fallback(self) -> None:
        """Show message when deps not available"""
        msg = "ML monitoring requires sklearn & matplotlib"
        ttk.Label(
            self.frame,
            text=msg,
            style='Fallback.TLabel'
        ).pack(expand=True)
        
    def _create_metrics_tab(self) -> None:
        """Create model metrics tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Metrics")
        
        # Metrics frame
        metrics = ttk.LabelFrame(
            tab,
            text="Model Performance",
            padding=10
        )
        metrics.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        self.metrics = {
            'Accuracy': tk.StringVar(value='0.00%'),
            'Precision': tk.StringVar(value='0.00%'),
            'Recall': tk.StringVar(value='0.00%'),
            'F1 Score': tk.StringVar(value='0.00'),
            'ROC AUC': tk.StringVar(value='0.00'),
            'Predictions': tk.StringVar(value='0')
        }
        
        row = 0
        for name, var in self.metrics.items():
            ttk.Label(
                metrics,
                text=name
            ).grid(
                row=row, column=0,
                sticky='w', padx=5, pady=2
            )
            ttk.Label(
                metrics,
                textvariable=var
            ).grid(
                row=row, column=1,
                sticky='e', padx=5, pady=2
            )
            row += 1
            
        # Performance plots
        plots = ttk.Frame(tab)
        plots.pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
        fig = Figure(figsize=(10, 6))
        self.ax1 = fig.add_subplot(121)  # ROC curve
        self.ax2 = fig.add_subplot(122)  # Confusion matrix
        
        self.canvas = FigureCanvasTkAgg(fig, plots)
        self.canvas.get_tk_widget().pack(
            fill='both', expand=True
        )
        
    def _create_predictions_tab(self) -> None:
        """Create predictions history tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Predictions")
        
        # Controls
        controls = ttk.Frame(tab)
        controls.pack(
            fill='x', expand=False,
            padx=5, pady=5
        )
        
        ttk.Button(
            controls,
            text="Clear History",
            command=self._clear_predictions
        ).pack(side='left', padx=5)
        
        ttk.Button(
            controls,
            text="Export Data",
            command=self._export_predictions
        ).pack(side='left', padx=5)
        
        # Predictions table
        cols = [
            'Time',
            'Prediction',
            'Actual',
            'Confidence',
            'Features'
        ]
        
        self.pred_tree = ttk.Treeview(
            tab,
            columns=cols,
            show='headings'
        )
        
        # Configure columns
        for col in cols:
            self.pred_tree.heading(
                col,
                text=col
            )
            width = 150 if col == 'Features' else 100
            self.pred_tree.column(
                col,
                width=width
            )
            
        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            tab,
            orient='vertical',
            command=self.pred_tree.yview
        )
        self.pred_tree.configure(
            yscrollcommand=scrollbar.set
        )
        
        # Pack
        self.pred_tree.pack(
            side='left',
            fill='both',
            expand=True
        )
        scrollbar.pack(
            side='right',
            fill='y'
        )
        
    def _create_features_tab(self) -> None:
        """Create feature importance tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Features")
        
        # Feature importance plot
        fig = Figure(figsize=(10, 6))
        self.ax3 = fig.add_subplot(111)
        
        self.feat_canvas = FigureCanvasTkAgg(fig, tab)
        self.feat_canvas.get_tk_widget().pack(
            fill='both', expand=True
        )
        
    def add_prediction(
        self,
        prediction: int,
        actual: Optional[int],
        confidence: float,
        features: Dict[str, float]
    ) -> None:
        """Add new prediction"""
        if not self.has_ml:
            return
            
        # Store prediction
        self.predictions.append(prediction)
        if actual is not None:
            self.actuals.append(actual)
            
        # Add to table
        self.pred_tree.insert(
            '',
            0,
            values=(
                datetime.now().strftime('%H:%M:%S'),
                'Buy' if prediction == 1 else 'Sell',
                'Buy' if actual == 1 else 'Sell' if actual is not None else 'Unknown',
                f'{confidence*100:.1f}%',
                ', '.join(f'{k}: {v:.2f}' for k, v in features.items())
            )
        )
        
        # Trim old items
        while len(self.pred_tree.get_children()) > 100:
            self.pred_tree.delete(
                self.pred_tree.get_children()[-1]
            )
            
        # Update metrics if we have actuals
        if len(self.actuals) > 0:
            self._update_metrics()
            
    def add_feature_importance(
        self,
        importance: Dict[str, float]
    ) -> None:
        """Update feature importance"""
        if not self.has_ml:
            return
            
        self.feature_importance = importance
        self._update_feature_plot()
        
    def _update_metrics(self) -> None:
        """Update performance metrics"""
        if not self.has_ml:
            return
            
        try:
            y_true = np.array(self.actuals)
            y_pred = np.array(self.predictions)
            
            # Calculate metrics
            cm = confusion_matrix(y_true, y_pred)
            accuracy = np.sum(y_true == y_pred) / len(y_true)
            
            precision = (
                cm[1,1] / (cm[1,1] + cm[0,1])
                if cm[1,1] + cm[0,1] > 0 else 0
            )
            
            recall = (
                cm[1,1] / (cm[1,1] + cm[1,0])
                if cm[1,1] + cm[1,0] > 0 else 0
            )
            
            f1 = (
                2 * precision * recall / (precision + recall)
                if precision + recall > 0 else 0
            )
            
            # ROC curve
            fpr, tpr, _ = roc_curve(y_true, y_pred)
            roc_auc = auc(fpr, tpr)
            
            # Update metrics
            self.metrics['Accuracy'].set(
                f'{accuracy*100:.2f}%'
            )
            self.metrics['Precision'].set(
                f'{precision*100:.2f}%'
            )
            self.metrics['Recall'].set(
                f'{recall*100:.2f}%'
            )
            self.metrics['F1 Score'].set(
                f'{f1:.2f}'
            )
            self.metrics['ROC AUC'].set(
                f'{roc_auc:.2f}'
            )
            self.metrics['Predictions'].set(
                str(len(self.predictions))
            )
            
            # Update plots
            self._update_performance_plots(
                fpr, tpr, roc_auc, cm
            )
            
        except Exception as e:
            logger.error(f"Metrics update error: {e}")
            
    def _update_performance_plots(
        self,
        fpr: np.ndarray,
        tpr: np.ndarray,
        roc_auc: float,
        cm: np.ndarray
    ) -> None:
        """Update ROC and confusion matrix plots"""
        if not self.has_ml:
            return
            
        try:
            # ROC curve
            self.ax1.clear()
            self.ax1.plot(
                fpr, tpr,
                color='b',
                label=f'ROC (AUC = {roc_auc:.2f})'
            )
            self.ax1.plot(
                [0, 1], [0, 1],
                color='gray',
                linestyle='--'
            )
            self.ax1.set_xlabel('False Positive Rate')
            self.ax1.set_ylabel('True Positive Rate')
            self.ax1.set_title('ROC Curve')
            self.ax1.legend()
            self.ax1.grid(True)
            
            # Confusion matrix
            self.ax2.clear()
            self.ax2.imshow(
                cm,
                interpolation='nearest',
                cmap=plt.cm.Blues
            )
            self.ax2.set_title('Confusion Matrix')
            self.ax2.set_xticks([0, 1])
            self.ax2.set_yticks([0, 1])
            self.ax2.set_xticklabels(['Sell', 'Buy'])
            self.ax2.set_yticklabels(['Sell', 'Buy'])
            
            # Add text annotations
            for i in range(2):
                for j in range(2):
                    self.ax2.text(
                        j, i, str(cm[i, j]),
                        ha='center', va='center'
                    )
                    
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Plot update error: {e}")
            
    def _update_feature_plot(self) -> None:
        """Update feature importance plot"""
        if not self.has_ml:
            return
            
        try:
            self.ax3.clear()
            
            # Sort features by importance
            features = {
                k: v for k, v in sorted(
                    self.feature_importance.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            }
            
            # Plot horizontal bar chart
            y_pos = np.arange(len(features))
            self.ax3.barh(
                y_pos,
                list(features.values()),
                align='center'
            )
            self.ax3.set_yticks(y_pos)
            self.ax3.set_yticklabels(
                list(features.keys())
            )
            self.ax3.set_xlabel('Importance')
            self.ax3.set_title('Feature Importance')
            
            self.feat_canvas.draw()
            
        except Exception as e:
            logger.error(f"Feature plot error: {e}")
            
    def _clear_predictions(self) -> None:
        """Clear prediction history"""
        self.predictions = []
        self.actuals = []
        
        for item in self.pred_tree.get_children():
            self.pred_tree.delete(item)
            
    def _export_predictions(self) -> None:
        """Export prediction history"""
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")]
            )
            if not filepath:
                return
                
            # Get all data
            data = []
            for item in self.pred_tree.get_children():
                values = self.pred_tree.item(item)['values']
                data.append({
                    'Time': values[0],
                    'Prediction': values[1],
                    'Actual': values[2],
                    'Confidence': values[3],
                    'Features': values[4]
                })
                
            # Save to CSV
            pd.DataFrame(data).to_csv(
                filepath,
                index=False
            )
            
        except Exception as e:
            messagebox.showerror(
                "Export Error",
                str(e)
            )


def main():
    """Test ML monitor"""
    root = tk.Tk()
    root.title("ML Monitor")
    root.geometry("1000x800")
    
    monitor = MLMonitor(root)
    
    # Add test data
    if HAS_ML:
        # Add predictions
        for _ in range(10):
            pred = np.random.randint(0, 2)
            actual = np.random.randint(0, 2)
            conf = np.random.random()
            features = {
                'SMA_20': np.random.random(),
                'RSI_14': np.random.random(),
                'MACD': np.random.random()
            }
            monitor.add_prediction(
                pred, actual, conf, features
            )
            
        # Add feature importance
        monitor.add_feature_importance({
            'SMA_20': 0.3,
            'RSI_14': 0.4,
            'MACD': 0.2,
            'ATR_14': 0.1
        })
    
    root.mainloop()


if __name__ == '__main__':
    main()