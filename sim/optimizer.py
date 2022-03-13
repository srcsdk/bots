#!/usr/bin/env python3
"""strategy parameter optimization via grid and random search"""

import random
import itertools


class StrategyOptimizer:
    """optimize strategy parameters to maximize performance."""

    def __init__(self, strategy_fn, evaluate_fn):
        self.strategy_fn = strategy_fn
        self.evaluate_fn = evaluate_fn
        self.results = []

    def grid_search(self, param_grid, data):
        """exhaustive grid search over parameter combinations."""
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))
        self.results.clear()
        for combo in combinations:
            params = dict(zip(keys, combo))
            strategy = self.strategy_fn(params)
            score = self.evaluate_fn(strategy, data)
            self.results.append({"params": params, "score": score})
        self.results.sort(key=lambda r: r["score"], reverse=True)
        return self.results

    def random_search(self, param_ranges, data, n_trials=100):
        """random search over parameter space."""
        self.results.clear()
        for _ in range(n_trials):
            params = {}
            for key, (low, high) in param_ranges.items():
                if isinstance(low, int) and isinstance(high, int):
                    params[key] = random.randint(low, high)
                else:
                    params[key] = round(random.uniform(low, high), 4)
            strategy = self.strategy_fn(params)
            score = self.evaluate_fn(strategy, data)
            self.results.append({"params": params, "score": score})
        self.results.sort(key=lambda r: r["score"], reverse=True)
        return self.results

    def walk_forward(self, params, data, n_splits=5):
        """walk-forward optimization with expanding window."""
        split_size = len(data) // (n_splits + 1)
        scores = []
        for i in range(n_splits):
            train_end = split_size * (i + 2)
            test_start = train_end
            test_end = min(test_start + split_size, len(data))
            if test_end <= test_start:
                break
            train_data = data[:train_end]
            test_data = data[test_start:test_end]
            strategy = self.strategy_fn(params)
            train_score = self.evaluate_fn(strategy, train_data)
            test_score = self.evaluate_fn(strategy, test_data)
            scores.append({
                "split": i,
                "train_score": train_score,
                "test_score": test_score,
                "overfit_ratio": round(
                    train_score / test_score, 4
                ) if test_score != 0 else 0,
            })
        return scores

    def best(self, n=5):
        """get top n results."""
        return self.results[:n]

    def sensitivity(self, base_params, param_name, values, data):
        """test sensitivity to a single parameter."""
        results = []
        for val in values:
            params = dict(base_params)
            params[param_name] = val
            strategy = self.strategy_fn(params)
            score = self.evaluate_fn(strategy, data)
            results.append({"value": val, "score": score})
        return results


if __name__ == "__main__":
    def dummy_strategy(params):
        return params

    def dummy_evaluate(strategy, data):
        return sum(strategy.values()) / len(strategy)

    optimizer = StrategyOptimizer(dummy_strategy, dummy_evaluate)
    grid = {"a": [1, 2, 3], "b": [0.1, 0.2]}
    results = optimizer.grid_search(grid, [])
    print(f"grid search: {len(results)} combinations")
    print(f"best: {results[0]}")
