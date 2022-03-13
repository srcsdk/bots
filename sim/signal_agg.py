#!/usr/bin/env python3
"""aggregate trading signals from multiple sources"""

from collections import defaultdict


class SignalAggregator:
    """combine signals from multiple strategies into consensus."""

    def __init__(self):
        self.sources = {}
        self.weights = {}
        self.signals = defaultdict(list)

    def register_source(self, name, weight=1.0):
        """register a signal source with weight."""
        self.sources[name] = True
        self.weights[name] = weight

    def add_signal(self, source, symbol, direction, strength=1.0):
        """add a signal from a source.

        direction: 1 for buy, -1 for sell, 0 for neutral.
        strength: 0-1 confidence level.
        """
        if source not in self.sources:
            return
        self.signals[symbol].append({
            "source": source,
            "direction": direction,
            "strength": strength,
            "weight": self.weights.get(source, 1.0),
        })

    def consensus(self, symbol, threshold=0.3):
        """calculate consensus signal for a symbol."""
        signals = self.signals.get(symbol, [])
        if not signals:
            return {"direction": 0, "confidence": 0, "sources": 0}
        total_weight = 0
        weighted_sum = 0
        for sig in signals:
            w = sig["weight"] * sig["strength"]
            weighted_sum += sig["direction"] * w
            total_weight += w
        if total_weight == 0:
            return {"direction": 0, "confidence": 0, "sources": 0}
        normalized = weighted_sum / total_weight
        if abs(normalized) < threshold:
            direction = 0
        elif normalized > 0:
            direction = 1
        else:
            direction = -1
        return {
            "direction": direction,
            "confidence": round(abs(normalized), 4),
            "sources": len(signals),
            "raw_score": round(normalized, 4),
        }

    def all_consensus(self, threshold=0.3):
        """get consensus for all symbols."""
        results = {}
        for symbol in self.signals:
            results[symbol] = self.consensus(symbol, threshold)
        return results

    def clear(self):
        """clear all signals."""
        self.signals.clear()

    def source_agreement(self, symbol):
        """check how many sources agree on direction."""
        signals = self.signals.get(symbol, [])
        if not signals:
            return {"buy": 0, "sell": 0, "neutral": 0}
        counts = {"buy": 0, "sell": 0, "neutral": 0}
        for sig in signals:
            if sig["direction"] > 0:
                counts["buy"] += 1
            elif sig["direction"] < 0:
                counts["sell"] += 1
            else:
                counts["neutral"] += 1
        return counts


if __name__ == "__main__":
    agg = SignalAggregator()
    agg.register_source("rsi", weight=1.0)
    agg.register_source("macd", weight=1.5)
    agg.register_source("ma_cross", weight=1.2)
    agg.add_signal("rsi", "AAPL", 1, 0.7)
    agg.add_signal("macd", "AAPL", 1, 0.9)
    agg.add_signal("ma_cross", "AAPL", -1, 0.4)
    result = agg.consensus("AAPL")
    print(f"AAPL consensus: {result}")
    agreement = agg.source_agreement("AAPL")
    print(f"agreement: {agreement}")
