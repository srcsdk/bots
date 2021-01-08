#!/usr/bin/env python3
"""movo: momentum and volume strategy
nobr: nolo + rsi <45
mobr: nobr + movo combined"""

import sys
from ohlc import fetch_ohlc
from indicators import rsi, macd, fifty_two_week_low, sma, volume_sma, atr


def scan_movo(ticker, period="1y"):
    """momentum + volume: price breaking above sma with volume surge"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return []

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]

    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    vol_sma = volume_sma(volumes, 20)
    rsi_vals = rsi(closes, 14)
    atr_vals = atr(highs, lows, closes, 14)

    signals = []
    for i in range(1, len(rows)):
        if sma_20[i] is None or sma_50[i] is None:
            continue
        if vol_sma[i] is None or rsi_vals[i] is None:
            continue

        price_above_sma = closes[i] > sma_20[i] and closes[i - 1] <= sma_20[i - 1]
        sma_trend = sma_20[i] > sma_50[i]
        volume_surge = volumes[i] > vol_sma[i] * 1.5
        rsi_range = 40 < rsi_vals[i] < 70

        if price_above_sma and sma_trend and volume_surge and rsi_range:
            signals.append({
                "date": rows[i]["date"],
                "price": closes[i],
                "volume": volumes[i],
                "vol_ratio": round(volumes[i] / vol_sma[i], 1),
                "rsi": rsi_vals[i],
            })

    return signals


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python movo.py <ticker> [period]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"movo scan: {ticker} ({period})")
    signals = scan_movo(ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            print(f"  {s['date']} ${s['price']:.2f}")
        print(f"\n{len(signals)} signals")
