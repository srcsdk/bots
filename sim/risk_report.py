#!/usr/bin/env python3
"""risk analysis reporting for portfolio assessment"""


def var_historical(returns, confidence=0.95):
    """value at risk using historical simulation."""
    if not returns:
        return 0
    sorted_returns = sorted(returns)
    index = int((1 - confidence) * len(sorted_returns))
    return round(sorted_returns[max(0, index)] * 100, 2)


def cvar(returns, confidence=0.95):
    """conditional value at risk (expected shortfall)."""
    if not returns:
        return 0
    sorted_returns = sorted(returns)
    cutoff = int((1 - confidence) * len(sorted_returns))
    if cutoff == 0:
        return round(sorted_returns[0] * 100, 2)
    tail = sorted_returns[:cutoff]
    return round(sum(tail) / len(tail) * 100, 2)


def risk_metrics(equity_curve):
    """calculate comprehensive risk metrics from equity curve."""
    if len(equity_curve) < 2:
        return {}
    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i - 1] > 0:
            r = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            returns.append(r)
    if not returns:
        return {}
    avg_return = sum(returns) / len(returns)
    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
    std_dev = variance ** 0.5
    neg_returns = [r for r in returns if r < 0]
    neg_var = 0
    if neg_returns:
        neg_var = sum(r ** 2 for r in neg_returns) / len(neg_returns)
    downside_dev = neg_var ** 0.5
    sharpe = avg_return / std_dev if std_dev > 0 else 0
    sortino = avg_return / downside_dev if downside_dev > 0 else 0
    return {
        "avg_daily_return": round(avg_return * 100, 4),
        "daily_std_dev": round(std_dev * 100, 4),
        "downside_dev": round(downside_dev * 100, 4),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "var_95": var_historical(returns, 0.95),
        "cvar_95": cvar(returns, 0.95),
        "best_day": round(max(returns) * 100, 2),
        "worst_day": round(min(returns) * 100, 2),
        "positive_days": len([r for r in returns if r > 0]),
        "negative_days": len([r for r in returns if r < 0]),
        "win_rate": round(
            len([r for r in returns if r > 0]) / len(returns) * 100, 1
        ),
    }


def format_risk_report(metrics):
    """format risk metrics into readable report."""
    lines = ["risk analysis report", "=" * 40]
    labels = {
        "avg_daily_return": "avg daily return",
        "daily_std_dev": "daily std deviation",
        "sharpe_ratio": "sharpe ratio",
        "sortino_ratio": "sortino ratio",
        "var_95": "value at risk (95%)",
        "cvar_95": "conditional var (95%)",
        "best_day": "best day",
        "worst_day": "worst day",
        "win_rate": "win rate",
    }
    for key, label in labels.items():
        val = metrics.get(key, "n/a")
        if isinstance(val, float):
            if "ratio" in key:
                lines.append(f"  {label}: {val}")
            else:
                lines.append(f"  {label}: {val}%")
        else:
            lines.append(f"  {label}: {val}")
    return "\n".join(lines)


if __name__ == "__main__":
    import random
    random.seed(42)
    equity = [100000]
    for _ in range(252):
        r = random.gauss(0.0003, 0.015)
        equity.append(equity[-1] * (1 + r))
    metrics = risk_metrics(equity)
    print(format_risk_report(metrics))
