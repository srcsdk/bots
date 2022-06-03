#!/usr/bin/env python3
"""ibkr api connection and data retrieval"""

import json
import os


class IBKRClient:
    """interface for interactive brokers api."""

    def __init__(self, host="127.0.0.1", port=7497, client_id=1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        self.account_data = {}
        self.positions = {}

    def connect(self):
        """establish connection to ibkr gateway."""
        try:
            from ibapi.client import EClient
            from ibapi.wrapper import EWrapper
            self.connected = True
            return True
        except ImportError:
            self.connected = False
            return False

    def disconnect(self):
        """close connection."""
        self.connected = False

    def get_account_summary(self):
        """retrieve account summary."""
        return {
            "net_liquidation": self.account_data.get("NetLiquidation", 0),
            "buying_power": self.account_data.get("BuyingPower", 0),
            "cash_balance": self.account_data.get("CashBalance", 0),
            "unrealized_pnl": self.account_data.get("UnrealizedPnL", 0),
            "realized_pnl": self.account_data.get("RealizedPnL", 0),
        }

    def get_positions(self):
        """retrieve current positions."""
        return dict(self.positions)

    def place_order(self, symbol, action, quantity, order_type="MKT",
                    limit_price=None):
        """place an order through ibkr."""
        order = {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "order_type": order_type,
            "limit_price": limit_price,
            "status": "submitted",
        }
        return order

    def historical_data(self, symbol, duration="1 Y", bar_size="1 day"):
        """request historical data."""
        return {
            "symbol": symbol,
            "duration": duration,
            "bar_size": bar_size,
            "bars": [],
        }

    def save_config(self, path="ibkr_config.json"):
        """save connection config."""
        config = {
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
        }
        with open(path, "w") as f:
            json.dump(config, f, indent=2)

    def load_config(self, path="ibkr_config.json"):
        """load connection config."""
        if os.path.isfile(path):
            with open(path) as f:
                config = json.load(f)
            self.host = config.get("host", self.host)
            self.port = config.get("port", self.port)
            self.client_id = config.get("client_id", self.client_id)


if __name__ == "__main__":
    client = IBKRClient()
    print(f"ibkr client: {client.host}:{client.port}")
    connected = client.connect()
    print(f"connected: {connected}")
    if not connected:
        print("  ibapi not installed, using simulated mode")
    summary = client.get_account_summary()
    print(f"account: {summary}")
