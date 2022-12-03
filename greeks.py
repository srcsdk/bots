#!/usr/bin/env python3
# fixed: validate inputs and handle edge cases
"""options greeks calculator with black-scholes model"""

import math


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _d1d2(s, k, t, r, sigma):
    if t <= 0 or sigma <= 0:
        return 0.0, 0.0
    d1 = (math.log(s / k) + (r + sigma ** 2 / 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    return d1, d2


def delta(s, k, t, r, sigma, option_type="call"):
    """option delta: rate of change of price with respect to underlying."""
    d1, _ = _d1d2(s, k, t, r, sigma)
    if option_type == "call":
        return _norm_cdf(d1)
    return _norm_cdf(d1) - 1


def gamma(s, k, t, r, sigma):
    """option gamma: rate of change of delta. same for calls and puts."""
    if t <= 0 or sigma <= 0:
        return 0.0
    d1, _ = _d1d2(s, k, t, r, sigma)
    return _norm_pdf(d1) / (s * sigma * math.sqrt(t))


def theta(s, k, t, r, sigma, option_type="call"):
    """option theta: time decay per day."""
    if t <= 0 or sigma <= 0:
        return 0.0
    d1, d2 = _d1d2(s, k, t, r, sigma)
    common = -s * _norm_pdf(d1) * sigma / (2 * math.sqrt(t))
    if option_type == "call":
        return (common - r * k * math.exp(-r * t) * _norm_cdf(d2)) / 365
    return (common + r * k * math.exp(-r * t) * _norm_cdf(-d2)) / 365


def vega(s, k, t, r, sigma):
    """option vega: sensitivity to volatility. same for calls and puts."""
    if t <= 0 or sigma <= 0:
        return 0.0
    d1, _ = _d1d2(s, k, t, r, sigma)
    return s * _norm_pdf(d1) * math.sqrt(t) / 100


def rho(s, k, t, r, sigma, option_type="call"):
    """option rho: sensitivity to interest rate."""
    _, d2 = _d1d2(s, k, t, r, sigma)
    if option_type == "call":
        return k * t * math.exp(-r * t) * _norm_cdf(d2) / 100
    return -k * t * math.exp(-r * t) * _norm_cdf(-d2) / 100


def all_greeks(s, k, t, r, sigma, option_type="call"):
    """calculate all greeks for an option."""
    return {
        "delta": round(delta(s, k, t, r, sigma, option_type), 4),
        "gamma": round(gamma(s, k, t, r, sigma), 6),
        "theta": round(theta(s, k, t, r, sigma, option_type), 4),
        "vega": round(vega(s, k, t, r, sigma), 4),
        "rho": round(rho(s, k, t, r, sigma, option_type), 4),
    }


if __name__ == "__main__":
    s, k, t, r, sigma = 100, 100, 0.25, 0.02, 0.20
    for otype in ["call", "put"]:
        g = all_greeks(s, k, t, r, sigma, otype)
        print(f"{otype}: {g}")
