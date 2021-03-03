#!/usr/bin/env python3
"""movo: momentum and volume strategy
nobr: nolo + rsi <45
mobr: nobr + movo combined"""

import sys
from ohlc import fetch_ohlc
from indicators import (rsi, macd, fifty_two_week_low, sma,
                        volume_sma)


def scan_movo(ticker, period="1y"):
    """momentum + volume: price breaking above sma with volume surge"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return []

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]

    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    vol_sma = volume_sma(volumes, 20)
    rsi_vals = rsi(closes, 14)
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


def scan_nobr(ticker, period="1y"):
    """nobr: nolo with rsi <45 instead of <30"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return []

    closes = [r["close"] for r in rows]
    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, _ = macd(closes)
    low_52 = fifty_two_week_low(closes)

    signals = []
    for i in range(1, len(rows)):
        if rsi_vals[i] is None or macd_line[i] is None:
            continue
        if signal_line[i] is None or macd_line[i - 1] is None:
            continue
        if signal_line[i - 1] is None:
            continue

        within_30 = closes[i] <= low_52[i] * 1.30
        rsi_low = rsi_vals[i] < 45
        macd_cross = (macd_line[i] > signal_line[i]
                      and macd_line[i - 1] <= signal_line[i - 1])

        if within_30 and rsi_low and macd_cross:
            signals.append({
                "date": rows[i]["date"],
                "price": closes[i],
                "rsi": rsi_vals[i],
            })

    return signals


def scan_mobr(ticker, period="1y"):
    """mobr: nobr + movo combined - both must trigger within 3 days"""
    nobr_signals = {s["date"]: s for s in scan_nobr(ticker, period)}
    movo_signals = {s["date"]: s for s in scan_movo(ticker, period)}

    rows = fetch_ohlc(ticker, period)
    if not rows:
        return []

    dates = [r["date"] for r in rows]
    signals = []

    for i, date in enumerate(dates):
        nearby_nobr = any(
            dates[j] in nobr_signals
            for j in range(max(0, i - 3), min(len(dates), i + 4))
        )
        nearby_movo = any(
            dates[j] in movo_signals
            for j in range(max(0, i - 3), min(len(dates), i + 4))
        )

        if nearby_nobr and nearby_movo and date not in [s["date"] for s in signals]:
            signals.append({
                "date": date,
                "price": rows[i]["close"],
                "type": "mobr",
            })

    return signals


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python movo.py <ticker> [--nobr|--mobr] [period]")
        sys.exit(1)

    mode = "movo"
    if "--nobr" in sys.argv:
        mode = "nobr"
    elif "--mobr" in sys.argv:
        mode = "mobr"

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ticker = args[0].upper()
    period = args[1] if len(args) > 1 else "1y"

    scanners = {"movo": scan_movo, "nobr": scan_nobr, "mobr": scan_mobr}
    print(f"{mode} scan: {ticker} ({period})")
    signals = scanners[mode](ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            print(f"  {s['date']} ${s['price']:.2f}")
        print(f"\n{len(signals)} signals")
