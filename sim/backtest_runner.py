#!/usr/bin/env python3
"""backtest runner for evaluating strategies on historical data"""


class BacktestRunner:
    """run a strategy against historical data and collect results."""

    def __init__(self, data, strategy_fn, initial_capital=100000):
        self.data = data
        self.strategy_fn = strategy_fn
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []

    def run(self, start=None, end=None):
        """execute backtest over date range."""
        filtered = self.data
        if start:
            filtered = [d for d in filtered if d["date"] >= start]
        if end:
            filtered = [d for d in filtered if d["date"] <= end]
        for i, bar in enumerate(filtered):
            lookback = filtered[max(0, i - 100):i + 1]
            signal = self.strategy_fn(lookback, self.positions)
            if signal:
                self._execute(signal, bar)
            self._update_equity(bar)
        return self._summary()

    def _execute(self, signal, bar):
        """execute a trade signal."""
        symbol = signal.get("symbol", "default")
        if signal["action"] == "buy" and self.capital > 0:
            shares = int(self.capital * signal.get("size", 0.1) / bar["close"])
            if shares > 0:
                cost = shares * bar["close"]
                self.capital -= cost
                self.positions[symbol] = self.positions.get(symbol, 0) + shares
                self.trades.append({
                    "date": bar["date"], "action": "buy",
                    "shares": shares, "price": bar["close"],
                })
        elif signal["action"] == "sell" and self.positions.get(symbol, 0) > 0:
            shares = self.positions[symbol]
            proceeds = shares * bar["close"]
            self.capital += proceeds
            self.positions[symbol] = 0
            self.trades.append({
                "date": bar["date"], "action": "sell",
                "shares": shares, "price": bar["close"],
            })

    def _update_equity(self, bar):
        """track portfolio value over time."""
        position_value = sum(
            qty * bar["close"] for qty in self.positions.values()
        )
        total = self.capital + position_value
        self.equity_curve.append({"date": bar["date"], "equity": round(total, 2)})

    def _summary(self):
        """generate backtest summary."""
        if not self.equity_curve:
            return {}
        final = self.equity_curve[-1]["equity"]
        total_return = (final - self.initial_capital) / self.initial_capital
        return {
            "initial_capital": self.initial_capital,
            "final_equity": final,
            "total_return_pct": round(total_return * 100, 2),
            "total_trades": len(self.trades),
            "equity_curve_length": len(self.equity_curve),
        }


def simple_ma_strategy(lookback, positions):
    """example: buy when price > 20-day ma, sell when below."""
    if len(lookback) < 20:
        return None
    closes = [b["close"] for b in lookback[-20:]]
    ma = sum(closes) / len(closes)
    current = lookback[-1]["close"]
    if current > ma and not positions.get("default"):
        return {"action": "buy", "symbol": "default", "size": 0.5}
    elif current < ma and positions.get("default", 0) > 0:
        return {"action": "sell", "symbol": "default"}
    return None


if __name__ == "__main__":
    import random
    data = []
    price = 100
    for i in range(252):
        price *= (1 + random.gauss(0.0003, 0.015))
        data.append({
            "date": f"2021-{(i // 22) + 1:02d}-{(i % 22) + 1:02d}",
            "open": round(price * 0.999, 2),
            "high": round(price * 1.01, 2),
            "low": round(price * 0.99, 2),
            "close": round(price, 2),
            "volume": random.randint(100000, 500000),
        })
    bt = BacktestRunner(data, simple_ma_strategy)
    result = bt.run()
    for k, v in result.items():
        print(f"  {k}: {v}")
