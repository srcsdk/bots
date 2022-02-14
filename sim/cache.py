#!/usr/bin/env python3
"""caching layer for historical data requests"""

import json
import os
import time
import hashlib


DEFAULT_CACHE_DIR = os.path.expanduser("~/.cache/bots_sim")


def cache_key(symbol, timeframe, start, end):
    """generate unique cache key from query params."""
    raw = f"{symbol}_{timeframe}_{start}_{end}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached(symbol, timeframe, start, end, cache_dir=None, ttl=86400):
    """retrieve cached data if fresh."""
    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR
    key = cache_key(symbol, timeframe, start, end)
    path = os.path.join(cache_dir, f"{key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if time.time() - data.get("cached_at", 0) > ttl:
            return None
        return data.get("bars", [])
    except (json.JSONDecodeError, KeyError):
        return None


def set_cached(symbol, timeframe, start, end, bars, cache_dir=None):
    """store data in cache."""
    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)
    key = cache_key(symbol, timeframe, start, end)
    path = os.path.join(cache_dir, f"{key}.json")
    data = {
        "symbol": symbol,
        "timeframe": timeframe,
        "start": start,
        "end": end,
        "cached_at": time.time(),
        "bars": bars,
    }
    with open(path, "w") as f:
        json.dump(data, f)


def clear_cache(cache_dir=None):
    """remove all cached files."""
    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR
    if not os.path.exists(cache_dir):
        return 0
    count = 0
    for fname in os.listdir(cache_dir):
        if fname.endswith(".json"):
            os.remove(os.path.join(cache_dir, fname))
            count += 1
    return count


def cache_stats(cache_dir=None):
    """return cache statistics."""
    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR
    if not os.path.exists(cache_dir):
        return {"entries": 0, "size_bytes": 0}
    entries = 0
    total_size = 0
    for fname in os.listdir(cache_dir):
        if fname.endswith(".json"):
            entries += 1
            total_size += os.path.getsize(os.path.join(cache_dir, fname))
    return {"entries": entries, "size_bytes": total_size}


if __name__ == "__main__":
    print(f"cache dir: {DEFAULT_CACHE_DIR}")
    stats = cache_stats()
    print(f"entries: {stats['entries']}, size: {stats['size_bytes']} bytes")
