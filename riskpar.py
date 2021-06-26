#!/usr/bin/env python3
"""risk parity allocation: weight assets inversely proportional to risk contribution.

calculates rolling volatility and correlation matrix, then finds weights
where each asset contributes equally to total portfolio risk. uses iterative
optimization since the analytical solution requires matrix operations.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sharpe_ratio


def daily_returns(closes):
    """calculate daily returns from close prices"""
    return [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]


def rolling_volatility(returns, window=60):
    """annualized rolling volatility"""
    result = [None] * (window - 1)
    for i in range(window - 1, len(returns)):
        window_rets = returns[i - window + 1:i + 1]
        mean = sum(window_rets) / len(window_rets)
        variance = sum((r - mean) ** 2 for r in window_rets) / (len(window_rets) - 1)
        annual_vol = (variance ** 0.5) * (252 ** 0.5)
        result.append(round(annual_vol, 4))
    return result


def correlation(returns_a, returns_b, window=60):
    """rolling correlation between two return series"""
    n = min(len(returns_a), len(returns_b))
    result = [None] * (window - 1)

    for i in range(window - 1, n):
        ra = returns_a[i - window + 1:i + 1]
        rb = returns_b[i - window + 1:i + 1]
        mean_a = sum(ra) / len(ra)
        mean_b = sum(rb) / len(rb)

        cov = sum((ra[j] - mean_a) * (rb[j] - mean_b) for j in range(len(ra))) / (len(ra) - 1)
        var_a = sum((x - mean_a) ** 2 for x in ra) / (len(ra) - 1)
        var_b = sum((x - mean_b) ** 2 for x in rb) / (len(rb) - 1)

        denom = (var_a ** 0.5) * (var_b ** 0.5)
        if denom == 0:
            result.append(0)
        else:
            result.append(round(cov / denom, 4))

    return result


def inverse_vol_weights(volatilities):
    """calculate inverse volatility weights"""
    inv_vols = [1.0 / v if v > 0 else 0 for v in volatilities]
    total = sum(inv_vols)
    if total == 0:
        n = len(volatilities)
        return [round(1.0 / n, 4)] * n
    return [round(iv / total, 4) for iv in inv_vols]


def risk_contribution(weights, volatilities, corr_matrix):
    """calculate each asset's marginal risk contribution to portfolio"""
    n = len(weights)
    port_var = 0
    for i in range(n):
        for j in range(n):
            port_var += weights[i] * weights[j] * volatilities[i] * volatilities[j] * corr_matrix[i][j]

    port_vol = port_var ** 0.5 if port_var > 0 else 0.0001
    contributions = []
    for i in range(n):
        marginal = 0
        for j in range(n):
            marginal += weights[j] * volatilities[i] * volatilities[j] * corr_matrix[i][j]
        rc = weights[i] * marginal / port_vol
        contributions.append(round(rc, 6))

    return contributions, round(port_vol, 4)


def optimize_risk_parity(volatilities, corr_matrix, iterations=100):
    """iterative risk parity optimization.

    starts with inverse volatility weights and adjusts until risk contributions
    are approximately equal.
    """
    n = len(volatilities)
    weights = inverse_vol_weights(volatilities)

    for _ in range(iterations):
        contribs, port_vol = risk_contribution(weights, volatilities, corr_matrix)
        target_rc = port_vol / n

        total_contribs = sum(contribs)
        if total_contribs == 0:
            break

        new_weights = []
        for i in range(n):
            if contribs[i] > 0:
                adjustment = target_rc / contribs[i]
                new_weights.append(weights[i] * (adjustment ** 0.5))
            else:
                new_weights.append(weights[i])

        total = sum(new_weights)
        weights = [round(w / total, 4) for w in new_weights]

    return weights


