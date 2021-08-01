#!/usr/bin/env python3
"""options chain scanner with unusual activity detection"""


def scan_unusual_volume(chain, vol_threshold=3.0):
    """detect options with unusually high volume relative to open interest.

    chain: list of dicts with strike, type, volume, open_interest, iv
    """
    alerts = []
    for opt in chain:
        oi = opt.get("open_interest", 0)
        vol = opt.get("volume", 0)
        if oi > 0 and vol > 0:
            ratio = vol / oi
            if ratio >= vol_threshold:
                alerts.append({
                    "strike": opt["strike"],
                    "type": opt.get("type", "call"),
                    "volume": vol,
                    "open_interest": oi,
                    "vol_oi_ratio": round(ratio, 2),
                    "iv": opt.get("iv", 0),
                })
    alerts.sort(key=lambda x: x["vol_oi_ratio"], reverse=True)
    return alerts


def detect_sweeps(trades, min_size=100):
    """detect potential option sweeps (large aggressive orders).

    trades: list of dicts with price, size, side, timestamp
    """
    sweeps = []
    for t in trades:
        if t.get("size", 0) >= min_size and t.get("side") == "buy":
            sweeps.append({
                "price": t["price"],
                "size": t["size"],
                "premium": round(t["price"] * t["size"] * 100, 2),
                "timestamp": t.get("timestamp", ""),
            })
    return sweeps


def put_call_ratio(chain):
    """calculate put/call ratio from options chain."""
    call_vol = sum(o.get("volume", 0) for o in chain if o.get("type") == "call")
    put_vol = sum(o.get("volume", 0) for o in chain if o.get("type") == "put")
    call_oi = sum(o.get("open_interest", 0) for o in chain if o.get("type") == "call")
    put_oi = sum(o.get("open_interest", 0) for o in chain if o.get("type") == "put")
    return {
        "volume_pcr": round(put_vol / call_vol, 3) if call_vol > 0 else 0,
        "oi_pcr": round(put_oi / call_oi, 3) if call_oi > 0 else 0,
        "sentiment": "bearish" if put_vol > call_vol * 1.5 else
                     "bullish" if call_vol > put_vol * 1.5 else "neutral",
    }


def max_pain(chain, spot_price):
    """calculate max pain strike where most options expire worthless."""
    strikes = sorted(set(o["strike"] for o in chain))
    min_pain = float("inf")
    max_pain_strike = spot_price
    for strike in strikes:
        pain = 0
        for opt in chain:
            oi = opt.get("open_interest", 0)
            if opt.get("type") == "call":
                pain += max(0, strike - opt["strike"]) * oi
            else:
                pain += max(0, opt["strike"] - strike) * oi
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = strike
    return {"max_pain_strike": max_pain_strike, "total_pain": min_pain}


if __name__ == "__main__":
    chain = [
        {"strike": 95, "type": "put", "volume": 500, "open_interest": 100, "iv": 0.35},
        {"strike": 100, "type": "call", "volume": 1200, "open_interest": 300, "iv": 0.25},
        {"strike": 100, "type": "put", "volume": 200, "open_interest": 800, "iv": 0.28},
        {"strike": 105, "type": "call", "volume": 800, "open_interest": 200, "iv": 0.22},
    ]
    unusual = scan_unusual_volume(chain)
    print(f"unusual activity: {len(unusual)}")
    for a in unusual:
        print(f"  {a['strike']} {a['type']} vol/oi={a['vol_oi_ratio']}")
    pcr = put_call_ratio(chain)
    print(f"put/call ratio: {pcr}")
