#!/usr/bin/env python3
"""run all strategies through backtrader with historical data and generate reports"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.backtrader_adapter import BacktraderAdapter, generate_sample_bars
from sim.strategy_registry import STRATEGY_REGISTRY, wrap_for_backtest
from sim.data_source import DataSource, generate_synthetic_bars
from sim.comparison_chart import ComparisonChart, calc_sharpe


class FullBacktest:
    """run all registered strategies and produce comparison reports."""

    def __init__(self, tickers=None, start_year=2015, end_year=2025):
        self.tickers = tickers or ["SPY"]
        self.start_year = start_year
        self.end_year = end_year
        self.adapter = BacktraderAdapter(initial_capital=100000)
        self.data_source = DataSource()
        self.results = {}
        self.equity_curves = {}

    def _load_data(self, ticker):
        """load data for a ticker, falling back to synthetic if needed."""
        cached = self.data_source.load_cached(ticker)
        if cached:
            return cached
        bars = self.data_source.fetch_yahoo(
            ticker,
            f"{self.start_year}-01-01",
            f"{self.end_year}-12-31",
        )
        if bars:
            self.data_source.cache_data(ticker, bars)
            return bars
        print(f"  using synthetic data for {ticker}")
        return generate_synthetic_bars(
            n=(self.end_year - self.start_year) * 252,
            start_price=100.0,
            seed=hash(ticker) % 10000,
            ticker=ticker,
        )

    def run_all_strategies(self):
        """load all strategies via registry and run each through backtrader.

        uses real data when available, synthetic fallback otherwise.
        stores results and equity curves for each strategy/ticker pair.
        """
        strategies = {}
        for name in sorted(STRATEGY_REGISTRY.keys()):
            fn = wrap_for_backtest(name)
            if fn is not None:
                strategies[name] = fn
        if not strategies:
            print("no strategies loaded")
            return {}
        print(f"loaded {len(strategies)} strategies")
        for ticker in self.tickers:
            bars = self._load_data(ticker)
            if not bars:
                print(f"  no data for {ticker}, skipping")
                continue
            bars = self.data_source.normalize(bars)
            print(f"\n{ticker}: {len(bars)} bars "
                  f"({bars[0]['date']} to {bars[-1]['date']})")
            for name, fn in sorted(strategies.items()):
                key = f"{name}_{ticker}"
                try:
                    result = self.adapter.run_custom_backtest(fn, bars)
                    self.results[key] = result
                    equity = self._build_equity_curve(fn, bars)
                    self.equity_curves[key] = {
                        "dates": [b["date"] for b in bars],
                        "values": equity,
                    }
                    ret = result.get("return_pct", 0)
                    trades = result.get("trade_count", 0)
                    print(f"  {name:<20} return={ret:>7.2f}%  trades={trades}")
                except Exception as e:
                    print(f"  {name:<20} error: {e}")
                    self.results[key] = {"error": str(e)}
        return self.results

    def _build_equity_curve(self, strategy_fn, bars):
        """run strategy and record equity at each bar."""
        capital = 100000.0
        position = 0
        avg_price = 0.0
        curve = []
        bar_history = []
        for bar in bars:
            bar_history.append(bar)
            positions = {}
            if position > 0:
                positions["default"] = {"size": position, "avg_price": avg_price}
            signal = strategy_fn(bar_history, positions)
            if signal:
                action = signal.get("action", "")
                size = signal.get("size", 100)
                price = bar["close"]
                cost = price * size * 0.001
                if action == "buy" and position == 0:
                    if capital >= price * size + cost:
                        capital -= price * size + cost
                        position = size
                        avg_price = price
                elif action == "sell" and position > 0:
                    revenue = price * position - cost
                    capital += revenue
                    position = 0
                    avg_price = 0.0
            equity = capital + position * bar["close"]
            curve.append(round(equity, 2))
        return curve

    def run_isolation(self):
        """test each strategy alone on the primary ticker.

        useful for identifying which strategies contribute positively.
        returns dict mapping strategy name to isolated result.
        """
        if not self.tickers:
            return {}
        ticker = self.tickers[0]
        bars = self._load_data(ticker)
        if not bars:
            return {}
        bars = self.data_source.normalize(bars)
        isolated = {}
        for name in sorted(STRATEGY_REGISTRY.keys()):
            fn = wrap_for_backtest(name)
            if fn is None:
                continue
            try:
                result = self.adapter.run_custom_backtest(fn, bars)
                isolated[name] = result
            except Exception as e:
                isolated[name] = {"error": str(e)}
        return isolated

    def run_combinations(self, pairs):
        """test pairs of strategies by averaging their signals.

        pairs: list of (name_a, name_b) tuples.
        returns dict mapping pair key to combined result.
        """
        if not self.tickers:
            return {}
        ticker = self.tickers[0]
        bars = self._load_data(ticker)
        if not bars:
            return {}
        bars = self.data_source.normalize(bars)
        combo_results = {}
        for name_a, name_b in pairs:
            fn_a = wrap_for_backtest(name_a)
            fn_b = wrap_for_backtest(name_b)
            if fn_a is None or fn_b is None:
                continue
            combined_fn = _combine_strategies(fn_a, fn_b)
            key = f"{name_a}+{name_b}"
            try:
                result = self.adapter.run_custom_backtest(combined_fn, bars)
                combo_results[key] = result
            except Exception as e:
                combo_results[key] = {"error": str(e)}
        return combo_results

    def generate_comparison(self, output_dir=None):
        """produce comparison chart from collected equity curves.

        returns the ComparisonChart object.
        """
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "reports"
            )
        chart = ComparisonChart(f"strategy comparison ({', '.join(self.tickers)})")
        for key, curve_data in sorted(self.equity_curves.items()):
            chart.add_equity_curve(key, curve_data["dates"], curve_data["values"])
        saved = chart.save_report(output_dir)
        if saved:
            print(f"\nsaved {len(saved)} charts to {output_dir}")
        else:
            print("\nno charts generated (check matplotlib installation)")
        return chart

    def generate_report(self, output_path=None):
        """generate json report with all results, rankings, and metrics.

        returns the report dict. saves to output_path if provided.
        """
        ranked = []
        for key, result in sorted(self.results.items()):
            if "error" in result:
                continue
            ret = result.get("return_pct", 0)
            trades = result.get("trade_count", 0)
            final_val = result.get("final_value", 0)
            curve_data = self.equity_curves.get(key, {})
            values = curve_data.get("values", [])
            daily_returns = []
            if len(values) > 1:
                for i in range(1, len(values)):
                    if values[i - 1] > 0:
                        daily_returns.append(
                            (values[i] - values[i - 1]) / values[i - 1]
                        )
            sharpe = calc_sharpe(daily_returns) if daily_returns else 0
            max_dd = _max_drawdown(values) if values else 0
            ranked.append({
                "strategy": key,
                "return_pct": ret,
                "final_value": final_val,
                "trade_count": trades,
                "sharpe_ratio": sharpe,
                "max_drawdown_pct": max_dd,
            })
        ranked.sort(key=lambda x: x["return_pct"], reverse=True)
        report = {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tickers": self.tickers,
            "period": f"{self.start_year}-{self.end_year}",
            "strategies_tested": len(self.results),
            "rankings": ranked,
            "raw_results": {k: v for k, v in self.results.items() if "error" not in v},
        }
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"report saved to {output_path}")
        return report


def _combine_strategies(fn_a, fn_b):
    """combine two strategy functions by requiring agreement for signals."""
    def combined(bars, positions):
        sig_a = fn_a(bars, positions)
        sig_b = fn_b(bars, positions)
        if sig_a and sig_b:
            if sig_a.get("action") == sig_b.get("action"):
                return sig_a
        return None
    combined.__name__ = "combined_strategy"
    return combined


def _max_drawdown(values):
    """calculate maximum drawdown percentage from equity curve."""
    if not values:
        return 0
    peak = values[0]
    max_dd = 0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


if __name__ == "__main__":
    print("full backtest: running all strategies")
    print("=" * 60)
    bt = FullBacktest(tickers=["SPY"], start_year=2015, end_year=2025)
    results = bt.run_all_strategies()
    if not results:
        print("no results generated")
        sys.exit(1)
    print("\nisolation test:")
    print("-" * 40)
    isolated = bt.run_isolation()
    for name, result in sorted(isolated.items()):
        if "error" not in result:
            ret = result.get("return_pct", 0)
            trades = result.get("trade_count", 0)
            print(f"  {name:<20} return={ret:>7.2f}%  trades={trades}")
    combo_pairs = [
        ("gapup", "movo"),
        ("bcross", "turtle"),
        ("across", "vested"),
        ("nolo", "nobr"),
    ]
    print("\ncombination test:")
    print("-" * 40)
    combos = bt.run_combinations(combo_pairs)
    for key, result in sorted(combos.items()):
        if "error" not in result:
            ret = result.get("return_pct", 0)
            print(f"  {key:<30} return={ret:>7.2f}%")
    report_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports"
    )
    bt.generate_comparison(report_dir)
    report_path = os.path.join(report_dir, "full_backtest_report.json")
    report = bt.generate_report(report_path)
    print("\nfinal rankings:")
    print(f"{'rank':<6} {'strategy':<30} {'return':>9} {'sharpe':>8} {'drawdown':>10} {'trades':>7}")
    print("-" * 72)
    for i, entry in enumerate(report["rankings"][:20]):
        print(
            f"  {i + 1:<4} {entry['strategy']:<30} "
            f"{entry['return_pct']:>8.2f}% "
            f"{entry['sharpe_ratio']:>8.4f} "
            f"{entry['max_drawdown_pct']:>9.2f}% "
            f"{entry['trade_count']:>7}"
        )
