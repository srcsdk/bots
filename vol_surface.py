#!/usr/bin/env python3
"""implied volatility surface interpolation"""

import math


def black_scholes_price(s, k, t, r, sigma, option_type="call"):
    """calculate black-scholes option price."""
    if t <= 0 or sigma <= 0:
        if option_type == "call":
            return max(0, s - k)
        return max(0, k - s)
    d1 = (math.log(s / k) + (r + sigma ** 2 / 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    nd1 = _norm_cdf(d1)
    nd2 = _norm_cdf(d2)
    if option_type == "call":
        return s * nd1 - k * math.exp(-r * t) * nd2
    return k * math.exp(-r * t) * (1 - nd2) - s * (1 - nd1)


def _norm_cdf(x):
    """standard normal cumulative distribution (approximation)."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def implied_vol(market_price, s, k, t, r, option_type="call",
                tol=1e-6, max_iter=100):
    """find implied volatility using bisection method."""
    lo, hi = 0.001, 5.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        price = black_scholes_price(s, k, t, r, mid, option_type)
        if abs(price - market_price) < tol:
            return mid
        if price > market_price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def build_surface(spot, rate, strikes, expiries, market_prices):
    """build iv surface from market option prices.

    market_prices: dict of {(strike, expiry): price}
    returns dict of {(strike, expiry): implied_vol}
    """
    surface = {}
    for strike in strikes:
        for expiry in expiries:
            key = (strike, expiry)
            if key in market_prices:
                iv = implied_vol(market_prices[key], spot, strike, expiry, rate)
                surface[key] = round(iv, 4)
    return surface


def interpolate_vol(surface, strike, expiry, strikes, expiries):
    """linear interpolation on the vol surface for a given strike/expiry."""
    s_lo = max([s for s in strikes if s <= strike], default=strikes[0])
    s_hi = min([s for s in strikes if s >= strike], default=strikes[-1])
    t_lo = max([t for t in expiries if t <= expiry], default=expiries[0])
    t_hi = min([t for t in expiries if t >= expiry], default=expiries[-1])
    corners = []
    for s in [s_lo, s_hi]:
        for t in [t_lo, t_hi]:
            if (s, t) in surface:
                corners.append(surface[(s, t)])
    if not corners:
        return 0.20
    return sum(corners) / len(corners)


def smile_skew(surface, expiry, strikes):
    """measure volatility skew at a given expiry."""
    vols = []
    for s in sorted(strikes):
        if (s, expiry) in surface:
            vols.append((s, surface[(s, expiry)]))
    if len(vols) < 2:
        return 0.0
    return vols[0][1] - vols[-1][1]


if __name__ == "__main__":
    spot = 100
    rate = 0.02
    strikes = [90, 95, 100, 105, 110]
    expiries = [0.25, 0.5, 1.0]
    prices = {}
    for k in strikes:
        for t in expiries:
            sigma = 0.20 + 0.05 * abs(k - spot) / spot + 0.02 * t
            prices[(k, t)] = black_scholes_price(spot, k, t, rate, sigma)
    surface = build_surface(spot, rate, strikes, expiries, prices)
    print("implied volatility surface:")
    for t in expiries:
        row = [f"{surface.get((k, t), 0):.2%}" for k in strikes]
        print(f"  T={t:.2f}: {' '.join(row)}")
