#!/usr/bin/env python3
"""trade journal with entry/exit logging and performance attribution"""

import json
import os
from datetime import datetime


class TradeJournal:
    """log trades with metadata for performance review."""

    def __init__(self, journal_file="trade_journal.json"):
        self.journal_file = journal_file
        self.trades = self._load()

    def _load(self):
        if os.path.exists(self.journal_file):
            try:
                with open(self.journal_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save(self):
        with open(self.journal_file, "w") as f:
            json.dump(self.trades, f, indent=2)

    def log_entry(self, ticker, action, price, size, strategy="",
                  reason="", tags=None):
        """log a trade entry or exit."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker,
            "action": action,
            "price": round(price, 4),
            "size": size,
            "strategy": strategy,
            "reason": reason,
            "tags": tags or [],
        }
        self.trades.append(entry)
        return entry

    def get_by_strategy(self, strategy):
        """filter trades by strategy name."""
        return [t for t in self.trades if t.get("strategy") == strategy]

    def get_by_ticker(self, ticker):
        """filter trades by ticker."""
        return [t for t in self.trades if t.get("ticker") == ticker]

    def strategy_summary(self):
        """summarize performance by strategy."""
        strategies = {}
        for trade in self.trades:
            strat = trade.get("strategy", "unknown")
            if strat not in strategies:
                strategies[strat] = {"trades": 0, "buys": 0, "sells": 0}
            strategies[strat]["trades"] += 1
            if trade.get("action") == "buy":
                strategies[strat]["buys"] += 1
            elif trade.get("action") == "sell":
                strategies[strat]["sells"] += 1
        return strategies

    def recent(self, n=10):
        """return n most recent trades."""
        return self.trades[-n:]


if __name__ == "__main__":
    j = TradeJournal("/tmp/test_journal.json")
    j.log_entry("AAPL", "buy", 150.25, 100, "momentum", "breakout above sma20")
    j.log_entry("AAPL", "sell", 160.50, 100, "momentum", "target hit")
    summary = j.strategy_summary()
    print(f"strategies: {summary}")
