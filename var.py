#!/usr/bin/env python3
"""portfolio risk: value at risk (var) and conditional var (cvar)"""

import sys
from ohlc import fetch_ohlc
from correlation import daily_returns


def historical_var(returns, confidence=0.95):
    """calculate historical value at risk.

    returns the loss threshold at the given confidence level.
    e.g. 95% VaR = we expect losses to exceed this 5% of the time.
    """
    if not returns:
        return 0
    sorted_returns = sorted(returns)
    idx = int(len(sorted_returns) * (1 - confidence))
    idx = max(0, min(idx, len(sorted_returns) - 1))
    return round(sorted_returns[idx] * 100, 4)


def historical_cvar(returns, confidence=0.95):
    """calculate conditional value at risk (expected shortfall).

    average of losses beyond the var threshold.
    """
    if not returns:
        return 0
    sorted_returns = sorted(returns)
    cutoff = int(len(sorted_returns) * (1 - confidence))
    cutoff = max(1, cutoff)
    tail = sorted_returns[:cutoff]
    return round(sum(tail) / len(tail) * 100, 4)


def parametric_var(returns, confidence=0.95):
    """calculate parametric (gaussian) var assuming normal distribution"""
    if len(returns) < 2:
        return 0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = variance ** 0.5
    z_scores = {0.90: 1.2816, 0.95: 1.6449, 0.99: 2.3263}
    z = z_scores.get(confidence, 1.6449)
    var = mean - z * std
    return round(var * 100, 4)


def portfolio_var(tickers, weights, period="1y", confidence=0.95):
    """calculate portfolio var using historical simulation.

    tickers: list of ticker symbols
    weights: list of portfolio weights (should sum to 1.0)
    """
    all_returns = []
    valid = []
    for ticker in tickers:
        rows = fetch_ohlc(ticker, period)
        if rows and len(rows) > 30:
            closes = [r["close"] for r in rows]
            all_returns.append(daily_returns(closes))
            valid.append(ticker)

    if not all_returns:
        return None

    min_len = min(len(r) for r in all_returns)
    portfolio_returns = []
    for i in range(min_len):
        daily = sum(
            all_returns[j][i] * weights[j]
            for j in range(len(valid))
        )
        portfolio_returns.append(daily)

    return {
        "tickers": valid,
        "weights": weights[:len(valid)],
        "var_95": historical_var(portfolio_returns, 0.95),
        "var_99": historical_var(portfolio_returns, 0.99),
        "cvar_95": historical_cvar(portfolio_returns, 0.95),
        "cvar_99": historical_cvar(portfolio_returns, 0.99),
        "parametric_var_95": parametric_var(portfolio_returns, 0.95),
        "observations": len(portfolio_returns),
    }


def stress_test(returns, scenarios=None):
    """run stress scenarios on return series.

    scenarios: dict of {name: multiplier} where multiplier
    simulates a market shock (e.g. 2.0 = double the worst days)
    """
    if scenarios is None:
        scenarios = {
            "normal": 1.0,
            "moderate_stress": 1.5,
            "severe_stress": 2.0,
            "crisis": 3.0,
        }

    results = {}
    for name, mult in scenarios.items():
        stressed = [r * mult for r in returns]
        results[name] = {
            "var_95": historical_var(stressed, 0.95),
            "cvar_95": historical_cvar(stressed, 0.95),
            "max_loss": round(min(stressed) * 100, 2),
        }
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python var.py <ticker1> [ticker2] ...")
        print("  calculates portfolio risk metrics")
        print("  equal weight assumed for multiple tickers")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]
    n = len(tickers)
    weights = [1.0 / n] * n

    print(f"calculating risk metrics for {', '.join(tickers)}...")
    result = portfolio_var(tickers, weights)

    if result is None:
        print("insufficient data")
        sys.exit(1)

    print(f"\nportfolio risk ({result['observations']} observations):")
    print(f"  var 95%:  {result['var_95']:+.4f}%")
    print(f"  var 99%:  {result['var_99']:+.4f}%")
    print(f"  cvar 95%: {result['cvar_95']:+.4f}%")
    print(f"  cvar 99%: {result['cvar_99']:+.4f}%")
    print(f"  p-var 95%: {result['parametric_var_95']:+.4f}% (gaussian)")

    returns_all = []
    for ticker in tickers:
        rows = fetch_ohlc(ticker, "1y")
        if rows:
            returns_all.extend(daily_returns([r["close"] for r in rows]))

    if returns_all:
        print("\nstress test:")
        stress = stress_test(returns_all)
        for name, vals in stress.items():
            print(f"  {name:<18} var={vals['var_95']:+.4f}%  "
                  f"cvar={vals['cvar_95']:+.4f}%  max={vals['max_loss']:+.2f}%")
