#!/usr/bin/env python3
"""asset allocation strategies"""


def equal_weight_allocation(symbols, capital):
    """allocate capital equally across symbols."""
    if not symbols:
        return {}
    per_symbol = capital / len(symbols)
    return {s: round(per_symbol, 2) for s in symbols}


def risk_parity(volatilities, capital):
    """allocate based on inverse volatility (risk parity)."""
    if not volatilities:
        return {}
    inv_vols = {}
    for sym, vol in volatilities.items():
        inv_vols[sym] = 1 / vol if vol > 0 else 0
    total_inv = sum(inv_vols.values())
    if total_inv == 0:
        return equal_weight_allocation(list(volatilities.keys()), capital)
    return {
        sym: round(capital * iv / total_inv, 2)
        for sym, iv in inv_vols.items()
    }


def momentum_allocation(returns, capital, top_n=3):
    """allocate to top performing assets by momentum."""
    ranked = sorted(returns.items(), key=lambda x: x[1], reverse=True)
    selected = ranked[:top_n]
    if not selected:
        return {}
    per_symbol = capital / len(selected)
    return {sym: round(per_symbol, 2) for sym, _ in selected}


def max_sharpe_allocation(expected_returns, volatilities, capital):
    """simple sharpe-weighted allocation."""
    sharpe_scores = {}
    for sym in expected_returns:
        vol = volatilities.get(sym, 1)
        if vol > 0:
            sharpe_scores[sym] = expected_returns[sym] / vol
        else:
            sharpe_scores[sym] = 0
    positive = {s: v for s, v in sharpe_scores.items() if v > 0}
    if not positive:
        return equal_weight_allocation(list(expected_returns.keys()), capital)
    total = sum(positive.values())
    return {
        sym: round(capital * score / total, 2)
        for sym, score in positive.items()
    }


def apply_constraints(allocation, min_pct=5, max_pct=40, capital=None):
    """apply min/max allocation constraints."""
    if capital is None:
        capital = sum(allocation.values())
    if capital <= 0:
        return allocation
    constrained = {}
    for sym, amount in allocation.items():
        pct = (amount / capital) * 100
        if pct < min_pct:
            constrained[sym] = round(capital * min_pct / 100, 2)
        elif pct > max_pct:
            constrained[sym] = round(capital * max_pct / 100, 2)
        else:
            constrained[sym] = amount
    return constrained


if __name__ == "__main__":
    symbols = ["AAPL", "MSFT", "GLD", "TLT"]
    capital = 100000
    eq = equal_weight_allocation(symbols, capital)
    print(f"equal weight: {eq}")
    vols = {"AAPL": 25, "MSFT": 22, "GLD": 15, "TLT": 8}
    rp = risk_parity(vols, capital)
    print(f"risk parity: {rp}")
    rets = {"AAPL": 0.15, "MSFT": 0.12, "GLD": 0.05, "TLT": -0.02}
    mom = momentum_allocation(rets, capital, top_n=2)
    print(f"momentum top 2: {mom}")
