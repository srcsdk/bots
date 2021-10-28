#!/usr/bin/env python3
"""ichimoku cloud indicator and strategy"""

import sys
from ohlc import fetch_ohlc


def ichimoku(highs, lows, closes, tenkan=9, kijun=26, senkou_b=52):
    """calculate ichimoku cloud components.

    returns dict of:
        tenkan_sen: conversion line (9-period midpoint)
        kijun_sen: base line (26-period midpoint)
        senkou_a: leading span a (midpoint of tenkan/kijun, shifted 26 ahead)
        senkou_b: leading span b (52-period midpoint, shifted 26 ahead)
        chikou: lagging span (close shifted 26 behind)
    """
    n = len(closes)

    def midpoint(series, period, idx):
        start = max(0, idx - period + 1)
        window = series[start:idx + 1]
        if not window:
            return None
        return (max(window) + min(window)) / 2

    tenkan_sen = [None] * n
    kijun_sen = [None] * n
    for i in range(n):
        if i >= tenkan - 1:
            tenkan_sen[i] = round(midpoint(highs, tenkan, i) + midpoint(lows, tenkan, i), 2) / 2
            tenkan_sen[i] = round((max(highs[i-tenkan+1:i+1]) + min(lows[i-tenkan+1:i+1])) / 2, 2)
        if i >= kijun - 1:
            kijun_sen[i] = round((max(highs[i-kijun+1:i+1]) + min(lows[i-kijun+1:i+1])) / 2, 2)

    senkou_a_vals = [None] * (n + kijun)
    senkou_b_vals = [None] * (n + kijun)
    for i in range(n):
        if tenkan_sen[i] is not None and kijun_sen[i] is not None:
            future_idx = i + kijun
            if future_idx < len(senkou_a_vals):
                senkou_a_vals[future_idx] = round((tenkan_sen[i] + kijun_sen[i]) / 2, 2)
        if i >= senkou_b - 1:
            future_idx = i + kijun
            val = round((max(highs[i-senkou_b+1:i+1]) + min(lows[i-senkou_b+1:i+1])) / 2, 2)
            if future_idx < len(senkou_b_vals):
                senkou_b_vals[future_idx] = val

    chikou = [None] * n
    for i in range(kijun, n):
        chikou[i - kijun] = closes[i]

    return {
        "tenkan": tenkan_sen,
        "kijun": kijun_sen,
        "senkou_a": senkou_a_vals[:n],
        "senkou_b": senkou_b_vals[:n],
        "chikou": chikou,
    }


def cloud_signal(closes, cloud):
    """generate signals based on ichimoku cloud analysis.

    strong buy: price above cloud + tenkan above kijun + chikou above price
    strong sell: price below cloud + tenkan below kijun + chikou below price
    """
    signals = []
    for i in range(1, len(closes)):
        tenkan = cloud["tenkan"][i]
        kijun = cloud["kijun"][i]
        senkou_a = cloud["senkou_a"][i]
        senkou_b = cloud["senkou_b"][i]
        chikou = cloud["chikou"][i]

        if any(v is None for v in [tenkan, kijun, senkou_a, senkou_b]):
            continue

        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        above_cloud = closes[i] > cloud_top
        below_cloud = closes[i] < cloud_bottom
        tk_cross_up = (tenkan > kijun and
                       cloud["tenkan"][i-1] is not None and
                       cloud["kijun"][i-1] is not None and
                       cloud["tenkan"][i-1] <= cloud["kijun"][i-1])
        tk_cross_down = (tenkan < kijun and
                        cloud["tenkan"][i-1] is not None and
                        cloud["kijun"][i-1] is not None and
                        cloud["tenkan"][i-1] >= cloud["kijun"][i-1])

        if above_cloud and tk_cross_up:
            signals.append({"date": None, "idx": i, "type": "strong_buy",
                           "price": closes[i]})
        elif below_cloud and tk_cross_down:
            signals.append({"date": None, "idx": i, "type": "strong_sell",
                           "price": closes[i]})
        elif tk_cross_up:
            signals.append({"date": None, "idx": i, "type": "buy",
                           "price": closes[i]})
        elif tk_cross_down:
            signals.append({"date": None, "idx": i, "type": "sell",
                           "price": closes[i]})

    return signals


def scan(ticker, period="1y"):
    """scan ticker for ichimoku signals"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return []

    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    closes = [r["close"] for r in rows]

    cloud = ichimoku(highs, lows, closes)
    signals = cloud_signal(closes, cloud)

    for sig in signals:
        sig["date"] = rows[sig["idx"]]["date"]

    return signals


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ichimoku.py <ticker> [period]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"ichimoku scan: {ticker} ({period})")
    signals = scan(ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            label = s["type"].upper().replace("_", " ")
            print(f"  [{label}] {s['date']} ${s['price']:.2f}")
        print(f"\n{len(signals)} signals")
