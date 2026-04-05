"""
Advanced Order Types Module
Provides sophisticated order types and execution algorithms
"""
import numpy as np
from typing import Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
from logging_utils import get_logger

logger = get_logger(__name__)

class OrderType(Enum):
    """Supported order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    OCO = "oco"  # One-Cancels-Other
    BRACKET = "bracket"

class TimeInForce(Enum):
    """Time in force options"""
    GTC = "gtc"  # Good Till Cancel
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    GTD = "gtd"  # Good Till Date

class OrderStatus(Enum):
    """Order status types"""
    PENDING = "pending"
    ACTIVE = "active"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class Order:
    """Base order class"""
    
    def __init__(self,
                 symbol: str,
                 side: str,
                 quantity: float,
                 order_type: OrderType,
                 price: Optional[float] = None,
                 stop_price: Optional[float] = None,
                 time_in_force: TimeInForce = TimeInForce.GTC,
                 expire_time: Optional[datetime] = None,
                 client_order_id: Optional[str] = None):
        self.symbol = symbol
        self.side = side.lower()
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.stop_price = stop_price
        self.time_in_force = time_in_force
        self.expire_time = expire_time
        self.client_order_id = client_order_id
        
        # Execution tracking
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0.0
        self.average_price = 0.0
        self.fills = []
        self.create_time = datetime.now()
        self.update_time = self.create_time
        
    def update(self, fill_qty: float, fill_price: float) -> None:
        """Update order with new fill"""
        self.fills.append({
            'quantity': fill_qty,
            'price': fill_price,
            'timestamp': datetime.now()
        })
        
        self.filled_quantity += fill_qty
        total_value = sum(f['quantity'] * f['price'] for f in self.fills)
        self.average_price = total_value / self.filled_quantity if self.filled_quantity > 0 else 0
        
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
            
        self.update_time = datetime.now()
        
    def cancel(self) -> None:
        """Cancel the order"""
        if self.status in [OrderStatus.PENDING, OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]:
            self.status = OrderStatus.CANCELLED
            self.update_time = datetime.now()
            
class TrailingStopOrder(Order):
    """Trailing stop order implementation"""
    
    def __init__(self,
                 symbol: str,
                 side: str,
                 quantity: float,
                 trail_type: str = "amount",
                 trail_value: float = 0.0,
                 **kwargs):
        super().__init__(
            symbol, side, quantity,
            OrderType.TRAILING_STOP,
            **kwargs
        )
        self.trail_type = trail_type  # "amount" or "percent"
        self.trail_value = trail_value
        self.activation_price = None
        self.stop_price = None
        
    def update_stop(self, current_price: float) -> None:
        """Update trailing stop level"""
        if self.activation_price is None:
            self.activation_price = current_price
            
        if self.side == "sell":
            # For sell orders, trail below the price
            new_stop = current_price - (
                self.trail_value if self.trail_type == "amount"
                else current_price * (self.trail_value / 100)
            )
            if self.stop_price is None or new_stop > self.stop_price:
                self.stop_price = new_stop
                
        else:  # buy
            # For buy orders, trail above the price
            new_stop = current_price + (
                self.trail_value if self.trail_type == "amount"
                else current_price * (self.trail_value / 100)
            )
            if self.stop_price is None or new_stop < self.stop_price:
                self.stop_price = new_stop
                
class IcebergOrder(Order):
    """Iceberg order implementation"""
    
    def __init__(self,
                 symbol: str,
                 side: str,
                 quantity: float,
                 visible_size: float,
                 price: float,
                 min_qty: Optional[float] = None,
                 **kwargs):
        super().__init__(
            symbol, side, quantity,
            OrderType.ICEBERG,
            price=price,
            **kwargs
        )
        self.visible_size = min(visible_size, quantity)
        self.min_qty = min_qty or visible_size
        self.displayed_quantity = self.visible_size
        self.real_quantity = quantity
        
    def refresh_display(self) -> None:
        """Refresh displayed quantity"""
        remaining = self.real_quantity - self.filled_quantity
        if remaining > 0:
            self.displayed_quantity = min(self.visible_size, remaining)
        else:
            self.displayed_quantity = 0
            
class TWAPOrder(Order):
    """Time-Weighted Average Price order"""
    
    def __init__(self,
                 symbol: str,
                 side: str,
                 quantity: float,
                 target_time: Union[timedelta, datetime],
                 num_slices: int = 10,
                 price_limit: Optional[float] = None,
                 **kwargs):
        super().__init__(
            symbol, side, quantity,
            OrderType.TWAP,
            price=price_limit,
            **kwargs
        )
        
        # TWAP specific
        if isinstance(target_time, datetime):
            self.end_time = target_time
            self.duration = target_time - datetime.now()
        else:
            self.duration = target_time
            self.end_time = datetime.now() + target_time
            
        self.num_slices = num_slices
        self.slice_quantity = quantity / num_slices
        self.next_slice_time = datetime.now()
        self.slice_interval = self.duration / num_slices
        
    def should_place_slice(self, current_time: datetime) -> bool:
        """Check if it's time to place next slice"""
        return current_time >= self.next_slice_time
        
    def update_next_slice(self) -> None:
        """Update timing for next slice"""
        self.next_slice_time += self.slice_interval
        
