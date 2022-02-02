#!/usr/bin/env python3
"""track sector allocation and exposure limits"""


SECTORS = {
    "technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA"],
    "healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK"],
    "financial": ["JPM", "BAC", "WFC", "GS", "MS"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "consumer": ["AMZN", "TSLA", "HD", "NKE", "SBUX"],
}


def get_sector(symbol):
    """look up sector for a symbol."""
    for sector, symbols in SECTORS.items():
        if symbol in symbols:
            return sector
    return "other"


def sector_allocation(positions, prices):
    """calculate portfolio allocation by sector."""
    total_value = sum(
        pos["shares"] * prices.get(sym, 0)
        for sym, pos in positions.items()
    )
    if total_value == 0:
        return {}
    allocation = {}
    for sym, pos in positions.items():
        sector = get_sector(sym)
        value = pos["shares"] * prices.get(sym, 0)
        allocation.setdefault(sector, 0)
        allocation[sector] += value
    return {s: round(v / total_value * 100, 2) for s, v in allocation.items()}


def check_concentration(allocation, max_sector_pct=30):
    """check if any sector exceeds concentration limit."""
    violations = []
    for sector, pct in allocation.items():
        if pct > max_sector_pct:
            violations.append({
                "sector": sector,
                "current_pct": pct,
                "limit_pct": max_sector_pct,
                "excess_pct": round(pct - max_sector_pct, 2),
            })
    return violations


def rebalance_suggestion(allocation, target_allocation):
    """suggest trades to rebalance toward target allocation."""
    suggestions = []
    for sector in set(list(allocation.keys()) + list(target_allocation.keys())):
        current = allocation.get(sector, 0)
        target = target_allocation.get(sector, 0)
        diff = round(target - current, 2)
        if abs(diff) > 1:
            action = "increase" if diff > 0 else "decrease"
            suggestions.append({
                "sector": sector,
                "current_pct": current,
                "target_pct": target,
                "action": action,
                "change_pct": abs(diff),
            })
    return sorted(suggestions, key=lambda s: s["change_pct"], reverse=True)


if __name__ == "__main__":
    positions = {
        "AAPL": {"shares": 100},
        "MSFT": {"shares": 50},
        "JPM": {"shares": 80},
    }
    prices = {"AAPL": 170, "MSFT": 300, "JPM": 155}
    alloc = sector_allocation(positions, prices)
    print(f"allocation: {alloc}")
    violations = check_concentration(alloc, max_sector_pct=60)
    print(f"violations: {violations}")
