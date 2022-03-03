#!/usr/bin/env python3
"""cross-asset correlation analysis for portfolio diversification"""


def rolling_correlation(series_a, series_b, window=20):
    """calculate rolling correlation between two price series."""
    if len(series_a) != len(series_b):
        return []
    correlations = []
    for i in range(window, len(series_a)):
        a_slice = series_a[i - window:i]
        b_slice = series_b[i - window:i]
        corr = _pearson(a_slice, b_slice)
        correlations.append(round(corr, 4))
    return correlations


def _pearson(x, y):
    """pearson correlation coefficient."""
    n = len(x)
    if n == 0:
        return 0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    std_x = (sum((xi - mean_x) ** 2 for xi in x) / n) ** 0.5
    std_y = (sum((yi - mean_y) ** 2 for yi in y) / n) ** 0.5
    if std_x == 0 or std_y == 0:
        return 0
    return cov / (n * std_x * std_y)


def correlation_matrix(price_dict):
    """build correlation matrix from dict of symbol -> price list."""
    symbols = sorted(price_dict.keys())
    matrix = {}
    for i, sym_a in enumerate(symbols):
        matrix[sym_a] = {}
        for j, sym_b in enumerate(symbols):
            if i == j:
                matrix[sym_a][sym_b] = 1.0
            elif j < i:
                matrix[sym_a][sym_b] = matrix[sym_b][sym_a]
            else:
                corr = _pearson(price_dict[sym_a], price_dict[sym_b])
                matrix[sym_a][sym_b] = round(corr, 4)
    return matrix


def find_low_correlation_pairs(matrix, threshold=0.3):
    """find pairs with correlation below threshold for diversification."""
    pairs = []
    symbols = sorted(matrix.keys())
    for i, a in enumerate(symbols):
        for j in range(i + 1, len(symbols)):
            b = symbols[j]
            if abs(matrix[a][b]) < threshold:
                pairs.append((a, b, matrix[a][b]))
    return sorted(pairs, key=lambda x: abs(x[2]))


if __name__ == "__main__":
    import random
    random.seed(42)
    prices = {
        "AAPL": [100 + random.gauss(0, 5) for _ in range(50)],
        "MSFT": [200 + random.gauss(0, 8) for _ in range(50)],
        "GLD": [150 + random.gauss(0, 3) for _ in range(50)],
    }
    mat = correlation_matrix(prices)
    for sym, row in mat.items():
        print(f"  {sym}: {row}")
    low = find_low_correlation_pairs(mat)
    print(f"low correlation pairs: {low}")
