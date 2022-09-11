#!/usr/bin/env python3
"""matplotlib multi-strategy comparison charts"""

import os
import math

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    plt = None


class ComparisonChart:
    """build and render multi-strategy comparison charts."""

    def __init__(self, title="strategy comparison"):
        self.title = title
        self._curves = {}
        self._colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
            "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
        ]

    def add_equity_curve(self, name, dates, values):
        """add a strategy's equity curve for comparison.

        name: strategy identifier
        dates: list of date strings YYYY-MM-DD
        values: list of portfolio values (floats)
        """
        self._curves[name] = {"dates": list(dates), "values": list(values)}

    def plot_comparison(self, output_path=None):
        """render all equity curves overlaid on a single chart.

        returns the figure object. saves to output_path if provided.
        """
        if not HAS_MPL:
            print("matplotlib not available, skipping chart")
            return None
        if not self._curves:
            return None
        fig, ax = plt.subplots(figsize=(14, 7))
        for idx, (name, data) in enumerate(sorted(self._curves.items())):
            color = self._colors[idx % len(self._colors)]
            ax.plot(
                range(len(data["values"])),
                data["values"],
                label=name,
                color=color,
                linewidth=1.2,
                alpha=0.85,
            )
        ax.set_title(self.title, fontsize=14, fontweight="bold")
        ax.set_xlabel("trading days")
        ax.set_ylabel("portfolio value ($)")
        ax.legend(loc="upper left", fontsize=8, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
        fig.tight_layout()
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            fig.savefig(output_path, dpi=150)
            plt.close(fig)
        return fig

    def plot_drawdowns(self, output_path=None):
        """render drawdown chart for each strategy.

        drawdown = (peak - current) / peak * 100.
        returns figure object.
        """
        if not HAS_MPL or not self._curves:
            return None
        fig, ax = plt.subplots(figsize=(14, 5))
        for idx, (name, data) in enumerate(sorted(self._curves.items())):
            values = data["values"]
            drawdowns = _calc_drawdown_series(values)
            color = self._colors[idx % len(self._colors)]
            ax.fill_between(
                range(len(drawdowns)),
                drawdowns,
                alpha=0.3,
                color=color,
                label=name,
            )
            ax.plot(range(len(drawdowns)), drawdowns, color=color, linewidth=0.8)
        ax.set_title("drawdown comparison", fontsize=14)
        ax.set_xlabel("trading days")
        ax.set_ylabel("drawdown (%)")
        ax.legend(loc="lower left", fontsize=8, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=min(-1, ax.get_ylim()[0]))
        fig.tight_layout()
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            fig.savefig(output_path, dpi=150)
            plt.close(fig)
        return fig

    def plot_monthly_returns(self, name, dates, values, output_path=None):
        """render a monthly return heatmap for a single strategy.

        groups returns by year (row) and month (column).
        """
        if not HAS_MPL:
            return None
        monthly = _aggregate_monthly_returns(dates, values)
        if not monthly:
            return None
        years = sorted(set(y for y, _ in monthly.keys()))
        months = list(range(1, 13))
        grid = []
        for year in years:
            row = []
            for month in months:
                row.append(monthly.get((year, month), 0.0))
            grid.append(row)
        fig, ax = plt.subplots(figsize=(12, max(3, len(years) * 0.6)))
        im = ax.imshow(grid, cmap="RdYlGn", aspect="auto", vmin=-10, vmax=10)
        ax.set_xticks(range(12))
        ax.set_xticklabels(["jan", "feb", "mar", "apr", "may", "jun",
                            "jul", "aug", "sep", "oct", "nov", "dec"])
        ax.set_yticks(range(len(years)))
        ax.set_yticklabels([str(y) for y in years])
        for i in range(len(years)):
            for j in range(12):
                val = grid[i][j]
                color = "white" if abs(val) > 5 else "black"
                ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                        fontsize=7, color=color)
        ax.set_title(f"{name} monthly returns (%)", fontsize=12)
        fig.colorbar(im, ax=ax, shrink=0.8, label="return %")
        fig.tight_layout()
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            fig.savefig(output_path, dpi=150)
            plt.close(fig)
        return fig

    def plot_indicator_attribution(self, rankings, output_path=None):
        """horizontal bar chart showing indicator effectiveness scores.

        rankings: dict mapping indicator_name -> score (float).
        """
        if not HAS_MPL or not rankings:
            return None
        sorted_items = sorted(rankings.items(), key=lambda x: x[1], reverse=True)
        names = [x[0] for x in sorted_items]
        scores = [x[1] for x in sorted_items]
        fig, ax = plt.subplots(figsize=(10, max(4, len(names) * 0.4)))
        colors = ["#2ca02c" if s > 0 else "#d62728" for s in scores]
        ax.barh(range(len(names)), scores, color=colors, alpha=0.8)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=9)
        ax.set_xlabel("effectiveness score")
        ax.set_title("indicator attribution", fontsize=12)
        ax.grid(True, alpha=0.3, axis="x")
        ax.invert_yaxis()
        fig.tight_layout()
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            fig.savefig(output_path, dpi=150)
            plt.close(fig)
        return fig

    def save_report(self, output_dir):
        """save all available charts as png files to a directory.

        generates comparison, drawdown, and attribution charts.
        returns list of saved file paths.
        """
        if not HAS_MPL:
            print("matplotlib not available, cannot save report")
            return []
        os.makedirs(output_dir, exist_ok=True)
        saved = []
        comp_path = os.path.join(output_dir, "equity_comparison.png")
        if self.plot_comparison(comp_path):
            saved.append(comp_path)
        dd_path = os.path.join(output_dir, "drawdown_comparison.png")
        if self.plot_drawdowns(dd_path):
            saved.append(dd_path)
        for name, data in self._curves.items():
            monthly_path = os.path.join(output_dir, f"{name}_monthly.png")
            if self.plot_monthly_returns(name, data["dates"], data["values"], monthly_path):
                saved.append(monthly_path)
        return saved


