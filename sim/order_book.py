#!/usr/bin/env python3
"""order book simulation for market microstructure"""

from collections import defaultdict
import bisect


class OrderBook:
    """simulated order book with bid/ask levels."""

    def __init__(self):
        self.bids = []
        self.asks = []
        self.bid_sizes = defaultdict(int)
        self.ask_sizes = defaultdict(int)

    def add_bid(self, price, size):
        """add a bid order."""
        if price not in self.bid_sizes or self.bid_sizes[price] == 0:
            bisect.insort(self.bids, price)
        self.bid_sizes[price] += size

    def add_ask(self, price, size):
        """add an ask order."""
        if price not in self.ask_sizes or self.ask_sizes[price] == 0:
            bisect.insort(self.asks, price)
        self.ask_sizes[price] += size

    def best_bid(self):
        """highest bid price."""
        while self.bids and self.bid_sizes[self.bids[-1]] <= 0:
            self.bids.pop()
        return self.bids[-1] if self.bids else 0

    def best_ask(self):
        """lowest ask price."""
        while self.asks and self.ask_sizes[self.asks[0]] <= 0:
            self.asks.pop(0)
        return self.asks[0] if self.asks else float("inf")

    def spread(self):
        """bid-ask spread."""
        return round(self.best_ask() - self.best_bid(), 4)

    def midpoint(self):
        """midpoint price."""
        bid = self.best_bid()
        ask = self.best_ask()
        if ask == float("inf") or bid == 0:
            return 0
        return round((bid + ask) / 2, 4)

    def depth(self, levels=5):
        """return top n levels of bids and asks."""
        bid_levels = []
        for price in reversed(self.bids[-levels:]):
            if self.bid_sizes[price] > 0:
                bid_levels.append((price, self.bid_sizes[price]))
        ask_levels = []
        for price in self.asks[:levels]:
            if self.ask_sizes[price] > 0:
                ask_levels.append((price, self.ask_sizes[price]))
        return {"bids": bid_levels, "asks": ask_levels}

    def fill_market_buy(self, size):
        """simulate market buy order, consuming asks."""
        filled = 0
        cost = 0
        while size > 0 and self.asks:
            price = self.asks[0]
            available = self.ask_sizes[price]
            if available <= 0:
                self.asks.pop(0)
                continue
            take = min(size, available)
            cost += take * price
            self.ask_sizes[price] -= take
            filled += take
            size -= take
            if self.ask_sizes[price] <= 0:
                self.asks.pop(0)
        avg_price = round(cost / filled, 4) if filled > 0 else 0
        return {"filled": filled, "avg_price": avg_price, "cost": round(cost, 2)}

    def fill_market_sell(self, size):
        """simulate market sell order, consuming bids."""
        filled = 0
        proceeds = 0
        while size > 0 and self.bids:
            price = self.bids[-1]
            available = self.bid_sizes[price]
            if available <= 0:
                self.bids.pop()
                continue
            take = min(size, available)
            proceeds += take * price
            self.bid_sizes[price] -= take
            filled += take
            size -= take
            if self.bid_sizes[price] <= 0:
                self.bids.pop()
        avg_price = round(proceeds / filled, 4) if filled > 0 else 0
        return {"filled": filled, "avg_price": avg_price,
                "proceeds": round(proceeds, 2)}


if __name__ == "__main__":
    book = OrderBook()
    book.add_bid(99.90, 100)
    book.add_bid(99.80, 200)
    book.add_bid(99.70, 300)
    book.add_ask(100.10, 150)
    book.add_ask(100.20, 250)
    book.add_ask(100.30, 100)
    print(f"spread: {book.spread()}")
    print(f"midpoint: {book.midpoint()}")
    depth = book.depth()
    print("bids:", depth["bids"])
    print("asks:", depth["asks"])
    result = book.fill_market_buy(200)
    print(f"market buy 200: avg {result['avg_price']}, cost {result['cost']}")
