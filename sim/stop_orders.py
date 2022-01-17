#!/usr/bin/env python3
"""stop and stop-limit order types for paper trading"""


class StopOrderManager:
    """manage stop loss and stop limit orders."""

    def __init__(self):
        self.stops = []
        self.next_id = 1

    def add_stop_loss(self, symbol, shares, stop_price, order_type="market"):
        """add stop loss order. triggers sell when price drops to stop_price."""
        order = {
            "id": self.next_id, "symbol": symbol, "shares": shares,
            "stop_price": stop_price, "type": order_type,
            "status": "active", "direction": "sell",
        }
        self.stops.append(order)
        self.next_id += 1
        return order

    def add_stop_buy(self, symbol, shares, stop_price):
        """add stop buy order. triggers buy when price rises to stop_price."""
        order = {
            "id": self.next_id, "symbol": symbol, "shares": shares,
            "stop_price": stop_price, "type": "market",
            "status": "active", "direction": "buy",
        }
        self.stops.append(order)
        self.next_id += 1
        return order

    def add_trailing_stop(self, symbol, shares, trail_pct, current_price):
        """add trailing stop that follows price up."""
        stop_price = round(current_price * (1 - trail_pct / 100), 4)
        order = {
            "id": self.next_id, "symbol": symbol, "shares": shares,
            "stop_price": stop_price, "type": "trailing",
            "trail_pct": trail_pct, "high_water": current_price,
            "status": "active", "direction": "sell",
        }
        self.stops.append(order)
        self.next_id += 1
        return order

    def check_stops(self, prices):
        """check all active stops against current prices.

        returns list of triggered orders.
        """
        triggered = []
        for order in self.stops:
            if order["status"] != "active":
                continue
            symbol = order["symbol"]
            price = prices.get(symbol)
            if price is None:
                continue
            if order["type"] == "trailing":
                if price > order["high_water"]:
                    order["high_water"] = price
                    order["stop_price"] = round(
                        price * (1 - order["trail_pct"] / 100), 4
                    )
            if order["direction"] == "sell" and price <= order["stop_price"]:
                order["status"] = "triggered"
                order["trigger_price"] = price
                triggered.append(order)
            elif order["direction"] == "buy" and price >= order["stop_price"]:
                order["status"] = "triggered"
                order["trigger_price"] = price
                triggered.append(order)
        return triggered

    def cancel(self, order_id):
        """cancel an active stop order."""
        for order in self.stops:
            if order["id"] == order_id and order["status"] == "active":
                order["status"] = "cancelled"
                return True
        return False

    def active_stops(self):
        """return all active stop orders."""
        return [o for o in self.stops if o["status"] == "active"]


if __name__ == "__main__":
    mgr = StopOrderManager()
    mgr.add_stop_loss("AAPL", 50, 145.0)
    mgr.add_trailing_stop("MSFT", 30, 5.0, 300.0)
    prices = {"AAPL": 144.0, "MSFT": 310.0}
    triggered = mgr.check_stops(prices)
    print(f"triggered: {len(triggered)}")
    for t in triggered:
        print(f"  {t['symbol']} {t['direction']} @ {t['trigger_price']}")
    print(f"active: {len(mgr.active_stops())}")
