#!/usr/bin/env python3
"""nolo: across within 30% of 52 week low

standalone wrapper for nolo strategy. uses scan_nolo from across module
but adds additional filtering and standalone cli.

usage: python nolo.py AAPL [period]
"""

import sys
from across import scan_nolo
from ohlc import fetch_ohlc
from indicators import fifty_two_week_low


def scan(ticker, period="1y"):
    """run nolo scan with extra distance metrics"""
    raw = scan_nolo(ticker, period)
    if not raw:
        return []

    rows = fetch_ohlc(ticker, period)
    if not rows:
        return raw

    closes = [r["close"] for r in rows]
    low_52 = fifty_two_week_low(closes)
    dates = {r["date"]: i for i, r in enumerate(rows)}

    enriched = []
    for sig in raw:
        idx = dates.get(sig["date"])
        if idx is None:
            enriched.append(sig)
            continue

        low = low_52[idx]
        distance = (sig["price"] - low) / low * 100 if low > 0 else 0
        sig["low_52"] = round(low, 2)
        sig["distance_pct"] = round(distance, 1)

        if idx + 5 < len(closes):
            fwd_return = (closes[idx + 5] - closes[idx]) / closes[idx] * 100
            sig["fwd_5d"] = round(fwd_return, 2)

        enriched.append(sig)

    return enriched


def summary(signals):
    """print signal summary with forward returns"""
    if not signals:
        return "no nolo signals"

    wins = sum(1 for s in signals if s.get("fwd_5d", 0) > 0)
    total = sum(1 for s in signals if "fwd_5d" in s)
    avg_dist = sum(s.get("distance_pct", 0) for s in signals) / len(signals)

    lines = [f"nolo: {len(signals)} signals, avg distance from 52wk low: {avg_dist:.1f}%"]
    if total > 0:
        lines.append(f"5-day forward win rate: {wins}/{total} ({wins/total*100:.0f}%)")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python nolo.py <ticker> [period]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"nolo scan: {ticker} ({period})")
    signals = scan(ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            parts = [f"  {s['date']} ${s['price']:.2f} rsi={s['rsi']:.1f}"]
            if "distance_pct" in s:
                parts.append(f"dist={s['distance_pct']:.1f}%")
            if "fwd_5d" in s:
                parts.append(f"fwd5d={s['fwd_5d']:+.2f}%")
            print(" ".join(parts))
        print()
        print(summary(signals))
