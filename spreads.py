#!/usr/bin/env python3
"""options spread strategy with risk/reward profiling"""


def vertical_spread(long_strike, short_strike, long_premium, short_premium,
                    option_type="call"):
    """calculate vertical spread payoff profile.

    bull call spread: buy lower strike call, sell higher strike call.
    bear put spread: buy higher strike put, sell lower strike put.
    """
    net_debit = long_premium - short_premium
    if option_type == "call":
        max_profit = abs(short_strike - long_strike) - net_debit
        max_loss = net_debit
        breakeven = min(long_strike, short_strike) + net_debit
    else:
        max_profit = abs(short_strike - long_strike) - net_debit
        max_loss = net_debit
        breakeven = max(long_strike, short_strike) - net_debit
    risk_reward = max_profit / max_loss if max_loss > 0 else float("inf")
    return {
        "type": f"vertical_{option_type}",
        "max_profit": round(max_profit, 2),
        "max_loss": round(max_loss, 2),
        "breakeven": round(breakeven, 2),
        "risk_reward": round(risk_reward, 2),
        "net_debit": round(net_debit, 2),
    }


def iron_condor(put_long, put_short, call_short, call_long,
                put_long_prem, put_short_prem, call_short_prem, call_long_prem):
    """calculate iron condor payoff."""
    credit = (put_short_prem - put_long_prem) + (call_short_prem - call_long_prem)
    put_width = put_short - put_long
    call_width = call_long - call_short
    max_loss = max(put_width, call_width) - credit
    return {
        "type": "iron_condor",
        "max_profit": round(credit, 2),
        "max_loss": round(max_loss, 2),
        "upper_breakeven": round(call_short + credit, 2),
        "lower_breakeven": round(put_short - credit, 2),
        "risk_reward": round(credit / max_loss, 2) if max_loss > 0 else 0,
    }


def butterfly(lower, middle, upper, lower_prem, middle_prem, upper_prem):
    """calculate butterfly spread payoff."""
    net_debit = lower_prem - 2 * middle_prem + upper_prem
    max_profit = (middle - lower) - net_debit
    return {
        "type": "butterfly",
        "max_profit": round(max_profit, 2),
        "max_loss": round(net_debit, 2),
        "breakeven_low": round(lower + net_debit, 2),
        "breakeven_high": round(upper - net_debit, 2),
    }


def payoff_at_expiry(spread_type, strikes, premiums, price_range):
    """calculate payoff at each price in range for visualization."""
    payoffs = []
    for price in price_range:
        pnl = -sum(premiums)
        for i, (strike, prem) in enumerate(zip(strikes, premiums)):
            if i % 2 == 0:
                pnl += max(0, price - strike)
            else:
                pnl -= max(0, price - strike)
        payoffs.append(round(pnl, 2))
    return payoffs


if __name__ == "__main__":
    spread = vertical_spread(100, 105, 3.50, 1.50)
    print("bull call spread:")
    for k, v in spread.items():
        print(f"  {k}: {v}")
    ic = iron_condor(90, 95, 105, 110, 0.50, 1.50, 1.50, 0.50)
    print("\niron condor:")
    for k, v in ic.items():
        print(f"  {k}: {v}")
