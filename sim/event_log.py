#!/usr/bin/env python3
"""market event logging for strategy analysis"""

import json
import os
from collections import defaultdict


class EventLog:
    """log and query market events for analysis."""

    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.events = []

    def log_event(self, event_type, data):
        """record a market event."""
        event = {
            "type": event_type,
            "data": data,
        }
        self.events.append(event)
        return event

    def log_trade(self, symbol, action, shares, price, reason=""):
        """log a trade event."""
        return self.log_event("trade", {
            "symbol": symbol, "action": action,
            "shares": shares, "price": price, "reason": reason,
        })

    def log_signal(self, symbol, signal_type, strength, source=""):
        """log a trading signal."""
        return self.log_event("signal", {
            "symbol": symbol, "signal": signal_type,
            "strength": strength, "source": source,
        })

    def log_risk(self, event_type, details):
        """log a risk management event."""
        return self.log_event("risk", {
            "risk_type": event_type, **details,
        })

    def filter_events(self, event_type=None, symbol=None):
        """filter events by type and symbol."""
        result = self.events
        if event_type:
            result = [e for e in result if e["type"] == event_type]
        if symbol:
            result = [
                e for e in result
                if e["data"].get("symbol") == symbol
            ]
        return result

    def event_counts(self):
        """count events by type."""
        counts = defaultdict(int)
        for event in self.events:
            counts[event["type"]] += 1
        return dict(counts)

    def save(self, filename="events.json"):
        """save events to json file."""
        filepath = os.path.join(self.log_dir, filename)
        with open(filepath, "w") as f:
            json.dump(self.events, f, indent=2)

    def load(self, filename="events.json"):
        """load events from json file."""
        filepath = os.path.join(self.log_dir, filename)
        if os.path.isfile(filepath):
            with open(filepath) as f:
                self.events = json.load(f)

    def summary(self):
        """generate event summary."""
        counts = self.event_counts()
        symbols = set()
        for event in self.events:
            sym = event["data"].get("symbol")
            if sym:
                symbols.add(sym)
        return {
            "total_events": len(self.events),
            "by_type": counts,
            "symbols": sorted(symbols),
        }


if __name__ == "__main__":
    log = EventLog("/tmp/test_events")
    log.log_trade("AAPL", "buy", 100, 150.0, "ma crossover")
    log.log_signal("AAPL", "bullish", 0.8, "rsi")
    log.log_signal("MSFT", "bearish", 0.6, "macd")
    log.log_trade("AAPL", "sell", 100, 160.0, "target hit")
    log.log_risk("stop_triggered", {"symbol": "MSFT", "price": 270.0})
    summary = log.summary()
    print(f"events: {summary['total_events']}")
    print(f"types: {summary['by_type']}")
    print(f"symbols: {summary['symbols']}")
