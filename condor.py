#!/usr/bin/env python3
"""iron condor strategy evaluator: find optimal strike selection based on historical data.

evaluates iron condor setups using historical volatility, implied move estimation,
and support/resistance levels. scores the setup quality and suggests strike prices.
an iron condor profits when price stays within a range.
"""

import sys
from ohlc import fetch_ohlc
from indicators import atr, bollinger_bands


def historical_volatility(closes, window=30):
    """calculate annualized historical volatility"""
    if len(closes) < window + 1:
        return None
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(len(closes) - window, len(closes))]
    mean = sum(rets) / len(rets)
    variance = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return round((variance ** 0.5) * (252 ** 0.5), 4)


def implied_move(price, hv, days=30):
    """estimate expected move based on historical volatility.

    expected move = price * hv * sqrt(days/365)
    """
    if hv is None or price <= 0:
        return None
    return round(price * hv * (days / 365) ** 0.5, 2)


def find_support_resistance(highs, lows, closes, window=20):
    """find key support and resistance levels from price pivots"""
    supports = []
    resistances = []

    for i in range(window, len(closes) - window):
        is_low = all(lows[i] <= lows[j] for j in range(i - window, i + window + 1) if j != i)
        is_high = all(highs[i] >= highs[j] for j in range(i - window, i + window + 1) if j != i)

        if is_low:
            supports.append(lows[i])
        if is_high:
            resistances.append(highs[i])

    return supports, resistances


def round_to_strike(price, increment=1.0):
    """round price to nearest option strike increment"""
    if price > 200:
        increment = 5.0
    elif price > 50:
        increment = 2.5
    return round(round(price / increment) * increment, 2)


def evaluate_condor(ticker, period="1y", dte=30, width=1):
    """evaluate iron condor setup for a ticker.

    iron condor structure:
    - sell otm put (lower middle strike)
    - buy further otm put (lower strike)
    - sell otm call (upper middle strike)
    - buy further otm call (upper strike)

    width: number of strike increments for wing width
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return None

    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    closes = [r["close"] for r in rows]

    price = closes[-1]
    hv_30 = historical_volatility(closes, 30)
    hv_60 = historical_volatility(closes, 60)
    hv_90 = historical_volatility(closes, 90) if len(closes) >= 91 else hv_60

    move = implied_move(price, hv_30, dte)
    atr_vals = atr(highs, lows, closes, 14)
    current_atr = atr_vals[-1] if atr_vals[-1] else 0
    _, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)

    supports, resistances = find_support_resistance(highs, lows, closes, 10)

    increment = 5.0 if price > 200 else 2.5 if price > 50 else 1.0

    short_put = round_to_strike(price - move, increment) if move else round_to_strike(price * 0.95, increment)
    long_put = round_to_strike(short_put - width * increment, increment)
    short_call = round_to_strike(price + move, increment) if move else round_to_strike(price * 1.05, increment)
    long_call = round_to_strike(short_call + width * increment, increment)

    put_near_support = any(abs(short_put - s) / price < 0.02 for s in supports[-5:]) if supports else False
    call_near_resistance = any(abs(short_call - r) / price < 0.02 for r in resistances[-5:]) if resistances else False

    vol_trend = "declining"
    if hv_30 and hv_60:
        if hv_30 > hv_60 * 1.1:
            vol_trend = "rising"
        elif hv_30 > hv_60 * 0.9:
            vol_trend = "stable"

    range_width = (short_call - short_put) / price * 100
    max_historical_range = 0
    for i in range(max(0, len(closes) - dte), len(closes)):
        start = max(0, i - dte)
        period_range = (max(highs[start:i + 1]) - min(lows[start:i + 1])) / closes[start] * 100
        max_historical_range = max(max_historical_range, period_range)

    range_score = min(100, max(0, int(range_width / max_historical_range * 100))) if max_historical_range > 0 else 50

    vol_score = 80 if vol_trend == "declining" else 50 if vol_trend == "stable" else 30
    support_score = 80 if put_near_support else 50
    resistance_score = 80 if call_near_resistance else 50
    hv_level_score = min(100, int(hv_30 * 200)) if hv_30 else 50

    composite = int(
        range_score * 0.30 +
        vol_score * 0.25 +
        hv_level_score * 0.20 +
        support_score * 0.15 +
        resistance_score * 0.10
    )

    return {
        "ticker": ticker,
        "price": price,
        "strikes": {
            "long_put": long_put,
            "short_put": short_put,
            "short_call": short_call,
            "long_call": long_call,
        },
        "metrics": {
            "hv_30": round(hv_30 * 100, 1) if hv_30 else None,
            "hv_60": round(hv_60 * 100, 1) if hv_60 else None,
            "hv_90": round(hv_90 * 100, 1) if hv_90 else None,
            "vol_trend": vol_trend,
            "implied_move": move,
            "atr_14": round(current_atr, 2),
            "bb_upper": bb_upper[-1],
            "bb_lower": bb_lower[-1],
        },
        "setup_quality": {
            "composite_score": composite,
            "range_score": range_score,
            "vol_score": vol_score,
            "support_score": support_score,
            "resistance_score": resistance_score,
            "put_near_support": put_near_support,
            "call_near_resistance": call_near_resistance,
        },
        "range_width_pct": round(range_width, 2),
        "max_historical_range_pct": round(max_historical_range, 2),
        "signal": "favorable" if composite >= 65 else "neutral" if composite >= 45 else "unfavorable",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python condor.py <ticker> [period]")
        print("  evaluate iron condor setup quality")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"iron condor evaluation: {ticker} ({period})")
    result = evaluate_condor(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    m = result["metrics"]
    print(f"\nprice: ${result['price']:.2f}")
    print(f"historical volatility: 30d={m['hv_30']}%  60d={m['hv_60']}%  trend={m['vol_trend']}")
    print(f"expected 30d move: +/- ${m['implied_move']:.2f}")
    print(f"atr(14): ${m['atr_14']:.2f}")
    print(f"bollinger bands: [{m['bb_lower']:.2f} - {m['bb_upper']:.2f}]")

    s = result["strikes"]
    print("\nsuggested strikes (30 dte):")
    print(f"  buy put:   ${s['long_put']:.2f}")
    print(f"  sell put:  ${s['short_put']:.2f}")
    print(f"  sell call: ${s['short_call']:.2f}")
    print(f"  buy call:  ${s['long_call']:.2f}")
    print(f"  profit zone: ${s['short_put']:.2f} - ${s['short_call']:.2f} ({result['range_width_pct']:.1f}%)")

    q = result["setup_quality"]
    print(f"\nsetup quality: {result['composite_score']}/100 -> {result['signal'].upper()}")
    print(f"  range coverage: {q['range_score']}/100")
    print(f"  volatility:     {q['vol_score']}/100")
    print(f"  support level:  {q['support_score']}/100 {'(near support)' if q['put_near_support'] else ''}")
    print(f"  resistance:     {q['resistance_score']}/100 {'(near resistance)' if q['call_near_resistance'] else ''}")
