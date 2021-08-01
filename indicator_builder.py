#!/usr/bin/env python3
"""custom indicator builder with expression parser"""

import re


def sma(data, period):
    """simple moving average."""
    result = [None] * (period - 1)
    for i in range(period - 1, len(data)):
        result.append(sum(data[i - period + 1:i + 1]) / period)
    return result


def ema(data, period):
    """exponential moving average."""
    if not data:
        return []
    mult = 2 / (period + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(data[i] * mult + result[-1] * (1 - mult))
    return result


def roc(data, period):
    """rate of change."""
    result = [None] * period
    for i in range(period, len(data)):
        if data[i - period] != 0:
            result.append((data[i] - data[i - period]) / data[i - period] * 100)
        else:
            result.append(0)
    return result


INDICATORS = {
    "sma": sma,
    "ema": ema,
    "roc": roc,
}


def parse_expression(expr):
    """parse indicator expression like 'sma(close, 20)'.

    returns (function_name, field, period).
    """
    match = re.match(r"(\w+)\((\w+),\s*(\d+)\)", expr.strip())
    if match:
        return match.group(1), match.group(2), int(match.group(3))
    return None, None, None


def build_indicator(expr, data):
    """build custom indicator from expression string.

    data: dict with 'close', 'high', 'low', 'volume' arrays.
    """
    func_name, field, period = parse_expression(expr)
    if func_name not in INDICATORS:
        return None
    series = data.get(field, [])
    if not series:
        return None
    return INDICATORS[func_name](series, period)


def combine_indicators(indicators, weights=None):
    """combine multiple indicator series into composite signal.

    normalizes each to 0-1 range then applies weights.
    """
    if not indicators:
        return []
    n = min(len(ind) for ind in indicators)
    if weights is None:
        weights = [1.0 / len(indicators)] * len(indicators)
    result = []
    for i in range(n):
        vals = [ind[i] for ind in indicators if ind[i] is not None]
        if not vals:
            result.append(None)
            continue
        normalized = []
        for v, ind in zip(vals, indicators):
            valid = [x for x in ind if x is not None]
            if valid:
                lo, hi = min(valid), max(valid)
                if hi > lo:
                    normalized.append((v - lo) / (hi - lo))
                else:
                    normalized.append(0.5)
        weighted = sum(n * w for n, w in zip(normalized, weights))
        result.append(round(weighted, 4))
    return result


if __name__ == "__main__":
    import random
    closes = [100 + random.gauss(0, 5) for _ in range(100)]
    data = {"close": closes}
    sma_20 = build_indicator("sma(close, 20)", data)
    ema_10 = build_indicator("ema(close, 10)", data)
    print(f"sma(20) last: {sma_20[-1]:.2f}" if sma_20 and sma_20[-1] else "n/a")
    print(f"ema(10) last: {ema_10[-1]:.2f}" if ema_10 and ema_10[-1] else "n/a")
    combo = combine_indicators([sma_20, ema_10])
    valid = [c for c in combo if c is not None]
    print(f"composite signal: {valid[-1]:.4f}" if valid else "n/a")
