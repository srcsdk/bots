#!/usr/bin/env python3
"""trading universe selection and filtering"""


def filter_by_market_cap(symbols_data, min_cap=0, max_cap=float("inf")):
    """filter symbols by market cap range."""
    return [
        s for s in symbols_data
        if min_cap <= s.get("market_cap", 0) <= max_cap
    ]


def filter_by_volume(symbols_data, min_avg_volume=100000):
    """filter by average daily volume."""
    return [
        s for s in symbols_data
        if s.get("avg_volume", 0) >= min_avg_volume
    ]


def filter_by_price(symbols_data, min_price=1.0, max_price=10000):
    """filter by price range."""
    return [
        s for s in symbols_data
        if min_price <= s.get("price", 0) <= max_price
    ]


def rank_by_momentum(symbols_data, period=20):
    """rank symbols by price momentum."""
    ranked = []
    for s in symbols_data:
        prices = s.get("prices", [])
        if len(prices) > period:
            momentum = (prices[-1] - prices[-period]) / prices[-period]
            ranked.append({**s, "momentum": round(momentum * 100, 2)})
    ranked.sort(key=lambda x: x["momentum"], reverse=True)
    return ranked


def sector_breakdown(symbols_data):
    """break down universe by sector."""
    sectors = {}
    for s in symbols_data:
        sector = s.get("sector", "unknown")
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(s.get("symbol", ""))
    return sectors


def build_universe(symbols_data, min_volume=100000, min_price=5.0,
                   max_symbols=100):
    """build filtered trading universe."""
    filtered = filter_by_volume(symbols_data, min_volume)
    filtered = filter_by_price(filtered, min_price)
    ranked = rank_by_momentum(filtered)
    return ranked[:max_symbols]


if __name__ == "__main__":
    symbols = [
        {"symbol": "AAPL", "price": 170, "avg_volume": 80000000,
         "market_cap": 2.7e12, "sector": "tech",
         "prices": [150, 155, 160, 165, 170]},
        {"symbol": "MSFT", "price": 300, "avg_volume": 25000000,
         "market_cap": 2.2e12, "sector": "tech",
         "prices": [280, 285, 290, 295, 300]},
        {"symbol": "XYZ", "price": 0.50, "avg_volume": 5000,
         "market_cap": 1e6, "sector": "penny",
         "prices": [0.40, 0.45, 0.50, 0.48, 0.50]},
    ]
    universe = build_universe(symbols, min_volume=10000, min_price=1.0)
    print(f"universe: {len(universe)} symbols")
    for s in universe:
        print(f"  {s['symbol']}: momentum {s['momentum']}%")
    sectors = sector_breakdown(symbols)
    print(f"\nsectors: {sectors}")
