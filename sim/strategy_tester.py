#!/usr/bin/env python3
# refactored: compare against spy benchmark
"""strategy tester with parameter sweeps and scoring"""

from sim.backtest_runner import BacktestRunner


def test_strategy(data, strategy_fn, params_list, initial_capital=100000):
    """test a strategy with multiple parameter sets.

    params_list: list of param dicts to sweep.
    returns sorted results by total_return_pct.
    """
    results = []
    for params in params_list:
        def make_strategy(p):
            def strategy(lookback, positions):
                return strategy_fn(lookback, positions, **p)
            return strategy

        runner = BacktestRunner(data, make_strategy(params), initial_capital)
        summary = runner.run()
        summary["params"] = params
        results.append(summary)
    results.sort(key=lambda r: r.get("total_return_pct", 0), reverse=True)
    return results


def param_grid(param_ranges):
    """generate all combinations from parameter ranges.

    param_ranges: dict of param_name -> list of values.
    """
    keys = list(param_ranges.keys())
    if not keys:
        return [{}]
    combos = [{}]
    for key in keys:
        new_combos = []
        for combo in combos:
            for val in param_ranges[key]:
                new_combo = combo.copy()
                new_combo[key] = val
                new_combos.append(new_combo)
        combos = new_combos
    return combos


def score_results(results, weights=None):
    """score results using weighted metrics."""
    if weights is None:
        weights = {"total_return_pct": 0.5, "total_trades": -0.1}
    for result in results:
        score = 0
        for metric, weight in weights.items():
            val = result.get(metric, 0)
            score += val * weight
        result["score"] = round(score, 4)
    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    return results


def top_n(results, n=5, metric="total_return_pct"):
    """return top n results by metric."""
    sorted_results = sorted(
        results,
        key=lambda r: r.get(metric, 0),
        reverse=True
    )
    return sorted_results[:n]


if __name__ == "__main__":
    grid = param_grid({"fast": [5, 10, 20], "slow": [30, 50]})
    print(f"parameter grid: {len(grid)} combinations")
    for combo in grid[:3]:
        print(f"  {combo}")
