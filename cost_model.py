#!/usr/bin/env python3
"""model execution costs including slippage, commission, and market impact"""


class CostModel:
    """estimate realistic execution costs for backtesting accuracy."""

    def __init__(self, commission_per_share=0.005, min_commission=1.0,
                 slippage_bps=5, market_impact_coeff=0.1):
        self.commission_per_share = commission_per_share
        self.min_commission = min_commission
        self.slippage_bps = slippage_bps
        self.market_impact_coeff = market_impact_coeff

    def commission(self, shares, price):
        """calculate commission for a trade."""
        if shares <= 0 or price <= 0:
            return 0.0
        raw = abs(shares) * self.commission_per_share
        return max(raw, self.min_commission)

    def slippage(self, shares, price):
        """estimate slippage cost based on basis points."""
        if shares <= 0 or price <= 0:
            return 0.0
        return abs(shares) * price * (self.slippage_bps / 10000)

    def market_impact(self, shares, avg_volume, price):
        """estimate market impact using square root model.

        larger orders relative to volume have outsized impact.
        """
        if avg_volume <= 0 or shares <= 0 or price <= 0:
            return 0.0
        participation = abs(shares) / avg_volume
        import math
        impact_bps = self.market_impact_coeff * math.sqrt(participation) * 10000
        return abs(shares) * price * (impact_bps / 10000)

    def total_cost(self, shares, price, avg_volume=None):
        """calculate total execution cost for a trade."""
        cost = self.commission(shares, price) + self.slippage(shares, price)
        if avg_volume and avg_volume > 0:
            cost += self.market_impact(shares, avg_volume, price)
        return round(cost, 2)

    def adjusted_price(self, shares, price, side="buy"):
        """return price adjusted for execution costs.

        buy orders get worse (higher) price, sell orders get worse (lower).
        """
        if price <= 0:
            return price
        slip = self.slippage_bps / 10000
        if side == "buy":
            return round(price * (1 + slip), 4)
        return round(price * (1 - slip), 4)


if __name__ == "__main__":
    model = CostModel()
    cost = model.total_cost(500, 150.0, avg_volume=1000000)
    print(f"total cost for 500 shares at $150: ${cost:.2f}")
    buy_price = model.adjusted_price(500, 150.0, "buy")
    sell_price = model.adjusted_price(500, 150.0, "sell")
    print(f"adjusted buy: ${buy_price}, sell: ${sell_price}")
