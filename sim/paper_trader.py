#!/usr/bin/env python3
"""paper trading simulator with order execution"""

from collections import defaultdict
from sim.costs import total_cost


class PaperTrader:
    """simulate live trading with paper money."""

    def __init__(self, initial_cash=100000, slippage_bps=5):
        self.cash = initial_cash
        self.slippage_bps = slippage_bps
        self.positions = defaultdict(lambda: {"shares": 0, "avg_cost": 0})
        self.open_orders = []
        self.filled_orders = []
        self.order_id = 0

    def market_buy(self, symbol, shares, current_price):
        """execute market buy order."""
        costs = total_cost(shares, current_price, slippage_bps=self.slippage_bps)
        fill_price = costs["fill_price"]
        total = shares * fill_price + costs["commission"]
        if total > self.cash:
            shares = int((self.cash - costs["commission"]) / fill_price)
            if shares <= 0:
                return None
            total = shares * fill_price + costs["commission"]
        self.cash -= total
        pos = self.positions[symbol]
        old_cost = pos["shares"] * pos["avg_cost"]
        pos["shares"] += shares
        pos["avg_cost"] = round((old_cost + shares * fill_price) / pos["shares"], 4)
        order = self._create_order("buy", symbol, shares, fill_price, costs)
        self.filled_orders.append(order)
        return order

    def market_sell(self, symbol, shares, current_price):
        """execute market sell order."""
        pos = self.positions[symbol]
        if pos["shares"] < shares:
            shares = pos["shares"]
        if shares <= 0:
            return None
        costs = total_cost(shares, current_price, slippage_bps=self.slippage_bps)
        fill_price = costs["fill_price"]
        proceeds = shares * fill_price - costs["commission"]
        self.cash += proceeds
        pos["shares"] -= shares
        pnl = (fill_price - pos["avg_cost"]) * shares
        if pos["shares"] == 0:
            del self.positions[symbol]
        order = self._create_order("sell", symbol, shares, fill_price, costs)
        order["pnl"] = round(pnl, 2)
        self.filled_orders.append(order)
        return order

    def limit_buy(self, symbol, shares, limit_price):
        """place limit buy order (fills when price <= limit)."""
        self.order_id += 1
        order = {
            "id": self.order_id, "type": "limit_buy",
            "symbol": symbol, "shares": shares,
            "limit_price": limit_price, "status": "open",
        }
        self.open_orders.append(order)
        return order

    def limit_sell(self, symbol, shares, limit_price):
        """place limit sell order (fills when price >= limit)."""
        self.order_id += 1
        order = {
            "id": self.order_id, "type": "limit_sell",
            "symbol": symbol, "shares": shares,
            "limit_price": limit_price, "status": "open",
        }
        self.open_orders.append(order)
        return order

    def check_orders(self, prices):
        """check open orders against current prices, fill if triggered."""
        remaining = []
        for order in self.open_orders:
            symbol = order["symbol"]
            price = prices.get(symbol, 0)
            if order["type"] == "limit_buy" and price <= order["limit_price"]:
                self.market_buy(symbol, order["shares"], price)
                order["status"] = "filled"
            elif order["type"] == "limit_sell" and price >= order["limit_price"]:
                self.market_sell(symbol, order["shares"], price)
                order["status"] = "filled"
            else:
                remaining.append(order)
        self.open_orders = remaining

    def portfolio_value(self, prices):
        """calculate total portfolio value."""
        pos_value = sum(
            p["shares"] * prices.get(s, 0) for s, p in self.positions.items()
        )
        return round(self.cash + pos_value, 2)

    def _create_order(self, action, symbol, shares, fill_price, costs):
        """create filled order record."""
        self.order_id += 1
        return {
            "id": self.order_id, "action": action, "symbol": symbol,
            "shares": shares, "fill_price": fill_price,
            "commission": costs["commission"],
            "slippage_cost": costs["slippage_cost"],
        }


if __name__ == "__main__":
    trader = PaperTrader(100000)
    trader.market_buy("AAPL", 50, 150.0)
    trader.market_buy("MSFT", 30, 300.0)
    prices = {"AAPL": 155.0, "MSFT": 305.0}
    print(f"portfolio: ${trader.portfolio_value(prices)}")
    print(f"cash: ${trader.cash:.2f}")
    print(f"orders filled: {len(trader.filled_orders)}")
