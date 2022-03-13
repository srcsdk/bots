#!/usr/bin/env python3
"""real-time position tracking and unrealized pnl"""


class PositionTracker:
    """track open positions with entry prices and unrealized pnl."""

    def __init__(self):
        self.positions = {}

    def open_position(self, symbol, shares, entry_price, side="long"):
        """open or add to a position."""
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_shares = pos["shares"] + shares
            total_cost = (
                pos["shares"] * pos["avg_price"] + shares * entry_price
            )
            pos["avg_price"] = round(total_cost / total_shares, 4)
            pos["shares"] = total_shares
        else:
            self.positions[symbol] = {
                "shares": shares,
                "avg_price": entry_price,
                "side": side,
            }

    def close_position(self, symbol, shares=None):
        """close all or part of a position."""
        if symbol not in self.positions:
            return None
        pos = self.positions[symbol]
        if shares is None or shares >= pos["shares"]:
            closed = dict(pos)
            del self.positions[symbol]
            return closed
        pos["shares"] -= shares
        return {"shares": shares, "avg_price": pos["avg_price"],
                "side": pos["side"]}

    def unrealized_pnl(self, symbol, current_price):
        """calculate unrealized pnl for a position."""
        if symbol not in self.positions:
            return 0
        pos = self.positions[symbol]
        if pos["side"] == "long":
            pnl = (current_price - pos["avg_price"]) * pos["shares"]
        else:
            pnl = (pos["avg_price"] - current_price) * pos["shares"]
        return round(pnl, 2)

    def total_unrealized(self, prices):
        """calculate total unrealized pnl across all positions."""
        total = 0
        for symbol in self.positions:
            if symbol in prices:
                total += self.unrealized_pnl(symbol, prices[symbol])
        return round(total, 2)

    def position_value(self, symbol, current_price):
        """current market value of a position."""
        if symbol not in self.positions:
            return 0
        return round(
            self.positions[symbol]["shares"] * current_price, 2
        )

    def total_value(self, prices):
        """total market value of all positions."""
        return round(sum(
            self.position_value(s, prices.get(s, 0))
            for s in self.positions
        ), 2)

    def summary(self, prices):
        """summary of all positions."""
        rows = []
        for symbol, pos in self.positions.items():
            price = prices.get(symbol, 0)
            rows.append({
                "symbol": symbol,
                "shares": pos["shares"],
                "avg_price": pos["avg_price"],
                "current": price,
                "pnl": self.unrealized_pnl(symbol, price),
                "value": self.position_value(symbol, price),
            })
        return rows


if __name__ == "__main__":
    tracker = PositionTracker()
    tracker.open_position("AAPL", 100, 150.0)
    tracker.open_position("AAPL", 50, 155.0)
    tracker.open_position("MSFT", 75, 280.0)
    prices = {"AAPL": 160.0, "MSFT": 290.0}
    for row in tracker.summary(prices):
        print(f"  {row['symbol']}: {row['shares']} @ "
              f"{row['avg_price']} -> pnl ${row['pnl']}")
    print(f"total unrealized: ${tracker.total_unrealized(prices)}")
