import asyncio
import websockets
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import threading
import time
from queue import Queue, Empty

@dataclass
class Order:
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: Optional[float] = None
    order_type: str = 'market'  # 'market', 'limit', 'stop'
    time_in_force: str = 'GTC'  # 'GTC', 'IOC', 'FOK'
    order_id: Optional[str] = None
    status: str = 'pending'
    timestamp: Optional[datetime] = None

@dataclass
class Fill:
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    commission: float = 0.0

class StepIndexExecutionEngine:
    def __init__(self, api_key: str = None, secret_key: str = None, sandbox: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.sandbox = sandbox
        
        # Order management
        self.pending_orders = {}
        self.filled_orders = {}
        self.order_queue = Queue()
        self.fill_callbacks = []
        
        # Market data
        self.market_data = {}
        self.last_prices = {}
        
        # Execution settings
        self.max_slippage = 0.1  # 0.1 steps
        self.order_timeout = 30  # seconds
        self.retry_attempts = 3
        
        # Connection management
        self.ws_connection = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Threading
        self.execution_thread = None
        self.market_data_thread = None
        self.running = False
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the execution engine"""
        self.running = True
        
        # Start execution thread
        self.execution_thread = threading.Thread(target=self._execution_worker)
        self.execution_thread.daemon = True
        self.execution_thread.start()
        
        # Start market data thread
        self.market_data_thread = threading.Thread(target=self._market_data_worker)
        self.market_data_thread.daemon = True
        self.market_data_thread.start()
        
        self.logger.info("Execution engine started")
    
    def stop(self):
        """Stop the execution engine"""
        self.running = False
        
        if self.ws_connection:
            asyncio.create_task(self.ws_connection.close())
        
        if self.execution_thread:
            self.execution_thread.join(timeout=5)
        
        if self.market_data_thread:
            self.market_data_thread.join(timeout=5)
        
        self.logger.info("Execution engine stopped")
    
    def submit_order(self, order: Order) -> str:
        """Submit an order for execution"""
        order.order_id = self._generate_order_id()
        order.timestamp = datetime.now()
        order.status = 'pending'
        
        self.pending_orders[order.order_id] = order
        self.order_queue.put(order)
        
        self.logger.info(f"Order submitted: {order.order_id} - {order.side} {order.quantity} {order.symbol}")
        return order.order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        if order_id in self.pending_orders:
            order = self.pending_orders[order_id]
            order.status = 'cancelled'
            
            # In production, send cancel request to broker
            self._simulate_order_cancel(order)
            
            del self.pending_orders[order_id]
            self.logger.info(f"Order cancelled: {order_id}")
            return True
        
        return False
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status"""
        if order_id in self.pending_orders:
            return asdict(self.pending_orders[order_id])
        elif order_id in self.filled_orders:
            return asdict(self.filled_orders[order_id])
        return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price"""
        return self.last_prices.get(symbol)
    
    def add_fill_callback(self, callback: Callable[[Fill], None]):
        """Add callback for order fills"""
        self.fill_callbacks.append(callback)
    
    def _execution_worker(self):
        """Main execution worker thread"""
        while self.running:
            try:
                # Process pending orders
                order = self.order_queue.get(timeout=1)
                self._process_order(order)
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Execution worker error: {e}")
    
    def _market_data_worker(self):
        """Market data worker thread"""
        while self.running:
            try:
                # Simulate market data updates
                self._update_market_data()
                time.sleep(0.1)  # 100ms updates
            except Exception as e:
                self.logger.error(f"Market data worker error: {e}")
    
    def _process_order(self, order: Order):
        """Process a single order"""
        try:
            if order.order_type == 'market':
                self._execute_market_order(order)
            elif order.order_type == 'limit':
                self._execute_limit_order(order)
            elif order.order_type == 'stop':
                self._execute_stop_order(order)
            else:
                self.logger.error(f"Unknown order type: {order.order_type}")
                order.status = 'rejected'
        
        except Exception as e:
            self.logger.error(f"Order processing error: {e}")
            order.status = 'error'
    
    def _execute_market_order(self, order: Order):
        """Execute market order"""
        current_price = self.get_current_price(order.symbol)
        
        if current_price is None:
            self.logger.error(f"No market price available for {order.symbol}")
            order.status = 'rejected'
            return
        
        # Simulate slippage for market orders
        slippage = self._calculate_slippage(order)
        execution_price = current_price + slippage
        
        # Round to Step Index precision (0.1)
        execution_price = round(execution_price, 1)
        
        # Create fill
        fill = Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=execution_price,
            timestamp=datetime.now(),
            commission=self._calculate_commission(order.quantity, execution_price)
        )
        
        # Update order status
        order.status = 'filled'
        order.price = execution_price
        
        # Move to filled orders
        self.filled_orders[order.order_id] = order
        if order.order_id in self.pending_orders:
            del self.pending_orders[order.order_id]
        
        # Notify callbacks
        for callback in self.fill_callbacks:
            try:
                callback(fill)
            except Exception as e:
                self.logger.error(f"Fill callback error: {e}")
        
        self.logger.info(f"Market order filled: {order.order_id} at {execution_price}")
    
    def _execute_limit_order(self, order: Order):
        """Execute limit order (simplified)"""
        current_price = self.get_current_price(order.symbol)
        
        if current_price is None:
            return
        
        # Check if limit price is hit
        should_fill = False
        
        if order.side == 'buy' and current_price <= order.price:
            should_fill = True
        elif order.side == 'sell' and current_price >= order.price:
            should_fill = True
        
        if should_fill:
            # Fill at limit price
            fill = Fill(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.price,
                timestamp=datetime.now(),
                commission=self._calculate_commission(order.quantity, order.price)
            )
            
            order.status = 'filled'
            self.filled_orders[order.order_id] = order
            if order.order_id in self.pending_orders:
                del self.pending_orders[order.order_id]
            
            for callback in self.fill_callbacks:
                try:
                    callback(fill)
                except Exception as e:
                    self.logger.error(f"Fill callback error: {e}")
            
            self.logger.info(f"Limit order filled: {order.order_id} at {order.price}")
    
    def _execute_stop_order(self, order: Order):
        """Execute stop order"""
        current_price = self.get_current_price(order.symbol)
        
        if current_price is None:
            return
        
        # Check if stop price is hit
        should_trigger = False
        
        if order.side == 'buy' and current_price >= order.price:  # Stop buy
            should_trigger = True
        elif order.side == 'sell' and current_price <= order.price:  # Stop sell
            should_trigger = True
        
        if should_trigger:
            # Convert to market order
            order.order_type = 'market'
            order.price = None
            self._execute_market_order(order)
    
    def _calculate_slippage(self, order: Order) -> float:
        """Calculate slippage for market orders"""
        # Simulate slippage based on order size and market conditions
        base_slippage = 0.05  # 0.05 steps base slippage
        
        # Increase slippage for larger orders
        size_factor = min(order.quantity / 10000, 2.0)  # Cap at 2x
        
        # Random component
        import random
        random_factor = random.uniform(0.5, 1.5)
        
        slippage = base_slippage * size_factor * random_factor
        
        # Apply direction
        if order.side == 'buy':
            return slippage  # Pay more when buying
        else:
            return -slippage  # Receive less when selling
    
    def _calculate_commission(self, quantity: float, price: float) -> float:
        """Calculate trading commission"""
        # Typical Step Index commission structure
        notional_value = quantity * price
        commission_rate = 0.0005  # 0.05%
        min_commission = 1.0
        
        commission = max(notional_value * commission_rate, min_commission)
        return commission
    
    def _update_market_data(self):
        """Simulate market data updates"""
        # Simulate Step Index price movement
        symbols = ['STEP_INDEX_10', 'STEP_INDEX_25', 'STEP_INDEX_50', 'STEP_INDEX_75', 'STEP_INDEX_100']
        
        for symbol in symbols:
            if symbol not in self.last_prices:
                self.last_prices[symbol] = 8500.0  # Starting price
            
            # Simulate step movement
            import random
            step_change = random.choice([-0.1, 0, 0.1])
            self.last_prices[symbol] += step_change
            self.last_prices[symbol] = round(self.last_prices[symbol], 1)
            
            # Update market data
            self.market_data[symbol] = {
                'price': self.last_prices[symbol],
                'timestamp': datetime.now(),
                'bid': self.last_prices[symbol] - 0.05,
                'ask': self.last_prices[symbol] + 0.05
            }
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        timestamp = int(datetime.now().timestamp() * 1000000)
        return f"ORD_{timestamp}"
    
    def _simulate_order_cancel(self, order: Order):
        """Simulate order cancellation"""
        # In production, this would send cancel request to broker API
        pass
    
    async def _connect_websocket(self):
        """Connect to market data websocket"""
        try:
            # In production, connect to actual broker websocket
            # For simulation, we'll use a mock connection
            self.is_connected = True
            self.reconnect_attempts = 0
            self.logger.info("WebSocket connected")
            
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
            self.is_connected = False
            
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                await asyncio.sleep(5)  # Wait before retry
                await self._connect_websocket()
    
    def get_execution_statistics(self) -> Dict:
        """Get execution statistics"""
        total_orders = len(self.filled_orders) + len(self.pending_orders)
        filled_orders = len(self.filled_orders)
        
        if filled_orders > 0:
            total_commission = sum(
                self._calculate_commission(order.quantity, order.price or 0)
                for order in self.filled_orders.values()
            )
            
            avg_fill_time = 0.5  # Simulated average fill time
        else:
            total_commission = 0
            avg_fill_time = 0
        
        return {
            'total_orders': total_orders,
            'filled_orders': filled_orders,
            'pending_orders': len(self.pending_orders),
            'fill_rate': filled_orders / total_orders if total_orders > 0 else 0,
            'total_commission': total_commission,
            'avg_fill_time': avg_fill_time,
            'is_connected': self.is_connected
        }

# Smart Order Router for Step Index
class StepIndexSmartRouter:
    def __init__(self, execution_engine: StepIndexExecutionEngine):
        self.execution_engine = execution_engine
        self.order_strategies = {
            'TWAP': self._twap_strategy,
            'VWAP': self._vwap_strategy,
            'ICEBERG': self._iceberg_strategy,
            'SNIPER': self._sniper_strategy
        }
    
    def route_order(self, order: Order, strategy: str = 'TWAP', **kwargs) -> List[str]:
        """Route order using specified strategy"""
        if strategy not in self.order_strategies:
            # Default to immediate execution
            return [self.execution_engine.submit_order(order)]
        
        return self.order_strategies[strategy](order, **kwargs)
    
    def _twap_strategy(self, order: Order, duration_minutes: int = 30, slices: int = 10) -> List[str]:
        """Time-Weighted Average Price strategy"""
        slice_size = order.quantity / slices
        slice_interval = (duration_minutes * 60) / slices
        
        order_ids = []
        
        for i in range(slices):
            slice_order = Order(
                symbol=order.symbol,
                side=order.side,
                quantity=slice_size,
                order_type='market',
                time_in_force='IOC'
            )
            
            if i == 0:
                # Submit first slice immediately
                order_id = self.execution_engine.submit_order(slice_order)
                order_ids.append(order_id)
            else:
                # Schedule remaining slices
                threading.Timer(
                    slice_interval * i,
                    lambda: order_ids.append(self.execution_engine.submit_order(slice_order))
                ).start()
        
        return order_ids
    
    def _vwap_strategy(self, order: Order, **kwargs) -> List[str]:
        """Volume-Weighted Average Price strategy"""
        # Simplified VWAP - in production would use historical volume patterns
        return self._twap_strategy(order, duration_minutes=15, slices=5)
    
    def _iceberg_strategy(self, order: Order, visible_size: float = 0.1) -> List[str]:
        """Iceberg order strategy"""
        visible_quantity = order.quantity * visible_size
        remaining_quantity = order.quantity - visible_quantity
        
        # Submit visible portion
        visible_order = Order(
            symbol=order.symbol,
            side=order.side,
            quantity=visible_quantity,
            price=order.price,
            order_type=order.order_type
        )
        
        order_id = self.execution_engine.submit_order(visible_order)
        
        # TODO: Implement logic to submit remaining quantity as visible portion fills
        
        return [order_id]
    
    def _sniper_strategy(self, order: Order, **kwargs) -> List[str]:
        """Sniper strategy for immediate execution at best price"""
        # Convert to aggressive market order
        order.order_type = 'market'
        order.time_in_force = 'IOC'
        
        return [self.execution_engine.submit_order(order)]

# Usage Example
if __name__ == "__main__":
    # Initialize execution engine
    engine = StepIndexExecutionEngine(sandbox=True)
    engine.start()
    
    # Initialize smart router
    router = StepIndexSmartRouter(engine)
    
    # Example order
    order = Order(
        symbol='STEP_INDEX_10',
        side='buy',
        quantity=1000,
        order_type='market'
    )
    
    # Submit order
    order_id = engine.submit_order(order)
    print(f"Order submitted: {order_id}")
    
    # Wait and check status
    time.sleep(2)
    status = engine.get_order_status(order_id)
    print(f"Order status: {status}")
    
    # Get execution statistics
    stats = engine.get_execution_statistics()
    print(f"Execution stats: {stats}")
    
    # Stop engine
    engine.stop()