class VWAPOrder(Order):
    """Volume-Weighted Average Price order"""
    
    def __init__(self,
                 symbol: str,
                 side: str,
                 quantity: float,
                 target_time: Union[timedelta, datetime],
                 volume_profile: Dict[datetime, float],
                 price_limit: Optional[float] = None,
                 **kwargs):
        super().__init__(
            symbol, side, quantity,
            OrderType.VWAP,
            price=price_limit,
            **kwargs
        )
        
        # VWAP specific
        if isinstance(target_time, datetime):
            self.end_time = target_time
            self.duration = target_time - datetime.now()
        else:
            self.duration = target_time
            self.end_time = datetime.now() + target_time
            
        self.volume_profile = volume_profile
        self.total_volume = sum(volume_profile.values())
        self.executed_volume = 0.0
        
    def get_target_quantity(self, current_time: datetime) -> float:
        """Calculate target quantity based on volume profile"""
        elapsed_volume = sum(
            vol for time, vol in self.volume_profile.items()
            if time <= current_time
        )
        target_ratio = elapsed_volume / self.total_volume
        target_quantity = self.quantity * target_ratio
        return max(0, target_quantity - self.executed_volume)
        
class OCOOrder:
    """One-Cancels-Other order pair"""
    
    def __init__(self,
                 symbol: str,
                 quantity: float,
                 price1: float,
                 price2: float,
                 order_type1: OrderType,
                 order_type2: OrderType,
                 **kwargs):
        # Create both orders
        self.order1 = Order(
            symbol=symbol,
            side=kwargs.get('side1', 'buy'),
            quantity=quantity,
            order_type=order_type1,
            price=price1,
            **kwargs
        )
        
        self.order2 = Order(
            symbol=symbol,
            side=kwargs.get('side2', 'sell'),
            quantity=quantity,
            order_type=order_type2,
            price=price2,
            **kwargs
        )
        
        self.status = OrderStatus.PENDING
        
    def fill_order(self, order_num: int, quantity: float, price: float) -> None:
        """Fill one of the orders and cancel the other"""
        if order_num == 1:
            self.order1.update(quantity, price)
            self.order2.cancel()
        else:
            self.order2.update(quantity, price)
            self.order1.cancel()
            
        self.status = OrderStatus.FILLED
        
class BracketOrder:
    """Bracket order (entry + stop loss + take profit)"""
    
    def __init__(self,
                 symbol: str,
                 side: str,
                 quantity: float,
                 entry_price: float,
                 stop_loss: float,
                 take_profit: float,
                 entry_type: OrderType = OrderType.LIMIT,
                 **kwargs):
        # Entry order
        self.entry = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=entry_type,
            price=entry_price,
            **kwargs
        )
        
        # Stop loss
        self.stop_loss = Order(
            symbol=symbol,
            side='sell' if side == 'buy' else 'buy',
            quantity=quantity,
            order_type=OrderType.STOP,
            stop_price=stop_loss,
            **kwargs
        )
        
        # Take profit
        self.take_profit = Order(
            symbol=symbol,
            side='sell' if side == 'buy' else 'buy',
            quantity=quantity,
            order_type=OrderType.LIMIT,
            price=take_profit,
            **kwargs
        )
        
        self.status = OrderStatus.PENDING
        
    def fill_entry(self, quantity: float, price: float) -> None:
        """Fill entry order and activate stop/profit orders"""
        self.entry.update(quantity, price)
        self.status = OrderStatus.ACTIVE
        
    def fill_exit(self, order_type: str, quantity: float, price: float) -> None:
        """Fill either stop loss or take profit and cancel the other"""
        if order_type == 'stop':
            self.stop_loss.update(quantity, price)
            self.take_profit.cancel()
        else:
            self.take_profit.update(quantity, price)
            self.stop_loss.cancel()
            
        self.status = OrderStatus.FILLED
        
