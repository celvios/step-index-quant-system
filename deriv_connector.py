import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
import ssl

class DerivConnector:
    def __init__(self, app_id: str, api_token: str = None, is_demo: bool = True):
        self.app_id = app_id
        self.api_token = api_token
        self.is_demo = is_demo
        
        # WebSocket connection
        self.ws = None
        self.is_connected = False
        self.req_id = 1
        
        # Callbacks
        self.tick_callbacks = []
        self.transaction_callbacks = []
        
        # Account info
        self.account_info = {}
        self.balance = 0
        self.positions = {}
        
        # Step Index symbols
        self.step_symbols = {
            'STEP_10': 'R_10',
            'STEP_25': 'R_25', 
            'STEP_50': 'R_50',
            'STEP_75': 'R_75',
            'STEP_100': 'R_100'
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def connect(self):
        """Connect to Deriv WebSocket API"""
        url = f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}"
        
        try:
            self.ws = await websockets.connect(url)
            self.is_connected = True
            
            # Authorize if token provided
            if self.api_token:
                await self.authorize()
                # Wait for authorization response
                await asyncio.sleep(3)
            
            # Start message handler
            asyncio.create_task(self._message_handler())
            
            self.logger.info("Connected to Deriv API")
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Deriv API"""
        if self.ws:
            await self.ws.close()
            self.is_connected = False
            self.logger.info("Disconnected from Deriv API")
    
    async def authorize(self):
        """Authorize with API token"""
        request = {
            "authorize": self.api_token,
            "req_id": self._get_req_id()
        }
        
        await self._send_request(request)
    
    async def get_account_info(self):
        """Get account information"""
        # Get balance
        balance_request = {
            "balance": 1,
            "req_id": self._get_req_id()
        }
        
        await self._send_request(balance_request)
    
    async def subscribe_ticks(self, symbol: str):
        """Subscribe to tick data for Step Index"""
        deriv_symbol = self.step_symbols.get(symbol, symbol)
        
        request = {
            "ticks": deriv_symbol,
            "subscribe": 1,
            "req_id": self._get_req_id()
        }
        
        await self._send_request(request)
        self.logger.info(f"Subscribed to {deriv_symbol} ticks")
    
    async def buy_contract(self, symbol: str, stake: float, duration: int = 5, 
                          contract_type: str = "CALL", barrier: float = None):
        """Buy a Step Index contract"""
        deriv_symbol = self.step_symbols.get(symbol, symbol)
        
        # Enable auto-buy for proposals
        self._auto_buy_proposals = True
        self._pending_stake = stake
        
        proposal_request = {
            "proposal": 1,
            "amount": stake,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": "USD",
            "symbol": deriv_symbol,
            "duration": duration,
            "duration_unit": "t",  # ticks
            "req_id": self._get_req_id()
        }
        
        if barrier:
            proposal_request["barrier"] = str(barrier)
        
        await self._send_request(proposal_request)
    
    async def buy_proposal(self, proposal_id: str, price: float):
        """Buy a contract using proposal ID"""
        request = {
            "buy": proposal_id,
            "price": price,
            "req_id": self._get_req_id()
        }
        
        await self._send_request(request)
    
    async def sell_contract(self, contract_id: str, price: float = None):
        """Sell an open contract"""
        request = {
            "sell": contract_id,
            "req_id": self._get_req_id()
        }
        
        if price:
            request["price"] = price
        
        await self._send_request(request)
    
    async def get_portfolio(self):
        """Get current portfolio/positions"""
        request = {
            "portfolio": 1,
            "req_id": self._get_req_id()
        }
        
        await self._send_request(request)
    
    async def get_profit_table(self, limit: int = 50):
        """Get profit/loss table"""
        request = {
            "profit_table": 1,
            "description": 1,
            "limit": limit,
            "req_id": self._get_req_id()
        }
        
        await self._send_request(request)
    
    def add_tick_callback(self, callback: Callable):
        """Add callback for tick updates"""
        self.tick_callbacks.append(callback)
    
    def add_transaction_callback(self, callback: Callable):
        """Add callback for transaction updates"""
        self.transaction_callbacks.append(callback)
    
    async def _send_request(self, request: Dict):
        """Send request to Deriv API"""
        if not self.is_connected or not self.ws:
            raise Exception("Not connected to Deriv API")
        
        message = json.dumps(request)
        await self.ws.send(message)
        self.logger.debug(f"Sent: {message}")
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self._process_message(data)
                
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
            self.logger.warning("WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")
    
    async def _process_message(self, data: Dict):
        """Process incoming message"""
        # Check for errors first
        if 'error' in data:
            error_msg = data['error'].get('message', 'Unknown error')
            self.logger.error(f"API Error: {error_msg}")
            self.is_connected = False
            return
        
        msg_type = data.get('msg_type')
        
        if msg_type == 'authorize':
            # Get balance from authorize response
            authorize_data = data.get('authorize', {})
            if not authorize_data or 'loginid' not in authorize_data:
                self.logger.error("Authorization failed - invalid token")
                self.is_connected = False
                return
            
            self.balance = float(authorize_data.get('balance', 0))
            self.account_info = authorize_data
            loginid = authorize_data.get('loginid', 'Unknown')
            self.logger.info(f"Authorization successful - Account: {loginid}, Balance: {self.balance}")
            
        elif msg_type == 'balance':
            balance_data = data.get('balance', {})
            self.balance = float(balance_data.get('balance', 0))
            self.logger.info(f"Balance updated: {self.balance}")
            
        elif msg_type == 'tick':
            await self._handle_tick(data)
            
        elif msg_type == 'buy':
            await self._handle_buy_response(data)
            
        elif msg_type == 'sell':
            await self._handle_sell_response(data)
            
        elif msg_type == 'portfolio':
            await self._handle_portfolio(data)
            
        elif msg_type == 'proposal':
            await self._handle_proposal(data)
            
        # Error handling moved to top of function
    
    async def _handle_tick(self, data: Dict):
        """Handle tick data"""
        tick_data = {
            'symbol': data.get('echo_req', {}).get('ticks'),
            'price': data.get('tick', {}).get('quote'),
            'timestamp': datetime.fromtimestamp(data.get('tick', {}).get('epoch', 0))
        }
        
        # Notify callbacks
        for callback in self.tick_callbacks:
            try:
                await callback(tick_data)
            except Exception as e:
                self.logger.error(f"Tick callback error: {e}")
    
    async def _handle_buy_response(self, data: Dict):
        """Handle buy response"""
        if 'buy' in data:
            contract_info = {
                'contract_id': data['buy']['contract_id'],
                'transaction_id': data['buy']['transaction_id'],
                'start_time': data['buy']['start_time'],
                'purchase_time': data['buy']['purchase_time'],
                'buy_price': data['buy']['buy_price']
            }
            
            self.logger.info(f"Contract purchased: {contract_info['contract_id']}")
            
            # Notify callbacks
            for callback in self.transaction_callbacks:
                try:
                    await callback('buy', contract_info)
                except Exception as e:
                    self.logger.error(f"Transaction callback error: {e}")
    
    async def _handle_sell_response(self, data: Dict):
        """Handle sell response"""
        if 'sell' in data:
            sell_info = {
                'transaction_id': data['sell']['transaction_id'],
                'sold_for': data['sell']['sold_for']
            }
            
            self.logger.info(f"Contract sold for: {sell_info['sold_for']}")
            
            # Notify callbacks
            for callback in self.transaction_callbacks:
                try:
                    await callback('sell', sell_info)
                except Exception as e:
                    self.logger.error(f"Transaction callback error: {e}")
    
    async def _handle_portfolio(self, data: Dict):
        """Handle portfolio data"""
        if 'portfolio' in data:
            self.positions = {}
            for contract in data['portfolio']['contracts']:
                self.positions[contract['contract_id']] = contract
            
            self.logger.info(f"Portfolio updated: {len(self.positions)} positions")
    
    async def _handle_proposal(self, data: Dict):
        """Handle proposal response"""
        if 'proposal' in data:
            proposal = data['proposal']
            self.logger.info(f"Proposal received: ID={proposal['id']}, Price={proposal['ask_price']}")
            
            # Auto-buy if enabled
            if hasattr(self, '_auto_buy_proposals') and self._auto_buy_proposals:
                self._auto_buy_proposals = False  # Reset flag
                await self.buy_proposal(proposal['id'], proposal['ask_price'])
    
    def _get_req_id(self) -> int:
        """Get next request ID"""
        self.req_id += 1
        return self.req_id

# Step Index Trading Adapter
class StepIndexDerivTrader:
    def __init__(self, app_id: str, api_token: str, is_demo: bool = True):
        self.connector = DerivConnector(app_id, api_token, is_demo)
        self.current_prices = {}
        self.active_contracts = {}
        
    async def connect(self):
        """Connect to Deriv and setup subscriptions"""
        await self.connector.connect()
        
        # Subscribe to Step Index ticks
        for symbol in ['STEP_10', 'STEP_25', 'STEP_50']:
            await self.connector.subscribe_ticks(symbol)
        
        # Setup callbacks
        self.connector.add_tick_callback(self._on_tick_update)
        self.connector.add_transaction_callback(self._on_transaction)
    
    async def place_step_trade(self, symbol: str, direction: str, stake: float, 
                              duration_ticks: int = 5):
        """Place a Step Index trade"""
        contract_type = "CALL" if direction.upper() == "LONG" else "PUT"
        
        # Store pending trade info
        self.pending_trade = {
            'symbol': symbol,
            'direction': direction,
            'stake': stake,
            'timestamp': datetime.now()
        }
        
        await self.connector.buy_contract(
            symbol=symbol,
            stake=stake,
            duration=duration_ticks,
            contract_type=contract_type
        )
        
        # Return a temporary contract ID (real one comes from buy response)
        return f"temp_{int(datetime.now().timestamp())}"
    
    async def close_position(self, contract_id: str):
        """Close an open position"""
        await self.connector.sell_contract(contract_id)
    
    async def get_account_balance(self) -> float:
        """Get current account balance"""
        return self.connector.balance
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        return self.current_prices.get(symbol)
    
    async def _on_tick_update(self, tick_data: Dict):
        """Handle tick updates"""
        symbol = tick_data['symbol']
        price = tick_data['price']
        
        # Convert Deriv symbol back to our format
        for our_symbol, deriv_symbol in self.connector.step_symbols.items():
            if deriv_symbol == symbol:
                self.current_prices[our_symbol] = price
                break
    
    async def _on_transaction(self, transaction_type: str, data: Dict):
        """Handle transaction updates"""
        if transaction_type == 'buy':
            contract_id = data['contract_id']
            self.active_contracts[contract_id] = data
            
            # Log successful trade placement
            if hasattr(self, 'pending_trade'):
                print(f"Contract purchased: {contract_id} for ${data.get('buy_price', 0)}")
                
        elif transaction_type == 'sell':
            # Remove from active contracts
            for contract_id in list(self.active_contracts.keys()):
                if data.get('transaction_id') in str(contract_id):
                    del self.active_contracts[contract_id]
                    break

# Usage Example
async def main():
    # Initialize trader (replace with your Deriv credentials)
    trader = StepIndexDerivTrader(
        app_id="YOUR_APP_ID",  # Get from Deriv API
        api_token="YOUR_API_TOKEN",  # Get from Deriv account
        is_demo=True  # Set to False for real account
    )
    
    try:
        # Connect
        await trader.connect()
        
        # Wait for price data
        await asyncio.sleep(2)
        
        # Get current price
        price = await trader.get_current_price('STEP_10')
        print(f"Current STEP_10 price: {price}")
        
        # Place a trade
        await trader.place_step_trade(
            symbol='STEP_10',
            direction='LONG',
            stake=10.0,
            duration_ticks=5
        )
        
        # Keep running
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await trader.connector.disconnect()

if __name__ == "__main__":
    asyncio.run(main())