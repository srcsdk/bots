#!/usr/bin/env python3
"""multi-timeframe analysis for trading signals"""


def resample_ohlcv(bars, target_minutes):
    """resample minute bars to larger timeframe."""
    if not bars:
        return []
    resampled = []
    group = []
    for bar in bars:
        group.append(bar)
        if len(group) >= target_minutes:
            resampled.append({
                "date": group[0]["date"],
                "open": group[0]["open"],
                "high": max(b["high"] for b in group),
                "low": min(b["low"] for b in group),
                "close": group[-1]["close"],
                "volume": sum(b.get("volume", 0) for b in group),
            })
            group = []
    return resampled


def multi_tf_trend(prices_short, prices_long):
    """determine trend alignment across timeframes."""
    if not prices_short or not prices_long:
        return "unknown"
    short_trend = "up" if prices_short[-1] > prices_short[0] else "down"
    long_trend = "up" if prices_long[-1] > prices_long[0] else "down"
    if short_trend == long_trend:
        return f"aligned_{short_trend}"
    return "divergent"


def tf_signal_strength(signals_by_tf):
    """calculate signal strength from multiple timeframes.

    signals_by_tf: dict of timeframe -> signal (-1, 0, 1).
    """
    if not signals_by_tf:
        return 0
    weights = {"1m": 0.1, "5m": 0.2, "15m": 0.3, "1h": 0.5,
               "4h": 0.7, "1d": 1.0, "1w": 0.8}
    total_weight = 0
    weighted_sum = 0
    for tf, signal in signals_by_tf.items():
        w = weights.get(tf, 0.5)
        weighted_sum += signal * w
        total_weight += w
    if total_weight == 0:
        return 0
    return round(weighted_sum / total_weight, 4)


def compute_sma(prices, period):
    """simple moving average for last n prices."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def multi_tf_sma_signal(data_by_tf, fast=10, slow=20):
    """generate sma crossover signals across timeframes."""
    signals = {}
    for tf, prices in data_by_tf.items():
        if len(prices) < slow:
            signals[tf] = 0
            continue
        fast_ma = compute_sma(prices, fast)
        slow_ma = compute_sma(prices, slow)
        if fast_ma > slow_ma:
            signals[tf] = 1
        elif fast_ma < slow_ma:
            signals[tf] = -1
        else:
            signals[tf] = 0
    return signals


if __name__ == "__main__":
    import random
    random.seed(42)
    prices = [100]
    for _ in range(200):
        prices.append(prices[-1] * (1 + random.gauss(0.001, 0.01)))
    data = {
        "5m": prices[-50:],
        "15m": prices[-100::2][:50],
        "1h": prices[-200::4][:50],
    }
    signals = multi_tf_sma_signal(data)
    print(f"signals: {signals}")
    strength = tf_signal_strength(signals)
    print(f"combined strength: {strength}")
