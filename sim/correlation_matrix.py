#!/usr/bin/env python3
"""build correlation matrices between strategies and indicators"""

import statistics


def correlation(series_a, series_b):
    """pearson correlation between two series."""
    n = min(len(series_a), len(series_b))
    if n < 3:
        return 0
    a = series_a[:n]
    b = series_b[:n]
    mean_a = statistics.mean(a)
    mean_b = statistics.mean(b)
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((x - mean_b) ** 2 for x in b)
    denom = (var_a * var_b) ** 0.5
    if denom == 0:
        return 0
    return round(cov / denom, 4)


def build_matrix(strategy_returns):
    """build correlation matrix from dict of strategy returns."""
    names = sorted(strategy_returns.keys())
    matrix = {}
    for name_a in names:
        matrix[name_a] = {}
        for name_b in names:
            matrix[name_a][name_b] = correlation(
                strategy_returns[name_a],
                strategy_returns[name_b],
            )
    return matrix


def find_uncorrelated(matrix, threshold=0.3):
    """find strategy pairs with low correlation."""
    pairs = []
    names = sorted(matrix.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            corr = abs(matrix[names[i]][names[j]])
            if corr < threshold:
                pairs.append({
                    "pair": (names[i], names[j]),
                    "correlation": matrix[names[i]][names[j]],
                })
    pairs.sort(key=lambda p: abs(p["correlation"]))
    return pairs


def find_redundant(matrix, threshold=0.8):
    """find strategy pairs that are too correlated."""
    pairs = []
    names = sorted(matrix.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            corr = abs(matrix[names[i]][names[j]])
            if corr > threshold:
                pairs.append({
                    "pair": (names[i], names[j]),
                    "correlation": matrix[names[i]][names[j]],
                })
    pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)
    return pairs


def portfolio_diversity_score(matrix):
    """score how diverse a portfolio of strategies is."""
    names = sorted(matrix.keys())
    if len(names) < 2:
        return 1.0
    total_corr = 0
    count = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            total_corr += abs(matrix[names[i]][names[j]])
            count += 1
    avg_corr = total_corr / count if count > 0 else 0
    return round(1 - avg_corr, 4)


if __name__ == "__main__":
    returns = {
        "rsi": [0.01, -0.02, 0.03, -0.01, 0.02],
        "macd": [0.02, -0.01, 0.02, -0.02, 0.01],
        "momentum": [-0.01, 0.03, -0.02, 0.04, -0.01],
    }
    matrix = build_matrix(returns)
    for name in sorted(matrix.keys()):
        vals = [f"{v:6.3f}" for v in matrix[name].values()]
        print(f"  {name:10s}: {' '.join(vals)}")
    score = portfolio_diversity_score(matrix)
    print(f"\ndiversity score: {score}")
