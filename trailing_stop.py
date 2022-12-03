#!/usr/bin/env python3
# updated: atr-based trailing with proper edge cases
"""trailing stop with atr-based dynamic distance"""


def atr(highs, lows, closes, period=14):
    """average true range."""
    if len(highs) < 2:
        return []
    tr = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    result = [None] * (period - 1)
    result.append(sum(tr[:period]) / period)
    for i in range(period, len(tr)):
        result.append((result[-1] * (period - 1) + tr[i]) / period)
    return result


def trailing_stop_long(closes, highs, lows, multiplier=3.0, atr_period=14):
    """calculate trailing stop for long positions.

    stop trails below price by multiplier * atr.
    only moves up, never down.
    """
    atr_values = atr(highs, lows, closes, atr_period)
    stops = [None] * len(closes)
    highest_stop = 0
    for i in range(len(closes)):
        if atr_values[i] is None:
            continue
        stop = closes[i] - multiplier * atr_values[i]
        highest_stop = max(highest_stop, stop)
        stops[i] = round(highest_stop, 4)
    return stops


def trailing_stop_short(closes, highs, lows, multiplier=3.0, atr_period=14):
    """calculate trailing stop for short positions. stop trails above price."""
    atr_values = atr(highs, lows, closes, atr_period)
    stops = [None] * len(closes)
    lowest_stop = float("inf")
    for i in range(len(closes)):
        if atr_values[i] is None:
            continue
        stop = closes[i] + multiplier * atr_values[i]
        lowest_stop = min(lowest_stop, stop)
        stops[i] = round(lowest_stop, 4)
    return stops


def chandelier_exit(closes, highs, lows, period=22, multiplier=3.0):
    """chandelier exit: trailing stop from highest high."""
    atr_values = atr(highs, lows, closes, period)
    exits = [None] * len(closes)
    for i in range(period, len(closes)):
        if atr_values[i] is None:
            continue
        highest = max(highs[i - period + 1:i + 1])
        exits[i] = round(highest - multiplier * atr_values[i], 4)
    return exits


def stop_signals(closes, highs, lows, multiplier=3.0):
    """generate stop-hit signals for a long position."""
    stops = trailing_stop_long(closes, highs, lows, multiplier)
    signals = []
    for i in range(len(closes)):
        if stops[i] is not None and closes[i] <= stops[i]:
            signals.append({
                "idx": i, "price": closes[i],
                "stop": stops[i], "type": "stop_hit",
            })
    return signals


if __name__ == "__main__":
    import random
    n = 100
    closes = [100]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + random.gauss(0.001, 0.02)))
    highs = [c * (1 + abs(random.gauss(0, 0.005))) for c in closes]
    lows = [c * (1 - abs(random.gauss(0, 0.005))) for c in closes]
    stops = trailing_stop_long(closes, highs, lows)
    valid = [s for s in stops if s is not None]
    print(f"trailing stop range: {min(valid):.2f} - {max(valid):.2f}")
    sigs = stop_signals(closes, highs, lows)
    print(f"stop hits: {len(sigs)}")
