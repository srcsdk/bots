#!/usr/bin/env python3
"""plot backtest results with matplotlib"""

import os


def plot_equity_curve(equity_curve, title="equity curve", save_path=None):
    """plot equity curve from backtest results."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dates = [e["date"] for e in equity_curve]
    values = [e["equity"] for e in equity_curve]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, values, linewidth=1.5)
    ax.set_title(title)
    ax.set_xlabel("date")
    ax.set_ylabel("equity ($)")
    ax.tick_params(axis="x", rotation=45)
    step = max(1, len(dates) // 20)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)])
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=100)
    plt.close(fig)
    return save_path


def plot_drawdown(equity_curve, save_path=None):
    """plot drawdown chart from equity curve."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    values = [e["equity"] for e in equity_curve]
    dates = [e["date"] for e in equity_curve]
    peak = values[0]
    drawdown = []
    for v in values:
        if v > peak:
            peak = v
        dd = (v - peak) / peak * 100
        drawdown.append(dd)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.fill_between(range(len(drawdown)), drawdown, 0, alpha=0.5, color="red")
    ax.set_title("drawdown (%)")
    ax.set_ylabel("drawdown %")
    step = max(1, len(dates) // 20)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=100)
    plt.close(fig)
    return save_path


def plot_trade_markers(data, trades, save_path=None):
    """plot price chart with buy/sell markers."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dates = [d["date"] for d in data]
    closes = [d["close"] for d in data]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, closes, linewidth=1, color="gray", alpha=0.7)
    date_idx = {d: i for i, d in enumerate(dates)}
    for trade in trades:
        idx = date_idx.get(trade["date"])
        if idx is None:
            continue
        color = "green" if trade["action"] == "buy" else "red"
        marker = "^" if trade["action"] == "buy" else "v"
        ax.scatter(idx, trade["price"], color=color, marker=marker, s=80, zorder=5)
    ax.set_title("trades")
    step = max(1, len(dates) // 20)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=100)
    plt.close(fig)
    return save_path


if __name__ == "__main__":
    curve = [{"date": f"2021-01-{i+1:02d}", "equity": 100000 + i * 100} for i in range(30)]
    plot_equity_curve(curve, save_path="/tmp/test_equity.png")
    print("saved equity curve to /tmp/test_equity.png")
