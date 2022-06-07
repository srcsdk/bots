#!/usr/bin/env python3
"""data ingestion and transformation pipeline"""

import csv
import json
import os


class DataPipeline:
    """pipeline for loading, transforming, and caching market data."""

    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.transformers = []

    def add_transform(self, func):
        """add a transformation step to the pipeline."""
        self.transformers.append(func)
        return self

    def load_csv(self, filepath, date_col="date"):
        """load data from csv file."""
        data = []
        with open(filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                for key in row:
                    if key != date_col:
                        try:
                            row[key] = float(row[key])
                        except (ValueError, TypeError):
                            pass
                data.append(row)
        return data

    def load_json(self, filepath):
        """load data from json file."""
        with open(filepath) as f:
            return json.load(f)

    def process(self, data):
        """run data through all transform steps."""
        for transform in self.transformers:
            data = transform(data)
        return data

    def cache_data(self, key, data):
        """cache processed data."""
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        with open(filepath, "w") as f:
            json.dump(data, f)

    def load_cached(self, key):
        """load cached data if available."""
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.isfile(filepath):
            with open(filepath) as f:
                return json.load(f)
        return None

    def clear_cache(self):
        """remove all cached data."""
        for name in os.listdir(self.cache_dir):
            filepath = os.path.join(self.cache_dir, name)
            if os.path.isfile(filepath):
                os.remove(filepath)


def fill_missing(data, fields=None):
    """forward-fill missing values in data."""
    if not data:
        return data
    if fields is None:
        fields = [k for k in data[0] if k != "date"]
    last_values = {}
    for row in data:
        for field in fields:
            val = row.get(field)
            if val is None or val == "":
                row[field] = last_values.get(field, 0)
            else:
                last_values[field] = val
    return data


def add_returns(data, price_field="close"):
    """add daily return column to data."""
    for i in range(len(data)):
        if i == 0:
            data[i]["return"] = 0
        else:
            prev = data[i - 1].get(price_field, 0)
            curr = data[i].get(price_field, 0)
            if prev > 0:
                data[i]["return"] = round((curr - prev) / prev, 6)
            else:
                data[i]["return"] = 0
    return data


def add_moving_average(data, period=20, field="close"):
    """add moving average column to data."""
    for i in range(len(data)):
        if i < period - 1:
            data[i][f"ma_{period}"] = None
        else:
            values = [data[j][field] for j in range(i - period + 1, i + 1)]
            data[i][f"ma_{period}"] = round(sum(values) / period, 4)
    return data


if __name__ == "__main__":
    import random
    random.seed(42)
    sample = []
    price = 100
    for i in range(50):
        price *= (1 + random.gauss(0, 0.02))
        sample.append({
            "date": f"2022-01-{i + 1:02d}",
            "close": round(price, 2),
            "volume": random.randint(100000, 500000),
        })
    pipeline = DataPipeline("/tmp/test_cache")
    pipeline.add_transform(add_returns)
    pipeline.add_transform(lambda d: add_moving_average(d, 10))
    processed = pipeline.process(sample)
    for row in processed[-5:]:
        print(f"  {row['date']}: close={row['close']}, "
              f"return={row['return']:.4f}, ma_10={row.get('ma_10')}")
