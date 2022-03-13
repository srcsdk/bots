#!/usr/bin/env python3
"""technical indicator library for strategy development"""

import math


def sma(prices, period):
    """simple moving average."""
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 4)


def ema(prices, period):
    """exponential moving average."""
    if len(prices) < period:
        return None
    multiplier = 2 / (period + 1)
    result = sum(prices[:period]) / period
    for price in prices[period:]:
        result = (price - result) * multiplier + result
    return round(result, 4)


def rsi(prices, period=14):
    """relative strength index."""
    if len(prices) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    if len(gains) < period:
        return None
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def macd(prices, fast=12, slow=26, signal=9):
    """moving average convergence divergence."""
    if len(prices) < slow:
        return None, None, None
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    if fast_ema is None or slow_ema is None:
        return None, None, None
    macd_line = round(fast_ema - slow_ema, 4)
    return macd_line, None, None


def bollinger_bands(prices, period=20, std_dev=2):
    """bollinger bands."""
    if len(prices) < period:
        return None, None, None
    middle = sma(prices, period)
    recent = prices[-period:]
    mean = sum(recent) / period
    variance = sum((p - mean) ** 2 for p in recent) / period
    std = math.sqrt(variance)
    upper = round(middle + std_dev * std, 4)
    lower = round(middle - std_dev * std, 4)
    return upper, middle, lower


def stochastic(highs, lows, closes, period=14):
    """stochastic oscillator %k."""
    if len(closes) < period:
        return None
    highest = max(highs[-period:])
    lowest = min(lows[-period:])
    if highest == lowest:
        return 50
    k = (closes[-1] - lowest) / (highest - lowest) * 100
    return round(k, 2)


def vwap(prices, volumes):
    """volume weighted average price."""
    if not prices or not volumes or len(prices) != len(volumes):
        return None
    total_pv = sum(p * v for p, v in zip(prices, volumes))
    total_v = sum(volumes)
    if total_v == 0:
        return None
    return round(total_pv / total_v, 4)


def atr(highs, lows, closes, period=14):
    """average true range."""
    if len(highs) < period + 1:
        return None
    true_ranges = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)
    if len(true_ranges) < period:
        return None
    return round(sum(true_ranges[-period:]) / period, 4)


if __name__ == "__main__":
    import random
    random.seed(42)
    prices = [100]
    for _ in range(100):
        prices.append(round(prices[-1] * (1 + random.gauss(0, 0.02)), 2))
    print(f"sma(20): {sma(prices, 20)}")
    print(f"ema(20): {ema(prices, 20)}")
    print(f"rsi(14): {rsi(prices)}")
    upper, mid, lower = bollinger_bands(prices)
    print(f"bollinger: {lower} - {mid} - {upper}")
    print(f"macd: {macd(prices)[0]}")
