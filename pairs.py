#!/usr/bin/env python3
"""pair trading: statistical arbitrage between correlated stocks"""

import sys
from ohlc import fetch_ohlc
from correlation import daily_returns, pearson_correlation


def price_ratio(closes_a, closes_b):
    """calculate price ratio series"""
    n = min(len(closes_a), len(closes_b))
    ratios = []
    for i in range(n):
        if closes_b[i] > 0:
            ratios.append(closes_a[i] / closes_b[i])
        else:
            ratios.append(None)
    return ratios


def zscore(values, lookback=20):
    """calculate rolling z-score of a series"""
    result = [None] * min(lookback - 1, len(values))
    for i in range(lookback - 1, len(values)):
        window = [v for v in values[i - lookback + 1:i + 1] if v is not None]
        if len(window) < 2:
            result.append(None)
            continue
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = variance ** 0.5
        if std == 0:
            result.append(0)
        else:
            result.append(round((values[i] - mean) / std, 4))
    return result


def find_entry_signals(z_scores, dates, threshold=2.0):
    """find pair trade entry signals from z-score crossings.

    long pair (buy A, short B) when z < -threshold
    short pair (short A, buy B) when z > threshold
    """
    signals = []
    for i in range(1, len(z_scores)):
        if z_scores[i] is None or z_scores[i - 1] is None:
            continue
        if z_scores[i - 1] > -threshold and z_scores[i] <= -threshold:
            signals.append({
                "date": dates[i],
                "type": "long_pair",
                "zscore": z_scores[i],
            })
        elif z_scores[i - 1] < threshold and z_scores[i] >= threshold:
            signals.append({
                "date": dates[i],
                "type": "short_pair",
                "zscore": z_scores[i],
            })
    return signals


def find_exit_signals(z_scores, dates, threshold=0.5):
    """find pair trade exit signals when z-score reverts to mean"""
    signals = []
    for i in range(1, len(z_scores)):
        if z_scores[i] is None or z_scores[i - 1] is None:
            continue
        if abs(z_scores[i - 1]) > threshold and abs(z_scores[i]) <= threshold:
            signals.append({
                "date": dates[i],
                "type": "exit",
                "zscore": z_scores[i],
            })
    return signals


def backtest_pair(ticker_a, ticker_b, period="2y", entry_z=2.0, exit_z=0.5):
    """backtest a pair trading strategy"""
    rows_a = fetch_ohlc(ticker_a, period)
    rows_b = fetch_ohlc(ticker_b, period)

    if not rows_a or not rows_b:
        return None

    n = min(len(rows_a), len(rows_b))
    closes_a = [r["close"] for r in rows_a[-n:]]
    closes_b = [r["close"] for r in rows_b[-n:]]
    dates = [r["date"] for r in rows_a[-n:]]

    corr = pearson_correlation(daily_returns(closes_a), daily_returns(closes_b))
    if abs(corr) < 0.5:
        return {"pair": f"{ticker_a}/{ticker_b}", "correlation": corr,
                "trades": 0, "note": "correlation too low"}

    ratios = price_ratio(closes_a, closes_b)
    z = zscore(ratios)
    entries = find_entry_signals(z, dates, entry_z)
    exits = find_exit_signals(z, dates, exit_z)

    trades = []
    in_trade = None
    for sig in sorted(entries + exits, key=lambda s: s["date"]):
        if sig["type"] in ("long_pair", "short_pair") and in_trade is None:
            in_trade = sig
        elif sig["type"] == "exit" and in_trade is not None:
            entry_idx = dates.index(in_trade["date"])
            exit_idx = dates.index(sig["date"])
            if in_trade["type"] == "long_pair":
                pnl_a = (closes_a[exit_idx] - closes_a[entry_idx]) / closes_a[entry_idx]
                pnl_b = (closes_b[entry_idx] - closes_b[exit_idx]) / closes_b[entry_idx]
            else:
                pnl_a = (closes_a[entry_idx] - closes_a[exit_idx]) / closes_a[entry_idx]
                pnl_b = (closes_b[exit_idx] - closes_b[entry_idx]) / closes_b[entry_idx]
            trades.append({
                "entry": in_trade["date"],
                "exit": sig["date"],
                "type": in_trade["type"],
                "pnl_pct": round((pnl_a + pnl_b) * 100, 2),
                "days": exit_idx - entry_idx,
            })
            in_trade = None

    wins = [t for t in trades if t["pnl_pct"] > 0]
    return {
        "pair": f"{ticker_a}/{ticker_b}",
        "correlation": corr,
        "trades": len(trades),
        "wins": len(wins),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "avg_pnl": round(sum(t["pnl_pct"] for t in trades) / len(trades), 2) if trades else 0,
        "total_pnl": round(sum(t["pnl_pct"] for t in trades), 2),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python pairs.py <ticker_a> <ticker_b> [period]")
        print("  example: python pairs.py AAPL MSFT 2y")
        sys.exit(1)

    a = sys.argv[1].upper()
    b = sys.argv[2].upper()
    period = sys.argv[3] if len(sys.argv) > 3 else "2y"

    print(f"pair analysis: {a}/{b} ({period})")
    result = backtest_pair(a, b, period)

    if result is None:
        print("insufficient data")
    elif result.get("note"):
        print(f"  correlation: {result['correlation']:.3f}")
        print(f"  {result['note']}")
    else:
        print(f"  correlation: {result['correlation']:.3f}")
        print(f"  trades: {result['trades']}  wins: {result['wins']}")
        print(f"  win rate: {result['win_rate']}%")
        print(f"  avg pnl: {result['avg_pnl']}%  total: {result['total_pnl']}%")
