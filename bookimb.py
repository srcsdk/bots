#!/usr/bin/env python3
"""order flow imbalance proxy.

uses volume and price action to infer buy/sell pressure via up-volume
vs down-volume ratio. generates signals on extreme imbalance conditions.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma


def classify_volume(rows):
    """split volume into up-volume and down-volume based on price action.

    up-volume: volume on bars where close > open (buying pressure)
    down-volume: volume on bars where close < open (selling pressure)
    """
    up_vol = []
    down_vol = []

    for r in rows:
        if r["close"] > r["open"]:
            up_vol.append(r["volume"])
            down_vol.append(0)
        elif r["close"] < r["open"]:
            up_vol.append(0)
            down_vol.append(r["volume"])
        else:
            half = r["volume"] // 2
            up_vol.append(half)
            down_vol.append(half)

    return up_vol, down_vol


def imbalance_ratio(up_vol, down_vol, period=10):
    """calculate rolling buy/sell imbalance ratio.

    ratio > 1: more buying pressure, ratio < 1: more selling pressure.
    """
    result = [None] * (period - 1)
    for i in range(period - 1, len(up_vol)):
        total_up = sum(up_vol[i - period + 1:i + 1])
        total_down = sum(down_vol[i - period + 1:i + 1])
        if total_down == 0:
            result.append(10.0)
        else:
            result.append(round(total_up / total_down, 4))
    return result


def cumulative_delta(up_vol, down_vol):
    """cumulative volume delta (running sum of up_vol - down_vol)"""
    result = []
    cum = 0
    for u, d in zip(up_vol, down_vol):
        cum += u - d
        result.append(cum)
    return result


def detect_imbalance_signals(rows, ratio_vals, cum_delta, threshold_high=2.0, threshold_low=0.5):
    """detect extreme order flow imbalance conditions"""
    signals = []
    for i in range(1, len(rows)):
        if ratio_vals[i] is None:
            continue

        delta_change = cum_delta[i] - cum_delta[i - 1] if i > 0 else 0

        if ratio_vals[i] >= threshold_high:
            strength = min(100, int((ratio_vals[i] - 1) * 50))
            signals.append({
                "date": rows[i]["date"],
                "price": rows[i]["close"],
                "type": "buy_pressure",
                "ratio": ratio_vals[i],
                "strength": strength,
                "delta_change": delta_change,
                "volume": rows[i]["volume"],
            })
        elif ratio_vals[i] <= threshold_low:
            strength = min(100, int((1 - ratio_vals[i]) * 50))
            signals.append({
                "date": rows[i]["date"],
                "price": rows[i]["close"],
                "type": "sell_pressure",
                "ratio": ratio_vals[i],
                "strength": strength,
                "delta_change": delta_change,
                "volume": rows[i]["volume"],
            })

    return signals


def analyze(ticker, period="1y"):
    """analyze order flow imbalance for a ticker.

    returns imbalance signals with buy/sell pressure classification.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 20:
        return None

    volumes = [r["volume"] for r in rows]
    vol_avg = sma(volumes, 20)

    up_vol, down_vol = classify_volume(rows)
    ratio_10 = imbalance_ratio(up_vol, down_vol, 10)
    ratio_5 = imbalance_ratio(up_vol, down_vol, 5)
    cum_delta = cumulative_delta(up_vol, down_vol)
    signals = detect_imbalance_signals(rows, ratio_10, cum_delta)

    latest_ratio = ratio_5[-1] if ratio_5[-1] is not None else 1.0
    if latest_ratio > 1.5:
        current_bias = "strong buying"
    elif latest_ratio > 1.1:
        current_bias = "mild buying"
    elif latest_ratio < 0.67:
        current_bias = "strong selling"
    elif latest_ratio < 0.9:
        current_bias = "mild selling"
    else:
        current_bias = "balanced"

    total_up = sum(up_vol[-20:])
    total_down = sum(down_vol[-20:])
    recent_ratio = round(total_up / total_down, 2) if total_down > 0 else 10.0

    delta_trend = cum_delta[-1] - cum_delta[-20] if len(cum_delta) > 20 else cum_delta[-1]
    avg_vol = vol_avg[-1] if vol_avg[-1] is not None else 0

    return {
        "ticker": ticker,
        "current_bias": current_bias,
        "latest_ratio_5d": round(latest_ratio, 2),
        "recent_20d_ratio": recent_ratio,
        "avg_volume_20d": round(avg_vol, 0),
        "cum_delta_trend": delta_trend,
        "signals": signals,
        "total_signals": len(signals),
        "buy_signals": sum(1 for s in signals if s["type"] == "buy_pressure"),
        "sell_signals": sum(1 for s in signals if s["type"] == "sell_pressure"),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python bookimb.py <ticker> [period]")
        print("  analyzes order flow imbalance from volume/price action")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"order flow imbalance: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    print(f"\n  current bias: {result['current_bias']}")
    print(f"  5d ratio: {result['latest_ratio_5d']:.2f}  20d ratio: {result['recent_20d_ratio']:.2f}")
    print(f"  cumulative delta trend: {result['cum_delta_trend']:+,.0f}")
    print(f"  buy signals: {result['buy_signals']}  sell signals: {result['sell_signals']}")

    if result["signals"]:
        print("\nrecent signals:")
        for s in result["signals"][-15:]:
            print(f"  {s['date']}  ${s['price']:>8.2f}  {s['type']:<14}  "
                  f"ratio={s['ratio']:.2f}  strength={s['strength']}")
    else:
        print("\nno extreme imbalance signals")
