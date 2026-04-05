"""
Animated trade display with real-time updates
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, List, Any
import logging
from datetime import datetime
import random

try:
    from PIL import Image, ImageTk
    HAS_ANIMATIONS = True
except ImportError:
    HAS_ANIMATIONS = False

logger = logging.getLogger(__name__)

class TradeDisplay:
    """Animated trade display with effects"""
    
    def __init__(self, parent: tk.Widget):
        """Initialize trade display"""
        self.parent = parent
        self.has_animations = HAS_ANIMATIONS
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(
            fill='both', expand=True,
            padx=5, pady=5
        )
        
        # Trade info
        self._create_trade_info()
        
        # Price display
        self._create_price_display()
        
        # Trade animation
        if self.has_animations:
            self._create_animation()
            
        # Initialize state
        self.last_price = 0.0
        self.last_update = None
        self.trades = []
        self.active_animations = set()
        self.animation_ids = {}
        
    def _create_trade_info(self) -> None:
        """Create trade information panel"""
        info = ttk.LabelFrame(
            self.frame,
            text="Trade Info",
            padding=10
        )
        info.pack(fill='x', expand=False)
        
        # Labels
        self.info_vars = {
            'Symbol': tk.StringVar(),
            'Position': tk.StringVar(),
            'Entry': tk.StringVar(),
            'Stop': tk.StringVar(),
            'Target': tk.StringVar(),
            'Risk': tk.StringVar()
        }
        
        row = 0
        for name, var in self.info_vars.items():
            ttk.Label(
                info,
                text=name
            ).grid(
                row=row, column=0,
                sticky='w', padx=5, pady=2
            )
            ttk.Label(
                info,
                textvariable=var
            ).grid(
                row=row, column=1,
                sticky='e', padx=5, pady=2
            )
            row += 1
            
    def _create_price_display(self) -> None:
        """Create price display panel"""
        price = ttk.LabelFrame(
            self.frame,
            text="Current Price",
            padding=10
        )
        price.pack(fill='x', expand=False)
        
        # Price label
        self.price_var = tk.StringVar(value="0.00")
        self.price_label = ttk.Label(
            price,
            textvariable=self.price_var,
            font=('Arial', 24, 'bold')
        )
        self.price_label.pack(expand=True)
        
        # Change label
        self.change_var = tk.StringVar()
        ttk.Label(
            price,
            textvariable=self.change_var
        ).pack(expand=True)
        
        # Last update
        self.update_var = tk.StringVar()
        ttk.Label(
            price,
            textvariable=self.update_var,
            style='Small.TLabel'
        ).pack(expand=True)
        
    def _create_animation(self) -> None:
        """Create trade animation canvas"""
        # Animation frame
        anim = ttk.LabelFrame(
            self.frame,
            text="Trade Animation",
            padding=10
        )
        anim.pack(fill='both', expand=True)
        
        # Canvas
        self.canvas = tk.Canvas(
            anim,
            width=200,
            height=200,
            bg='black'
        )
        self.canvas.pack(expand=True)
        
        # Load images
        self.images = {}
        try:
            for name in ['buy', 'sell', 'arrow']:
                img = Image.open(f"images/{name}.png")
                img = img.resize((32, 32))
                self.images[name] = ImageTk.PhotoImage(img)
        except Exception as e:
            logger.error(f"Failed to load images: {e}")
            self.has_animations = False
            
    def update_trade(self, trade_dict: Dict[str, Any]) -> None:
        """Update with new trade information"""
        # Update info
        symbol = trade_dict.get('symbol', '')
        pos_size = trade_dict.get('position', 0.0)
        entry = trade_dict.get('entry_price', 0.0)
        stop = trade_dict.get('stop_loss', 0.0)
        target = trade_dict.get('take_profit', 0.0)
        risk = trade_dict.get('risk_amount', 0.0)
        
        self.info_vars['Symbol'].set(symbol)
        self.info_vars['Position'].set(f"{pos_size:.6f}")
        self.info_vars['Entry'].set(f"${entry:.2f}")
        self.info_vars['Stop'].set(f"${stop:.2f}")
        self.info_vars['Target'].set(f"${target:.2f}")
        self.info_vars['Risk'].set(f"${risk:.2f}")
        
        # Store trade
        if trade_dict.get('type'):
            self.trades.append(trade_dict)
            if self.has_animations:
                self._animate_trade(trade_dict)
                
    def update_price(
        self,
        price: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Update current price display"""
        if timestamp is None:
            timestamp = datetime.now()
            
        # Calculate change
        if self.last_price > 0:
            change = price - self.last_price
            pct = change / self.last_price * 100
            
            color = 'green' if change >= 0 else 'red'
            sign = '+' if change >= 0 else ''
            
            self.change_var.set(
                f"{sign}${change:.2f} ({sign}{pct:.2f}%)"
            )
            
            self.price_label.configure(
                style=f'{color}.Price.TLabel'
            )
            
        # Update price
        self.price_var.set(f"${price:.2f}")
        self.last_price = price
        
        # Update timestamp
        self.last_update = timestamp
        self.update_var.set(
            f"Last Update: {timestamp:%H:%M:%S}"
        )
        
        if self.has_animations:
            self._update_animation()
            
    def _animate_trade(self, trade: Dict[str, Any]) -> None:
        """Show trade animation"""
        if not self.has_animations:
            return
            
        try:
            # Get image
            img = self.images.get(
                trade['type'].lower()
            )
            if not img:
                return
                
            # Create sprite
            sprite = self.canvas.create_image(
                100, 200,  # Start at bottom
                image=img,
                tags='trade'
            )
            
            # Animate upward
            self._move_sprite(sprite, 0, -2)
            
        except Exception as e:
            logger.error(f"Animation error: {e}")
            
    def _move_sprite(
        self,
        sprite: int,
        dx: float,
        dy: float,
        steps: int = 50
    ) -> None:
        """Animate sprite movement with proper cleanup"""
        if steps <= 0:
            try:
                if sprite in self.animation_ids:
                    del self.animation_ids[sprite]
                self.active_animations.discard(sprite)
                self.canvas.delete(sprite)
            except tk.TclError:
                pass  # Canvas or sprite already deleted
            return
        
        try:
            self.canvas.move(sprite, dx, dy)
            self.active_animations.add(sprite)
            anim_id = self.parent.after(
                15,  # Faster animation (15ms instead of 20ms)
                self._move_sprite,
                sprite, dx, dy, steps - 1
            )
            self.animation_ids[sprite] = anim_id
        except tk.TclError:
            # Canvas destroyed, cleanup
            self.active_animations.discard(sprite)
            if sprite in self.animation_ids:
                del self.animation_ids[sprite]
        
    def _update_animation(self) -> None:
        """Update background animation with throttling"""
        if not self.has_animations:
            return
            
        try:
            # Limit particle generation to prevent lag
            if len(self.active_animations) < 20 and random.random() < 0.2:
                x = random.randint(0, 200)
                particle = self.canvas.create_oval(
                    x, 200, x+2, 202,
                    fill='#00FF00' if random.random() > 0.5 else '#FFFF00',
                    tags='particle'
                )
                self._move_sprite(
                    particle,
                    random.uniform(-0.5, 0.5),
                    -1.2,  # Faster fall
                    80  # Fewer steps for smoother decay
                )
                
        except tk.TclError:
            # Canvas destroyed, skip
            pass
        except Exception as e:
            logger.error(f"Animation update error: {e}")
    
    def cleanup(self) -> None:
        """Cleanup animations and resources"""
        try:
            # Cancel all pending animations
            for anim_id in self.animation_ids.values():
                try:
                    self.parent.after_cancel(anim_id)
                except:
                    pass
            self.animation_ids.clear()
            self.active_animations.clear()
            
            # Clear canvas
            if self.has_animations and hasattr(self, 'canvas'):
                self.canvas.delete('all')
        except:
            pass
            
    def clear_trades(self) -> None:
        """Clear trade history"""
        self.trades = []
        if self.has_animations:
            self.canvas.delete('trade')
            self.canvas.delete('particle')


def main():
    """Test trade display"""
    root = tk.Tk()
    root.title("Trade Display Test")
    
    display = TradeDisplay(root)
    
    # Test updates
    def update():
        price = random.uniform(90, 110)
        display.update_price(price)
        
        if random.random() < 0.1:
            trade = {
                'symbol': 'BTCUSDT',
                'type': random.choice(['buy', 'sell']),
                'position': random.uniform(0.1, 1.0),
                'entry_price': price,
                'stop_loss': price * 0.99,
                'take_profit': price * 1.02,
                'risk_amount': 100.0
            }
            display.update_trade(trade)
            
        root.after(1000, update)
        
    update()
    root.mainloop()


if __name__ == '__main__':
    main()