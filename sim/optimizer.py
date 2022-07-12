#!/usr/bin/env python3
"""portfolio optimization with mean-variance framework"""


def expected_returns(price_histories):
    """calculate expected returns for each asset."""
    returns = {}
    for symbol, prices in price_histories.items():
        if len(prices) < 2:
            returns[symbol] = 0
            continue
        daily_returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                r = (prices[i] - prices[i - 1]) / prices[i - 1]
                daily_returns.append(r)
        avg = sum(daily_returns) / len(daily_returns) if daily_returns else 0
        returns[symbol] = round(avg * 252, 4)
    return returns


def portfolio_return(weights, expected_ret):
    """calculate expected portfolio return."""
    total = 0
    for symbol, weight in weights.items():
        total += weight * expected_ret.get(symbol, 0)
    return round(total, 4)


def portfolio_variance(weights, cov_matrix):
    """calculate portfolio variance from covariance matrix."""
    symbols = sorted(weights.keys())
    var = 0
    for i, sym_a in enumerate(symbols):
        for j, sym_b in enumerate(symbols):
            w_a = weights.get(sym_a, 0)
            w_b = weights.get(sym_b, 0)
            cov = cov_matrix.get(sym_a, {}).get(sym_b, 0)
            var += w_a * w_b * cov
    return round(var, 6)


def covariance_matrix(price_histories):
    """calculate covariance matrix from price histories."""
    symbols = sorted(price_histories.keys())
    returns_data = {}
    for symbol in symbols:
        prices = price_histories[symbol]
        returns_data[symbol] = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                returns_data[symbol].append(
                    (prices[i] - prices[i - 1]) / prices[i - 1]
                )
    min_len = min(len(r) for r in returns_data.values()) if returns_data else 0
    cov = {}
    for sym_a in symbols:
        cov[sym_a] = {}
        for sym_b in symbols:
            ra = returns_data[sym_a][:min_len]
            rb = returns_data[sym_b][:min_len]
            if not ra or not rb:
                cov[sym_a][sym_b] = 0
                continue
            mean_a = sum(ra) / len(ra)
            mean_b = sum(rb) / len(rb)
            covariance = sum(
                (ra[i] - mean_a) * (rb[i] - mean_b)
                for i in range(min_len)
            ) / min_len
            cov[sym_a][sym_b] = round(covariance * 252, 6)
    return cov


def equal_weight(symbols):
    """equal weight allocation."""
    w = round(1.0 / len(symbols), 4)
    return {s: w for s in symbols}


def min_variance_weights(symbols, cov_matrix, iterations=1000):
    """approximate minimum variance portfolio via random sampling."""
    import random
    best_weights = equal_weight(symbols)
    best_var = portfolio_variance(best_weights, cov_matrix)
    for _ in range(iterations):
        raw = [random.random() for _ in symbols]
        total = sum(raw)
        weights = {s: round(r / total, 4) for s, r in zip(symbols, raw)}
        var = portfolio_variance(weights, cov_matrix)
        if var < best_var:
            best_var = var
            best_weights = weights
    return best_weights


if __name__ == "__main__":
    import random
    random.seed(42)
    histories = {}
    for sym in ["AAPL", "MSFT", "GLD", "TLT"]:
        price = 100
        histories[sym] = [price]
        for _ in range(252):
            price *= (1 + random.gauss(0.0003, 0.02))
            histories[sym].append(round(price, 2))
    exp_ret = expected_returns(histories)
    print("expected returns:")
    for s, r in exp_ret.items():
        print(f"  {s}: {r:.2%}")
    cov = covariance_matrix(histories)
    symbols = sorted(histories.keys())
    eq = equal_weight(symbols)
    print(f"\nequal weight return: {portfolio_return(eq, exp_ret):.2%}")
    mv = min_variance_weights(symbols, cov)
    print(f"min variance weights: {mv}")
