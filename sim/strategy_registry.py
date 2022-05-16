#!/usr/bin/env python3
"""registry mapping strategy names to their entry points and metadata"""

import importlib
import importlib.util
import os
import sys


STRATEGY_REGISTRY = {
    "gapup": {
        "module": "gapup",
        "function": "scan",
        "description": "buy on rsi oversold + macd turning up at 52wk low with gap down",
        "category": "mean_reversion",
    },
    "bcross": {
        "module": "bcross",
        "function": "scan",
        "description": "gapup variant requiring macd line cross above signal",
        "category": "mean_reversion",
    },
    "across": {
        "module": "across",
        "function": "scan",
        "description": "bcross without macd banana requirement",
        "category": "mean_reversion",
    },
    "nolo": {
        "module": "nolo",
        "function": "scan",
        "description": "across within 30pct of 52wk low with distance metrics",
        "category": "mean_reversion",
    },
    "nobr": {
        "module": "nobr",
        "function": "scan",
        "description": "nolo with relaxed rsi threshold at 45 with quality scoring",
        "category": "mean_reversion",
    },
    "movo": {
        "module": "movo",
        "function": "scan_movo",
        "description": "momentum + volume breakout above sma with volume surge",
        "category": "momentum",
    },
    "mobr": {
        "module": "movo",
        "function": "scan_mobr",
        "description": "nobr + movo combined signal",
        "category": "momentum",
    },
    "turtle": {
        "module": "turtle",
        "function": "scan",
        "description": "donchian channel breakout with atr position sizing",
        "category": "trend",
    },
    "dca": {
        "module": "dca",
        "function": "scan",
        "description": "dollar cost averaging with rsi/volatility adjustments",
        "category": "passive",
    },
    "vested": {
        "module": "vested",
        "function": "analyze",
        "description": "reverse engineer indicators that flagged bottoms in winners",
        "category": "pattern",
    },
    "reta": {
        "module": "reta",
        "function": "analyze_ticker",
        "description": "short squeeze detection with volume and compression scoring",
        "category": "event",
    },
    "hype": {
        "module": "hype",
        "function": "scan_all",
        "description": "social media ticker sentiment aggregator from reddit",
        "category": "sentiment",
    },
    "wsb": {
        "module": "wsb",
        "function": "scan_wsb",
        "description": "wallstreetbets ticker mention scraper",
        "category": "sentiment",
    },
    "sector_rotation": {
        "module": "sector_rotation",
        "function": "scan",
        "description": "sector etf relative strength rotation",
        "category": "rotation",
    },
    "ichimoku": {
        "module": "ichimoku",
        "function": "scan",
        "description": "ichimoku cloud breakout signals",
        "category": "trend",
    },
    "fibonacci": {
        "module": "fibonacci",
        "function": "scan",
        "description": "fibonacci retracement level entries",
        "category": "support_resistance",
    },
    "darvas": {
        "module": "darvas",
        "function": "scan",
        "description": "darvas box breakout detector",
        "category": "trend",
    },
    "pairs": {
        "module": "pairs",
        "function": "scan",
        "description": "pairs trading with cointegration checks",
        "category": "stat_arb",
    },
    "gridbot": {
        "module": "gridbot",
        "function": "scan",
        "description": "grid trading with configurable levels",
        "category": "range",
    },
    "vwap_strategy": {
        "module": "vwap_strategy",
        "function": "scan",
        "description": "vwap-based intraday mean reversion",
        "category": "intraday",
    },
    "wheel": {
        "module": "wheel",
        "function": "scan",
        "description": "options wheel strategy with csp and cc selection",
        "category": "options",
    },
    "condor": {
        "module": "condor",
        "function": "scan",
        "description": "iron condor setup with delta-based strikes",
        "category": "options",
    },
    "canslim": {
        "module": "canslim",
        "function": "scan",
        "description": "canslim growth stock screening",
        "category": "fundamental",
    },
    "swingpat": {
        "module": "swingpat",
        "function": "scan",
        "description": "swing pattern recognition with candlestick analysis",
        "category": "pattern",
    },
    "riskpar": {
        "module": "riskpar",
        "function": "scan",
        "description": "risk parity portfolio allocation",
        "category": "allocation",
    },
}


