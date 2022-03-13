#!/usr/bin/env python3
"""generate formatted backtest reports"""

import json
import os
from datetime import datetime


class ReportGenerator:
    """generate backtest result reports in multiple formats."""

    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, results, strategy_name, format="json"):
        """generate report in specified format."""
        report = self._build_report(results, strategy_name)
        if format == "json":
            return self._to_json(report, strategy_name)
        elif format == "text":
            return self._to_text(report, strategy_name)
        return None

    def _build_report(self, results, strategy_name):
        """build structured report from results."""
        return {
            "strategy": strategy_name,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "summary": {
                "total_trades": results.get("total_trades", 0),
                "total_pnl": results.get("total_pnl", 0),
                "total_return_pct": results.get("total_return_pct", 0),
                "win_rate": results.get("win_rate", 0),
                "sharpe": results.get("sharpe", 0),
                "max_drawdown": results.get("max_drawdown_pct", 0),
            },
            "details": {
                "avg_win": results.get("avg_win", 0),
                "avg_loss": results.get("avg_loss", 0),
                "best_trade": results.get("best_trade", 0),
                "worst_trade": results.get("worst_trade", 0),
            },
        }

    def _to_json(self, report, name):
        """save report as json."""
        filename = f"{name}_{report['generated'].replace(' ', '_')}.json"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        return filepath

    def _to_text(self, report, name):
        """save report as formatted text."""
        filename = f"{name}_{report['generated'].replace(' ', '_')}.txt"
        filepath = os.path.join(self.output_dir, filename)
        lines = [
            f"backtest report: {report['strategy']}",
            f"generated: {report['generated']}",
            "",
            "summary:",
        ]
        for key, val in report["summary"].items():
            lines.append(f"  {key}: {val}")
        lines.append("")
        lines.append("details:")
        for key, val in report["details"].items():
            lines.append(f"  {key}: {val}")
        with open(filepath, "w") as f:
            f.write("\n".join(lines) + "\n")
        return filepath

    def compare(self, results_list, names):
        """generate comparison report across strategies."""
        comparison = []
        for results, name in zip(results_list, names):
            comparison.append({
                "strategy": name,
                "return_pct": results.get("total_return_pct", 0),
                "win_rate": results.get("win_rate", 0),
                "sharpe": results.get("sharpe", 0),
                "trades": results.get("total_trades", 0),
            })
        comparison.sort(key=lambda x: x["return_pct"], reverse=True)
        return comparison


if __name__ == "__main__":
    gen = ReportGenerator()
    sample = {
        "total_trades": 50, "total_pnl": 2500,
        "total_return_pct": 25.0, "win_rate": 62.0,
    }
    path = gen.generate(sample, "test_strategy", format="json")
    print(f"report saved: {path}")
