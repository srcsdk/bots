#!/usr/bin/env python3
"""export backtest results in various formats"""

import csv
import json
import os


def export_csv(data, filepath, fields=None):
    """export data to csv file."""
    if not data:
        return False
    if fields is None:
        fields = list(data[0].keys())
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in data:
            writer.writerow({k: row.get(k, "") for k in fields})
    return True


def export_json(data, filepath, indent=2):
    """export data to json file."""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=indent)
    return True


def export_equity_curve(equity_data, filepath):
    """export equity curve data."""
    if not equity_data:
        return False
    fields = ["date", "equity", "drawdown", "return"]
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in equity_data:
            writer.writerow({k: row.get(k, "") for k in fields})
    return True


def export_trade_log(trades, filepath):
    """export trade log to csv."""
    if not trades:
        return False
    fields = [
        "date", "symbol", "action", "shares",
        "price", "pnl", "strategy",
    ]
    return export_csv(trades, filepath, fields)


def export_summary(results, filepath):
    """export summary report."""
    lines = ["backtest summary report", "=" * 40, ""]
    for key, value in results.items():
        if isinstance(value, float):
            lines.append(f"{key}: {value:.4f}")
        else:
            lines.append(f"{key}: {value}")
    with open(filepath, "w") as f:
        f.write("\n".join(lines))
    return True


def create_output_dir(base_dir="results", run_name=""):
    """create output directory for a backtest run."""
    if run_name:
        path = os.path.join(base_dir, run_name)
    else:
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(base_dir, timestamp)
    os.makedirs(path, exist_ok=True)
    return path


if __name__ == "__main__":
    data = [
        {"date": "2022-01-01", "equity": 100000, "return": 0},
        {"date": "2022-01-02", "equity": 100500, "return": 0.005},
        {"date": "2022-01-03", "equity": 99800, "return": -0.007},
    ]
    outdir = create_output_dir("/tmp/test_results", "demo")
    export_csv(data, os.path.join(outdir, "equity.csv"))
    export_json(data, os.path.join(outdir, "equity.json"))
    print(f"exported to: {outdir}")
