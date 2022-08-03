#!/usr/bin/env python3
"""backtrader integration adapter for comparing engines"""

import math
import statistics
from sim.backtest_engine import BacktestEngine

try:
    import backtrader as bt
    HAS_BACKTRADER = True
except ImportError:
    bt = None
    HAS_BACKTRADER = False


def convert_to_bt_data(bars, dataname="data"):
    """convert ohlc bar dicts to backtrader data feed.

    bars: list of dicts with date, open, high, low, close, volume keys.
    returns a backtrader data feed or None if backtrader not installed.
    """
    if not HAS_BACKTRADER:
        return None
    import io
    import csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
    for bar in bars:
        writer.writerow([
            bar.get("date", "2020-01-01"),
            bar.get("open", 0),
            bar.get("high", 0),
            bar.get("low", 0),
            bar.get("close", 0),
            bar.get("volume", 0),
        ])
    buf.seek(0)
    data = bt.feeds.GenericCSVData(
        dataname=buf,
        dtformat="%Y-%m-%d",
        openinterest=-1,
    )
    return data


def _make_bt_strategy(strategy_fn):
    """wrap a simple strategy function into a backtrader strategy class.

    strategy_fn should accept (prices, positions) and return a signal dict
    with action/symbol/size keys, or None.
    """
    if not HAS_BACKTRADER:
        return None

    class WrappedStrategy(bt.Strategy):
        def __init__(self):
            self.bar_history = []

        def next(self):
            bar = {
                "date": self.data.datetime.date(0).isoformat(),
                "open": float(self.data.open[0]),
                "high": float(self.data.high[0]),
                "low": float(self.data.low[0]),
                "close": float(self.data.close[0]),
                "volume": float(self.data.volume[0]),
            }
            self.bar_history.append(bar)
            positions = {}
            if self.position.size > 0:
                positions["default"] = {
                    "size": self.position.size,
                    "avg_price": self.position.price,
                }
            signal = strategy_fn(self.bar_history, positions)
            if signal:
                action = signal.get("action", "")
                size = signal.get("size", 100)
                if action == "buy" and not self.position:
                    self.buy(size=size)
                elif action == "sell" and self.position:
                    self.sell(size=self.position.size)

    return WrappedStrategy


class BacktraderAdapter:
    """adapter to run strategies through backtrader cerebro engine."""

    def __init__(self, initial_capital=100000, commission=0.001):
        self.initial_capital = initial_capital
        self.commission = commission

    def run_backtest(self, strategy_fn, bars, start=None, end=None):
        """run strategy through backtrader engine.

        strategy_fn: callable(bars, positions) -> signal dict or None
        bars: list of ohlc bar dicts
        start/end: date strings to filter bars (YYYY-MM-DD)
        returns dict with portfolio value, return, trade count.
        """
        if not HAS_BACKTRADER:
            return {"error": "backtrader not installed"}
        filtered = bars
        if start:
            filtered = [b for b in filtered if b.get("date", "") >= start]
        if end:
            filtered = [b for b in filtered if b.get("date", "") <= end]
        if not filtered:
            return {"error": "no data in range"}
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)
        data_feed = convert_to_bt_data(filtered)
        if data_feed is None:
            return {"error": "failed to create data feed"}
        cerebro.adddata(data_feed)
        strat_class = _make_bt_strategy(strategy_fn)
        cerebro.addstrategy(strat_class)
        results = cerebro.run()
        final_value = cerebro.broker.getvalue()
        ret_pct = (final_value - self.initial_capital) / self.initial_capital * 100
        analyzer = results[0] if results else None
        trade_count = 0
        if analyzer and hasattr(analyzer, "analyzers"):
            try:
                ta = analyzer.analyzers.tradeanalyzer.get_analysis()
                trade_count = ta.get("total", {}).get("total", 0)
            except Exception:
                pass
        return {
            "engine": "backtrader",
            "initial_capital": self.initial_capital,
            "final_value": round(final_value, 2),
            "return_pct": round(ret_pct, 2),
            "trade_count": trade_count,
        }

    def run_custom_backtest(self, strategy_fn, bars, start=None, end=None):
        """run strategy through the custom backtest engine."""
        filtered = bars
        if start:
            filtered = [b for b in filtered if b.get("date", "") >= start]
        if end:
            filtered = [b for b in filtered if b.get("date", "") <= end]
        if not filtered:
            return {"error": "no data in range"}
        engine = BacktestEngine(
            initial_capital=self.initial_capital,
            commission=self.commission,
        )
        result = engine.run(strategy_fn, filtered)
        return {
            "engine": "custom",
            "initial_capital": self.initial_capital,
            "final_value": round(
                self.initial_capital + result.get("total_pnl", 0), 2
            ),
            "return_pct": result.get("total_return_pct", 0),
            "trade_count": result.get("total_trades", 0),
        }

    def compare_engines(self, strategy_fn, bars, start=None, end=None):
        """run same strategy on both engines and compare results.

        returns dict with both results and difference metrics.
        """
        custom = self.run_custom_backtest(strategy_fn, bars, start, end)
        bt_result = self.run_backtest(strategy_fn, bars, start, end)
        comparison = {
            "custom": custom,
            "backtrader": bt_result,
        }
        if "error" not in custom and "error" not in bt_result:
            comparison["return_diff"] = round(
                abs(custom["return_pct"] - bt_result["return_pct"]), 4
            )
            comparison["trade_diff"] = abs(
                custom["trade_count"] - bt_result["trade_count"]
            )
            comparison["value_diff"] = round(
                abs(custom["final_value"] - bt_result["final_value"]), 2
            )
        return comparison


def generate_sample_bars(n=500, start_price=100.0, seed=42):
    """generate synthetic ohlc data for testing.

    simple random walk with realistic open/high/low/close relationships.
    """
    import random
    random.seed(seed)
    bars = []
    price = start_price
    base_date = 20200101
    for i in range(n):
        day = base_date + i
        year = 2020 + (day - 20200101) // 365
        day_of_year = (day - 20200101) % 365
        month = day_of_year // 30 + 1
        dom = day_of_year % 30 + 1
        if month > 12:
            month = 12
        date_str = f"{year}-{month:02d}-{dom:02d}"
        change = random.gauss(0, 0.02) * price
        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + abs(random.gauss(0, 0.005) * price)
        low_p = min(open_p, close_p) - abs(random.gauss(0, 0.005) * price)
        volume = int(random.gauss(1000000, 300000))
        if volume < 100000:
            volume = 100000
        bars.append({
            "date": date_str,
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": volume,
        })
        price = close_p
    return bars


if __name__ == "__main__":
    bars = generate_sample_bars(200)
    print(f"generated {len(bars)} bars for testing")

    def simple_sma_strategy(bars, positions):
        if len(bars) < 20:
            return None
        closes = [b["close"] for b in bars]
        sma_short = sum(closes[-5:]) / 5
        sma_long = sum(closes[-20:]) / 20
        if sma_short > sma_long and not positions:
            return {"action": "buy", "symbol": "default", "size": 100}
        elif sma_short < sma_long and positions:
            return {"action": "sell", "symbol": "default", "size": 100}
        return None

    adapter = BacktraderAdapter(initial_capital=100000)
    custom = adapter.run_custom_backtest(simple_sma_strategy, bars)
    print(f"custom engine: {custom}")
    bt_result = adapter.run_backtest(simple_sma_strategy, bars)
    print(f"backtrader: {bt_result}")
