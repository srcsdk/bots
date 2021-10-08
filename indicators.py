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


def sharpe_ratio(returns, risk_free_rate=0.02, periods=252):
    """calculate annualized sharpe ratio from daily returns"""
    if not returns or len(returns) < 2:
        return None
    mean_return = sum(returns) / len(returns)
    daily_rf = risk_free_rate / periods
    excess = [r - daily_rf for r in returns]
    mean_excess = sum(excess) / len(excess)
    variance = sum((r - mean_excess) ** 2 for r in excess) / (len(excess) - 1)
    std = variance ** 0.5
    if std == 0:
        return None
    return round(mean_excess / std * (periods ** 0.5), 4)


def max_drawdown(prices):
    """calculate maximum drawdown from a price series"""
    if not prices or len(prices) < 2:
        return 0
    peak = prices[0]
    max_dd = 0
    for price in prices:
        if price > peak:
            peak = price
        dd = (peak - price) / peak
        if dd > max_dd:
            max_dd = dd
    return round(max_dd * 100, 2)


def vwap(closes, volumes):
    """volume weighted average price"""
    if len(closes) != len(volumes):
        return [None] * len(closes)
    result = []
    cum_vol = 0
    cum_pv = 0
    for i in range(len(closes)):
        cum_vol += volumes[i]
        cum_pv += closes[i] * volumes[i]
        if cum_vol > 0:
            result.append(round(cum_pv / cum_vol, 2))
        else:
            result.append(None)
    return result


def obv(closes, volumes):
    """on-balance volume"""
    if len(closes) < 2:
        return [0] * len(closes)
    result = [0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            result.append(result[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(result[-1] - volumes[i])
        else:
            result.append(result[-1])
    return result


def adl(highs, lows, closes, volumes):
    """accumulation/distribution line"""
    result = [0]
    for i in range(len(closes)):
        hl = highs[i] - lows[i]
        if hl == 0:
            mfv = 0
        else:
            mfm = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
            mfv = mfm * volumes[i]
        if i == 0:
            result[0] = mfv
        else:
            result.append(result[-1] + mfv)
    return result


def stochastic(highs, lows, closes, k_period=14, d_period=3):
    """stochastic oscillator %k and %d.

    %k = (close - lowest low) / (highest high - lowest low) * 100
    %d = sma of %k
    """
    n = len(closes)
    k_values = [None] * (k_period - 1)
    for i in range(k_period - 1, n):
        low_min = min(lows[i - k_period + 1:i + 1])
        high_max = max(highs[i - k_period + 1:i + 1])
        if high_max == low_min:
            k_values.append(50.0)
        else:
            k_values.append(round((closes[i] - low_min) / (high_max - low_min) * 100, 2))

    valid_k = [v for v in k_values if v is not None]
    d_raw = sma(valid_k, d_period)
    d_values = [None] * (k_period - 1)
    d_values.extend(d_raw)

    return k_values, d_values[:n]


def williams_r(highs, lows, closes, period=14):
    """williams %r oscillator.

    similar to stochastic but inverted: -100 to 0 range
    """
    n = len(closes)
    result = [None] * (period - 1)
    for i in range(period - 1, n):
        high_max = max(highs[i - period + 1:i + 1])
        low_min = min(lows[i - period + 1:i + 1])
        if high_max == low_min:
            result.append(-50.0)
        else:
            result.append(round((high_max - closes[i]) / (high_max - low_min) * -100, 2))
    return result


def cci(highs, lows, closes, period=20):
    """commodity channel index"""
    n = len(closes)
    result = [None] * (period - 1)
    for i in range(period - 1, n):
        tp_window = []
        for j in range(i - period + 1, i + 1):
            tp_window.append((highs[j] + lows[j] + closes[j]) / 3)
        mean_tp = sum(tp_window) / len(tp_window)
        mean_dev = sum(abs(tp - mean_tp) for tp in tp_window) / len(tp_window)
        tp_current = tp_window[-1]
        if mean_dev == 0:
            result.append(0)
        else:
            result.append(round((tp_current - mean_tp) / (0.015 * mean_dev), 2))
    return result