class OrderManager:
    """Manages order creation and execution"""
    
    def __init__(self):
        self.orders = {}
        self.active_orders = set()
        
    def create_order(self,
                    order_type: OrderType,
                    **kwargs) -> Union[Order, OCOOrder, BracketOrder]:
        """Create new order of specified type"""
        try:
            if order_type == OrderType.TRAILING_STOP:
                order = TrailingStopOrder(**kwargs)
            elif order_type == OrderType.ICEBERG:
                order = IcebergOrder(**kwargs)
            elif order_type == OrderType.TWAP:
                order = TWAPOrder(**kwargs)
            elif order_type == OrderType.VWAP:
                order = VWAPOrder(**kwargs)
            elif order_type == OrderType.OCO:
                order = OCOOrder(**kwargs)
            elif order_type == OrderType.BRACKET:
                order = BracketOrder(**kwargs)
            else:
                order = Order(order_type=order_type, **kwargs)
                
            # Store order
            order_id = kwargs.get('client_order_id') or str(len(self.orders) + 1)
            self.orders[order_id] = order
            
            if order.status not in [OrderStatus.CANCELLED, OrderStatus.FILLED]:
                self.active_orders.add(order_id)
                
            return order
            
        except Exception as e:
            logger.error(f"Order creation error: {e}")
            return None
            
    def cancel_order(self, order_id: str) -> bool:
        """Cancel specified order"""
        try:
            if order_id in self.orders:
                order = self.orders[order_id]
                order.cancel()
                self.active_orders.discard(order_id)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Order cancellation error: {e}")
            return False
            
    def update_order(self,
                    order_id: str,
                    quantity: float,
                    price: float) -> bool:
        """Update order with fill information"""
        try:
            if order_id in self.orders:
                order = self.orders[order_id]
                order.update(quantity, price)
                
                if order.status == OrderStatus.FILLED:
                    self.active_orders.discard(order_id)
                    
                return True
            return False
            
        except Exception as e:
            logger.error(f"Order update error: {e}")
            return False
            
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
        
    def get_active_orders(self) -> List[Order]:
        """Get all active orders"""
        return [self.orders[oid] for oid in self.active_orders]
        
    def update_trailing_stops(self, current_prices: Dict[str, float]) -> None:
        """Update all trailing stop orders"""
        try:
            for order_id in self.active_orders:
                order = self.orders[order_id]
                if isinstance(order, TrailingStopOrder):
                    if order.symbol in current_prices:
                        order.update_stop(current_prices[order.symbol])
                        
        except Exception as e:
            logger.error(f"Trailing stop update error: {e}")
            
    def process_twap_orders(self, current_time: datetime) -> List[Dict]:
        """Process TWAP orders and generate child orders"""
        try:
            child_orders = []
            
            for order_id in list(self.active_orders):
                order = self.orders[order_id]
                if isinstance(order, TWAPOrder):
                    if order.should_place_slice():
                        child_orders.append({
                            'symbol': order.symbol,
                            'side': order.side,
                            'quantity': order.slice_quantity,
                            'order_type': OrderType.MARKET,
                            'parent_id': order_id
                        })
                        order.update_next_slice()
                        
                    # Check for expiration
                    if current_time >= order.end_time:
                        self.cancel_order(order_id)
                        
            return child_orders
            
        except Exception as e:
            logger.error(f"TWAP processing error: {e}")
            return []
            
    def process_vwap_orders(self,
                          current_time: datetime,
                          current_prices: Dict[str, float]) -> List[Dict]:
        """Process VWAP orders and generate child orders"""
        try:
            child_orders = []
            
            for order_id in list(self.active_orders):
                order = self.orders[order_id]
                if isinstance(order, VWAPOrder):
                    target_qty = order.get_target_quantity(current_time)
                    
                    if target_qty > 0:
                        child_orders.append({
                            'symbol': order.symbol,
                            'side': order.side,
                            'quantity': target_qty,
                            'order_type': OrderType.MARKET,
                            'parent_id': order_id
                        })
                        order.executed_volume += target_qty
                        
                    # Check for expiration
                    if current_time >= order.end_time:
                        self.cancel_order(order_id)
                        
            return child_orders
            
        except Exception as e:
            logger.error(f"VWAP processing error: {e}")
            return []
            
    def update_iceberg_orders(self) -> List[Dict]:
        """Refresh iceberg order displayed quantities"""
        try:
            updates = []
            
            for order_id in self.active_orders:
                order = self.orders[order_id]
                if isinstance(order, IcebergOrder):
                    old_display = order.displayed_quantity
                    order.refresh_display()
                    
                    if order.displayed_quantity != old_display:
                        updates.append({
                            'order_id': order_id,
                            'new_quantity': order.displayed_quantity
                        })
                        
            return updates
            
        except Exception as e:
            logger.error(f"Iceberg update error: {e}")
            return []