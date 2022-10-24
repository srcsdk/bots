#!/usr/bin/env python3
"""shared indicator utilities with proper edge case handling"""


def safe_divide(numerator, denominator, default=0.0):
    """divide with zero and none protection."""
    if denominator is None or denominator == 0:
        return default
    if numerator is None:
        return default
    return numerator / denominator


def rolling_window(data, window):
    """generate rolling windows from data list.

    yields (index, window_slice) tuples.
    handles none values by skipping them.
    """
    if not data or window <= 0 or window > len(data):
        return
    for i in range(window - 1, len(data)):
        segment = data[i - window + 1:i + 1]
        valid = [x for x in segment if x is not None]
        if len(valid) == window:
            yield i, segment


def ema(values, period):
    """exponential moving average with none padding."""
    if not values or period <= 0:
        return [None] * len(values)
    result = [None] * len(values)
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(valid) < period:
        return result
    first_vals = [v for _, v in valid[:period]]
    sma_val = sum(first_vals) / period
    idx = valid[period - 1][0]
    result[idx] = sma_val
    multiplier = 2 / (period + 1)
    prev = sma_val
    for i in range(period, len(valid)):
        idx = valid[i][0]
        val = valid[i][1]
        ema_val = (val - prev) * multiplier + prev
        result[idx] = round(ema_val, 6)
        prev = ema_val
    return result


def true_range(high, low, prev_close):
    """calculate true range for a single bar."""
    if any(v is None for v in (high, low, prev_close)):
        return None
    return max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close),
    )


def atr(highs, lows, closes, period=14):
    """average true range with proper none handling."""
    n = len(highs)
    if n < 2 or n != len(lows) or n != len(closes):
        return [None] * n
    tr_vals = [None]
    for i in range(1, n):
        tr_vals.append(true_range(highs[i], lows[i], closes[i - 1]))
    return ema(tr_vals, period)


def crossover(fast, slow):
    """detect crossover points between two indicator series.

    returns list of (index, direction) where direction is 1 for
    fast crossing above slow, -1 for crossing below.
    """
    if len(fast) != len(slow) or len(fast) < 2:
        return []
    crosses = []
    for i in range(1, len(fast)):
        if any(v is None for v in (fast[i], fast[i-1], slow[i], slow[i-1])):
            continue
        prev_diff = fast[i-1] - slow[i-1]
        curr_diff = fast[i] - slow[i]
        if prev_diff <= 0 and curr_diff > 0:
            crosses.append((i, 1))
        elif prev_diff >= 0 and curr_diff < 0:
            crosses.append((i, -1))
    return crosses


if __name__ == "__main__":
    data = [10, 11, 12, 11, 13, 14, 13, 15, 16, 14]
    result = ema(data, 3)
    print(f"ema(3): {[round(x, 2) if x else None for x in result]}")
    fast = [1, 2, 3, 4, 5]
    slow = [2, 2, 2, 3, 4]
    print(f"crossovers: {crossover(fast, slow)}")