def analyze(tickers, period="1y", vol_window=60):
    """calculate risk parity weights for a set of tickers"""
    all_data = {}
    all_returns = {}

    for t in tickers:
        rows = fetch_ohlc(t, period)
        if not rows or len(rows) < vol_window + 10:
            print(f"  skipping {t}: insufficient data", file=sys.stderr)
            continue
        closes = [r["close"] for r in rows]
        rets = daily_returns(closes)
        all_data[t] = {"closes": closes, "rows": rows}
        all_returns[t] = rets

    valid_tickers = list(all_returns.keys())
    if len(valid_tickers) < 2:
        return None

    min_len = min(len(all_returns[t]) for t in valid_tickers)
    for t in valid_tickers:
        all_returns[t] = all_returns[t][-min_len:]

    current_vols = []
    for t in valid_tickers:
        vol = rolling_volatility(all_returns[t], vol_window)
        last_vol = None
        for v in reversed(vol):
            if v is not None:
                last_vol = v
                break
        current_vols.append(last_vol or 0.2)

    n = len(valid_tickers)
    corr_matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        corr_matrix[i][i] = 1.0
        for j in range(i + 1, n):
            corr_vals = correlation(all_returns[valid_tickers[i]], all_returns[valid_tickers[j]], vol_window)
            last_corr = 0.5
            for c in reversed(corr_vals):
                if c is not None:
                    last_corr = c
                    break
            corr_matrix[i][j] = last_corr
            corr_matrix[j][i] = last_corr

    iv_weights = inverse_vol_weights(current_vols)
    rp_weights = optimize_risk_parity(current_vols, corr_matrix)
    equal_weights = [round(1.0 / n, 4)] * n

    rp_contribs, rp_vol = risk_contribution(rp_weights, current_vols, corr_matrix)
    eq_contribs, eq_vol = risk_contribution(equal_weights, current_vols, corr_matrix)

    assets = {}
    for i, t in enumerate(valid_tickers):
        closes = all_data[t]["closes"]
        perf = round((closes[-1] - closes[0]) / closes[0] * 100, 2)
        sr = sharpe_ratio(all_returns[t])
        assets[t] = {
            "volatility": round(current_vols[i] * 100, 2),
            "performance": perf,
            "sharpe": sr,
            "equal_weight": equal_weights[i],
            "inv_vol_weight": iv_weights[i],
            "risk_parity_weight": rp_weights[i],
            "risk_contribution": rp_contribs[i],
        }

    return {
        "tickers": valid_tickers,
        "assets": assets,
        "correlation_matrix": corr_matrix,
        "portfolio_vol_rp": rp_vol,
        "portfolio_vol_eq": eq_vol,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python riskpar.py <ticker1> <ticker2> [ticker3...] [period]")
        print("  calculate risk parity allocation weights")
        print("  period as last arg: 1y, 2y, 5y (default: 1y)")
        sys.exit(1)

    args = sys.argv[1:]
    periods = {"1mo", "3mo", "6mo", "1y", "2y", "5y"}
    if args[-1].lower() in periods:
        period = args[-1].lower()
        tickers = [a.upper() for a in args[:-1]]
    else:
        period = "1y"
        tickers = [a.upper() for a in args]

    print(f"risk parity analysis: {', '.join(tickers)} ({period})")
    result = analyze(tickers, period)

    if not result:
        print("insufficient data for analysis")
        sys.exit(1)

    print(f"\n{'ticker':<8} {'vol':>8} {'perf':>8} {'equal':>8} {'inv_vol':>8} {'risk_par':>8} {'risk_ctr':>8}")
    print("-" * 64)
    for t in result["tickers"]:
        a = result["assets"][t]
        print(f"{t:<8} {a['volatility']:>7.1f}% {a['performance']:>7.1f}% "
              f"{a['equal_weight']:>7.1%} {a['inv_vol_weight']:>7.1%} "
              f"{a['risk_parity_weight']:>7.1%} {a['risk_contribution']:>8.4f}")

    print("\nportfolio volatility:")
    print(f"  equal weight:  {result['portfolio_vol_eq']*100:.2f}%")
    print(f"  risk parity:   {result['portfolio_vol_rp']*100:.2f}%")

    n = len(result["tickers"])
    print("\ncorrelation matrix:")
    print(f"{'':>8}", end="")
    for t in result["tickers"]:
        print(f"{t:>8}", end="")
    print()
    for i, t in enumerate(result["tickers"]):
        print(f"{t:<8}", end="")
        for j in range(n):
            print(f"{result['correlation_matrix'][i][j]:>8.2f}", end="")
        print()
