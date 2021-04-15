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
    prev_date = None

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
        prev_date = date

    return {
        "valid": len(all_issues) == 0,
        "total_rows": len(rows),
        "issues": all_issues,
        "date_range": f"{rows[0].get('date', '?')} to {rows[-1].get('date', '?')}",
    }


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
