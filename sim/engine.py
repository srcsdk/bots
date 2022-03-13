#!/usr/bin/env python3
"""unified backtest engine combining all sim components"""

from sim.data_pipeline import DataPipeline, add_returns
from sim.risk_limits import RiskLimits
from sim.journal import TradeJournal


class BacktestEngine:
    """unified engine for running complete backtests."""

    def __init__(self, initial_capital=100000):
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.positions = {}
        self.equity_curve = []
        self.risk = RiskLimits()
        self.pipeline = DataPipeline()
        self.journal = TradeJournal("/dev/null")

    def load_data(self, filepath):
        """load and process market data."""
        data = self.pipeline.load_csv(filepath)
        self.pipeline.add_transform(add_returns)
        return self.pipeline.process(data)

    def run(self, data, strategy_fn):
        """run backtest with given strategy."""
        self.risk.reset_daily()
        for i, bar in enumerate(data):
            lookback = data[max(0, i - 200):i + 1]
            signal = strategy_fn(lookback, self.positions)
            if signal:
                self._process_signal(signal, bar)
            self._update_equity(bar)
        return self._results()

    def _process_signal(self, signal, bar):
        """process a trading signal."""
        symbol = signal.get("symbol", "default")
        action = signal.get("action", "")
        if action == "buy":
            size_pct = signal.get("size", 0.1)
            shares = int(self.capital * size_pct / bar["close"])
            if shares <= 0:
                return
            order = {
                "action": "buy", "shares": shares,
                "price": bar["close"],
            }
            allowed, reason = self.risk.check_order(
                order, self._portfolio_value(bar), self.positions
            )
            if not allowed:
                return
            cost = shares * bar["close"]
            if cost > self.capital:
                return
            self.capital -= cost
            self.positions[symbol] = self.positions.get(symbol, 0) + shares
            self.risk.record_trade()
        elif action == "sell" and self.positions.get(symbol, 0) > 0:
            shares = self.positions[symbol]
            proceeds = shares * bar["close"]
            self.capital += proceeds
            self.positions[symbol] = 0
            self.risk.record_trade()

    def _portfolio_value(self, bar):
        """calculate total portfolio value."""
        pos_value = sum(
            qty * bar["close"] for qty in self.positions.values()
        )
        return self.capital + pos_value

    def _update_equity(self, bar):
        """record equity at current bar."""
        value = self._portfolio_value(bar)
        self.equity_curve.append(round(value, 2))

    def _results(self):
        """generate backtest results."""
        if not self.equity_curve:
            return {}
        final = self.equity_curve[-1]
        total_return = (final - self.initial_capital) / self.initial_capital
        peak = self.equity_curve[0]
        max_dd = 0
        for val in self.equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return {
            "initial_capital": self.initial_capital,
            "final_equity": final,
            "total_return_pct": round(total_return * 100, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "equity_length": len(self.equity_curve),
        }


if __name__ == "__main__":
    import random
    random.seed(42)
    data = []
    price = 100
    for i in range(252):
        price *= (1 + random.gauss(0.0003, 0.015))
        data.append({
            "date": f"2022-{(i // 22) + 1:02d}-{(i % 22) + 1:02d}",
            "close": round(price, 2),
        })

    def simple_strategy(lookback, positions):
        if len(lookback) < 20:
            return None
        closes = [b["close"] for b in lookback[-20:]]
        ma = sum(closes) / 20
        if lookback[-1]["close"] > ma and not positions.get("default"):
            return {"action": "buy", "symbol": "default", "size": 0.5}
        if lookback[-1]["close"] < ma and positions.get("default", 0) > 0:
            return {"action": "sell", "symbol": "default"}
        return None

    engine = BacktestEngine()
    result = engine.run(data, simple_strategy)
    for k, v in result.items():
        print(f"  {k}: {v}")
