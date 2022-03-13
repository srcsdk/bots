#!/usr/bin/env python3
"""strategy registry for managing and selecting strategies"""


class StrategyRegistry:
    """register and manage trading strategies."""

    def __init__(self):
        self._strategies = {}
        self._metadata = {}

    def register(self, name, strategy_fn, description="", tags=None,
                 params=None):
        """register a strategy function."""
        self._strategies[name] = strategy_fn
        self._metadata[name] = {
            "description": description,
            "tags": tags or [],
            "params": params or {},
            "active": True,
        }

    def get(self, name):
        """get a strategy by name."""
        return self._strategies.get(name)

    def list_strategies(self, tag=None):
        """list registered strategies, optionally filtered by tag."""
        results = []
        for name, meta in self._metadata.items():
            if tag and tag not in meta.get("tags", []):
                continue
            results.append({
                "name": name,
                "description": meta["description"],
                "tags": meta["tags"],
                "active": meta["active"],
            })
        return results

    def enable(self, name):
        """enable a strategy."""
        if name in self._metadata:
            self._metadata[name]["active"] = True

    def disable(self, name):
        """disable a strategy."""
        if name in self._metadata:
            self._metadata[name]["active"] = False

    def active_strategies(self):
        """get all active strategies."""
        return {
            name: fn for name, fn in self._strategies.items()
            if self._metadata.get(name, {}).get("active", False)
        }

    def get_params(self, name):
        """get default parameters for a strategy."""
        return dict(self._metadata.get(name, {}).get("params", {}))

    def remove(self, name):
        """remove a strategy from registry."""
        self._strategies.pop(name, None)
        self._metadata.pop(name, None)


registry = StrategyRegistry()


def register_defaults():
    """register built-in strategies."""
    def ma_cross(lookback, positions, fast=10, slow=20):
        if len(lookback) < slow:
            return None
        closes = [b["close"] for b in lookback]
        fast_ma = sum(closes[-fast:]) / fast
        slow_ma = sum(closes[-slow:]) / slow
        if fast_ma > slow_ma and not positions.get("default"):
            return {"action": "buy", "symbol": "default", "size": 0.5}
        if fast_ma < slow_ma and positions.get("default", 0) > 0:
            return {"action": "sell", "symbol": "default"}
        return None

    registry.register(
        "ma_crossover", ma_cross,
        description="moving average crossover strategy",
        tags=["trend", "momentum"],
        params={"fast": 10, "slow": 20},
    )


if __name__ == "__main__":
    register_defaults()
    strategies = registry.list_strategies()
    print(f"registered strategies: {len(strategies)}")
    for s in strategies:
        print(f"  {s['name']}: {s['description']} [{', '.join(s['tags'])}]")
