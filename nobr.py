#!/usr/bin/env python3
"""nobr: nolo with rsi <45 instead of <30

relaxed rsi threshold catches more entries near 52wk lows.
standalone wrapper with additional signal quality scoring.

usage: python nobr.py AAPL [period]
"""

import sys
from movo import scan_nobr
from ohlc import fetch_ohlc
from indicators import sma


def scan(ticker, period="1y"):
    """run nobr scan with trend context and scoring"""
    raw = scan_nobr(ticker, period)
    if not raw:
        return []

    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 50:
        return raw

    closes = [r["close"] for r in rows]
    sma_50 = sma(closes, 50)
    dates = {r["date"]: i for i, r in enumerate(rows)}

    scored = []
    for sig in raw:
        idx = dates.get(sig["date"])
        if idx is None:
            sig["quality"] = 0
            scored.append(sig)
            continue

        quality = 0

        if sig["rsi"] < 35:
            quality += 2
        elif sig["rsi"] < 40:
            quality += 1

        if sma_50[idx] is not None and closes[idx] < sma_50[idx]:
            quality += 1

        if idx > 0 and closes[idx] < closes[idx - 1]:
            quality += 1

        if idx + 5 < len(closes):
            fwd = (closes[idx + 5] - closes[idx]) / closes[idx] * 100
            sig["fwd_5d"] = round(fwd, 2)

        if idx + 10 < len(closes):
            fwd = (closes[idx + 10] - closes[idx]) / closes[idx] * 100
            sig["fwd_10d"] = round(fwd, 2)

        sig["quality"] = quality
        scored.append(sig)

    scored.sort(key=lambda s: s["quality"], reverse=True)
    return scored


def summary(signals):
    """signal quality breakdown"""
    if not signals:
        return "no nobr signals"

    high = sum(1 for s in signals if s.get("quality", 0) >= 3)
    med = sum(1 for s in signals if 1 <= s.get("quality", 0) < 3)
    low = sum(1 for s in signals if s.get("quality", 0) < 1)

    fwd_5 = [s["fwd_5d"] for s in signals if "fwd_5d" in s]
    avg_5 = sum(fwd_5) / len(fwd_5) if fwd_5 else 0

    lines = [
        f"nobr: {len(signals)} signals (high={high} med={med} low={low})",
    ]
    if fwd_5:
        lines.append(f"avg 5d forward return: {avg_5:+.2f}%")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python nobr.py <ticker> [period]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"nobr scan: {ticker} ({period})")
    signals = scan(ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            parts = [f"  {s['date']} ${s['price']:.2f} rsi={s['rsi']:.1f}"]
            parts.append(f"q={s.get('quality', 0)}")
            if "fwd_5d" in s:
                parts.append(f"fwd5d={s['fwd_5d']:+.2f}%")
            if "fwd_10d" in s:
                parts.append(f"fwd10d={s['fwd_10d']:+.2f}%")
            print(" ".join(parts))
        print()
        print(summary(signals))
