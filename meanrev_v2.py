#!/usr/bin/env python3
"""mean reversion v2 with dynamic lookback and z-score"""

import math


def rolling_mean(data, window):
    """simple rolling mean."""
    result = [None] * len(data)
    for i in range(window - 1, len(data)):
        result[i] = sum(data[i - window + 1:i + 1]) / window
    return result


def rolling_std(data, window):
    """rolling standard deviation."""
    result = [None] * len(data)
    for i in range(window - 1, len(data)):
        subset = data[i - window + 1:i + 1]
        mean = sum(subset) / window
        var = sum((x - mean) ** 2 for x in subset) / window
        result[i] = math.sqrt(var)
    return result


def zscore_series(prices, window=20):
    """calculate rolling z-score of price series."""
    means = rolling_mean(prices, window)
    stds = rolling_std(prices, window)
    zscores = [None] * len(prices)
    for i in range(len(prices)):
        if means[i] is not None and stds[i] is not None and stds[i] > 0:
            zscores[i] = (prices[i] - means[i]) / stds[i]
    return zscores


def adaptive_lookback(prices, min_window=10, max_window=50):
    """determine optimal lookback based on recent volatility regime.

    high volatility -> shorter lookback for faster adaptation.
    low volatility -> longer lookback for stability.
    """
    if len(prices) < max_window:
        return min_window
    recent_std = rolling_std(prices[-max_window:], min_window)
    recent_vol = [s for s in recent_std if s is not None]
    if not recent_vol:
        return min_window
    avg_vol = sum(recent_vol) / len(recent_vol)
    long_std = rolling_std(prices[-max_window:], max_window)
    long_vol = [s for s in long_std if s is not None]
    if not long_vol:
        return min_window
    hist_vol = sum(long_vol) / len(long_vol)
    if hist_vol == 0:
        return min_window
    ratio = avg_vol / hist_vol
    window = int(max_window / max(ratio, 0.5))
    return max(min_window, min(max_window, window))


def scan(prices, entry_z=-2.0, exit_z=0.0, min_window=10, max_window=50):
    """scan for mean reversion entry and exit signals.

    entry when z-score drops below entry_z (oversold).
    exit when z-score returns to exit_z (mean).
    """
    if len(prices) < max_window:
        return []
    window = adaptive_lookback(prices, min_window, max_window)
    zscores = zscore_series(prices, window)
    signals = []
    in_trade = False
    for i in range(len(prices)):
        if zscores[i] is None:
            continue
        if not in_trade and zscores[i] <= entry_z:
            signals.append({
                "idx": i, "type": "entry", "price": prices[i],
                "zscore": round(zscores[i], 3), "lookback": window,
            })
            in_trade = True
        elif in_trade and zscores[i] >= exit_z:
            signals.append({
                "idx": i, "type": "exit", "price": prices[i],
                "zscore": round(zscores[i], 3), "lookback": window,
            })
            in_trade = False
    return signals


if __name__ == "__main__":
    import random
    prices = [100]
    for _ in range(200):
        prices.append(prices[-1] + random.gauss(0, 1.5))
    signals = scan(prices)
    print(f"adaptive lookback: {adaptive_lookback(prices)}")
    print(f"signals found: {len(signals)}")
    for s in signals:
        print(f"  {s['type']} idx={s['idx']} price={s['price']:.2f} z={s['zscore']}")
