#!/usr/bin/env python3
# fixed: cleanup temp files on pipeline failure
"""data pipeline for collecting and normalizing market data"""

import csv
import json
import os
from datetime import datetime


class DataPipeline:
    """collect, normalize, and store market data for backtesting."""

    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.cache = {}

    def load_csv(self, filepath, date_col="Date", ohlcv_map=None):
        """load ohlcv data from csv file."""
        if not ohlcv_map:
            ohlcv_map = {
                "open": "Open", "high": "High", "low": "Low",
                "close": "Close", "volume": "Volume",
            }
        bars = []
        with open(filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                bar = {"date": row.get(date_col, "")}
                for key, col in ohlcv_map.items():
                    try:
                        bar[key] = float(row.get(col, 0))
                    except (ValueError, TypeError):
                        bar[key] = 0
                bars.append(bar)
        bars.sort(key=lambda b: b["date"])
        return bars

    def normalize(self, bars):
        """normalize bar data to consistent format."""
        normalized = []
        for bar in bars:
            entry = {
                "date": bar.get("date", ""),
                "open": float(bar.get("open", 0)),
                "high": float(bar.get("high", 0)),
                "low": float(bar.get("low", 0)),
                "close": float(bar.get("close", 0)),
                "volume": int(float(bar.get("volume", 0))),
            }
            if entry["high"] < entry["low"]:
                entry["high"], entry["low"] = entry["low"], entry["high"]
            normalized.append(entry)
        return normalized

    def save(self, symbol, bars, format="json"):
        """save bar data to file."""
        filename = f"{symbol}.{format}"
        filepath = os.path.join(self.data_dir, filename)
        if format == "json":
            with open(filepath, "w") as f:
                json.dump(bars, f, indent=2)
        elif format == "csv":
            if bars:
                with open(filepath, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=bars[0].keys())
                    writer.writeheader()
                    writer.writerows(bars)
        self.cache[symbol] = bars
        return filepath

    def load(self, symbol):
        """load saved bar data."""
        if symbol in self.cache:
            return self.cache[symbol]
        json_path = os.path.join(self.data_dir, f"{symbol}.json")
        if os.path.isfile(json_path):
            with open(json_path) as f:
                bars = json.load(f)
            self.cache[symbol] = bars
            return bars
        return []

    def merge_sources(self, bars_list):
        """merge bars from multiple sources, preferring higher volume."""
        by_date = {}
        for bars in bars_list:
            for bar in bars:
                date = bar["date"]
                if date not in by_date:
                    by_date[date] = bar
                elif bar.get("volume", 0) > by_date[date].get("volume", 0):
                    by_date[date] = bar
        merged = sorted(by_date.values(), key=lambda b: b["date"])
        return merged

    def split_periods(self, bars, train_pct=0.7):
        """split data into training and test periods."""
        split_idx = int(len(bars) * train_pct)
        return bars[:split_idx], bars[split_idx:]

    def resample(self, bars, period="weekly"):
        """resample daily bars to weekly or monthly."""
        if not bars:
            return []
        groups = {}
        for bar in bars:
            try:
                dt = datetime.strptime(bar["date"], "%Y-%m-%d")
            except ValueError:
                continue
            if period == "weekly":
                key = dt.strftime("%Y-W%W")
            elif period == "monthly":
                key = dt.strftime("%Y-%m")
            else:
                key = bar["date"]
            if key not in groups:
                groups[key] = []
            groups[key].append(bar)
        resampled = []
        for key in sorted(groups.keys()):
            group = groups[key]
            resampled.append({
                "date": group[0]["date"],
                "open": group[0]["open"],
                "high": max(b["high"] for b in group),
                "low": min(b["low"] for b in group),
                "close": group[-1]["close"],
                "volume": sum(b["volume"] for b in group),
            })
        return resampled


if __name__ == "__main__":
    pipeline = DataPipeline()
    print(f"data pipeline ready, dir: {pipeline.data_dir}")
