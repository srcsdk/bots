#!/usr/bin/env python3
"""portfolio snapshot and history tracking"""

import json
import os
import time


class PortfolioSnapshot:
    """capture and track portfolio state over time."""

    def __init__(self, history_file="portfolio_history.json"):
        self.history_file = history_file
        self.snapshots = self._load()

    def capture(self, positions, cash, prices):
        """take a snapshot of current portfolio state."""
        holdings = {}
        total_value = cash
        for symbol, shares in positions.items():
            price = prices.get(symbol, 0)
            value = shares * price
            holdings[symbol] = {
                "shares": shares,
                "price": price,
                "value": round(value, 2),
            }
            total_value += value
        snapshot = {
            "timestamp": time.time(),
            "cash": round(cash, 2),
            "holdings": holdings,
            "total_value": round(total_value, 2),
            "num_positions": len(positions),
        }
        self.snapshots.append(snapshot)
        self._save()
        return snapshot

    def latest(self):
        """get most recent snapshot."""
        return self.snapshots[-1] if self.snapshots else None

    def value_history(self):
        """get portfolio value over time."""
        return [
            {"timestamp": s["timestamp"], "value": s["total_value"]}
            for s in self.snapshots
        ]

    def position_history(self, symbol):
        """track a specific position over time."""
        history = []
        for snap in self.snapshots:
            holding = snap["holdings"].get(symbol)
            if holding:
                history.append({
                    "timestamp": snap["timestamp"],
                    "shares": holding["shares"],
                    "value": holding["value"],
                })
        return history

    def concentration(self):
        """calculate portfolio concentration."""
        latest = self.latest()
        if not latest or latest["total_value"] <= 0:
            return {}
        return {
            symbol: round(
                holding["value"] / latest["total_value"] * 100, 1
            )
            for symbol, holding in latest["holdings"].items()
        }

    def changes_since(self, n=1):
        """compare current snapshot to n snapshots ago."""
        if len(self.snapshots) <= n:
            return {}
        current = self.snapshots[-1]
        previous = self.snapshots[-1 - n]
        return {
            "value_change": round(
                current["total_value"] - previous["total_value"], 2
            ),
            "pct_change": round(
                (current["total_value"] - previous["total_value"])
                / previous["total_value"] * 100, 2
            ) if previous["total_value"] > 0 else 0,
        }

    def _load(self):
        if os.path.isfile(self.history_file):
            with open(self.history_file) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.history_file, "w") as f:
            json.dump(self.snapshots, f, indent=2)


if __name__ == "__main__":
    snap = PortfolioSnapshot("/tmp/test_portfolio.json")
    positions = {"AAPL": 100, "MSFT": 50}
    prices = {"AAPL": 150, "MSFT": 280}
    snap.capture(positions, 10000, prices)
    prices = {"AAPL": 155, "MSFT": 285}
    snap.capture(positions, 10000, prices)
    latest = snap.latest()
    print(f"portfolio value: ${latest['total_value']}")
    conc = snap.concentration()
    print(f"concentration: {conc}")
    changes = snap.changes_since(1)
    print(f"changes: {changes}")
