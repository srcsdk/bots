#!/usr/bin/env python3
"""track portfolio value over time with daily snapshots"""

import json
import os
from datetime import datetime


class PortfolioTracker:
    """record and query portfolio value history."""

    def __init__(self, data_file="portfolio_history.json"):
        self.data_file = data_file
        self.history = self._load()

    def _load(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save(self):
        with open(self.data_file, "w") as f:
            json.dump(self.history, f, indent=2)

    def snapshot(self, positions, prices):
        """record current portfolio state.

        positions: dict of ticker -> shares
        prices: dict of ticker -> current_price
        """
        if not positions or not prices:
            return None
        total = 0.0
        holdings = {}
        for ticker, shares in positions.items():
            price = prices.get(ticker, 0)
            value = shares * price
            total += value
            holdings[ticker] = {
                "shares": shares,
                "price": round(price, 2),
                "value": round(value, 2),
            }
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_value": round(total, 2),
            "holdings": holdings,
        }
        self.history.append(entry)
        return entry

    def get_returns(self, period_days=30):
        """calculate returns over a period."""
        if len(self.history) < 2:
            return 0.0
        start_idx = max(0, len(self.history) - period_days)
        start_val = self.history[start_idx]["total_value"]
        end_val = self.history[-1]["total_value"]
        if start_val <= 0:
            return 0.0
        return round((end_val - start_val) / start_val * 100, 2)

    def peak_value(self):
        """return highest portfolio value recorded."""
        if not self.history:
            return 0.0
        return max(h["total_value"] for h in self.history)

    def current_drawdown(self):
        """calculate current drawdown from peak."""
        peak = self.peak_value()
        if peak <= 0 or not self.history:
            return 0.0
        current = self.history[-1]["total_value"]
        return round((peak - current) / peak * 100, 2)


if __name__ == "__main__":
    tracker = PortfolioTracker("/tmp/test_portfolio.json")
    tracker.snapshot(
        {"AAPL": 100, "GOOGL": 50},
        {"AAPL": 150.0, "GOOGL": 100.0},
    )
    print(f"peak: ${tracker.peak_value():,.2f}")
    print(f"drawdown: {tracker.current_drawdown():.2f}%")
