#!/usr/bin/env python3
"""trade execution simulator with realistic fills"""

import random


class ExecutionSimulator:
    """simulate realistic trade execution with delays and partial fills."""

    def __init__(self, slippage_bps=5, fill_rate=0.95, latency_ms=50):
        self.slippage_bps = slippage_bps
        self.fill_rate = fill_rate
        self.latency_ms = latency_ms
        self.order_history = []
        self._order_id = 0

    def submit_order(self, symbol, side, quantity, order_type="market",
                     limit_price=None):
        """submit an order and return order id."""
        self._order_id += 1
        order = {
            "id": self._order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "type": order_type,
            "limit_price": limit_price,
            "status": "pending",
            "fills": [],
        }
        self.order_history.append(order)
        return self._order_id

    def execute(self, order_id, market_price, volume=100000):
        """simulate order execution against market."""
        order = self._find_order(order_id)
        if not order or order["status"] != "pending":
            return None
        if order["type"] == "limit":
            if order["side"] == "buy" and market_price > order["limit_price"]:
                return None
            if order["side"] == "sell" and market_price < order["limit_price"]:
                return None
        slippage = market_price * (self.slippage_bps / 10000)
        if order["side"] == "buy":
            fill_price = market_price + slippage
        else:
            fill_price = market_price - slippage
        max_fill = int(volume * 0.1)
        fill_qty = min(order["quantity"], max_fill)
        if random.random() > self.fill_rate:
            fill_qty = int(fill_qty * random.uniform(0.3, 0.9))
        if fill_qty <= 0:
            return None
        fill = {
            "price": round(fill_price, 4),
            "quantity": fill_qty,
        }
        order["fills"].append(fill)
        filled_total = sum(f["quantity"] for f in order["fills"])
        if filled_total >= order["quantity"]:
            order["status"] = "filled"
        else:
            order["status"] = "partial"
        return fill

    def cancel_order(self, order_id):
        """cancel a pending order."""
        order = self._find_order(order_id)
        if order and order["status"] in ("pending", "partial"):
            order["status"] = "cancelled"
            return True
        return False

    def avg_fill_price(self, order_id):
        """calculate average fill price for an order."""
        order = self._find_order(order_id)
        if not order or not order["fills"]:
            return 0
        total_cost = sum(
            f["price"] * f["quantity"] for f in order["fills"]
        )
        total_qty = sum(f["quantity"] for f in order["fills"])
        return round(total_cost / total_qty, 4) if total_qty > 0 else 0

    def _find_order(self, order_id):
        for order in self.order_history:
            if order["id"] == order_id:
                return order
        return None

    def stats(self):
        """execution statistics."""
        filled = [o for o in self.order_history if o["status"] == "filled"]
        partial = [o for o in self.order_history if o["status"] == "partial"]
        return {
            "total_orders": len(self.order_history),
            "filled": len(filled),
            "partial": len(partial),
            "fill_rate": round(
                len(filled) / len(self.order_history) * 100, 1
            ) if self.order_history else 0,
        }


if __name__ == "__main__":
    sim = ExecutionSimulator(slippage_bps=5)
    oid = sim.submit_order("AAPL", "buy", 500, "market")
    fill = sim.execute(oid, 150.0, volume=50000)
    print(f"fill: {fill}")
    print(f"avg price: {sim.avg_fill_price(oid)}")
    print(f"stats: {sim.stats()}")
