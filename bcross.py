#!/usr/bin/env python3
"""bcross: gapup + macd must cross above signal line"""

import sys
from ohlc import fetch_ohlc
from indicators import rsi, macd, fifty_two_week_low, gap_percent


def scan(ticker, period="1y"):
    """scan for bcross buy signals"""
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
        if signal_line[i] is None or signal_line[i - 1] is None:
            continue
        if macd_line[i - 1] is None:
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
                "signal": signal_line[i],
            })

    return signals


def scan_multi_period(ticker, periods=None):
    """run scan across multiple periods and return combined signals with period context"""
    if periods is None:
        periods = ["3mo", "6mo", "1y", "2y"]
    combined = []
    seen_dates = set()
    for p in periods:
        signals = scan(ticker, p)
        for sig in signals:
            if sig["date"] not in seen_dates:
                sig["period"] = p
                combined.append(sig)
                seen_dates.add(sig["date"])
    combined.sort(key=lambda s: s["date"])
    return combined


def bollinger_squeeze_detect(closes, period=20):
    """detect bollinger band squeeze (low volatility periods).

    returns list of booleans where True indicates squeeze is active.
    squeeze = bandwidth at or near its minimum over lookback window.
    """
    if len(closes) < period:
        return [False] * len(closes)
    result = [False] * len(closes)
    bandwidths = []
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        mean = sum(window) / period
        std = (sum((x - mean) ** 2 for x in window) / period) ** 0.5
        if mean == 0:
            bandwidths.append((i, 0))
            continue
        bw = (std * 2) / mean
        bandwidths.append((i, bw))
    if len(bandwidths) < 2:
        return result
    bw_vals = [b[1] for b in bandwidths]
    min_bw = min(bw_vals)
    threshold = min_bw * 1.1
    for idx, bw in bandwidths:
        if bw <= threshold:
            result[idx] = True
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python bcross.py <ticker> [period]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"bcross scan: {ticker} ({period})")
    signals = scan(ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            print(f"  {s['date']} ${s['price']:.2f} "
                  f"rsi={s['rsi']:.1f} macd={s['macd']:.4f}")
        print(f"\n{len(signals)} signals")
