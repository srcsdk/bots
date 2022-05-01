#!/usr/bin/env python3
"""market regime detection for adaptive strategy selection"""

import math


def sma(prices, period):
    """simple moving average."""
    if len(prices) < period:
        return 0
    return sum(prices[-period:]) / period


def detect_trend(prices, short=20, long=50):
    """detect trend using moving average crossover."""
    if len(prices) < long:
        return "unknown"
    short_ma = sma(prices, short)
    long_ma = sma(prices, long)
    if short_ma > long_ma * 1.02:
        return "uptrend"
    elif short_ma < long_ma * 0.98:
        return "downtrend"
    return "sideways"


def detect_volatility_regime(prices, window=20, low=10, high=25):
    """classify volatility regime from price series."""
    if len(prices) < window + 1:
        return "unknown"
    returns = []
    for i in range(len(prices) - window, len(prices)):
        if prices[i - 1] > 0:
            returns.append(math.log(prices[i] / prices[i - 1]))
    if not returns:
        return "unknown"
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / len(returns)
    vol = math.sqrt(var) * math.sqrt(252) * 100
    if vol < low:
        return "low_vol"
    elif vol > high:
        return "high_vol"
    return "normal_vol"


def detect_momentum(prices, period=14):
    """detect momentum using rate of change."""
    if len(prices) < period + 1:
        return "unknown"
    roc = (prices[-1] - prices[-period - 1]) / prices[-period - 1]
    if roc > 0.05:
        return "strong_bullish"
    elif roc > 0.01:
        return "bullish"
    elif roc < -0.05:
        return "strong_bearish"
    elif roc < -0.01:
        return "bearish"
    return "neutral"


def regime_summary(prices):
    """comprehensive regime analysis."""
    return {
        "trend": detect_trend(prices),
        "volatility": detect_volatility_regime(prices),
        "momentum": detect_momentum(prices),
    }


def strategy_for_regime(regime):
    """suggest strategy parameters based on market regime."""
    suggestions = {
        "uptrend": {
            "bias": "long", "position_size": 1.0, "stop_distance": 0.03,
        },
        "downtrend": {
            "bias": "short", "position_size": 0.5, "stop_distance": 0.02,
        },
        "sideways": {
            "bias": "neutral", "position_size": 0.3, "stop_distance": 0.015,
        },
    }
    trend = regime.get("trend", "sideways")
    params = suggestions.get(trend, suggestions["sideways"])
    if regime.get("volatility") == "high_vol":
        params["position_size"] *= 0.5
        params["stop_distance"] *= 1.5
    return params


if __name__ == "__main__":
    import random
    random.seed(42)
    prices = [100]
    for _ in range(100):
        prices.append(prices[-1] * (1 + random.gauss(0.001, 0.015)))
    regime = regime_summary(prices)
    print(f"regime: {regime}")
    params = strategy_for_regime(regime)
    print(f"suggested params: {params}")
