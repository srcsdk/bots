#!/usr/bin/env python3
"""mobr: nobr + movo combined signal

requires both momentum/volume (movo) and oversold near 52wk low (nobr)
to trigger within 3 days. high conviction entry when both conditions align.

usage: python mobr.py AAPL [period]
"""

import sys
from movo import scan_mobr, scan_nobr, scan_movo
from ohlc import fetch_ohlc
from indicators import rsi, sma, volume_sma


def scan(ticker, period="1y"):
    """run mobr scan with component breakdown and scoring"""
    raw = scan_mobr(ticker, period)
    if not raw:
        return []

    rows = fetch_ohlc(ticker, period)
    if not rows:
        return raw

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    rsi_vals = rsi(closes, 14)
    sma_20 = sma(closes, 20)
    vol_avg = volume_sma(volumes, 20)
    dates = {r["date"]: i for i, r in enumerate(rows)}

    nobr_dates = {s["date"] for s in scan_nobr(ticker, period)}
    movo_dates = {s["date"] for s in scan_movo(ticker, period)}

    enriched = []
    for sig in raw:
        idx = dates.get(sig["date"])
        if idx is None:
            enriched.append(sig)
            continue

        sig["has_nobr"] = sig["date"] in nobr_dates
        sig["has_movo"] = sig["date"] in movo_dates

        if rsi_vals[idx] is not None:
            sig["rsi"] = round(rsi_vals[idx], 1)

        if vol_avg[idx] is not None and vol_avg[idx] > 0:
            sig["vol_ratio"] = round(volumes[idx] / vol_avg[idx], 1)

        if sma_20[idx] is not None:
            sig["above_sma20"] = closes[idx] > sma_20[idx]

        strength = 0
        if sig.get("has_nobr") and sig.get("has_movo"):
            strength += 3
        elif sig.get("has_nobr") or sig.get("has_movo"):
            strength += 1
        if sig.get("vol_ratio", 0) > 2.0:
            strength += 1
        if sig.get("rsi", 50) < 40:
            strength += 1
        sig["strength"] = strength

        if idx + 5 < len(closes):
            sig["fwd_5d"] = round(
                (closes[idx + 5] - closes[idx]) / closes[idx] * 100, 2
            )
        if idx + 10 < len(closes):
            sig["fwd_10d"] = round(
                (closes[idx + 10] - closes[idx]) / closes[idx] * 100, 2
            )

        enriched.append(sig)

    enriched.sort(key=lambda s: s.get("strength", 0), reverse=True)
    return enriched


def summary(signals):
    """aggregate stats for mobr signals"""
    if not signals:
        return "no mobr signals"

    strong = sum(1 for s in signals if s.get("strength", 0) >= 3)
    fwd = [s["fwd_5d"] for s in signals if "fwd_5d" in s]
    avg_fwd = sum(fwd) / len(fwd) if fwd else 0
    wins = sum(1 for f in fwd if f > 0)

    lines = [f"mobr: {len(signals)} signals ({strong} strong)"]
    if fwd:
        lines.append(f"5d avg return: {avg_fwd:+.2f}% win rate: {wins}/{len(fwd)}")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python mobr.py <ticker> [period]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"mobr scan: {ticker} ({period})")
    signals = scan(ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            parts = [f"  {s['date']} ${s['price']:.2f}"]
            if "rsi" in s:
                parts.append(f"rsi={s['rsi']}")
            parts.append(f"str={s.get('strength', 0)}")
            if "vol_ratio" in s:
                parts.append(f"vol={s['vol_ratio']}x")
            if "fwd_5d" in s:
                parts.append(f"fwd5d={s['fwd_5d']:+.2f}%")
            print(" ".join(parts))
        print()
        print(summary(signals))
