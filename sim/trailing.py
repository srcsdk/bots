#!/usr/bin/env python3
"""trailing stop implementations for paper trading"""


class TrailingStop:
    """trailing stop with percentage or atr-based distance."""

    def __init__(self, method="percent", distance=5.0):
        self.method = method
        self.distance = distance
        self.high_water = None
        self.stop_price = None

    def update(self, current_price, atr=None):
        """update stop price based on current price."""
        if self.high_water is None or current_price > self.high_water:
            self.high_water = current_price
            if self.method == "percent":
                self.stop_price = round(
                    self.high_water * (1 - self.distance / 100), 4
                )
            elif self.method == "atr" and atr:
                self.stop_price = round(self.high_water - atr * self.distance, 4)
            elif self.method == "fixed":
                self.stop_price = round(self.high_water - self.distance, 4)
        return self.stop_price

    def is_triggered(self, current_price):
        """check if stop is triggered."""
        if self.stop_price is None:
            return False
        return current_price <= self.stop_price

    def reset(self):
        """reset trailing stop state."""
        self.high_water = None
        self.stop_price = None


def chandelier_exit(highs, closes, period=22, multiplier=3.0):
    """chandelier exit: trailing stop based on atr from highest high."""
    if len(highs) < period:
        return []
    stops = [None] * (period - 1)
    for i in range(period - 1, len(highs)):
        highest = max(highs[i - period + 1:i + 1])
        tr_values = []
        for j in range(max(1, i - period + 1), i + 1):
            tr = max(
                highs[j] - closes[j],
                abs(highs[j] - closes[j - 1]),
                abs(closes[j] - closes[j - 1])
            )
            tr_values.append(tr)
        atr = sum(tr_values) / len(tr_values)
        stop = highest - multiplier * atr
        stops.append(round(stop, 4))
    return stops


if __name__ == "__main__":
    ts = TrailingStop("percent", 5.0)
    prices = [100, 105, 110, 108, 112, 106, 103]
    for p in prices:
        stop = ts.update(p)
        triggered = ts.is_triggered(p)
        print(f"  price={p} stop={stop} triggered={triggered}")
