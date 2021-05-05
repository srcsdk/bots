#!/usr/bin/env python3
"""canslim technical screener: score stocks on technical components of o'neil's method.

since fundamental data (earnings, sales) is unavailable, this focuses on the
technical components: new highs, relative strength, volume patterns, and
price vs moving averages.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma, rsi, volume_sma


def relative_strength(closes, benchmark_closes):
    """calculate relative strength vs benchmark (percentile rank of performance)"""
    if len(closes) < 63 or len(benchmark_closes) < 63:
        return None

    stock_ret = (closes[-1] - closes[-63]) / closes[-63] * 100
    bench_ret = (benchmark_closes[-1] - benchmark_closes[-63]) / benchmark_closes[-63] * 100
    outperformance = stock_ret - bench_ret
    return round(outperformance, 2)


def score_new_high(closes, window=252):
    """score based on proximity to 52-week high (0-100)"""
    if len(closes) < window:
        window = len(closes)
    high_52 = max(closes[-window:])
    pct_from_high = (closes[-1] - high_52) / high_52 * 100

    if pct_from_high >= 0:
        return 100
    elif pct_from_high > -5:
        return 80
    elif pct_from_high > -10:
        return 60
    elif pct_from_high > -20:
        return 40
    elif pct_from_high > -30:
        return 20
    return 0


def score_volume_pattern(volumes, closes, period=50):
    """score volume pattern: accumulation vs distribution.

    looks for volume surges on up days (accumulation) vs down days (distribution)
    """
    if len(volumes) < period or len(closes) < period:
        return 0

    up_vol = 0
    down_vol = 0
    for i in range(-period, 0):
        if closes[i] > closes[i - 1]:
            up_vol += volumes[i]
        elif closes[i] < closes[i - 1]:
            down_vol += volumes[i]

    if down_vol == 0:
        return 100
    ratio = up_vol / down_vol
    if ratio > 1.5:
        return 100
    elif ratio > 1.2:
        return 75
    elif ratio > 1.0:
        return 50
    elif ratio > 0.8:
        return 25
    return 0


def score_moving_averages(closes):
    """score price position relative to key moving averages"""
    sma_50 = sma(closes, 50)
    sma_200 = sma(closes, 200)
    score = 0

    if sma_50[-1] is not None and closes[-1] > sma_50[-1]:
        score += 25
    if sma_200[-1] is not None and closes[-1] > sma_200[-1]:
        score += 25
    if sma_50[-1] is not None and sma_200[-1] is not None and sma_50[-1] > sma_200[-1]:
        score += 25

    if len(closes) >= 10:
        recent_trend = (closes[-1] - closes[-10]) / closes[-10] * 100
        if recent_trend > 0:
            score += 25

    return score


def score_volume_surge(volumes, period=20, threshold=2.0):
    """detect recent volume surges indicating institutional interest"""
    vol_avg = volume_sma(volumes, period)
    if vol_avg[-1] is None or vol_avg[-1] == 0:
        return 0

    recent_max = max(volumes[-5:])
    ratio = recent_max / vol_avg[-1]

    if ratio > threshold * 2:
        return 100
    elif ratio > threshold:
        return 75
    elif ratio > threshold * 0.75:
        return 50
    elif ratio > 1.0:
        return 25
    return 0


def scan(ticker, period="1y", benchmark="SPY"):
    """run canslim technical screen on a ticker.

    scores each component 0-100 and returns weighted composite.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 50:
        return None

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]

    bench_rows = fetch_ohlc(benchmark, period)
    bench_closes = [r["close"] for r in bench_rows] if bench_rows else closes

    rs_raw = relative_strength(closes, bench_closes)
    rs_score = min(100, max(0, 50 + (rs_raw or 0) * 2))

    new_high_score = score_new_high(closes)
    vol_pattern = score_volume_pattern(volumes, closes)
    ma_score = score_moving_averages(closes)
    vol_surge = score_volume_surge(volumes)

    rsi_vals = rsi(closes, 14)
    rsi_current = rsi_vals[-1] if rsi_vals[-1] is not None else 50
    momentum_score = min(100, max(0, rsi_current))

    components = {
        "new_high": {"score": new_high_score, "weight": 0.20},
        "relative_strength": {"score": round(rs_score), "weight": 0.25},
        "volume_accumulation": {"score": vol_pattern, "weight": 0.15},
        "moving_averages": {"score": ma_score, "weight": 0.15},
        "volume_surge": {"score": vol_surge, "weight": 0.15},
        "momentum": {"score": round(momentum_score), "weight": 0.10},
    }

    composite = sum(c["score"] * c["weight"] for c in components.values())

    return {
        "ticker": ticker,
        "price": closes[-1],
        "composite_score": round(composite, 1),
        "components": components,
        "relative_strength_raw": rs_raw,
        "rsi": round(rsi_current, 1) if rsi_current else None,
        "signal": "strong buy" if composite >= 80 else
                  "buy" if composite >= 65 else
                  "neutral" if composite >= 45 else
                  "weak" if composite >= 30 else "avoid",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python canslim.py <ticker> [period]")
        print("  canslim technical screener (technical components only)")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"canslim technical screen: {ticker} ({period})")
    result = scan(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    print(f"\nprice: ${result['price']:.2f}  rsi: {result['rsi']}")
    print(f"relative strength vs spy: {result['relative_strength_raw']:+.1f}%")
    print(f"\ncomposite score: {result['composite_score']:.1f}/100  -> {result['signal'].upper()}")

    print("\ncomponents:")
    for name, comp in result["components"].items():
        bar = "#" * (comp["score"] // 5)
        label = name.replace("_", " ")
        print(f"  {label:<25} {comp['score']:>3}/100  [{bar:<20}]  (weight: {comp['weight']:.0%})")
