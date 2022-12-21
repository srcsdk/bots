#!/usr/bin/env python3
# improved: proper efficiency ratio edge cases
"""kaufman adaptive moving average (kama)"""


def efficiency_ratio(prices, period=10):
    """calculate kaufman efficiency ratio.

    er = direction / volatility
    high er = trending, low er = choppy.
    """
    if len(prices) < period + 1:
        return []
    er = [None] * period
    for i in range(period, len(prices)):
        direction = abs(prices[i] - prices[i - period])
        volatility = sum(abs(prices[j] - prices[j - 1]) for j in range(i - period + 1, i + 1))
        if volatility == 0:
            er.append(0.0)
        else:
            er.append(direction / volatility)
    return er


def kama(prices, er_period=10, fast_period=2, slow_period=30):
    """calculate kaufman adaptive moving average.

    adapts smoothing constant based on efficiency ratio.
    trending markets -> faster response, choppy -> slower.
    """
    er = efficiency_ratio(prices, er_period)
    fast_sc = 2 / (fast_period + 1)
    slow_sc = 2 / (slow_period + 1)
    result = [None] * er_period
    result.append(prices[er_period])
    for i in range(er_period + 1, len(prices)):
        if er[i] is None:
            result.append(result[-1])
            continue
        sc = (er[i] * (fast_sc - slow_sc) + slow_sc) ** 2
        prev = result[-1]
        result.append(prev + sc * (prices[i] - prev))
    return result


def kama_signal(prices, er_period=10):
    """generate buy/sell signals from kama crossover.

    buy when price crosses above kama, sell when below.
    """
    k = kama(prices, er_period)
    signals = []
    above = None
    for i in range(len(prices)):
        if k[i] is None:
            continue
        currently_above = prices[i] > k[i]
        if above is not None and currently_above != above:
            signals.append({
                "idx": i,
                "type": "buy" if currently_above else "sell",
                "price": prices[i],
                "kama": round(k[i], 4),
                "er": round(efficiency_ratio(prices, er_period)[i] or 0, 4),
            })
        above = currently_above
    return signals


if __name__ == "__main__":
    import random
    prices = [100]
    for _ in range(200):
        prices.append(prices[-1] * (1 + random.gauss(0.0002, 0.015)))
    er = efficiency_ratio(prices)
    valid_er = [e for e in er if e is not None]
    print(f"avg efficiency ratio: {sum(valid_er)/len(valid_er):.4f}")
    signals = kama_signal(prices)
    print(f"signals: {len(signals)}")
    for s in signals[:5]:
        print(f"  {s['type']} idx={s['idx']} price={s['price']:.2f} er={s['er']:.4f}")
