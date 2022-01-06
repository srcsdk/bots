#!/usr/bin/env python3
"""portfolio simulator with position tracking and cash management"""


class PortfolioSim:
    """simulate portfolio with multiple positions and cash balance."""

    def __init__(self, initial_cash=100000):
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.positions = {}
        self.history = []

    def buy(self, symbol, shares, price):
        """buy shares of a symbol."""
        cost = shares * price
        if cost > self.cash:
            shares = int(self.cash / price)
            cost = shares * price
        if shares <= 0:
            return False
        self.cash -= cost
        pos = self.positions.get(symbol, {"shares": 0, "avg_cost": 0})
        total_shares = pos["shares"] + shares
        total_cost = pos["shares"] * pos["avg_cost"] + cost
        pos["avg_cost"] = round(total_cost / total_shares, 4)
        pos["shares"] = total_shares
        self.positions[symbol] = pos
        return True

    def sell(self, symbol, shares, price):
        """sell shares of a symbol."""
        pos = self.positions.get(symbol)
        if not pos or pos["shares"] < shares:
            return False
        proceeds = shares * price
        self.cash += proceeds
        pos["shares"] -= shares
        if pos["shares"] == 0:
            del self.positions[symbol]
        return True

    def value(self, prices):
        """calculate total portfolio value given current prices."""
        position_value = sum(
            pos["shares"] * prices.get(sym, 0)
            for sym, pos in self.positions.items()
        )
        return round(self.cash + position_value, 2)

    def snapshot(self, date, prices):
        """record portfolio state at a point in time."""
        total = self.value(prices)
        self.history.append({
            "date": date,
            "cash": round(self.cash, 2),
            "positions": {s: p["shares"] for s, p in self.positions.items()},
            "total_value": total,
        })
        return total

    def pnl(self, prices):
        """calculate unrealized pnl for all positions."""
        result = {}
        for sym, pos in self.positions.items():
            current = prices.get(sym, 0)
            cost_basis = pos["avg_cost"] * pos["shares"]
            market_value = current * pos["shares"]
            result[sym] = {
                "shares": pos["shares"],
                "avg_cost": pos["avg_cost"],
                "current": current,
                "pnl": round(market_value - cost_basis, 2),
                "pnl_pct": round((current / pos["avg_cost"] - 1) * 100, 2),
            }
        return result

    def allocation(self, prices):
        """calculate position weights as percentage of portfolio."""
        total = self.value(prices)
        if total == 0:
            return {}
        alloc = {"cash": round(self.cash / total * 100, 2)}
        for sym, pos in self.positions.items():
            mv = pos["shares"] * prices.get(sym, 0)
            alloc[sym] = round(mv / total * 100, 2)
        return alloc


if __name__ == "__main__":
    port = PortfolioSim(100000)
    port.buy("AAPL", 100, 150.0)
    port.buy("MSFT", 50, 300.0)
    prices = {"AAPL": 155.0, "MSFT": 310.0}
    print(f"total value: ${port.value(prices)}")
    print(f"allocation: {port.allocation(prices)}")
    for sym, data in port.pnl(prices).items():
        print(f"  {sym}: ${data['pnl']} ({data['pnl_pct']}%)")
