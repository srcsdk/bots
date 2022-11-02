#!/usr/bin/env python3
"""order type definitions for backtesting and live trading"""


class Order:
    """base order with common fields."""

    def __init__(self, ticker, side, quantity, order_type="market"):
        if side not in ("buy", "sell"):
            raise ValueError(f"invalid side: {side}")
        if quantity <= 0:
            raise ValueError(f"invalid quantity: {quantity}")
        self.ticker = ticker
        self.side = side
        self.quantity = quantity
        self.order_type = order_type
        self.filled = False
        self.fill_price = None
        self.fill_time = None

    def can_fill(self, current_price, current_time=None):
        """check if order can be filled at current price."""
        if self.filled:
            return False
        return True

    def fill(self, price, time=None):
        """mark order as filled."""
        self.filled = True
        self.fill_price = price
        self.fill_time = time

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "type": self.order_type,
            "filled": self.filled,
            "fill_price": self.fill_price,
        }


class LimitOrder(Order):
    """limit order that only fills at specified price or better."""

    def __init__(self, ticker, side, quantity, limit_price):
        super().__init__(ticker, side, quantity, "limit")
        if limit_price <= 0:
            raise ValueError(f"invalid limit price: {limit_price}")
        self.limit_price = limit_price

    def can_fill(self, current_price, current_time=None):
        if self.filled:
            return False
        if self.side == "buy" and current_price <= self.limit_price:
            return True
        if self.side == "sell" and current_price >= self.limit_price:
            return True
        return False


class StopOrder(Order):
    """stop order triggered when price hits stop level."""

    def __init__(self, ticker, side, quantity, stop_price):
        super().__init__(ticker, side, quantity, "stop")
        if stop_price <= 0:
            raise ValueError(f"invalid stop price: {stop_price}")
        self.stop_price = stop_price
        self.triggered = False

    def can_fill(self, current_price, current_time=None):
        if self.filled:
            return False
        if not self.triggered:
            if self.side == "sell" and current_price <= self.stop_price:
                self.triggered = True
            elif self.side == "buy" and current_price >= self.stop_price:
                self.triggered = True
        return self.triggered


class StopLimitOrder(Order):
    """stop limit: triggered at stop, fills at limit or better."""

    def __init__(self, ticker, side, quantity, stop_price, limit_price):
        super().__init__(ticker, side, quantity, "stop_limit")
        self.stop_price = stop_price
        self.limit_price = limit_price
        self.triggered = False

    def can_fill(self, current_price, current_time=None):
        if self.filled:
            return False
        if not self.triggered:
            if self.side == "sell" and current_price <= self.stop_price:
                self.triggered = True
            elif self.side == "buy" and current_price >= self.stop_price:
                self.triggered = True
        if not self.triggered:
            return False
        if self.side == "buy" and current_price <= self.limit_price:
            return True
        if self.side == "sell" and current_price >= self.limit_price:
            return True
        return False


if __name__ == "__main__":
    limit = LimitOrder("AAPL", "buy", 100, 145.0)
    print(f"limit buy at 145: can fill at 144? {limit.can_fill(144.0)}")
    print(f"limit buy at 145: can fill at 146? {limit.can_fill(146.0)}")

    stop = StopOrder("AAPL", "sell", 100, 140.0)
    print(f"stop sell at 140: triggered at 141? {stop.can_fill(141.0)}")
    print(f"stop sell at 140: triggered at 139? {stop.can_fill(139.0)}")
