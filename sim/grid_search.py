#!/usr/bin/env python3
"""parameter optimization with grid search"""

import itertools
from sim.backtest_runner import BacktestRunner


def grid_search(data, strategy_factory, param_grid, initial_capital=100000,
                metric="total_return_pct"):
    """run exhaustive grid search over parameter space.

    strategy_factory: function(params) -> strategy_fn.
    param_grid: dict of param_name -> list of values.
    """
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    results = []
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        strategy_fn = strategy_factory(params)
        runner = BacktestRunner(data, strategy_fn, initial_capital)
        summary = runner.run()
        summary["params"] = params
        results.append(summary)
    results.sort(key=lambda r: r.get(metric, 0), reverse=True)
    return results


def top_results(results, n=10, metric="total_return_pct"):
    """return top n parameter combinations."""
    return [
        {"params": r["params"], metric: r.get(metric, 0)}
        for r in results[:n]
    ]


def parameter_sensitivity(results, param_name, metric="total_return_pct"):
    """analyze sensitivity of results to a single parameter."""
    by_value = {}
    for r in results:
        val = r["params"].get(param_name)
        if val is not None:
            by_value.setdefault(val, []).append(r.get(metric, 0))
    return {
        val: {
            "mean": round(sum(scores) / len(scores), 2),
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
            "count": len(scores),
        }
        for val, scores in sorted(by_value.items())
    }


def overfitting_check(in_sample_results, out_sample_results, top_n=5):
    """check for overfitting by comparing in-sample vs out-of-sample."""
    is_top = in_sample_results[:top_n]
    comparisons = []
    for is_result in is_top:
        params = is_result["params"]
        os_match = next(
            (r for r in out_sample_results if r["params"] == params), None
        )
        if os_match:
            comparisons.append({
                "params": params,
                "in_sample": is_result.get("total_return_pct", 0),
                "out_sample": os_match.get("total_return_pct", 0),
                "degradation": round(
                    is_result.get("total_return_pct", 0) -
                    os_match.get("total_return_pct", 0), 2
                ),
            })
    return comparisons


if __name__ == "__main__":
    grid = {"fast": [5, 10, 20], "slow": [30, 50, 100]}
    total = 1
    for vals in grid.values():
        total *= len(vals)
    print(f"grid search: {total} combinations")
    print(f"parameters: {list(grid.keys())}")
