#!/usr/bin/env python3
"""automatic strategy generation from discovered patterns"""

import math
import statistics


def _sharpe(returns, risk_free=0.02):
    """calculate annualized sharpe ratio from daily returns."""
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


def _max_drawdown(equity_curve):
    """calculate maximum drawdown from equity curve."""
    if len(equity_curve) < 2:
        return 0
    peak = equity_curve[0]
    max_dd = 0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return round(max_dd * 100, 2)


class PatternToStrategy:
    """convert discovered patterns into executable trading rules."""

    def __init__(self):
        self.rules = []
        self.results = {}

    def rule_from_time_pattern(self, time_patterns, min_trades=10, min_wr=60):
        """generate entry rules based on time-of-day patterns.

        time_patterns: dict from pattern_detect.detect_time_patterns
        returns list of generated rule dicts.
        """
        generated = []
        for hour, stats in time_patterns.items():
            if stats["trades"] < min_trades:
                continue
            if stats["win_rate"] < min_wr:
                continue
            rule = {
                "type": "time_entry",
                "hour": hour,
                "direction": "long" if stats["avg_return"] > 0 else "short",
                "expected_return": stats["avg_return"],
                "win_rate": stats["win_rate"],
                "confidence": min(stats["trades"] / 50, 1.0),
            }
            generated.append(rule)
        self.rules.extend(generated)
        return generated

    def rule_from_regime(self, regime_performance, regime_transitions=None):
        """generate entry/exit rules based on regime classification.

        regime_performance: dict from regime_classifier.regime_performance
        regime_transitions: optional transition matrix for predictive rules
        """
        generated = []
        for regime, perf in regime_performance.items():
            if regime == "unknown":
                continue
            if perf.get("trades", 0) < 5:
                continue
            avg_ret = perf.get("avg_return", 0)
            wr = perf.get("win_rate", 50)
            if wr >= 55 and avg_ret > 0:
                rule = {
                    "type": "regime_entry",
                    "regime": regime,
                    "action": "enter_long",
                    "expected_return": avg_ret,
                    "win_rate": wr,
                }
                generated.append(rule)
            elif wr < 40 or avg_ret < -0.005:
                rule = {
                    "type": "regime_exit",
                    "regime": regime,
                    "action": "exit_all",
                    "expected_loss": avg_ret,
                }
                generated.append(rule)
        if regime_transitions:
            for from_regime, transitions in regime_transitions.items():
                for to_regime, prob in transitions.items():
                    if prob > 0.4 and to_regime in ("bull_low_vol", "bull_high_vol"):
                        rule = {
                            "type": "regime_anticipation",
                            "from_regime": from_regime,
                            "to_regime": to_regime,
                            "probability": prob,
                            "action": "scale_in",
                        }
                        generated.append(rule)
        self.rules.extend(generated)
        return generated

    def rule_from_correlation(self, corr_data, threshold=0.7):
        """generate trading rules from indicator correlations.

        corr_data: list of dicts with indicator_a, indicator_b, correlation,
                   and performance fields.
        """
        generated = []
        for entry in corr_data:
            corr = entry.get("correlation", 0)
            if abs(corr) < threshold:
                continue
            perf = entry.get("combined_sharpe", 0)
            if perf <= 0:
                continue
            rule = {
                "type": "correlation_pair",
                "indicator_a": entry.get("indicator_a", ""),
                "indicator_b": entry.get("indicator_b", ""),
                "correlation": round(corr, 4),
                "direction": "same" if corr > 0 else "opposite",
                "combined_sharpe": perf,
                "action": "use_pair",
            }
            generated.append(rule)
        self.rules.extend(generated)
        return generated

    def rule_from_streak(self, streaks, min_avg_return=0.001):
        """generate rules from streak pattern data."""
        generated = []
        win_streaks = [s for s in streaks if s.get("type") == "win"]
        loss_streaks = [s for s in streaks if s.get("type") == "loss"]
        if win_streaks:
            avg_len = statistics.mean(s["length"] for s in win_streaks)
            avg_total = statistics.mean(s["total"] for s in win_streaks)
            if avg_total / max(avg_len, 1) > min_avg_return:
                rule = {
                    "type": "streak_continuation",
                    "streak_type": "win",
                    "avg_length": round(avg_len, 1),
                    "action": "hold_through",
                    "avg_return_per_bar": round(avg_total / max(avg_len, 1), 4),
                }
                generated.append(rule)
        if loss_streaks:
            avg_len = statistics.mean(s["length"] for s in loss_streaks)
            if avg_len >= 3:
                rule = {
                    "type": "streak_reversal",
                    "streak_type": "loss",
                    "avg_length": round(avg_len, 1),
                    "action": "reduce_size_after_3",
                }
                generated.append(rule)
        self.rules.extend(generated)
        return generated

    def build_strategy_fn(self, rules=None):
        """build a callable strategy function from accumulated rules.

        returns a function compatible with backtest engine:
            fn(bars, positions) -> signal or None
        """
        active_rules = rules or self.rules
        regime_entries = [r for r in active_rules if r["type"] == "regime_entry"]
        regime_exits = [r for r in active_rules if r["type"] == "regime_exit"]

        def strategy(bars, positions):
            if len(bars) < 20:
                return None
            closes = [b["close"] for b in bars]
            returns = []
            for i in range(1, len(closes)):
                if closes[i - 1] > 0:
                    returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
            regime = _classify_simple(returns[-20:]) if len(returns) >= 20 else "unknown"
            for rule in regime_exits:
                if rule["regime"] == regime and positions:
                    return {"action": "sell", "symbol": "default", "size": 1000}
            for rule in regime_entries:
                if rule["regime"] == regime and not positions:
                    return {"action": "buy", "symbol": "default", "size": 100}
            return None

        return strategy


