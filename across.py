#!/usr/bin/env python3
"""across: bcross without requiring macd banana up"""

import sys
from ohlc import fetch_ohlc
from indicators import rsi, macd, fifty_two_week_low, gap_percent


def scan(ticker, period="1y"):
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return []

    closes = [r["close"] for r in rows]
    opens = [r["open"] for r in rows]

    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, hist = macd(closes)
    low_52 = fifty_two_week_low(closes)
    gaps = gap_percent(opens, closes)

    signals = []
    for i in range(1, len(rows)):
        if rsi_vals[i] is None or macd_line[i] is None:
            continue
        if signal_line[i] is None or macd_line[i - 1] is None:
            continue
        if signal_line[i - 1] is None:
            continue

        at_52_low = closes[i] <= low_52[i] * 1.05
        rsi_oversold = rsi_vals[i] < 30
        macd_cross = (macd_line[i] > signal_line[i]
                      and macd_line[i - 1] <= signal_line[i - 1])

        recent_gap = False
        for j in range(max(0, i - 5), i):
            if gaps[j] is not None and gaps[j] < -2:
                recent_gap = True
                break

        if at_52_low and rsi_oversold and macd_cross and recent_gap:
            signals.append({
                "date": rows[i]["date"],
                "price": closes[i],
                "rsi": rsi_vals[i],
                "macd": macd_line[i],
            })

    return signals


def scan_nolo(ticker, period="1y"):
    """nolo: across but within 30% of 52wk low"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return []

    closes = [r["close"] for r in rows]
    opens = [r["open"] for r in rows]

    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, _ = macd(closes)
    low_52 = fifty_two_week_low(closes)
    gaps = gap_percent(opens, closes)

    signals = []
    for i in range(1, len(rows)):
        if rsi_vals[i] is None or macd_line[i] is None:
            continue
        if signal_line[i] is None or macd_line[i - 1] is None:
            continue
        if signal_line[i - 1] is None:
            continue

        within_30 = closes[i] <= low_52[i] * 1.30
        rsi_oversold = rsi_vals[i] < 30
        macd_cross = (macd_line[i] > signal_line[i]
                      and macd_line[i - 1] <= signal_line[i - 1])

        if within_30 and rsi_oversold and macd_cross:
            pct_above_low = (closes[i] - low_52[i]) / low_52[i] * 100
            signals.append({
                "date": rows[i]["date"],
                "price": closes[i],
                "rsi": rsi_vals[i],
                "pct_above_52low": round(pct_above_low, 1),
            })

    return signals


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python across.py <ticker> [period]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"across scan: {ticker} ({period})")
    signals = scan(ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            print(f"  {s['date']} ${s['price']:.2f} rsi={s['rsi']:.1f}")
        print(f"\n{len(signals)} signals")
