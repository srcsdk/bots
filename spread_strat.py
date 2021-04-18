#!/usr/bin/env python3
"""mean reversion on spread between correlated assets.

calculates rolling spread between two tickers, computes z-score,
and generates entry/exit signals on z-score thresholds.
classic pairs trading strategy.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma


def align_series(rows_a, rows_b):
    """align two price series by date, returning matched closes"""
    dates_a = {r["date"]: r["close"] for r in rows_a}
    dates_b = {r["date"]: r["close"] for r in rows_b}

    common_dates = sorted(set(dates_a.keys()) & set(dates_b.keys()))
    if not common_dates:
        return [], [], []

    closes_a = [dates_a[d] for d in common_dates]
    closes_b = [dates_b[d] for d in common_dates]

    return common_dates, closes_a, closes_b


def calculate_spread(closes_a, closes_b):
    """calculate price ratio spread between two series"""
    spread = []
    for a, b in zip(closes_a, closes_b):
        if b > 0:
            spread.append(round(a / b, 6))
        else:
            spread.append(None)
    return spread


def spread_zscore(spread, period=20):
    """calculate rolling z-score of spread"""
    result = [None] * (period - 1)
    for i in range(period - 1, len(spread)):
        if spread[i] is None:
            result.append(None)
            continue
        window = [s for s in spread[i - period + 1:i + 1] if s is not None]
        if len(window) < period // 2:
            result.append(None)
            continue
        mean = sum(window) / len(window)
        variance = sum((s - mean) ** 2 for s in window) / len(window)
        std = variance ** 0.5
        if std == 0:
            result.append(0)
        else:
            result.append(round((spread[i] - mean) / std, 4))
    return result


def generate_signals(dates, closes_a, closes_b, spread, zscores,
                     entry_z=2.0, exit_z=0.5):
    """generate entry/exit signals based on z-score thresholds.

    enter short spread when z > entry_z (sell a, buy b)
    enter long spread when z < -entry_z (buy a, sell b)
    exit when z crosses back through exit_z
    """
    signals = []
    position = None

    for i in range(1, len(dates)):
        if zscores[i] is None or zscores[i - 1] is None:
            continue

        if position is None:
            if zscores[i] >= entry_z:
                position = "short_spread"
                signals.append({
                    "date": dates[i],
                    "action": "enter_short_spread",
                    "zscore": zscores[i],
                    "spread": spread[i],
                    "price_a": closes_a[i],
                    "price_b": closes_b[i],
                })
            elif zscores[i] <= -entry_z:
                position = "long_spread"
                signals.append({
                    "date": dates[i],
                    "action": "enter_long_spread",
                    "zscore": zscores[i],
                    "spread": spread[i],
                    "price_a": closes_a[i],
                    "price_b": closes_b[i],
                })
        elif position == "short_spread":
            if zscores[i] <= exit_z:
                signals.append({
                    "date": dates[i],
                    "action": "exit_short_spread",
                    "zscore": zscores[i],
                    "spread": spread[i],
                    "price_a": closes_a[i],
                    "price_b": closes_b[i],
                })
                position = None
        elif position == "long_spread":
            if zscores[i] >= -exit_z:
                signals.append({
                    "date": dates[i],
                    "action": "exit_long_spread",
                    "zscore": zscores[i],
                    "spread": spread[i],
                    "price_a": closes_a[i],
                    "price_b": closes_b[i],
                })
                position = None

    return signals


def correlation(closes_a, closes_b, period=60):
    """rolling correlation between two price series"""
    if len(closes_a) < period:
        return [None] * len(closes_a)

    result = [None] * (period - 1)
    for i in range(period - 1, len(closes_a)):
        wa = closes_a[i - period + 1:i + 1]
        wb = closes_b[i - period + 1:i + 1]
        mean_a = sum(wa) / len(wa)
        mean_b = sum(wb) / len(wb)

        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(wa, wb)) / len(wa)
        var_a = sum((a - mean_a) ** 2 for a in wa) / len(wa)
        var_b = sum((b - mean_b) ** 2 for b in wb) / len(wb)

        denom = (var_a * var_b) ** 0.5
        if denom == 0:
            result.append(0)
        else:
            result.append(round(cov / denom, 4))

    return result


def analyze(ticker_a, ticker_b, period="1y"):
    """analyze spread between two correlated assets for mean reversion signals"""
    rows_a = fetch_ohlc(ticker_a, period)
    rows_b = fetch_ohlc(ticker_b, period)

    if not rows_a or not rows_b:
        return None

    dates, closes_a, closes_b = align_series(rows_a, rows_b)
    if len(dates) < 40:
        return None

    spread = calculate_spread(closes_a, closes_b)
    valid_spread_vals = [s for s in spread if s is not None]
    spread_ma = sma(valid_spread_vals, 20)
    zscores = spread_zscore(spread, 20)
    corr = correlation(closes_a, closes_b, 60)
    signals = generate_signals(dates, closes_a, closes_b, spread, zscores)

    latest_z = zscores[-1] if zscores[-1] is not None else 0
    latest_corr = corr[-1] if corr[-1] is not None else 0
    valid_spread = [s for s in spread if s is not None]
    avg_spread = round(sum(valid_spread) / len(valid_spread), 4) if valid_spread else 0

    trades = []
    entry = None
    for sig in signals:
        if "enter" in sig["action"]:
            entry = sig
        elif "exit" in sig["action"] and entry is not None:
            spread_pnl = sig["spread"] - entry["spread"]
            if "short" in entry["action"]:
                spread_pnl = -spread_pnl
            trades.append({
                "entry_date": entry["date"],
                "exit_date": sig["date"],
                "pnl_spread": round(spread_pnl, 4),
            })
            entry = None

    win_rate = 0
    if trades:
        wins = sum(1 for t in trades if t["pnl_spread"] > 0)
        win_rate = round(wins / len(trades) * 100, 1)

    return {
        "ticker_a": ticker_a,
        "ticker_b": ticker_b,
        "data_points": len(dates),
        "latest_spread": spread[-1],
        "spread_sma20": spread_ma[-1] if spread_ma and spread_ma[-1] is not None else avg_spread,
        "avg_spread": avg_spread,
        "latest_zscore": latest_z,
        "latest_correlation": latest_corr,
        "signals": signals,
        "total_signals": len(signals),
        "completed_trades": len(trades),
        "win_rate": win_rate,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python spread_strat.py <ticker_a> <ticker_b> [period]")
        print("  mean reversion on spread between two correlated tickers")
        sys.exit(1)

    ticker_a = sys.argv[1].upper()
    ticker_b = sys.argv[2].upper()
    period = sys.argv[3] if len(sys.argv) > 3 else "1y"

    print(f"spread analysis: {ticker_a} / {ticker_b} ({period})")
    result = analyze(ticker_a, ticker_b, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    print(f"\n  data points: {result['data_points']}")
    print(f"  correlation: {result['latest_correlation']:.4f}")
    print(f"  spread: {result['latest_spread']:.4f} (avg: {result['avg_spread']:.4f})")
    print(f"  z-score: {result['latest_zscore']:+.2f}")
    print(f"  trades: {result['completed_trades']}  win rate: {result['win_rate']}%")

    if result["signals"]:
        print(f"\nrecent signals ({result['total_signals']} total):")
        for s in result["signals"][-10:]:
            print(f"  {s['date']}  {s['action']:<20}  z={s['zscore']:+.2f}  "
                  f"spread={s['spread']:.4f}")
    else:
        print("\nno spread signals")
