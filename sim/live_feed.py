#!/usr/bin/env python3
"""live market data feed for real-time strategy execution"""

import time
import threading
from collections import deque


class LiveFeed:
    """stream live market data with buffering and callbacks."""

    def __init__(self, buffer_size=1000):
        self.buffer = deque(maxlen=buffer_size)
        self.subscribers = []
        self._running = False
        self._lock = threading.Lock()
        self.stats = {"ticks": 0, "errors": 0}

    def subscribe(self, callback):
        """register callback for new data."""
        self.subscribers.append(callback)

    def on_tick(self, data):
        """process incoming tick data."""
        tick = {
            "timestamp": time.time(),
            "symbol": data.get("symbol", ""),
            "price": float(data.get("price", 0)),
            "volume": int(data.get("volume", 0)),
            "bid": float(data.get("bid", 0)),
            "ask": float(data.get("ask", 0)),
        }
        with self._lock:
            self.buffer.append(tick)
            self.stats["ticks"] += 1
        for callback in self.subscribers:
            try:
                callback(tick)
            except Exception:
                self.stats["errors"] += 1

    def get_recent(self, n=100):
        """get recent ticks."""
        with self._lock:
            return list(self.buffer)[-n:]

    def get_ohlcv(self, period_seconds=60):
        """aggregate ticks into ohlcv bars."""
        with self._lock:
            ticks = list(self.buffer)
        if not ticks:
            return []
        bars = []
        current_bar = None
        for tick in ticks:
            bar_time = int(tick["timestamp"] / period_seconds) * period_seconds
            if current_bar is None or current_bar["time"] != bar_time:
                if current_bar:
                    bars.append(current_bar)
                current_bar = {
                    "time": bar_time,
                    "open": tick["price"],
                    "high": tick["price"],
                    "low": tick["price"],
                    "close": tick["price"],
                    "volume": tick["volume"],
                }
            else:
                current_bar["high"] = max(current_bar["high"], tick["price"])
                current_bar["low"] = min(current_bar["low"], tick["price"])
                current_bar["close"] = tick["price"]
                current_bar["volume"] += tick["volume"]
        if current_bar:
            bars.append(current_bar)
        return bars

    def start(self):
        """start the feed."""
        self._running = True

    def stop(self):
        """stop the feed."""
        self._running = False

    def is_running(self):
        """check feed status."""
        return self._running

    def get_stats(self):
        """return feed statistics."""
        return dict(self.stats)


if __name__ == "__main__":
    feed = LiveFeed()
    feed.subscribe(lambda t: None)
    feed.on_tick({"symbol": "AAPL", "price": 150.0, "volume": 100})
    feed.on_tick({"symbol": "AAPL", "price": 150.5, "volume": 200})
    print(f"ticks: {feed.stats['ticks']}")
    print(f"recent: {len(feed.get_recent())}")
