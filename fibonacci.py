#!/usr/bin/env python3
"""fibonacci retracement and extension levels"""

import sys
from ohlc import fetch_ohlc


FIB_RATIOS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
FIB_EXTENSIONS = [1.0, 1.272, 1.414, 1.618, 2.0, 2.618]


def find_swing_points(closes, window=5):
    """find swing highs and lows in price data.

    window: number of bars on each side to confirm swing
    """
    highs = []
    lows = []
    for i in range(window, len(closes) - window):
        left = closes[i - window:i]
        right = closes[i + 1:i + window + 1]
        if closes[i] >= max(left) and closes[i] >= max(right):
            highs.append((i, closes[i]))
        if closes[i] <= min(left) and closes[i] <= min(right):
            lows.append((i, closes[i]))
    return highs, lows


def retracement_levels(swing_high, swing_low):
    """calculate fibonacci retracement levels between two prices"""
    diff = swing_high - swing_low
    levels = {}
    for ratio in FIB_RATIOS:
        price = swing_high - diff * ratio
        levels[f"{ratio:.3f}"] = round(price, 2)
    return levels


def extension_levels(swing_high, swing_low, direction="up"):
    """calculate fibonacci extension levels"""
    diff = swing_high - swing_low
    levels = {}
    for ratio in FIB_EXTENSIONS:
        if direction == "up":
            price = swing_low + diff * ratio
        else:
            price = swing_high - diff * ratio
        levels[f"{ratio:.3f}"] = round(price, 2)
    return levels


def auto_fib(ticker, period="6mo"):
    """automatically find swing points and calculate fib levels.

    uses the most recent significant swing high and low
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 30:
        return None

    closes = [r["close"] for r in rows]
    dates = [r["date"] for r in rows]
    swing_highs, swing_lows = find_swing_points(closes)

    if not swing_highs or not swing_lows:
        high_idx = closes.index(max(closes))
        low_idx = closes.index(min(closes))
        swing_high = max(closes)
        swing_low = min(closes)
    else:
        high_idx, swing_high = max(swing_highs, key=lambda x: x[1])
        low_idx, swing_low = min(swing_lows, key=lambda x: x[1])

    retrace = retracement_levels(swing_high, swing_low)
    if high_idx > low_idx:
        extend = extension_levels(swing_high, swing_low, "up")
        trend = "uptrend retracement"
    else:
        extend = extension_levels(swing_high, swing_low, "down")
        trend = "downtrend retracement"

    current = closes[-1]
    nearest_level = None
    nearest_dist = float("inf")
    for name, price in retrace.items():
        dist = abs(current - price)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest_level = (name, price)

    return {
        "ticker": ticker,
        "trend": trend,
        "swing_high": swing_high,
        "swing_high_date": dates[high_idx],
        "swing_low": swing_low,
        "swing_low_date": dates[low_idx],
        "current": current,
        "retracement": retrace,
        "extensions": extend,
        "nearest_fib": nearest_level,
    }


def support_resistance_from_fib(fib_data, tolerance=0.02):
    """identify support/resistance zones from fib levels near current price"""
    if not fib_data:
        return []
    current = fib_data["current"]
    zones = []
    for name, price in fib_data["retracement"].items():
        pct_diff = (price - current) / current
        if abs(pct_diff) < tolerance * 3:
            role = "support" if price < current else "resistance"
            zones.append({
                "level": name,
                "price": price,
                "role": role,
                "distance_pct": round(pct_diff * 100, 2),
            })
    zones.sort(key=lambda z: abs(z["distance_pct"]))
    return zones


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python fibonacci.py <ticker> [period]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "6mo"

    result = auto_fib(ticker, period)
    if result is None:
        print("insufficient data")
        sys.exit(1)

    print(f"\n{ticker} fibonacci levels ({result['trend']})")
    print(f"  swing high: ${result['swing_high']:.2f} ({result['swing_high_date']})")
    print(f"  swing low:  ${result['swing_low']:.2f} ({result['swing_low_date']})")
    print(f"  current:    ${result['current']:.2f}")

    print(f"\nretracement levels:")
    for name, price in result["retracement"].items():
        marker = " <--" if result["nearest_fib"] and price == result["nearest_fib"][1] else ""
        print(f"  {name}  ${price:.2f}{marker}")

    print(f"\nextension levels:")
    for name, price in result["extensions"].items():
        print(f"  {name}  ${price:.2f}")

    zones = support_resistance_from_fib(result)
    if zones:
        print(f"\nnearby s/r zones:")
        for z in zones:
            print(f"  {z['role']:<11} ${z['price']:.2f} "
                  f"(fib {z['level']}, {z['distance_pct']:+.2f}%)")
