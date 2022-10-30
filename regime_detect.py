#!/usr/bin/env python3
"""detect market regime using volatility and trend analysis"""

import math


def classify_regime(closes, window=20):
    """classify current market regime.

    returns regime dict with type, volatility, and trend direction.
    regimes: trending_up, trending_down, mean_reverting, high_volatility.
    """
    if len(closes) < window * 2:
        return {"regime": "unknown", "confidence": 0}

    recent = closes[-window:]
    prior = closes[-window * 2:-window]

    recent_ret = [(recent[i] - recent[i-1]) / recent[i-1]
                  for i in range(1, len(recent))]
    prior_ret = [(prior[i] - prior[i-1]) / prior[i-1]
                 for i in range(1, len(prior))]

    recent_vol = _std(recent_ret)
    prior_vol = _std(prior_ret)
    vol_ratio = recent_vol / prior_vol if prior_vol > 0 else 1.0

    trend = (closes[-1] - closes[-window]) / closes[-window]

    if vol_ratio > 1.5:
        regime = "high_volatility"
        confidence = min(vol_ratio / 2, 1.0)
    elif abs(trend) > 0.05:
        regime = "trending_up" if trend > 0 else "trending_down"
        confidence = min(abs(trend) * 5, 1.0)
    else:
        regime = "mean_reverting"
        auto_corr = _autocorrelation(recent_ret)
        confidence = max(0, -auto_corr)

    return {
        "regime": regime,
        "confidence": round(confidence, 4),
        "volatility": round(recent_vol * math.sqrt(252) * 100, 2),
        "trend_pct": round(trend * 100, 2),
        "vol_ratio": round(vol_ratio, 4),
    }


def _std(values):
    """calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _autocorrelation(values, lag=1):
    """calculate autocorrelation at given lag."""
    n = len(values)
    if n < lag + 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    if variance == 0:
        return 0.0
    cov = sum(
        (values[i] - mean) * (values[i - lag] - mean)
        for i in range(lag, n)
    ) / n
    return cov / variance


def suggest_strategy(regime_info):
    """suggest strategy type based on current regime."""
    regime = regime_info.get("regime", "unknown")
    suggestions = {
        "trending_up": ["momentum", "trend_following", "breakout"],
        "trending_down": ["short_momentum", "protective_puts"],
        "mean_reverting": ["mean_reversion", "pairs", "rsi_revert"],
        "high_volatility": ["options_selling", "iron_condor", "straddle"],
        "unknown": ["equal_weight", "conservative"],
    }
    return suggestions.get(regime, ["conservative"])


if __name__ == "__main__":
    import random
    random.seed(42)
    prices = [100]
    for _ in range(100):
        prices.append(prices[-1] * (1 + random.gauss(0.001, 0.015)))
    regime = classify_regime(prices)
    print(f"regime: {regime['regime']} ({regime['confidence']:.2f})")
    print(f"volatility: {regime['volatility']:.1f}%")
    print(f"suggested: {suggest_strategy(regime)}")
