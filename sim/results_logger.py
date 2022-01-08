#!/usr/bin/env python3
"""log and export backtest results"""

import csv
import json
import os
from datetime import datetime


class ResultsLogger:
    """collect and export backtest results."""

    def __init__(self, output_dir="sim_results"):
        self.output_dir = output_dir
        self.runs = []
        os.makedirs(output_dir, exist_ok=True)

    def log_run(self, name, params, results, equity_curve=None):
        """record a single backtest run."""
        run = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "params": params,
            "results": results,
        }
        self.runs.append(run)
        if equity_curve:
            self._save_equity_csv(name, equity_curve)
        return run

    def _save_equity_csv(self, name, curve):
        """save equity curve to csv."""
        safe_name = name.replace(" ", "_").lower()
        path = os.path.join(self.output_dir, f"{safe_name}_equity.csv")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "equity"])
            writer.writeheader()
            writer.writerows(curve)

    def export_json(self, filename=None):
        """export all runs to json."""
        if filename is None:
            filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(self.output_dir, filename)
        with open(path, "w") as f:
            json.dump(self.runs, f, indent=2)
        return path

    def export_csv(self, filename=None):
        """export run summaries to csv."""
        if not self.runs:
            return None
        if filename is None:
            filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = os.path.join(self.output_dir, filename)
        flat = []
        for run in self.runs:
            row = {"name": run["name"], "timestamp": run["timestamp"]}
            row.update(run.get("results", {}))
            flat.append(row)
        fieldnames = list(flat[0].keys())
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flat)
        return path

    def best_run(self, metric="total_return_pct"):
        """find best run by given metric."""
        if not self.runs:
            return None
        return max(
            self.runs,
            key=lambda r: r.get("results", {}).get(metric, float("-inf"))
        )

    def compare(self, metric="total_return_pct"):
        """compare all runs by metric, sorted descending."""
        ranked = sorted(
            self.runs,
            key=lambda r: r.get("results", {}).get(metric, 0),
            reverse=True
        )
        return [
            {"name": r["name"], metric: r["results"].get(metric)}
            for r in ranked
        ]


if __name__ == "__main__":
    logger = ResultsLogger("/tmp/sim_test")
    logger.log_run("ma_crossover", {"fast": 10, "slow": 50}, {
        "total_return_pct": 12.5, "trades": 45, "win_rate": 55.2
    })
    logger.log_run("rsi_strategy", {"period": 14, "oversold": 30}, {
        "total_return_pct": 8.3, "trades": 32, "win_rate": 60.1
    })
    print(f"best: {logger.best_run()['name']}")
    for r in logger.compare():
        print(f"  {r['name']}: {r['total_return_pct']}%")
