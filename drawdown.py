#!/usr/bin/env python3
"""drawdown analysis and tracking"""


def max_drawdown(equity_curve):
    """calculate maximum drawdown from equity curve.

    returns (max_dd_pct, peak_idx, trough_idx).
    """
    if len(equity_curve) < 2:
        return 0.0, 0, 0
    peak = equity_curve[0]
    peak_idx = 0
    max_dd = 0.0
    max_peak_idx = 0
    max_trough_idx = 0
    for i in range(1, len(equity_curve)):
        if equity_curve[i] > peak:
            peak = equity_curve[i]
            peak_idx = i
        dd = (peak - equity_curve[i]) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
            max_peak_idx = peak_idx
            max_trough_idx = i
    return round(max_dd * 100, 2), max_peak_idx, max_trough_idx


def drawdown_duration(equity_curve):
    """calculate longest drawdown duration in periods."""
    if len(equity_curve) < 2:
        return 0
    peak = equity_curve[0]
    current_duration = 0
    max_duration = 0
    for val in equity_curve[1:]:
        if val < peak:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            peak = val
            current_duration = 0
    return max_duration


def calmar_ratio(annual_return, max_dd_pct):
    """calculate calmar ratio (return / max drawdown)."""
    if max_dd_pct == 0:
        return float("inf")
    return round(annual_return / max_dd_pct, 2)


def underwater_equity(equity_curve):
    """calculate underwater equity (drawdown at each point)."""
    peak = equity_curve[0]
    underwater = []
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (val - peak) / peak * 100 if peak > 0 else 0
        underwater.append(round(dd, 2))
    return underwater


if __name__ == "__main__":
    curve = [100, 105, 103, 98, 102, 110, 95, 108]
    dd, pi, ti = max_drawdown(curve)
    print(f"max drawdown: {dd}% (peak idx {pi}, trough idx {ti})")
    print(f"max duration: {drawdown_duration(curve)} periods")
    print(f"underwater: {underwater_equity(curve)}")
