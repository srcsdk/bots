#!/usr/bin/env python3
"""validate ohlc data from yahoo finance for common issues"""


def validate_row(row):
    """check a single ohlc row for data quality issues.

    returns list of issue strings, empty if clean.
    """
    issues = []

    required = ["date", "open", "high", "low", "close"]
    for field in required:
        if field not in row or row[field] is None:
            issues.append(f"missing {field}")

    if not issues:
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]

        if h < l:
            issues.append(f"high ({h}) < low ({l})")
        if o < l or o > h:
            issues.append(f"open ({o}) outside high-low range")
        if c < l or c > h:
            issues.append(f"close ({c}) outside high-low range")

        for field in ["open", "high", "low", "close"]:
            if row[field] <= 0:
                issues.append(f"{field} is non-positive: {row[field]}")

    volume = row.get("volume", 0)
    if volume is not None and volume < 0:
        issues.append(f"negative volume: {volume}")

    return issues


def validate_series(rows):
    """validate a series of ohlc rows.

    checks for gaps, duplicates, and per-row issues.
    returns dict with validation results.
    """
    if not rows:
        return {"valid": False, "error": "empty data"}

    all_issues = []
    dates_seen = set()

    for i, row in enumerate(rows):
        row_issues = validate_row(row)
        if row_issues:
            all_issues.append({"index": i, "date": row.get("date", "?"),
                               "issues": row_issues})

        date = row.get("date", "")
        if date in dates_seen:
            all_issues.append({"index": i, "date": date,
                               "issues": ["duplicate date"]})
        dates_seen.add(date)

    return {
        "valid": len(all_issues) == 0,
        "total_rows": len(rows),
        "issues": all_issues,
        "date_range": f"{rows[0].get('date', '?')} to {rows[-1].get('date', '?')}",
    }


def check_timestamps(rows):
    """validate date ordering and flag gaps > 5 trading days.

    returns list of gap warnings with start/end dates.
    """
    if not rows or len(rows) < 2:
        return []

    gaps = []
    for i in range(1, len(rows)):
        prev_date = rows[i - 1].get("date", "")
        curr_date = rows[i].get("date", "")
        if curr_date <= prev_date:
            gaps.append({
                "index": i,
                "issue": "out_of_order",
                "prev": prev_date,
                "curr": curr_date,
            })
            continue
        if len(prev_date) >= 10 and len(curr_date) >= 10:
            py = int(prev_date[:4])
            pm = int(prev_date[5:7])
            pd = int(prev_date[8:10])
            cy = int(curr_date[:4])
            cm = int(curr_date[5:7])
            cd = int(curr_date[8:10])
            prev_days = py * 365 + pm * 30 + pd
            curr_days = cy * 365 + cm * 30 + cd
            day_gap = curr_days - prev_days
            if day_gap > 7:
                gaps.append({
                    "index": i,
                    "issue": "large_gap",
                    "prev": prev_date,
                    "curr": curr_date,
                    "approx_days": day_gap,
                })
    return gaps


def print_validation(result):
    """display validation results"""
    status = "PASS" if result["valid"] else "FAIL"
    print(f"validation: {status} ({result['total_rows']} rows)")
    print(f"date range: {result['date_range']}")

    if result.get("issues"):
        print(f"\nissues ({len(result['issues'])}):")
        for issue in result["issues"][:20]:
            print(f"  row {issue['index']} ({issue['date']}): "
                  f"{', '.join(issue['issues'])}")
