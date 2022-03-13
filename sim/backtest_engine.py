#!/usr/bin/env python3
"""core backtesting engine for strategy evaluation"""


class BacktestEngine:
    """run strategies against historical data and collect results."""

    def __init__(self, initial_capital=100000, commission=0.001):
        self.initial_capital = initial_capital
        self.commission = commission
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []

    def run(self, strategy, data):
        """run strategy against price data."""
        self.capital = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.equity_curve.clear()
        for i, bar in enumerate(data):
            signal = strategy(data[:i + 1], self.positions)
            if signal:
                self._execute_signal(signal, bar)
            equity = self.capital + self._position_value(bar)
            self.equity_curve.append(equity)
        self._close_all(data[-1] if data else {})
        return self.results()

    def _execute_signal(self, signal, bar):
        """execute a trade signal."""
        symbol = signal.get("symbol", "default")
        action = signal.get("action")
        price = bar.get("close", 0)
        size = signal.get("size", 100)
        cost = price * size * self.commission
        if action == "buy" and self.capital >= price * size + cost:
            self.capital -= price * size + cost
            if symbol not in self.positions:
                self.positions[symbol] = {"size": 0, "avg_price": 0}
            pos = self.positions[symbol]
            total_cost = pos["avg_price"] * pos["size"] + price * size
            pos["size"] += size
            pos["avg_price"] = total_cost / pos["size"] if pos["size"] else 0
        elif action == "sell" and symbol in self.positions:
            pos = self.positions[symbol]
            sell_size = min(size, pos["size"])
            revenue = price * sell_size - cost
            pnl = (price - pos["avg_price"]) * sell_size - cost
            self.capital += revenue
            self.trades.append({
                "symbol": symbol,
                "entry": pos["avg_price"],
                "exit": price,
                "size": sell_size,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl / (pos["avg_price"] * sell_size) * 100, 2),
            })
            pos["size"] -= sell_size
            if pos["size"] <= 0:
                del self.positions[symbol]

    def _position_value(self, bar):
        """calculate current value of open positions."""
        price = bar.get("close", 0)
        return sum(
            pos["size"] * price for pos in self.positions.values()
        )

    def _close_all(self, bar):
        """close all positions at end of backtest."""
        for symbol in list(self.positions.keys()):
            self._execute_signal(
                {"symbol": symbol, "action": "sell",
                 "size": self.positions[symbol]["size"]},
                bar,
            )

    def results(self):
        """calculate backtest results."""
        if not self.trades:
            return {"total_trades": 0, "total_return": 0}
        total_pnl = sum(t["pnl"] for t in self.trades)
        wins = [t for t in self.trades if t["pnl"] > 0]
        losses = [t for t in self.trades if t["pnl"] <= 0]
        return {
            "total_trades": len(self.trades),
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(
                total_pnl / self.initial_capital * 100, 2
            ),
            "win_rate": round(len(wins) / len(self.trades) * 100, 1),
            "avg_win": round(
                sum(t["pnl"] for t in wins) / len(wins), 2
            ) if wins else 0,
            "avg_loss": round(
                sum(t["pnl"] for t in losses) / len(losses), 2
            ) if losses else 0,
            "max_equity": max(self.equity_curve) if self.equity_curve else 0,
            "min_equity": min(self.equity_curve) if self.equity_curve else 0,
        }


if __name__ == "__main__":
    engine = BacktestEngine(initial_capital=10000)
    print(f"backtest engine ready, capital: ${engine.initial_capital}")
