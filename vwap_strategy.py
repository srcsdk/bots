#!/usr/bin/env python3
"""vwap deviation strategy with session anchoring"""


def vwap(prices, volumes):
    """calculate volume-weighted average price."""
    if not prices or not volumes or len(prices) != len(volumes):
        return []
    cum_pv = 0
    cum_vol = 0
    result = []
    for p, v in zip(prices, volumes):
        cum_pv += p * v
        cum_vol += v
        result.append(cum_pv / cum_vol if cum_vol > 0 else p)
    return result


def vwap_bands(prices, volumes, num_std=2):
    """calculate vwap with standard deviation bands."""
    vw = vwap(prices, volumes)
    if not vw:
        return [], [], []
    cum_vol = 0
    cum_pv2 = 0
    upper = []
    lower = []
    for i, (p, v) in enumerate(zip(prices, volumes)):
        cum_pv2 += p * p * v
        cum_vol += v
        if cum_vol > 0:
            var = cum_pv2 / cum_vol - vw[i] ** 2
            std = var ** 0.5 if var > 0 else 0
            upper.append(vw[i] + num_std * std)
            lower.append(vw[i] - num_std * std)
        else:
            upper.append(vw[i])
            lower.append(vw[i])
    return vw, upper, lower


def scan(prices, volumes, entry_std=2.0, exit_std=0.5):
    """scan for vwap mean reversion signals.

    enter when price deviates beyond entry_std from vwap.
    exit when price returns within exit_std of vwap.
    """
    vw, upper, lower = vwap_bands(prices, volumes, entry_std)
    _, exit_upper, exit_lower = vwap_bands(prices, volumes, exit_std)
    if not vw:
        return []
    signals = []
    position = None
    for i in range(1, len(prices)):
        if position is None:
            if prices[i] <= lower[i]:
                signals.append({
                    "idx": i, "type": "long_entry", "price": prices[i],
                    "vwap": round(vw[i], 2), "dev": round(prices[i] - vw[i], 2),
                })
                position = "long"
            elif prices[i] >= upper[i]:
                signals.append({
                    "idx": i, "type": "short_entry", "price": prices[i],
                    "vwap": round(vw[i], 2), "dev": round(prices[i] - vw[i], 2),
                })
                position = "short"
        elif position == "long" and prices[i] >= exit_lower[i]:
            signals.append({"idx": i, "type": "long_exit", "price": prices[i]})
            position = None
        elif position == "short" and prices[i] <= exit_upper[i]:
            signals.append({"idx": i, "type": "short_exit", "price": prices[i]})
            position = None
    return signals


if __name__ == "__main__":
    import random
    prices = [100 + random.gauss(0, 2) for _ in range(200)]
    volumes = [random.randint(100, 10000) for _ in range(200)]
    signals = scan(prices, volumes)
    print(f"vwap signals: {len(signals)}")
    for s in signals[:10]:
        print(f"  {s['type']} idx={s['idx']} ${s['price']:.2f}")
