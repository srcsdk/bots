#!/usr/bin/env python3
"""scaffold for indicator calculations on ohlc data.

this module will be expanded into a full indicator library.
starting with basic moving averages as building blocks.
"""


def simple_moving_average(values, period):
    """calculate simple moving average.

    returns list same length as input, with none for
    positions where not enough data exists.
    """
    if len(values) < period:
        return [None] * len(values)

    result = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        result.append(sum(window) / period)
    return result


def exponential_moving_average(values, period):
    """calculate exponential moving average.

    uses standard multiplier: 2 / (period + 1).
    seed value is sma of first period values.
    """
    if len(values) < period:
        return [None] * len(values)

    k = 2 / (period + 1)
    result = [None] * (period - 1)

    # seed with sma
    seed = sum(values[:period]) / period
    result.append(seed)

    for i in range(period, len(values)):
        ema_val = values[i] * k + result[-1] * (1 - k)
        result.append(ema_val)

    return result


def price_change(values):
    """calculate period-over-period price changes"""
    if len(values) < 2:
        return [None]

    changes = [None]
    for i in range(1, len(values)):
        changes.append(values[i] - values[i - 1])
    return changes


def percent_change(values):
    """calculate period-over-period percent changes"""
    if len(values) < 2:
        return [None]

    changes = [None]
    for i in range(1, len(values)):
        if values[i - 1] != 0:
            pct = (values[i] - values[i - 1]) / values[i - 1] * 100
            changes.append(round(pct, 4))
        else:
            changes.append(None)
    return changes
