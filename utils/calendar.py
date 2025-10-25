"""Korean Exchange (KRX) trading calendar utilities."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import pandas as pd


# KRX public holidays (common fixed dates)
# Note: This is a simplified list. For production, use actual KRX calendar API
KRX_HOLIDAYS = [
    # 2024 holidays
    "2024-01-01", "2024-02-09", "2024-02-10", "2024-02-11", "2024-02-12",
    "2024-03-01", "2024-04-10", "2024-05-01", "2024-05-05", "2024-05-15",
    "2024-06-06", "2024-08-15", "2024-09-16", "2024-09-17", "2024-09-18",
    "2024-10-03", "2024-10-09", "2024-12-25",
    # 2025 holidays
    "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30", "2025-03-01",
    "2025-03-03", "2025-05-01", "2025-05-05", "2025-05-06", "2025-06-06",
    "2025-08-15", "2025-10-03", "2025-10-06", "2025-10-07", "2025-10-08",
    "2025-10-09", "2025-12-25",
]


class KRXCalendar:
    """Korean Exchange trading calendar.

    Provides utilities for working with KRX trading days, excluding
    weekends and Korean public holidays.
    """

    def __init__(self, holidays: List[str] | None = None):
        """Initialize KRX calendar.

        Args:
            holidays: List of holiday dates in YYYY-MM-DD format.
                     If None, uses default KRX_HOLIDAYS.
        """
        self.holidays = set(holidays or KRX_HOLIDAYS)

    def is_trading_day(self, date: datetime | pd.Timestamp | str) -> bool:
        """Check if a date is a trading day.

        Args:
            date: Date to check

        Returns:
            True if trading day, False otherwise
        """
        if isinstance(date, str):
            date = pd.to_datetime(date)

        # Weekend check
        if date.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Holiday check
        date_str = date.strftime("%Y-%m-%d")
        if date_str in self.holidays:
            return False

        return True

    def next_trading_day(self, date: datetime | pd.Timestamp | str) -> pd.Timestamp:
        """Get next trading day after given date.

        Args:
            date: Reference date

        Returns:
            Next trading day
        """
        if isinstance(date, str):
            date = pd.to_datetime(date)

        current = date + timedelta(days=1)
        while not self.is_trading_day(current):
            current += timedelta(days=1)

        return pd.Timestamp(current)

    def prev_trading_day(self, date: datetime | pd.Timestamp | str) -> pd.Timestamp:
        """Get previous trading day before given date.

        Args:
            date: Reference date

        Returns:
            Previous trading day
        """
        if isinstance(date, str):
            date = pd.to_datetime(date)

        current = date - timedelta(days=1)
        while not self.is_trading_day(current):
            current -= timedelta(days=1)

        return pd.Timestamp(current)

    def trading_days_between(
        self,
        start: datetime | pd.Timestamp | str,
        end: datetime | pd.Timestamp | str,
        inclusive: str = "both"
    ) -> pd.DatetimeIndex:
        """Get all trading days between two dates.

        Args:
            start: Start date
            end: End date
            inclusive: 'both', 'left', 'right', or 'neither'

        Returns:
            DatetimeIndex of trading days
        """
        if isinstance(start, str):
            start = pd.to_datetime(start)
        if isinstance(end, str):
            end = pd.to_datetime(end)

        all_dates = pd.date_range(start, end, freq='D')
        trading_days = [d for d in all_dates if self.is_trading_day(d)]

        return pd.DatetimeIndex(trading_days)

    def add_trading_days(
        self,
        date: datetime | pd.Timestamp | str,
        n_days: int
    ) -> pd.Timestamp:
        """Add n trading days to a date.

        Args:
            date: Starting date
            n_days: Number of trading days to add (can be negative)

        Returns:
            Resulting date
        """
        if isinstance(date, str):
            date = pd.to_datetime(date)

        current = pd.Timestamp(date)
        direction = 1 if n_days > 0 else -1
        remaining = abs(n_days)

        while remaining > 0:
            if direction > 0:
                current = self.next_trading_day(current)
            else:
                current = self.prev_trading_day(current)
            remaining -= 1

        return current


# Global calendar instance
_default_calendar = None


def get_calendar() -> KRXCalendar:
    """Get default KRX calendar instance.

    Returns:
        Global KRXCalendar instance
    """
    global _default_calendar
    if _default_calendar is None:
        _default_calendar = KRXCalendar()
    return _default_calendar
