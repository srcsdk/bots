#!/usr/bin/env python3
"""prototype rsi calculation with wilder smoothing.

testing different smoothing methods to compare accuracy
against reference implementations.
"""


def rsi_simple(prices, period=14):
    """rsi with simple average smoothing.

    less common but simpler to understand.
    """
    if len(prices) < period + 1:
        return [None] * len(prices)

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    result = [None] * period

    for i in range(period, len(deltas) + 1):
        window = deltas[i - period:i]
        gains = [d for d in window if d > 0]
        losses = [abs(d) for d in window if d < 0]

        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - (100 / (1 + rs)), 2))

    return result


def rsi_wilder(prices, period=14):
    """rsi with wilder smoothing (standard method).

    uses recursive smoothing where:
    avg_gain = (prev_avg_gain * (period-1) + current_gain) / period
    """
    if len(prices) < period + 1:
        return [None] * len(prices)

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    result = [None] * period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(round(100 - (100 / (1 + rs)), 2))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - (100 / (1 + rs)), 2))

    return result


def smoothed_rsi(closes, period=14, smooth=3):
    """rsi with additional ema smoothing applied.

    calculates standard wilder rsi then smooths with ema
    to reduce noise and false signals.
    """
    raw = rsi_wilder(closes, period)
    valid = [v for v in raw if v is not None]
    if len(valid) < smooth:
        return raw

    k = 2 / (smooth + 1)
    smoothed = [valid[0]]
    for i in range(1, len(valid)):
        smoothed.append(round(valid[i] * k + smoothed[-1] * (1 - k), 2))

    result = []
    j = 0
    for v in raw:
        if v is None:
            result.append(None)
        else:
            result.append(smoothed[j])
            j += 1
    return result


def compare_methods(prices, period=14):
    """compare simple and wilder rsi outputs"""
    simple = rsi_simple(prices, period)
    wilder = rsi_wilder(prices, period)

    print(f"rsi comparison (period={period}, {len(prices)} prices):")
    print(f"{'idx':>4} {'price':>8} {'simple':>8} {'wilder':>8} {'diff':>8}")

    for i in range(max(0, len(prices) - 10), len(prices)):
        s = f"{simple[i]:.2f}" if simple[i] is not None else "-"
        w = f"{wilder[i]:.2f}" if wilder[i] is not None else "-"
        diff = ""
        if simple[i] is not None and wilder[i] is not None:
            diff = f"{abs(simple[i] - wilder[i]):.2f}"
        print(f"{i:>4} {prices[i]:>8.2f} {s:>8} {w:>8} {diff:>8}")


if __name__ == "__main__":
    # test with sample data
    sample = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10,
              45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28,
              46.28, 46.00, 46.03, 46.41, 46.22, 45.64]
    compare_methods(sample)
