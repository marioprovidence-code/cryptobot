"""
CryptoBot Notifications System
Provides alerts and notifications for trading events.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional
from datetime import datetime
import json
import logging
import os
import threading
import queue
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Notification:
    """Trading notification object"""
    timestamp: datetime
    type: str  # info, warning, error, trade
    title: str
    message: str
    data: Optional[Dict] = None


class NotificationManager:
    """Manages trading notifications and alerts"""
    
    def __init__(self):
        """Initialize notification manager"""
        self.notifications: List[Notification] = []
        self.subscribers: List = []
        self.queue = queue.Queue()
        self.thread = None
        self.running = False
        
        # Load settings
        self.settings = {
            'max_notifications': 100,
            'save_to_file': True,
            'notification_types': {
                'trade': True,
                'risk': True,
                'error': True,
                'info': True
            }
        }
        self._load_settings()
        
    def start(self) -> None:
        """Start notification processing"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(
                target=self._process_queue
            )
            self.thread.daemon = True
            self.thread.start()
            
    def stop(self) -> None:
        """Stop notification processing"""
        self.running = False
        if self.thread:
            self.thread.join()
            
    def add_notification(
        self,
        type_: str,
        title: str,
        message: str,
        data: Optional[Dict] = None
    ) -> None:
        """Add new notification"""
        if not self.settings['notification_types'].get(
            type_,
            True
        ):
            return
            
        notification = Notification(
            timestamp=datetime.now(),
            type=type_,
            title=title,
            message=message,
            data=data
        )
        
        self.queue.put(notification)
        
    def subscribe(self, callback) -> None:
        """Subscribe to notifications"""
        if callback not in self.subscribers:
            self.subscribers.append(callback)
            
    def unsubscribe(self, callback) -> None:
        """Unsubscribe from notifications"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            
    def _process_queue(self) -> None:
        """Process notification queue"""
        while self.running:
            try:
                notification = self.queue.get(timeout=1)
                
                # Add to history
                self.notifications.append(notification)
                
                # Trim if needed
                while (len(self.notifications) >
                       self.settings['max_notifications']):
                    self.notifications.pop(0)
                    
                # Save to file
                if self.settings['save_to_file']:
                    self._save_notification(notification)
                    
                # Notify subscribers
                for subscriber in self.subscribers:
                    try:
                        subscriber(notification)
                    except Exception as e:
                        logger.error(
                            f"Subscriber error: {e}"
                        )
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(
                    f"Queue processing error: {e}"
                )
                
    def _save_notification(
        self,
        notification: Notification
    ) -> None:
        """Save notification to file"""
        try:
            # Create logs dir
            os.makedirs('logs', exist_ok=True)
            
            # Save to file
            filename = (
                f"notifications_{notification.timestamp.strftime('%Y%m%d')}.log"
            )
            filepath = os.path.join('logs', filename)
            
            with open(filepath, 'a') as f:
                f.write(
                    json.dumps({
                        'timestamp': notification.timestamp.isoformat(),
                        'type': notification.type,
                        'title': notification.title,
                        'message': notification.message,
                        'data': notification.data
                    }) + '\n'
                )
                
        except Exception as e:
            logger.error(
                f"Failed to save notification: {e}"
            )
            
    def _load_settings(self) -> None:
        """Load notification settings"""
        try:
            if os.path.exists('notification_settings.json'):
                with open('notification_settings.json', 'r') as f:
                    self.settings.update(json.load(f))
        except Exception as e:
            logger.error(
                f"Failed to load settings: {e}"
            )
            
    def save_settings(self) -> None:
        """Save notification settings"""
        try:
            with open('notification_settings.json', 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(
                f"Failed to save settings: {e}"
            )


class NotificationPanel:
    """GUI panel for notifications"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize notification panel"""
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill='both', expand=True)
        
        # Create manager
        self.manager = NotificationManager()
        self.manager.subscribe(self._on_notification)
        self.manager.start()
        
        # Create widgets
        self._create_widgets()
        
    def _create_widgets(self) -> None:
        """Create notification widgets"""
        # Controls
        controls = ttk.Frame(self.frame)
        controls.pack(fill='x', expand=False, pady=5)
        
        ttk.Button(
            controls,
            text="Clear All",
            command=self._clear_notifications
        ).pack(side='left', padx=5)
        
        ttk.Button(
            controls,
            text="Settings",
            command=self._show_settings
        ).pack(side='left', padx=5)
        
        # Notification list
        self.tree = ttk.Treeview(
            self.frame,
            columns=[
                'Time',
                'Type',
                'Title',
                'Message'
            ],
            show='headings'
        )
        
        # Configure columns
        self.tree.heading('Time', text='Time')
        self.tree.heading('Type', text='Type')
        self.tree.heading('Title', text='Title')
        self.tree.heading('Message', text='Message')
        
        self.tree.column('Time', width=100)
        self.tree.column('Type', width=70)
        self.tree.column('Title', width=150)
        self.tree.column('Message', width=300)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            self.frame,
            orient='vertical',
            command=self.tree.yview
        )
        self.tree.configure(
            yscrollcommand=scrollbar.set
        )
        
        # Pack
        self.tree.pack(
            side='left',
            fill='both',
            expand=True
        )
        scrollbar.pack(
            side='right',
            fill='y'
        )
        
        # Bind double-click
        self.tree.bind(
            '<Double-1>',
            self._on_double_click
        )
        
    def _on_notification(
        self,
        notification: Notification
    ) -> None:
        """Handle new notification"""
        # Add to tree
        self.tree.insert(
            '',
            0,
            values=(
                notification.timestamp.strftime('%H:%M:%S'),
                notification.type,
                notification.title,
                notification.message
            )
        )
        
        # Trim old items
        while len(self.tree.get_children()) > 100:
            self.tree.delete(
                self.tree.get_children()[-1]
            )
            
    def _clear_notifications(self) -> None:
        """Clear all notifications"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
    def _show_settings(self) -> None:
        """Show notification settings"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Notification Settings")
        dialog.geometry("300x400")
        
        # Create settings widgets
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill='both', expand=True)
        
        # Max notifications
        ttk.Label(
            frame,
            text="Max Notifications:"
        ).pack(anchor='w')
        
        max_var = tk.StringVar(
            value=str(
                self.manager.settings['max_notifications']
            )
        )
        ttk.Entry(
            frame,
            textvariable=max_var
        ).pack(fill='x', pady=5)
        
        # Save to file
        save_var = tk.BooleanVar(
            value=self.manager.settings['save_to_file']
        )
        ttk.Checkbutton(
            frame,
            text="Save to File",
            variable=save_var
        ).pack(anchor='w', pady=5)
        
        # Notification types
        ttk.Label(
            frame,
            text="Notification Types:"
        ).pack(anchor='w', pady=5)
        
        type_vars = {}
        for type_, enabled in self.manager.settings[
            'notification_types'
        ].items():
            var = tk.BooleanVar(value=enabled)
            type_vars[type_] = var
            ttk.Checkbutton(
                frame,
                text=type_.title(),
                variable=var
            ).pack(anchor='w')
            
        def save_settings():
            """Save dialog settings"""
            try:
                max_not = int(max_var.get())
                if max_not < 1:
                    raise ValueError(
                        "Max notifications must be >= 1"
                    )
                    
                self.manager.settings.update({
                    'max_notifications': max_not,
                    'save_to_file': save_var.get(),
                    'notification_types': {
                        type_: var.get()
                        for type_, var in type_vars.items()
                    }
                })
                
                self.manager.save_settings()
                dialog.destroy()
                
            except ValueError as e:
                tk.messagebox.showerror(
                    "Error",
                    str(e)
                )
                
        ttk.Button(
            frame,
            text="Save",
            command=save_settings
        ).pack(pady=10)
        
    def _on_double_click(self, event) -> None:
        """Show notification details"""
        item = self.tree.selection()[0]
        values = self.tree.item(item)['values']
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("Notification Details")
        dialog.geometry("400x300")
        
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill='both', expand=True)
        
        # Show details
        details = (
            f"Time: {values[0]}\n"
            f"Type: {values[1]}\n"
            f"Title: {values[2]}\n\n"
            f"Message:\n{values[3]}"
        )
        
        text = tk.Text(
            frame,
            wrap='word',
            height=10
        )
        text.pack(fill='both', expand=True)
        text.insert('1.0', details)
        text.configure(state='disabled')
        
        ttk.Button(
            frame,
            text="Close",
            command=dialog.destroy
        ).pack(pady=10)


def main():
    """Test notification panel"""
    root = tk.Tk()
    root.title("Notifications")
    root.geometry("800x600")
    
    panel = NotificationPanel(root)
    
    # Add test notifications
    panel.manager.add_notification(
        'trade',
        'New Trade',
        'Bought BTC at $50,000',
        {'price': 50000, 'size': 0.1}
    )
    
    panel.manager.add_notification(
        'risk',
        'Risk Alert',
        'Position size exceeds limit',
        {'current': 1.5, 'limit': 1.0}
    )
    
    panel.manager.add_notification(
        'error',
        'API Error',
        'Failed to connect to exchange',
        {'error': 'Connection timeout'}
    )
    
    root.mainloop()


if __name__ == '__main__':
    main()