def _calc_drawdown_series(values):
    """calculate drawdown percentage series from equity values."""
    if not values:
        return []
    peak = values[0]
    drawdowns = []
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        drawdowns.append(-dd)
    return drawdowns


def _aggregate_monthly_returns(dates, values):
    """group daily values into monthly returns.

    returns dict of (year, month) -> return_pct.
    """
    if len(dates) < 2 or len(values) < 2:
        return {}
    monthly = {}
    prev_month = None
    month_start_val = values[0]
    for i in range(len(dates)):
        parts = dates[i].split("-")
        if len(parts) < 2:
            continue
        year = int(parts[0])
        month = int(parts[1])
        key = (year, month)
        if prev_month is not None and key != prev_month:
            end_val = values[i - 1]
            if month_start_val > 0:
                ret = (end_val - month_start_val) / month_start_val * 100
                monthly[prev_month] = round(ret, 2)
            month_start_val = values[i]
        prev_month = key
    if prev_month and month_start_val > 0:
        ret = (values[-1] - month_start_val) / month_start_val * 100
        monthly[prev_month] = round(ret, 2)
    return monthly


def calc_sharpe(returns, risk_free_rate=0.02):
    """calculate annualized sharpe ratio from daily return percentages."""
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / 252
    excess = [r - daily_rf for r in returns]
    mean_excess = sum(excess) / len(excess)
    variance = sum((r - mean_excess) ** 2 for r in excess) / len(excess)
    std = math.sqrt(variance) if variance > 0 else 0
    if std == 0:
        return 0.0
    return round(mean_excess / std * math.sqrt(252), 4)


if __name__ == "__main__":
    chart = ComparisonChart("test comparison")
    import random
    random.seed(99)
    for strat_name in ["sma_cross", "rsi_revert", "momentum"]:
        vals = [100000]
        dates = []
        for d in range(500):
            year = 2020 + d // 252
            doy = d % 252
            month = doy // 21 + 1
            if month > 12:
                month = 12
            dom = doy % 21 + 1
            if dom > 28:
                dom = 28
            dates.append(f"{year}-{month:02d}-{dom:02d}")
            change = random.gauss(0.0003, 0.01)
            vals.append(vals[-1] * (1 + change))
        chart.add_equity_curve(strat_name, dates, vals[1:])
    saved = chart.save_report("/tmp/test_charts")
    if saved:
        print(f"saved {len(saved)} charts: {saved}")
    else:
        print("no charts saved (matplotlib may not be installed)")
