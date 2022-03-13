#!/usr/bin/env python3
"""market scanner for finding trading opportunities"""


def scan_momentum(symbols_data, period=14, threshold=5.0):
    """scan for momentum breakout candidates."""
    results = []
    for symbol, prices in symbols_data.items():
        if len(prices) < period + 1:
            continue
        roc = (prices[-1] - prices[-period]) / prices[-period] * 100
        if abs(roc) >= threshold:
            results.append({
                "symbol": symbol,
                "roc": round(roc, 2),
                "direction": "bullish" if roc > 0 else "bearish",
                "price": prices[-1],
            })
    results.sort(key=lambda x: abs(x["roc"]), reverse=True)
    return results


def scan_volume_spike(symbols_data, threshold=2.0):
    """scan for unusual volume activity."""
    results = []
    for symbol, bars in symbols_data.items():
        if len(bars) < 21:
            continue
        volumes = [b.get("volume", 0) for b in bars[-21:]]
        avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
        if avg_vol > 0:
            ratio = volumes[-1] / avg_vol
            if ratio >= threshold:
                results.append({
                    "symbol": symbol,
                    "volume_ratio": round(ratio, 2),
                    "volume": volumes[-1],
                    "avg_volume": round(avg_vol),
                })
    results.sort(key=lambda x: x["volume_ratio"], reverse=True)
    return results


def scan_ma_crossover(symbols_data, fast=10, slow=20):
    """scan for moving average crossover signals."""
    results = []
    for symbol, prices in symbols_data.items():
        if len(prices) < slow + 1:
            continue
        fast_ma_now = sum(prices[-fast:]) / fast
        fast_ma_prev = sum(prices[-fast - 1:-1]) / fast
        slow_ma_now = sum(prices[-slow:]) / slow
        slow_ma_prev = sum(prices[-slow - 1:-1]) / slow
        if fast_ma_prev <= slow_ma_prev and fast_ma_now > slow_ma_now:
            results.append({
                "symbol": symbol,
                "signal": "golden_cross",
                "price": prices[-1],
            })
        elif fast_ma_prev >= slow_ma_prev and fast_ma_now < slow_ma_now:
            results.append({
                "symbol": symbol,
                "signal": "death_cross",
                "price": prices[-1],
            })
    return results


def scan_support_resistance(prices, window=20, tolerance=0.02):
    """find support and resistance levels."""
    if len(prices) < window:
        return {"support": [], "resistance": []}
    levels = {"support": [], "resistance": []}
    for i in range(window, len(prices) - window):
        is_low = all(
            prices[i] <= prices[i + j] for j in range(-window, window + 1)
            if j != 0 and 0 <= i + j < len(prices)
        )
        is_high = all(
            prices[i] >= prices[i + j] for j in range(-window, window + 1)
            if j != 0 and 0 <= i + j < len(prices)
        )
        if is_low:
            levels["support"].append(round(prices[i], 2))
        if is_high:
            levels["resistance"].append(round(prices[i], 2))
    return levels


if __name__ == "__main__":
    import random
    random.seed(42)
    data = {}
    for sym in ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA"]:
        price = 100 + random.uniform(-20, 80)
        data[sym] = [price]
        for _ in range(30):
            price *= (1 + random.gauss(0.002, 0.02))
            data[sym].append(round(price, 2))
    momentum = scan_momentum(data)
    print("momentum signals:")
    for r in momentum[:3]:
        print(f"  {r['symbol']}: {r['roc']}% ({r['direction']})")
    crosses = scan_ma_crossover(data)
    print(f"ma crossovers: {len(crosses)}")