def _classify_simple(returns):
    """simplified regime classification for generated strategies."""
    if len(returns) < 5:
        return "unknown"
    mean_r = statistics.mean(returns)
    vol = statistics.pstdev(returns)
    if mean_r > 0.005 and vol < 0.02:
        return "bull_low_vol"
    elif mean_r > 0.005:
        return "bull_high_vol"
    elif mean_r < -0.005 and vol < 0.02:
        return "bear_low_vol"
    elif mean_r < -0.005:
        return "bear_high_vol"
    elif vol < 0.01:
        return "sideways_quiet"
    return "sideways_choppy"


def backtest_generated(strategy_fn, bars, initial_capital=100000):
    """run a generated strategy through simple backtest loop.

    returns performance metrics dict.
    """
    capital = initial_capital
    positions = {}
    trades = []
    equity = [initial_capital]
    for i, bar in enumerate(bars):
        signal = strategy_fn(bars[:i + 1], positions)
        if signal:
            action = signal.get("action", "")
            price = bar["close"]
            size = signal.get("size", 100)
            symbol = signal.get("symbol", "default")
            if action == "buy" and symbol not in positions:
                cost = price * size
                if cost <= capital:
                    capital -= cost
                    positions[symbol] = {"size": size, "entry": price}
            elif action == "sell" and symbol in positions:
                pos = positions[symbol]
                revenue = price * pos["size"]
                pnl = (price - pos["entry"]) * pos["size"]
                capital += revenue
                trades.append({
                    "entry": pos["entry"],
                    "exit": price,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl / (pos["entry"] * pos["size"]) * 100, 2),
                })
                del positions[symbol]
        pos_value = sum(
            bar["close"] * p["size"] for p in positions.values()
        )
        equity.append(capital + pos_value)
    daily_returns = []
    for i in range(1, len(equity)):
        if equity[i - 1] > 0:
            daily_returns.append((equity[i] - equity[i - 1]) / equity[i - 1])
    wins = [t for t in trades if t["pnl"] > 0]
    return {
        "total_return": round(
            (equity[-1] - initial_capital) / initial_capital * 100, 2
        ),
        "sharpe": _sharpe(daily_returns),
        "max_drawdown": _max_drawdown(equity),
        "total_trades": len(trades),
        "win_rate": round(
            len(wins) / len(trades) * 100, 1
        ) if trades else 0,
        "avg_pnl": round(
            statistics.mean(t["pnl"] for t in trades), 2
        ) if trades else 0,
    }


def rank_generated(strategy_results, min_trades=5):
    """rank auto-generated strategies by risk-adjusted return.

    strategy_results: dict of name -> backtest result dict
    returns sorted list of (name, score, result) tuples.
    """
    scored = []
    for name, result in strategy_results.items():
        if result.get("total_trades", 0) < min_trades:
            continue
        sharpe = result.get("sharpe", 0)
        ret = result.get("total_return", 0)
        dd = result.get("max_drawdown", 100)
        wr = result.get("win_rate", 0)
        if dd == 0:
            dd = 0.01
        score = sharpe * 0.4 + (ret / max(dd, 1)) * 0.3 + (wr / 100) * 0.3
        scored.append((name, round(score, 4), result))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


if __name__ == "__main__":
    gen = PatternToStrategy()
    regime_perf = {
        "bull_low_vol": {"trades": 50, "avg_return": 0.015, "win_rate": 65},
        "bear_high_vol": {"trades": 30, "avg_return": -0.02, "win_rate": 35},
        "sideways_quiet": {"trades": 40, "avg_return": 0.003, "win_rate": 52},
    }
    rules = gen.rule_from_regime(regime_perf)
    print(f"generated {len(rules)} regime rules")
    for r in rules:
        print(f"  {r['type']}: {r.get('regime', '')} -> {r.get('action', '')}")
