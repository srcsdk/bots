#!/usr/bin/env python3
"""manage multiple data sources for backtesting"""

import os
import json
import csv


class DataSourceManager:
    """manage and merge data from multiple sources."""

    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.sources = {}
        os.makedirs(data_dir, exist_ok=True)

    def register_source(self, name, source_type, config=None):
        """register a data source."""
        self.sources[name] = {
            "type": source_type,
            "config": config or {},
            "active": True,
        }

    def load_csv_source(self, name, filepath):
        """load data from a csv source."""
        if not os.path.isfile(filepath):
            return []
        data = []
        with open(filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                for key in row:
                    if key != "date":
                        try:
                            row[key] = float(row[key])
                        except (ValueError, TypeError):
                            pass
                data.append(row)
        return data

    def load_json_source(self, name, filepath):
        """load data from a json source."""
        if not os.path.isfile(filepath):
            return []
        with open(filepath) as f:
            return json.load(f)

    def merge_sources(self, datasets, date_field="date"):
        """merge multiple datasets by date."""
        by_date = {}
        for name, data in datasets.items():
            for row in data:
                date = row.get(date_field, "")
                if date not in by_date:
                    by_date[date] = {}
                for key, val in row.items():
                    if key != date_field:
                        by_date[date][f"{name}_{key}"] = val
                by_date[date][date_field] = date
        merged = sorted(by_date.values(), key=lambda r: r.get(date_field, ""))
        return merged

    def cache_data(self, name, data):
        """cache data locally."""
        filepath = os.path.join(self.data_dir, f"{name}_cache.json")
        with open(filepath, "w") as f:
            json.dump(data, f)

    def load_cache(self, name):
        """load cached data."""
        filepath = os.path.join(self.data_dir, f"{name}_cache.json")
        if os.path.isfile(filepath):
            with open(filepath) as f:
                return json.load(f)
        return None

    def list_sources(self):
        """list registered sources."""
        return {
            name: info["type"]
            for name, info in self.sources.items()
        }


if __name__ == "__main__":
    mgr = DataSourceManager("/tmp/data_sources")
    mgr.register_source("yahoo", "csv")
    mgr.register_source("alpaca", "api")
    print(f"sources: {mgr.list_sources()}")
    data_a = [
        {"date": "2022-01-01", "close": 100},
        {"date": "2022-01-02", "close": 102},
    ]
    data_b = [
        {"date": "2022-01-01", "volume": 50000},
        {"date": "2022-01-02", "volume": 60000},
    ]
    merged = mgr.merge_sources({"price": data_a, "vol": data_b})
    for row in merged:
        print(f"  {row}")
