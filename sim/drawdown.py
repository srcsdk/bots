#!/usr/bin/env python3
"""maximum drawdown analysis and recovery tracking"""


def max_drawdown(equity_curve):
    """calculate maximum drawdown from equity curve.

    returns (max_dd_pct, peak_idx, trough_idx).
    """
    if len(equity_curve) < 2:
        return 0, 0, 0
    peak = equity_curve[0]
    peak_idx = 0
    max_dd = 0
    max_dd_peak = 0
    max_dd_trough = 0
    for i, value in enumerate(equity_curve):
        if value > peak:
            peak = value
            peak_idx = i
        dd = (peak - value) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
            max_dd_peak = peak_idx
            max_dd_trough = i
    return round(max_dd * 100, 2), max_dd_peak, max_dd_trough


def drawdown_series(equity_curve):
    """calculate drawdown at each point in time."""
    if not equity_curve:
        return []
    peak = equity_curve[0]
    series = []
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0
        series.append(round(dd * 100, 2))
    return series


def recovery_time(equity_curve):
    """calculate time to recover from max drawdown."""
    dd_pct, peak_idx, trough_idx = max_drawdown(equity_curve)
    if dd_pct == 0:
        return 0
    peak_value = equity_curve[peak_idx]
    for i in range(trough_idx, len(equity_curve)):
        if equity_curve[i] >= peak_value:
            return i - trough_idx
    return len(equity_curve) - trough_idx


def underwater_periods(equity_curve, threshold=5.0):
    """find periods where drawdown exceeds threshold percent."""
    periods = []
    in_drawdown = False
    start = 0
    peak = equity_curve[0] if equity_curve else 0
    for i, value in enumerate(equity_curve):
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100 if peak > 0 else 0
        if dd >= threshold and not in_drawdown:
            in_drawdown = True
            start = i
        elif dd < threshold and in_drawdown:
            in_drawdown = False
            periods.append({"start": start, "end": i, "length": i - start})
    if in_drawdown:
        periods.append({
            "start": start, "end": len(equity_curve) - 1,
            "length": len(equity_curve) - 1 - start,
        })
    return periods


if __name__ == "__main__":
    curve = [100, 105, 110, 95, 88, 92, 98, 112, 108, 115]
    dd, peak, trough = max_drawdown(curve)
    print(f"max drawdown: {dd}% (peak idx {peak}, trough idx {trough})")
    rec = recovery_time(curve)
    print(f"recovery time: {rec} bars")
    series = drawdown_series(curve)
    print(f"drawdown series: {series}")
