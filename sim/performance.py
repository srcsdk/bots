#!/usr/bin/env python3
"""real-time performance tracking and metrics"""

import math


class PerformanceTracker:
    """track portfolio performance in real-time."""

    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.daily_values = [initial_capital]
        self.daily_returns = []
        self.high_water_mark = initial_capital
        self.trades_today = 0

    def update(self, current_value):
        """record daily portfolio value."""
        if self.daily_values:
            prev = self.daily_values[-1]
            ret = (current_value - prev) / prev if prev > 0 else 0
            self.daily_returns.append(ret)
        self.daily_values.append(current_value)
        if current_value > self.high_water_mark:
            self.high_water_mark = current_value

    def total_return(self):
        """total return since inception."""
        if not self.daily_values:
            return 0
        current = self.daily_values[-1]
        return round(
            (current - self.initial_capital) / self.initial_capital * 100, 2
        )

    def sharpe(self, risk_free=0.02):
        """annualized sharpe ratio."""
        if len(self.daily_returns) < 2:
            return 0
        daily_rf = risk_free / 252
        excess = [r - daily_rf for r in self.daily_returns]
        mean = sum(excess) / len(excess)
        var = sum((r - mean) ** 2 for r in excess) / (len(excess) - 1)
        std = math.sqrt(var) if var > 0 else 0
        if std == 0:
            return 0
        return round(mean / std * math.sqrt(252), 4)

    def max_drawdown(self):
        """maximum drawdown percentage."""
        peak = self.daily_values[0]
        max_dd = 0
        for val in self.daily_values:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return round(max_dd * 100, 2)

    def calmar_ratio(self):
        """calmar ratio (annualized return / max drawdown)."""
        dd = self.max_drawdown()
        if dd == 0:
            return 0
        days = len(self.daily_returns)
        if days == 0:
            return 0
        total_ret = self.total_return()
        ann_ret = total_ret * (252 / days)
        return round(ann_ret / dd, 4)

    def win_rate(self):
        """percentage of positive return days."""
        if not self.daily_returns:
            return 0
        wins = sum(1 for r in self.daily_returns if r > 0)
        return round(wins / len(self.daily_returns) * 100, 1)

    def summary(self):
        """comprehensive performance summary."""
        return {
            "total_return": self.total_return(),
            "sharpe": self.sharpe(),
            "max_drawdown": self.max_drawdown(),
            "calmar": self.calmar_ratio(),
            "win_rate": self.win_rate(),
            "days": len(self.daily_returns),
            "current_value": self.daily_values[-1] if self.daily_values else 0,
            "hwm": round(self.high_water_mark, 2),
        }


if __name__ == "__main__":
    import random
    random.seed(42)
    tracker = PerformanceTracker(100000)
    value = 100000
    for _ in range(252):
        value *= (1 + random.gauss(0.0003, 0.012))
        tracker.update(round(value, 2))
    summary = tracker.summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")
