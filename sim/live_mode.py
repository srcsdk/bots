#!/usr/bin/env python3
"""live trading mode with paper/real switching"""

import time
import json
import os


class LiveMode:
    """manage live trading operations."""

    def __init__(self, mode="paper", config=None):
        self.mode = mode
        self.config = config or {}
        self.running = False
        self.trades_executed = 0
        self.errors = []
        self.last_heartbeat = 0

    def start(self):
        """start live trading loop."""
        self.running = True
        self.last_heartbeat = time.time()
        return {"status": "started", "mode": self.mode}

    def stop(self):
        """stop live trading."""
        self.running = False
        return {
            "status": "stopped",
            "trades": self.trades_executed,
            "errors": len(self.errors),
        }

    def heartbeat(self):
        """check system health."""
        now = time.time()
        elapsed = now - self.last_heartbeat
        self.last_heartbeat = now
        return {
            "alive": self.running,
            "mode": self.mode,
            "interval": round(elapsed, 1),
            "trades": self.trades_executed,
        }

    def execute_signal(self, signal):
        """execute a trading signal."""
        if not self.running:
            return {"success": False, "reason": "not running"}
        if self.mode == "paper":
            return self._paper_execute(signal)
        return self._live_execute(signal)

    def _paper_execute(self, signal):
        """simulate trade execution."""
        self.trades_executed += 1
        return {
            "success": True,
            "mode": "paper",
            "action": signal.get("action"),
            "symbol": signal.get("symbol"),
        }

    def _live_execute(self, signal):
        """execute real trade (requires broker connection)."""
        self.trades_executed += 1
        return {
            "success": True,
            "mode": "live",
            "action": signal.get("action"),
            "symbol": signal.get("symbol"),
            "warning": "live execution",
        }

    def save_state(self, filepath="live_state.json"):
        """save current state."""
        state = {
            "mode": self.mode,
            "running": self.running,
            "trades": self.trades_executed,
            "errors": self.errors,
        }
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)


if __name__ == "__main__":
    live = LiveMode(mode="paper")
    status = live.start()
    print(f"started: {status}")
    result = live.execute_signal({
        "action": "buy", "symbol": "AAPL", "shares": 100,
    })
    print(f"executed: {result}")
    hb = live.heartbeat()
    print(f"heartbeat: {hb}")
    stopped = live.stop()
    print(f"stopped: {stopped}")
