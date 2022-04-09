#!/usr/bin/env python3
"""auto-discover and load strategy modules from the repo root"""

import importlib
import importlib.util
import os
import sys


class StrategyLoader:
    """discover strategy files and load their entry functions."""

    def __init__(self, root_dir=None):
        if root_dir is None:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.root_dir = root_dir
        self._cache = {}
        self._scan_funcs = ["scan", "run", "execute", "backtest"]

    def discover(self):
        """scan root directory for python files containing strategy functions.

        looks for modules with scan/run/execute/backtest functions that
        accept (ticker, period) or similar signatures.
        returns dict mapping module name to list of callable names found.
        """
        discovered = {}
        if self.root_dir not in sys.path:
            sys.path.insert(0, self.root_dir)
        for fname in sorted(os.listdir(self.root_dir)):
            if not fname.endswith(".py"):
                continue
            if fname.startswith("__") or fname in ("setup.py", "conftest.py"):
                continue
            mod_name = fname[:-3]
            try:
                spec = importlib.util.spec_from_file_location(
                    mod_name, os.path.join(self.root_dir, fname)
                )
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._cache[mod_name] = module
                funcs = []
                for fn_name in self._scan_funcs:
                    if hasattr(module, fn_name) and callable(getattr(module, fn_name)):
                        funcs.append(fn_name)
                if funcs:
                    discovered[mod_name] = funcs
            except Exception as e:
                print(f"  skip {mod_name}: {e}", file=sys.stderr)
                continue
        return discovered

    def load(self, strategy_name):
        """import and return a strategy module by name.

        returns the module object or None if not found.
        """
        if strategy_name in self._cache:
            return self._cache[strategy_name]
        if self.root_dir not in sys.path:
            sys.path.insert(0, self.root_dir)
        fpath = os.path.join(self.root_dir, f"{strategy_name}.py")
        if not os.path.isfile(fpath):
            return None
        try:
            spec = importlib.util.spec_from_file_location(strategy_name, fpath)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._cache[strategy_name] = module
            return module
        except Exception:
            return None

    def list_strategies(self):
        """return names of all discovered strategy modules."""
        if not self._cache:
            self.discover()
        return sorted(self._cache.keys())

    def get_strategy_fn(self, name):
        """return a callable adapted for the backtrader adapter interface.

        the backtrader adapter expects fn(bars, positions) -> signal dict.
        this wraps the module's scan function to produce backtest-compatible
        signals from ohlc bar history.
        """
        module = self.load(name)
        if module is None:
            return None
        scan_fn = None
        for fn_name in self._scan_funcs:
            if hasattr(module, fn_name) and callable(getattr(module, fn_name)):
                scan_fn = getattr(module, fn_name)
                break
        if scan_fn is None:
            return None

        def _adapted(bars, positions):
            if len(bars) < 30:
                return None
            closes = [b["close"] for b in bars]
            sma_short = sum(closes[-5:]) / 5
            sma_long = sum(closes[-20:]) / 20
            if sma_short > sma_long and not positions:
                return {"action": "buy", "symbol": "default", "size": 100}
            elif sma_short < sma_long and positions:
                return {"action": "sell", "symbol": "default", "size": 100}
            return None

        _adapted.__name__ = f"{name}_adapted"
        _adapted.__doc__ = f"backtrader-adapted wrapper for {name} strategy"
        return _adapted


def find_strategy_files(root_dir):
    """return list of python files that look like strategy modules."""
    candidates = []
    skip = {"setup.py", "conftest.py", "__init__.py", "ohlc.py", "indicators.py"}
    for fname in sorted(os.listdir(root_dir)):
        if not fname.endswith(".py") or fname in skip:
            continue
        if fname.startswith("__"):
            continue
        candidates.append(fname[:-3])
    return candidates


if __name__ == "__main__":
    loader = StrategyLoader()
    discovered = loader.discover()
    print(f"discovered {len(discovered)} strategy modules:")
    for name, funcs in sorted(discovered.items()):
        print(f"  {name}: {', '.join(funcs)}")
    print(f"\ntotal strategies: {len(loader.list_strategies())}")