def get_strategy(name):
    """import and return the strategy function by registry name.

    returns the callable or None if not found.
    """
    entry = STRATEGY_REGISTRY.get(name)
    if entry is None:
        return None
    mod_name = entry["module"]
    fn_name = entry["function"]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        fpath = os.path.join(root, f"{mod_name}.py")
        spec = importlib.util.spec_from_file_location(mod_name, fpath)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, fn_name, None)
    except Exception:
        return None


def list_by_category(category=None):
    """list strategies optionally filtered by category.

    returns list of dicts with name, module, function, description.
    """
    results = []
    for name, entry in sorted(STRATEGY_REGISTRY.items()):
        if category and entry.get("category") != category:
            continue
        results.append({
            "name": name,
            "module": entry["module"],
            "function": entry["function"],
            "description": entry["description"],
            "category": entry.get("category", "uncategorized"),
        })
    return results


def get_categories():
    """return set of all strategy categories."""
    return sorted(set(e.get("category", "uncategorized") for e in STRATEGY_REGISTRY.values()))


def wrap_for_backtest(name):
    """wrap a strategy's scan function into a backtest-compatible callable.

    the backtest engine expects fn(bars, positions) -> signal dict.
    most strategies use scan(ticker, period) which fetches data internally.
    this wrapper generates signals from raw bar data instead.
    """
    entry = STRATEGY_REGISTRY.get(name)
    if entry is None:
        return None
    category = entry.get("category", "")
    if category in ("mean_reversion",):
        return _mean_reversion_wrapper(name)
    elif category in ("momentum", "trend"):
        return _momentum_wrapper(name)
    else:
        return _generic_wrapper(name)


def _mean_reversion_wrapper(name):
    """wrapper for mean reversion strategies using rsi + sma logic."""
    def strategy_fn(bars, positions):
        if len(bars) < 30:
            return None
        closes = [b["close"] for b in bars]
        n = len(closes)
        period = 14
        if n < period + 1:
            return None
        deltas = [closes[i] - closes[i - 1] for i in range(1, n)]
        gains = [max(d, 0) for d in deltas[-period:]]
        losses = [abs(min(d, 0)) for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            rsi_val = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100 - (100 / (1 + rs))
        sma_20 = sum(closes[-20:]) / 20
        if rsi_val < 30 and closes[-1] < sma_20 and not positions:
            return {"action": "buy", "symbol": "default", "size": 100}
        elif rsi_val > 70 and positions:
            return {"action": "sell", "symbol": "default", "size": 100}
        return None
    strategy_fn.__name__ = f"{name}_mean_reversion"
    return strategy_fn


def _momentum_wrapper(name):
    """wrapper for momentum/trend strategies using moving average crossover."""
    def strategy_fn(bars, positions):
        if len(bars) < 50:
            return None
        closes = [b["close"] for b in bars]
        volumes = [b.get("volume", 0) for b in bars]
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50
        vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 1
        vol_ratio = volumes[-1] / vol_avg if vol_avg > 0 else 1
        cross_up = closes[-1] > sma_20 and closes[-2] <= sma_20 if len(closes) > 1 else False
        trend_up = sma_20 > sma_50
        if cross_up and trend_up and vol_ratio > 1.2 and not positions:
            return {"action": "buy", "symbol": "default", "size": 100}
        elif closes[-1] < sma_50 and positions:
            return {"action": "sell", "symbol": "default", "size": 100}
        return None
    strategy_fn.__name__ = f"{name}_momentum"
    return strategy_fn


def _generic_wrapper(name):
    """generic wrapper using simple sma crossover for strategies without clear signal type."""
    def strategy_fn(bars, positions):
        if len(bars) < 20:
            return None
        closes = [b["close"] for b in bars]
        sma_5 = sum(closes[-5:]) / 5
        sma_20 = sum(closes[-20:]) / 20
        if sma_5 > sma_20 and not positions:
            return {"action": "buy", "symbol": "default", "size": 100}
        elif sma_5 < sma_20 and positions:
            return {"action": "sell", "symbol": "default", "size": 100}
        return None
    strategy_fn.__name__ = f"{name}_generic"
    return strategy_fn


if __name__ == "__main__":
    print(f"registered {len(STRATEGY_REGISTRY)} strategies")
    for cat in get_categories():
        strats = list_by_category(cat)
        print(f"\n{cat} ({len(strats)}):")
        for s in strats:
            print(f"  {s['name']:<20} {s['description']}")
