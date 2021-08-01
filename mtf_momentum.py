#!/usr/bin/env python3
"""multi-timeframe momentum confluence scanner"""


def resample_to_weekly(daily_prices):
    """resample daily prices to weekly (every 5 bars)."""
    return [daily_prices[i] for i in range(0, len(daily_prices), 5)]


def resample_to_monthly(daily_prices):
    """resample daily prices to monthly (every 21 bars)."""
    return [daily_prices[i] for i in range(0, len(daily_prices), 21)]


def momentum(prices, period):
    """price momentum: current / price n periods ago - 1."""
    if len(prices) <= period:
        return []
    return [None] * period + [
        (prices[i] - prices[i - period]) / prices[i - period]
        for i in range(period, len(prices))
    ]


def ema(prices, period):
    """exponential moving average."""
    if not prices:
        return []
    mult = 2 / (period + 1)
    result = [prices[0]]
    for i in range(1, len(prices)):
        result.append(prices[i] * mult + result[-1] * (1 - mult))
    return result


def trend_direction(prices, period=20):
    """determine trend direction: 1=up, -1=down, 0=neutral."""
    e = ema(prices, period)
    if len(e) < 2:
        return 0
    if prices[-1] > e[-1] and e[-1] > e[-2]:
        return 1
    elif prices[-1] < e[-1] and e[-1] < e[-2]:
        return -1
    return 0


def confluence_score(daily_prices):
    """score momentum confluence across daily, weekly, monthly timeframes.

    range: -3 (all bearish) to +3 (all bullish).
    """
    if len(daily_prices) < 63:
        return 0, {}
    daily_trend = trend_direction(daily_prices, 10)
    weekly = resample_to_weekly(daily_prices)
    weekly_trend = trend_direction(weekly, 10) if len(weekly) > 10 else 0
    monthly = resample_to_monthly(daily_prices)
    monthly_trend = trend_direction(monthly, 5) if len(monthly) > 5 else 0
    score = daily_trend + weekly_trend + monthly_trend
    details = {
        "daily": daily_trend,
        "weekly": weekly_trend,
        "monthly": monthly_trend,
        "score": score,
        "aligned": abs(score) == 3,
    }
    return score, details


def scan_momentum(prices, threshold=2):
    """scan for periods where momentum aligns across timeframes."""
    signals = []
    for i in range(63, len(prices)):
        score, details = confluence_score(prices[:i + 1])
        if abs(score) >= threshold:
            signals.append({
                "idx": i, "price": prices[i],
                "score": score,
                "direction": "bullish" if score > 0 else "bearish",
                **details,
            })
    return signals


if __name__ == "__main__":
    import random
    prices = [100]
    for _ in range(252):
        prices.append(prices[-1] * (1 + random.gauss(0.0005, 0.015)))
    score, details = confluence_score(prices)
    print(f"confluence score: {score}")
    for k, v in details.items():
        print(f"  {k}: {v}")
