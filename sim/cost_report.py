#!/usr/bin/env python3
"""transaction cost analysis report"""


def analyze_costs(trades):
    """analyze transaction costs across all trades."""
    if not trades:
        return {}
    total_commission = sum(t.get("commission", 0) for t in trades)
    total_slippage = sum(t.get("slippage_cost", 0) for t in trades)
    total_volume = sum(t.get("shares", 0) * t.get("fill_price", 0) for t in trades)
    return {
        "total_trades": len(trades),
        "total_commission": round(total_commission, 2),
        "total_slippage": round(total_slippage, 2),
        "total_costs": round(total_commission + total_slippage, 2),
        "avg_commission": round(total_commission / len(trades), 2),
        "avg_slippage": round(total_slippage / len(trades), 2),
        "cost_as_pct_volume": round(
            (total_commission + total_slippage) / total_volume * 100, 4
        ) if total_volume > 0 else 0,
    }


def cost_impact_on_returns(gross_return_pct, total_costs, initial_capital):
    """calculate how much costs reduce returns."""
    cost_drag = total_costs / initial_capital * 100
    net_return = gross_return_pct - cost_drag
    return {
        "gross_return_pct": round(gross_return_pct, 2),
        "cost_drag_pct": round(cost_drag, 2),
        "net_return_pct": round(net_return, 2),
    }


def breakeven_trades(avg_cost_per_trade, avg_profit_per_trade):
    """calculate minimum profitable trades to cover costs."""
    if avg_profit_per_trade <= 0:
        return float("inf")
    if avg_profit_per_trade <= avg_cost_per_trade:
        return float("inf")
    ratio = avg_cost_per_trade / (avg_profit_per_trade - avg_cost_per_trade)
    return round(ratio, 2)


if __name__ == "__main__":
    trades = [
        {"shares": 100, "fill_price": 150.0, "commission": 1.0, "slippage_cost": 0.75},
        {"shares": 50, "fill_price": 300.0, "commission": 1.0, "slippage_cost": 1.50},
        {"shares": 200, "fill_price": 50.0, "commission": 1.0, "slippage_cost": 0.50},
    ]
    analysis = analyze_costs(trades)
    print("cost analysis:")
    for k, v in analysis.items():
        print(f"  {k}: {v}")
