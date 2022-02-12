#!/usr/bin/env python3
"""combine and weight multiple strategy signals"""


def weighted_signal(signals, weights):
    """combine strategy signals with weights.

    signals: dict of strategy_name -> score (-1 to 1).
    weights: dict of strategy_name -> weight.
    """
    total_weight = sum(weights.get(s, 1) for s in signals)
    if total_weight == 0:
        return 0.0
    weighted = sum(
        signals[s] * weights.get(s, 1) for s in signals
    )
    return round(weighted / total_weight, 4)


def signal_to_action(score, buy_threshold=0.3, sell_threshold=-0.3):
    """convert numeric score to buy/sell/hold action."""
    if score >= buy_threshold:
        return "buy"
    elif score <= sell_threshold:
        return "sell"
    return "hold"


def strategy_agreement(signals):
    """measure how much strategies agree on direction."""
    if not signals:
        return 0.0
    directions = []
    for score in signals.values():
        if score > 0:
            directions.append(1)
        elif score < 0:
            directions.append(-1)
        else:
            directions.append(0)
    if not directions:
        return 0.0
    majority = max(
        directions.count(1), directions.count(-1), directions.count(0)
    )
    return round(majority / len(directions), 2)


def adaptive_weights(strategy_performance):
    """adjust weights based on recent strategy performance.

    strategy_performance: dict of name -> recent_return_pct.
    """
    if not strategy_performance:
        return {}
    min_perf = min(strategy_performance.values())
    shifted = {
        k: v - min_perf + 1 for k, v in strategy_performance.items()
    }
    total = sum(shifted.values())
    if total == 0:
        return {k: 1.0 for k in strategy_performance}
    return {k: round(v / total * len(shifted), 4) for k, v in shifted.items()}


def combine_with_filter(signals, weights, min_agreement=0.5):
    """only generate signal if enough strategies agree."""
    agreement = strategy_agreement(signals)
    if agreement < min_agreement:
        return {"action": "hold", "score": 0, "agreement": agreement}
    score = weighted_signal(signals, weights)
    return {
        "action": signal_to_action(score),
        "score": score,
        "agreement": agreement,
    }


if __name__ == "__main__":
    signals = {"momentum": 0.7, "mean_rev": -0.3, "breakout": 0.5}
    weights = {"momentum": 1.5, "mean_rev": 1.0, "breakout": 1.2}
    combined = weighted_signal(signals, weights)
    print(f"combined score: {combined}")
    print(f"action: {signal_to_action(combined)}")
    print(f"agreement: {strategy_agreement(signals)}")
