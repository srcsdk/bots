#!/usr/bin/env python3
"""volatility estimation models for risk assessment"""

import math


def historical_volatility(prices, window=20):
    """annualized historical volatility from price series."""
    if len(prices) < window + 1:
        return 0
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0:
            r = math.log(prices[i] / prices[i - 1])
            returns.append(r)
    if len(returns) < window:
        return 0
    recent = returns[-window:]
    mean = sum(recent) / len(recent)
    variance = sum((r - mean) ** 2 for r in recent) / (len(recent) - 1)
    daily_vol = math.sqrt(variance)
    return round(daily_vol * math.sqrt(252) * 100, 2)


def parkinson_volatility(highs, lows, window=20):
    """parkinson volatility estimator using high-low range."""
    if len(highs) < window or len(lows) < window:
        return 0
    factor = 1 / (4 * window * math.log(2))
    total = 0
    for i in range(-window, 0):
        if lows[i] > 0 and highs[i] > 0:
            total += math.log(highs[i] / lows[i]) ** 2
    return round(math.sqrt(factor * total) * math.sqrt(252) * 100, 2)


def ewma_volatility(prices, decay=0.94):
    """exponentially weighted moving average volatility."""
    if len(prices) < 2:
        return 0
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0:
            returns.append(math.log(prices[i] / prices[i - 1]))
    if not returns:
        return 0
    variance = returns[0] ** 2
    for r in returns[1:]:
        variance = decay * variance + (1 - decay) * r ** 2
    daily_vol = math.sqrt(variance)
    return round(daily_vol * math.sqrt(252) * 100, 2)


def atr(highs, lows, closes, period=14):
    """average true range indicator."""
    if len(highs) < period + 1:
        return 0
    true_ranges = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)
    if len(true_ranges) < period:
        return 0
    current_atr = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        current_atr = (current_atr * (period - 1) + tr) / period
    return round(current_atr, 4)


def vol_regime(volatility, low=15, high=30):
    """classify volatility regime."""
    if volatility < low:
        return "low"
    elif volatility > high:
        return "high"
    return "normal"


if __name__ == "__main__":
    import random
    random.seed(42)
    prices = [100]
    for _ in range(100):
        prices.append(prices[-1] * (1 + random.gauss(0, 0.02)))
    hv = historical_volatility(prices)
    ewma = ewma_volatility(prices)
    regime = vol_regime(hv)
    print(f"historical vol: {hv}%")
    print(f"ewma vol: {ewma}%")
    print(f"regime: {regime}")
