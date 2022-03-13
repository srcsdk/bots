#!/usr/bin/env python3
"""trade journal for tracking and reviewing trades"""

import json
import os


class TradeJournal:
    """structured trade journal for review and analysis."""

    def __init__(self, journal_file="trade_journal.json"):
        self.journal_file = journal_file
        self.entries = self._load()

    def add_entry(self, symbol, action, shares, price, strategy="",
                  notes="", tags=None):
        """add a journal entry."""
        entry = {
            "symbol": symbol,
            "action": action,
            "shares": shares,
            "price": price,
            "strategy": strategy,
            "notes": notes,
            "tags": tags or [],
        }
        self.entries.append(entry)
        self._save()
        return entry

    def close_trade(self, symbol, exit_price, notes=""):
        """close an open trade and calculate pnl."""
        for entry in reversed(self.entries):
            if entry["symbol"] == symbol and entry["action"] == "buy":
                if "exit_price" not in entry:
                    entry["exit_price"] = exit_price
                    entry["pnl"] = round(
                        (exit_price - entry["price"]) * entry["shares"], 2
                    )
                    entry["pnl_pct"] = round(
                        (exit_price - entry["price"]) / entry["price"] * 100,
                        2,
                    )
                    entry["exit_notes"] = notes
                    self._save()
                    return entry
        return None

    def open_trades(self):
        """list trades without exit prices."""
        return [
            e for e in self.entries
            if e["action"] == "buy" and "exit_price" not in e
        ]

    def closed_trades(self):
        """list completed trades."""
        return [e for e in self.entries if "exit_price" in e]

    def by_strategy(self):
        """group trades by strategy."""
        by_strat = {}
        for entry in self.entries:
            strat = entry.get("strategy", "unknown")
            if strat not in by_strat:
                by_strat[strat] = []
            by_strat[strat].append(entry)
        return by_strat

    def by_tag(self, tag):
        """filter entries by tag."""
        return [e for e in self.entries if tag in e.get("tags", [])]

    def performance_summary(self):
        """summarize journal performance."""
        closed = self.closed_trades()
        if not closed:
            return {"trades": 0}
        wins = [t for t in closed if t.get("pnl", 0) > 0]
        losses = [t for t in closed if t.get("pnl", 0) < 0]
        total_pnl = sum(t.get("pnl", 0) for t in closed)
        return {
            "trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(closed) * 100, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / len(closed), 2),
        }

    def _load(self):
        if os.path.isfile(self.journal_file):
            with open(self.journal_file) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.journal_file, "w") as f:
            json.dump(self.entries, f, indent=2)


if __name__ == "__main__":
    journal = TradeJournal("/tmp/test_journal.json")
    journal.add_entry("AAPL", "buy", 100, 150.0,
                      strategy="ma_cross", tags=["tech"])
    journal.close_trade("AAPL", 160.0, "target hit")
    journal.add_entry("MSFT", "buy", 50, 280.0,
                      strategy="breakout", tags=["tech"])
    journal.close_trade("MSFT", 275.0, "stopped out")
    summary = journal.performance_summary()
    print(f"summary: {summary}")
