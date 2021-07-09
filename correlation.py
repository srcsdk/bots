#!/usr/bin/env python3
"""correlation matrix for multi-ticker analysis"""

import sys
from ohlc import fetch_ohlc


def daily_returns(closes):
    """calculate daily return percentages"""
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        else:
            returns.append(0)
    return returns


def pearson_correlation(x, y):
    """calculate pearson correlation coefficient between two series"""
    n = min(len(x), len(y))
    if n < 2:
        return 0
    x, y = x[:n], y[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
    std_x = (sum((xi - mean_x) ** 2 for xi in x) / n) ** 0.5
    std_y = (sum((yi - mean_y) ** 2 for yi in y) / n) ** 0.5
    if std_x == 0 or std_y == 0:
        return 0
    return round(cov / (std_x * std_y), 4)


def correlation_matrix(tickers, period="1y"):
    """build correlation matrix for a list of tickers.

    returns (matrix, tickers_used) where matrix[i][j] is the
    pearson correlation between tickers_used[i] and tickers_used[j].
    """
    returns_data = {}
    valid_tickers = []

    for ticker in tickers:
        rows = fetch_ohlc(ticker, period)
        if rows and len(rows) > 30:
            closes = [r["close"] for r in rows]
            returns_data[ticker] = daily_returns(closes)
            valid_tickers.append(ticker)

    n = len(valid_tickers)
    matrix = [[0.0] * n for _ in range(n)]

    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            corr = pearson_correlation(
                returns_data[valid_tickers[i]],
                returns_data[valid_tickers[j]]
            )
            matrix[i][j] = corr
            matrix[j][i] = corr

    return matrix, valid_tickers


def find_pairs(matrix, tickers, threshold=0.8):
    """find highly correlated pairs above threshold"""
    pairs = []
    n = len(tickers)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(matrix[i][j]) >= threshold:
                pairs.append((tickers[i], tickers[j], matrix[i][j]))
    pairs.sort(key=lambda p: abs(p[2]), reverse=True)
    return pairs


def find_uncorrelated(matrix, tickers, threshold=0.3):
    """find uncorrelated pairs below threshold for diversification"""
    pairs = []
    n = len(tickers)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(matrix[i][j]) <= threshold:
                pairs.append((tickers[i], tickers[j], matrix[i][j]))
    pairs.sort(key=lambda p: abs(p[2]))
    return pairs


def rolling_correlation_regime(series_a, series_b, window=60):
    """detect correlation regime changes between two return series.

    computes rolling correlation and flags regime shifts where
    correlation moves significantly from its recent average.
    returns list of (index, correlation, regime) tuples
    """
    n = min(len(series_a), len(series_b))
    if n < window:
        return []
    a = series_a[:n]
    b = series_b[:n]
    results = []
    rolling_corrs = []
    for i in range(window - 1, n):
        chunk_a = a[i - window + 1:i + 1]
        chunk_b = b[i - window + 1:i + 1]
        corr = pearson_correlation(chunk_a, chunk_b)
        rolling_corrs.append(corr)

        if len(rolling_corrs) >= 10:
            recent_avg = sum(rolling_corrs[-10:]) / 10
            if corr > recent_avg + 0.2:
                regime = "converging"
            elif corr < recent_avg - 0.2:
                regime = "diverging"
            else:
                regime = "stable"
        else:
            regime = "stable"

        results.append((i, corr, regime))
    return results


def format_matrix(matrix, tickers):
    """format correlation matrix as aligned text"""
    col_width = 8
    header = " " * col_width
    for t in tickers:
        header += f"{t:>{col_width}}"
    lines = [header]
    for i, ticker in enumerate(tickers):
        row = f"{ticker:<{col_width}}"
        for j in range(len(tickers)):
            val = matrix[i][j]
            row += f"{val:>{col_width}.3f}"
        lines.append(row)
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python correlation.py <ticker1> <ticker2> [ticker3] ...")
        print("  example: python correlation.py AAPL MSFT GOOGL AMZN")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]
    period = "1y"

    print(f"building correlation matrix for {', '.join(tickers)}...")
    matrix, valid = correlation_matrix(tickers, period)

    if not valid:
        print("no valid data", file=sys.stderr)
        sys.exit(1)

    print(f"\ncorrelation matrix ({period}):")
    print(format_matrix(matrix, valid))

    correlated = find_pairs(matrix, valid, 0.7)
    if correlated:
        print("\nhighly correlated pairs (>0.7):")
        for t1, t2, corr in correlated:
            print(f"  {t1}-{t2}: {corr:+.3f}")

    diverse = find_uncorrelated(matrix, valid, 0.3)
    if diverse:
        print("\nuncorrelated pairs (<0.3, good for diversification):")
        for t1, t2, corr in diverse[:5]:
            print(f"  {t1}-{t2}: {corr:+.3f}")
