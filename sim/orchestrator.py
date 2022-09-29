#!/usr/bin/env python3
"""master orchestrator for the full analysis pipeline"""

import json
import math
import os
import statistics
import time
from collections import defaultdict
from datetime import datetime


class StrategyOrchestrator:
    """runs the full strategy analysis pipeline."""

    def __init__(self, data_dir="data", report_dir="reports"):
        self.data_dir = data_dir
        self.report_dir = report_dir
        self.indicators = {}
        self.strategies = {}
        self.results = {}
        self.rankings = []
        os.makedirs(report_dir, exist_ok=True)

    def register_indicator(self, name, fn):
        """register an indicator function for testing.

        fn should accept (prices) and return a value or series.
        """
        self.indicators[name] = fn

    def register_strategy(self, name, fn):
        """register a strategy function for backtesting.

        fn should accept (bars, positions) and return signal or None.
        """
        self.strategies[name] = fn

    def run_isolation_test(self, bars, initial_capital=100000):
        """test each indicator in isolation.

        runs a simple strategy using only one indicator at a time,
        measures sharpe, return, drawdown for each.
        """
        results = {}
        closes = [b["close"] for b in bars]
        for name, ind_fn in self.indicators.items():
            try:
                values = [ind_fn(closes[:i + 1]) for i in range(len(closes))]
            except Exception:
                results[name] = {"error": "indicator failed"}
                continue
            trades = self._simple_signal_backtest(bars, values, initial_capital)
            results[name] = trades
        self.results["isolation"] = results
        return results

    def _simple_signal_backtest(self, bars, indicator_values, capital):
        """run simple backtest using indicator crossover logic."""
        initial = capital
        position = 0
        entry_price = 0
        trades = []
        equity = [capital]
        for i in range(1, len(bars)):
            val = indicator_values[i]
            prev_val = indicator_values[i - 1]
            if val is None or prev_val is None:
                equity.append(equity[-1])
                continue
            price = bars[i]["close"]
            if isinstance(val, (int, float)) and isinstance(prev_val, (int, float)):
                if val > prev_val and position == 0:
                    shares = int(capital * 0.95 / price)
                    if shares > 0:
                        capital -= shares * price
                        position = shares
                        entry_price = price
                elif val < prev_val and position > 0:
                    capital += position * price
                    pnl = (price - entry_price) * position
                    trades.append({
                        "entry": entry_price,
                        "exit": price,
                        "pnl": round(pnl, 2),
                    })
                    position = 0
            equity.append(capital + position * price)
        if position > 0:
            capital += position * bars[-1]["close"]
            pnl = (bars[-1]["close"] - entry_price) * position
            trades.append({"entry": entry_price, "exit": bars[-1]["close"],
                           "pnl": round(pnl, 2)})
        daily_returns = []
        for i in range(1, len(equity)):
            if equity[i - 1] > 0:
                daily_returns.append(
                    (equity[i] - equity[i - 1]) / equity[i - 1]
                )
        wins = [t for t in trades if t["pnl"] > 0]
        return {
            "total_return": round(
                (equity[-1] - initial) / initial * 100, 2
            ),
            "sharpe": self._sharpe(daily_returns),
            "max_drawdown": self._max_drawdown(equity),
            "trades": len(trades),
            "win_rate": round(
                len(wins) / len(trades) * 100, 1
            ) if trades else 0,
        }

    def run_combination_test(self, bars, initial_capital=100000):
        """test all indicator pairs, then best pairs of pairs.

        first tests all 2-indicator combinations, then combines
        the top performing pairs.
        """
        closes = [b["close"] for b in bars]
        ind_names = list(self.indicators.keys())
        pair_results = {}
        for i in range(len(ind_names)):
            for j in range(i + 1, len(ind_names)):
                name_a = ind_names[i]
                name_b = ind_names[j]
                pair_name = f"{name_a}+{name_b}"
                try:
                    vals_a = [
                        self.indicators[name_a](closes[:k + 1])
                        for k in range(len(closes))
                    ]
                    vals_b = [
                        self.indicators[name_b](closes[:k + 1])
                        for k in range(len(closes))
                    ]
                except Exception:
                    continue
                combined = []
                for k in range(len(vals_a)):
                    if vals_a[k] is not None and vals_b[k] is not None:
                        combined.append((vals_a[k] + vals_b[k]) / 2)
                    else:
                        combined.append(None)
                result = self._simple_signal_backtest(
                    bars, combined, initial_capital
                )
                pair_results[pair_name] = result
        self.results["combinations"] = pair_results
        return pair_results

    def run_factor_analysis(self, bars, macro_file=None, news_file=None):
        """cross-reference strategy results with macro/news factors."""
        from sim.cross_factor import CrossFactorAnalyzer
        analyzer = CrossFactorAnalyzer()
        analyzer.load_factors(macro_file, news_file)
        returns_by_date = {}
        closes = [b["close"] for b in bars]
        for i in range(1, len(bars)):
            date = bars[i].get("date", "")
            if date and closes[i - 1] > 0:
                ret = (closes[i] - closes[i - 1]) / closes[i - 1]
                returns_by_date[date] = ret
        analyzer.set_strategy_returns(returns_by_date)
        attribution = analyzer.factor_attribution()
        self.results["factor_analysis"] = attribution
        return attribution

    def run_pattern_discovery(self, bars):
        """find new patterns and auto-generate strategies."""
        from sim.pattern_detect import (
            detect_time_patterns, detect_streak_patterns,
            detect_correlation,
        )
        from sim.auto_strategy import PatternToStrategy, backtest_generated
        trades = []
        closes = [b["close"] for b in bars]
        for i in range(1, len(closes)):
            ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            trades.append({
                "pnl_pct": ret * 100,
                "entry_time": f"{(i * 7) % 24}:00",
                "day_of_week": i % 5,
            })
        time_patterns = detect_time_patterns(trades)
        returns = [t["pnl_pct"] / 100 for t in trades]
        streaks = detect_streak_patterns(returns)
        gen = PatternToStrategy()
        gen.rule_from_time_pattern(time_patterns)
        gen.rule_from_streak(streaks)
        strategy_fn = gen.build_strategy_fn()
        result = backtest_generated(strategy_fn, bars)
        self.results["pattern_discovery"] = {
            "time_patterns": len(time_patterns),
            "streaks": len(streaks),
            "rules_generated": len(gen.rules),
            "backtest": result,
        }
        return self.results["pattern_discovery"]

    def generate_report(self):
        """generate comprehensive report with all results."""
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sections": {},
        }
        if "isolation" in self.results:
            ranked = sorted(
                self.results["isolation"].items(),
                key=lambda x: x[1].get("sharpe", 0) if isinstance(x[1], dict) else 0,
                reverse=True,
            )
            report["sections"]["isolation_rankings"] = [
                {"rank": i + 1, "indicator": name, **data}
                for i, (name, data) in enumerate(ranked)
                if isinstance(data, dict) and "error" not in data
            ]
        if "combinations" in self.results:
            ranked = sorted(
                self.results["combinations"].items(),
                key=lambda x: x[1].get("sharpe", 0),
                reverse=True,
            )[:10]
            report["sections"]["top_combinations"] = [
                {"rank": i + 1, "pair": name, **data}
                for i, (name, data) in enumerate(ranked)
            ]
        if "factor_analysis" in self.results:
            report["sections"]["factor_analysis"] = self.results["factor_analysis"]
        if "pattern_discovery" in self.results:
            report["sections"]["pattern_discovery"] = self.results["pattern_discovery"]
        report_path = os.path.join(
            self.report_dir,
            f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        self.rankings = report.get("sections", {}).get("isolation_rankings", [])
        return report

    def weekly_cycle(self, bars, macro_file=None, news_file=None):
        """run the full weekly analysis loop.

        1. isolation tests for all indicators
        2. combination tests for pairs
        3. factor analysis with macro/news
        4. pattern discovery and auto-generation
        5. generate comprehensive report
        """
        print("running isolation tests...")
        self.run_isolation_test(bars)
        print("running combination tests...")
        self.run_combination_test(bars)
        print("running factor analysis...")
        self.run_factor_analysis(bars, macro_file, news_file)
        print("running pattern discovery...")
        self.run_pattern_discovery(bars)
        print("generating report...")
        report = self.generate_report()
        print(f"weekly cycle complete. {len(self.results)} result sets.")
        return report

    def _sharpe(self, returns, risk_free=0.02):
        """annualized sharpe ratio."""
        if len(returns) < 5:
            return 0
        daily_rf = risk_free / 252
        excess = [r - daily_rf for r in returns]
        mean = sum(excess) / len(excess)
        var = sum((r - mean) ** 2 for r in excess) / (len(excess) - 1)
        std = math.sqrt(var) if var > 0 else 0
        if std == 0:
            return 0
        return round(mean / std * math.sqrt(252), 4)

    def _max_drawdown(self, equity):
        """maximum drawdown percentage."""
        if len(equity) < 2:
            return 0
        peak = equity[0]
        max_dd = 0
        for val in equity:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return round(max_dd * 100, 2)


if __name__ == "__main__":
    from sim.indicators import sma, ema, rsi
    orch = StrategyOrchestrator()
    orch.register_indicator("sma_20", lambda p: sma(p, 20))
    orch.register_indicator("sma_50", lambda p: sma(p, 50))
    orch.register_indicator("ema_12", lambda p: ema(p, 12))
    orch.register_indicator("rsi_14", lambda p: rsi(p, 14))
    import random
    random.seed(42)
    price = 100.0
    bars = []
    for i in range(500):
        change = random.gauss(0, 0.015) * price
        o = price
        c = price + change
        h = max(o, c) + abs(random.gauss(0, 0.003) * price)
        lo = min(o, c) - abs(random.gauss(0, 0.003) * price)
        bars.append({
            "date": f"2021-{(i // 30) % 12 + 1:02d}-{i % 28 + 1:02d}",
            "open": round(o, 2), "high": round(h, 2),
            "low": round(lo, 2), "close": round(c, 2),
            "volume": int(random.gauss(1000000, 200000)),
        })
        price = c
    report = orch.weekly_cycle(bars)
    print(f"\nreport sections: {list(report['sections'].keys())}")
    if "isolation_rankings" in report["sections"]:
        print("\ntop indicators:")
        for item in report["sections"]["isolation_rankings"][:5]:
            print(f"  {item['rank']}. {item['indicator']}: "
                  f"sharpe={item['sharpe']}, return={item['total_return']}%")
