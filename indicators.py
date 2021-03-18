"""technical indicators for trading strategies"""


def sma(prices, period):
    """simple moving average"""
    if len(prices) < period:
        return [None] * len(prices)
    result = [None] * (period - 1)
    for i in range(period - 1, len(prices)):
        result.append(sum(prices[i - period + 1:i + 1]) / period)
    return result


def ema(prices, period):
    """exponential moving average"""
    if len(prices) < period:
        return [None] * len(prices)
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    result.append(sum(prices[:period]) / period)
    for i in range(period, len(prices)):
        result.append(prices[i] * k + result[-1] * (1 - k))
    return result


def rsi(prices, period=14):
    """relative strength index"""
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
        result.append(100 - (100 / (1 + rs)))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - (100 / (1 + rs)), 2))

    return result


def macd(prices, fast=12, slow=26, signal=9):
    """macd line, signal line, histogram"""
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)

    macd_line = []
    for f, s in zip(fast_ema, slow_ema):
        if f is not None and s is not None:
            macd_line.append(round(f - s, 4))
        else:
            macd_line.append(None)

    valid = [v for v in macd_line if v is not None]
    signal_line_raw = ema(valid, signal)

    signal_line = []
    j = 0
    for v in macd_line:
        if v is None:
            signal_line.append(None)
        else:
            if j < len(signal_line_raw):
                signal_line.append(signal_line_raw[j])
                j += 1
            else:
                signal_line.append(None)

    histogram = []
    for m, s in zip(macd_line, signal_line):
        if m is not None and s is not None:
            histogram.append(round(m - s, 4))
        else:
            histogram.append(None)

    return macd_line, signal_line, histogram


def bollinger_bands(prices, period=20, std_dev=2):
    """bollinger bands: middle, upper, lower"""
    middle = sma(prices, period)
    upper = []
    lower = []

    for i in range(len(prices)):
        if middle[i] is None:
            upper.append(None)
            lower.append(None)
        else:
            window = prices[max(0, i - period + 1):i + 1]
            mean = sum(window) / len(window)
            variance = sum((x - mean) ** 2 for x in window) / len(window)
            std = variance ** 0.5
            upper.append(round(middle[i] + std_dev * std, 2))
            lower.append(round(middle[i] - std_dev * std, 2))

    return middle, upper, lower


def atr(highs, lows, closes, period=14):
    """average true range"""
    if len(closes) < 2:
        return [None] * len(closes)

    true_ranges = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        true_ranges.append(tr)

    result = [None] * (period - 1)
    result.append(sum(true_ranges[:period]) / period)
    for i in range(period, len(true_ranges)):
        result.append((result[-1] * (period - 1) + true_ranges[i]) / period)

    return result


def fifty_two_week_low(closes, window=252):
    """rolling 52-week low"""
    result = []
    for i in range(len(closes)):
        start = max(0, i - window + 1)
        result.append(min(closes[start:i + 1]))
    return result


def fifty_two_week_high(closes, window=252):
    """rolling 52-week high"""
    result = []
    for i in range(len(closes)):
        start = max(0, i - window + 1)
        result.append(max(closes[start:i + 1]))
    return result


def volume_sma(volumes, period=20):
    """volume simple moving average"""
    return sma(volumes, period)


def gap_percent(opens, prev_closes):
    """gap up/down percentage from previous close"""
    result = [None]
    for i in range(1, len(opens)):
        if prev_closes[i - 1] > 0:
            gap = (opens[i] - prev_closes[i - 1]) / prev_closes[i - 1] * 100
            result.append(round(gap, 2))
        else:
            result.append(None)
    return result
