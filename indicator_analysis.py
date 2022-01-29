#!/usr/bin/env python3
"""analyze correlation between indicators"""

import math


def correlation(x, y):
    """calculate pearson correlation between two series."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    x, y = x[:n], y[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
    if std_x == 0 or std_y == 0:
        return 0.0
    return round(cov / (std_x * std_y), 4)


def correlation_matrix(indicators):
    """build correlation matrix from dict of indicator series.

    indicators: dict of name -> list of values.
    """
    names = list(indicators.keys())
    matrix = {}
    for i, name_a in enumerate(names):
        matrix[name_a] = {}
        for j, name_b in enumerate(names):
            if i == j:
                matrix[name_a][name_b] = 1.0
            elif j < i:
                matrix[name_a][name_b] = matrix[name_b][name_a]
            else:
                matrix[name_a][name_b] = correlation(
                    indicators[name_a], indicators[name_b]
                )
    return matrix


def find_redundant(matrix, threshold=0.85):
    """find highly correlated indicator pairs (potentially redundant)."""
    pairs = []
    names = list(matrix.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            corr = matrix[names[i]][names[j]]
            if abs(corr) >= threshold:
                pairs.append((names[i], names[j], corr))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    return pairs


def indicator_contribution(signals, returns):
    """measure how much an indicator contributes to returns.

    signals: list of 1 (buy), -1 (sell), 0 (hold).
    returns: list of period returns.
    """
    if len(signals) != len(returns):
        return {}
    active = [(s, r) for s, r in zip(signals, returns) if s != 0]
    if not active:
        return {"contribution": 0, "active_periods": 0}
    correct = sum(1 for s, r in active if (s > 0 and r > 0) or (s < 0 and r < 0))
    avg_return = sum(s * r for s, r in active) / len(active)
    return {
        "accuracy": round(correct / len(active) * 100, 1),
        "avg_return": round(avg_return * 100, 4),
        "active_periods": len(active),
    }


if __name__ == "__main__":
    import random
    indicators = {
        "rsi": [random.uniform(20, 80) for _ in range(100)],
        "macd": [random.gauss(0, 2) for _ in range(100)],
        "sma_20": [100 + random.gauss(0, 5) for _ in range(100)],
    }
    matrix = correlation_matrix(indicators)
    print("correlation matrix:")
    for name, row in matrix.items():
        print(f"  {name}: {row}")
    redundant = find_redundant(matrix)
    print(f"redundant pairs: {redundant}")
