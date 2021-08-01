#!/usr/bin/env python3
"""pairs trading cointegration scanner"""

import math


def ols_regression(x, y):
    """simple ordinary least squares regression. returns (slope, intercept, r_squared)."""
    n = len(x)
    if n < 2 or len(y) != n:
        return 0, 0, 0
    sx = sum(x)
    sy = sum(y)
    sxx = sum(xi ** 2 for xi in x)
    sxy = sum(xi * yi for xi, yi in zip(x, y))
    denom = n * sxx - sx ** 2
    if denom == 0:
        return 0, 0, 0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    y_hat = [slope * xi + intercept for xi in x]
    ss_res = sum((yi - yh) ** 2 for yi, yh in zip(y, y_hat))
    y_mean = sy / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return slope, intercept, r_sq


def spread(prices_a, prices_b, hedge_ratio=None):
    """calculate spread between two price series."""
    if hedge_ratio is None:
        hedge_ratio, _, _ = ols_regression(prices_b, prices_a)
    return [a - hedge_ratio * b for a, b in zip(prices_a, prices_b)]


def adf_statistic(series):
    """simplified augmented dickey-fuller test statistic.

    tests if spread is stationary (mean-reverting).
    more negative = more likely stationary.
    """
    if len(series) < 10:
        return 0.0
    diffs = [series[i] - series[i - 1] for i in range(1, len(series))]
    lagged = series[:-1]
    slope, _, _ = ols_regression(lagged, diffs)
    mean_lag = sum(lagged) / len(lagged)
    var_lag = sum((x - mean_lag) ** 2 for x in lagged) / len(lagged)
    if var_lag == 0:
        return 0.0
    se = math.sqrt(var_lag / len(lagged))
    return slope / se if se > 0 else 0.0


def zscore_spread(sprd, window=20):
    """rolling z-score of the spread for entry/exit signals."""
    result = [None] * len(sprd)
    for i in range(window - 1, len(sprd)):
        subset = sprd[i - window + 1:i + 1]
        mean = sum(subset) / window
        std = math.sqrt(sum((x - mean) ** 2 for x in subset) / window)
        if std > 0:
            result[i] = (sprd[i] - mean) / std
    return result


def scan_pair(prices_a, prices_b, entry_z=2.0, exit_z=0.5):
    """scan a pair for trading signals based on spread z-score."""
    hr, _, r_sq = ols_regression(prices_b, prices_a)
    sprd = spread(prices_a, prices_b, hr)
    adf = adf_statistic(sprd)
    zscores = zscore_spread(sprd)
    signals = []
    for i in range(len(zscores)):
        if zscores[i] is None:
            continue
        if abs(zscores[i]) >= entry_z:
            signals.append({
                "idx": i, "type": "entry",
                "direction": "short_spread" if zscores[i] > 0 else "long_spread",
                "zscore": round(zscores[i], 3),
            })
    return {
        "hedge_ratio": round(hr, 4),
        "r_squared": round(r_sq, 4),
        "adf_stat": round(adf, 4),
        "is_cointegrated": adf < -2.86,
        "signals": signals,
    }


if __name__ == "__main__":
    import random
    base = [100]
    for _ in range(200):
        base.append(base[-1] + random.gauss(0, 1))
    a = [b + random.gauss(0, 0.5) for b in base]
    b_prices = [b * 0.8 + 20 + random.gauss(0, 0.5) for b in base]
    result = scan_pair(a, b_prices)
    print(f"hedge ratio: {result['hedge_ratio']}")
    print(f"r-squared: {result['r_squared']}")
    print(f"adf: {result['adf_stat']} cointegrated: {result['is_cointegrated']}")
    print(f"signals: {len(result['signals'])}")
