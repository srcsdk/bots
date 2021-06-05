#!/usr/bin/env python3
"""risk management: stop loss, take profit, trailing stops"""

import sys
from ohlc import fetch_ohlc
from indicators import atr


def fixed_stop(entry, stop_pct=0.05):
    """calculate fixed percentage stop loss"""
    return round(entry * (1 - stop_pct), 2)


def fixed_target(entry, target_pct=0.10):
    """calculate fixed percentage take profit"""
    return round(entry * (1 + target_pct), 2)


def atr_stop(entry, atr_value, multiplier=2.0):
    """calculate stop loss based on atr"""
    if atr_value is None or atr_value <= 0:
        return fixed_stop(entry)
    return round(entry - (atr_value * multiplier), 2)


def atr_target(entry, atr_value, multiplier=3.0):
    """calculate take profit based on atr"""
    if atr_value is None or atr_value <= 0:
        return fixed_target(entry)
    return round(entry + (atr_value * multiplier), 2)


def trailing_stop(prices, trail_pct=0.05):
    """simulate trailing stop on a price series.

    returns index where stop was hit, or -1 if never triggered.
    """
    if not prices:
        return -1
    peak = prices[0]
    for i, price in enumerate(prices):
        if price > peak:
            peak = price
        stop = peak * (1 - trail_pct)
        if price <= stop:
            return i
    return -1


def risk_reward_ratio(entry, stop, target):
    """calculate risk/reward ratio"""
    risk = entry - stop
    reward = target - entry
    if risk <= 0:
        return 0
    return round(reward / risk, 2)


def simulate_exit(rows, entry_idx, stop, target, max_hold=30):
    """simulate trade exit with stop loss and take profit.

    returns (exit_idx, exit_price, exit_reason)
    """
    for i in range(entry_idx + 1, min(len(rows), entry_idx + max_hold + 1)):
        low = rows[i]["low"]
        high = rows[i]["high"]
        close = rows[i]["close"]

        if low <= stop:
            return i, stop, "stop_loss"
        if high >= target:
            return i, target, "take_profit"

    if entry_idx + max_hold < len(rows):
        exit_idx = entry_idx + max_hold
        return exit_idx, rows[exit_idx]["close"], "max_hold"

    return len(rows) - 1, rows[-1]["close"], "open"


def backtest_with_risk(ticker, signals, stop_pct=0.05, target_pct=0.10,
                       max_hold=30, period="2y"):
    """backtest signals with stop loss and take profit rules.

    signals: list of dicts with 'date' and 'price' keys
    returns trade results with exit reasons
    """
    rows = fetch_ohlc(ticker, period)
    if not rows:
        return []

    date_to_idx = {r["date"]: i for i, r in enumerate(rows)}
    trades = []

    for sig in signals:
        if sig["date"] not in date_to_idx:
            continue
        entry_idx = date_to_idx[sig["date"]]
        entry = sig["price"]
        stop = fixed_stop(entry, stop_pct)
        target = fixed_target(entry, target_pct)
        rr = risk_reward_ratio(entry, stop, target)

        exit_idx, exit_price, reason = simulate_exit(
            rows, entry_idx, stop, target, max_hold
        )

        pnl = (exit_price - entry) / entry * 100
        trades.append({
            "entry_date": sig["date"],
            "exit_date": rows[exit_idx]["date"],
            "entry": entry,
            "exit": exit_price,
            "stop": stop,
            "target": target,
            "rr_ratio": rr,
            "pnl_pct": round(pnl, 2),
            "reason": reason,
            "hold_days": exit_idx - entry_idx,
        })

    return trades


def summarize_trades(trades):
    """generate summary statistics from trade results"""
    if not trades:
        return {}
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    reasons = {}
    for t in trades:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1

    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
    avg_hold = sum(t["hold_days"] for t in trades) / len(trades)

    return {
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "avg_hold_days": round(avg_hold, 1),
        "exit_reasons": reasons,
        "expectancy": round(
            (len(wins) / len(trades) * avg_win +
             len(losses) / len(trades) * avg_loss), 2
        ),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python risk.py <ticker> [stop_pct] [target_pct]")
        print("  runs backtest with risk management on gapup signals")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    stop_pct = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
    target_pct = float(sys.argv[3]) if len(sys.argv) > 3 else 0.10

    from gapup import scan
    signals = scan(ticker, "2y")

    if not signals:
        print(f"no signals for {ticker}")
        sys.exit(0)

    trades = backtest_with_risk(ticker, signals, stop_pct, target_pct)
    summary = summarize_trades(trades)

    print(f"\nrisk backtest: {ticker} (stop={stop_pct*100:.0f}% target={target_pct*100:.0f}%)")
    print(f"  trades: {summary['total']}  wins: {summary['wins']}  losses: {summary['losses']}")
    print(f"  win rate: {summary['win_rate']}%  expectancy: {summary['expectancy']}%")
    print(f"  avg win: {summary['avg_win']}%  avg loss: {summary['avg_loss']}%")
    print(f"  avg hold: {summary['avg_hold_days']} days")
    print(f"  exits: {summary['exit_reasons']}")

    for t in trades:
        print(f"  {t['entry_date']} -> {t['exit_date']}  "
              f"${t['entry']:.2f} -> ${t['exit']:.2f}  "
              f"{t['pnl_pct']:+.2f}%  ({t['reason']})")
