#!/usr/bin/env python3
"""market calendar for trading day management"""

import datetime


US_HOLIDAYS_2022 = {
    datetime.date(2022, 1, 17),   # mlk day
    datetime.date(2022, 2, 21),   # presidents day
    datetime.date(2022, 4, 15),   # good friday
    datetime.date(2022, 5, 30),   # memorial day
    datetime.date(2022, 6, 20),   # juneteenth
    datetime.date(2022, 7, 4),    # independence day
    datetime.date(2022, 9, 5),    # labor day
    datetime.date(2022, 11, 24),  # thanksgiving
    datetime.date(2022, 12, 26),  # christmas observed
}


def is_trading_day(date):
    """check if a date is a trading day."""
    if date.weekday() >= 5:
        return False
    if date in US_HOLIDAYS_2022:
        return False
    return True


def next_trading_day(date):
    """get the next trading day after a date."""
    current = date + datetime.timedelta(days=1)
    while not is_trading_day(current):
        current += datetime.timedelta(days=1)
    return current


def prev_trading_day(date):
    """get the previous trading day before a date."""
    current = date - datetime.timedelta(days=1)
    while not is_trading_day(current):
        current -= datetime.timedelta(days=1)
    return current


def trading_days_between(start, end):
    """count trading days between two dates."""
    count = 0
    current = start
    while current <= end:
        if is_trading_day(current):
            count += 1
        current += datetime.timedelta(days=1)
    return count


def trading_days_in_month(year, month):
    """get all trading days in a month."""
    days = []
    date = datetime.date(year, month, 1)
    while date.month == month:
        if is_trading_day(date):
            days.append(date)
        date += datetime.timedelta(days=1)
    return days


def market_hours(date):
    """get market open/close times for a date."""
    if not is_trading_day(date):
        return None
    return {
        "pre_market": "04:00",
        "open": "09:30",
        "close": "16:00",
        "after_hours": "20:00",
    }


if __name__ == "__main__":
    today = datetime.date(2022, 7, 11)
    print(f"is trading day: {is_trading_day(today)}")
    print(f"next trading day: {next_trading_day(today)}")
    days = trading_days_in_month(2022, 7)
    print(f"trading days in jul 2022: {len(days)}")
    hours = market_hours(today)
    print(f"market hours: {hours}")
