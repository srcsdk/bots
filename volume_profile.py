#!/usr/bin/env python3
# updated: proper poc and value area calculation
"""volume profile analysis with point of control and value area"""

from collections import defaultdict


def build_profile(prices, volumes, num_bins=50):
    """build volume profile from price and volume data.

    divides price range into bins and accumulates volume at each level.
    returns sorted list of (price_level, volume) tuples.
    """
    if not prices or not volumes or len(prices) != len(volumes):
        return []
    price_min = min(prices)
    price_max = max(prices)
    if price_max == price_min:
        return [(price_min, sum(volumes))]
    bin_size = (price_max - price_min) / num_bins
    profile = defaultdict(float)
    for price, vol in zip(prices, volumes):
        bin_idx = min(int((price - price_min) / bin_size), num_bins - 1)
        level = round(price_min + bin_idx * bin_size + bin_size / 2, 4)
        profile[level] += vol
    return sorted(profile.items(), key=lambda x: x[0])


def point_of_control(profile):
    """find price level with highest volume (poc)."""
    if not profile:
        return 0.0
    return max(profile, key=lambda x: x[1])[0]


def value_area(profile, pct=0.70):
    """calculate value area containing pct of total volume.

    starts from poc and expands outward until threshold is met.
    returns (va_low, va_high, poc_price).
    """
    if not profile:
        return 0.0, 0.0, 0.0
    total_vol = sum(v for _, v in profile)
    target = total_vol * pct
    poc_price = point_of_control(profile)
    poc_idx = 0
    for i, (p, _) in enumerate(profile):
        if p == poc_price:
            poc_idx = i
            break
    included = {poc_idx}
    accumulated = profile[poc_idx][1]
    lo, hi = poc_idx, poc_idx
    while accumulated < target and (lo > 0 or hi < len(profile) - 1):
        up_vol = profile[hi + 1][1] if hi + 1 < len(profile) else 0
        down_vol = profile[lo - 1][1] if lo > 0 else 0
        if up_vol >= down_vol and hi + 1 < len(profile):
            hi += 1
            accumulated += profile[hi][1]
            included.add(hi)
        elif lo > 0:
            lo -= 1
            accumulated += profile[lo][1]
            included.add(lo)
        else:
            hi += 1
            accumulated += profile[hi][1]
            included.add(hi)
    return profile[lo][0], profile[hi][0], poc_price


def session_profile(rows, num_bins=30):
    """build volume profile from ohlc row dicts with close and volume keys."""
    prices = [r["close"] for r in rows]
    volumes = [r.get("volume", 0) for r in rows]
    profile = build_profile(prices, volumes, num_bins)
    va_low, va_high, poc = value_area(profile)
    return {
        "profile": profile,
        "poc": poc,
        "value_area_low": va_low,
        "value_area_high": va_high,
        "total_volume": sum(volumes),
    }


if __name__ == "__main__":
    import random
    prices = [100 + random.gauss(0, 2) for _ in range(200)]
    volumes = [random.randint(100, 10000) for _ in range(200)]
    profile = build_profile(prices, volumes)
    poc = point_of_control(profile)
    va_lo, va_hi, _ = value_area(profile)
    print(f"poc: {poc:.2f}")
    print(f"value area: {va_lo:.2f} - {va_hi:.2f}")
    print(f"bins: {len(profile)}")
