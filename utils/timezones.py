"""Timezone utilities for KST (Korea Standard Time) and UTC conversions."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd


# Timezone constants
KST = ZoneInfo("Asia/Seoul")
UTC = timezone.utc


def to_kst(dt: datetime | pd.Timestamp | str) -> pd.Timestamp:
    """Convert datetime to KST timezone.

    Args:
        dt: Input datetime (can be naive or timezone-aware)

    Returns:
        Timezone-aware timestamp in KST
    """
    if isinstance(dt, str):
        dt = pd.to_datetime(dt)

    ts = pd.Timestamp(dt)

    # If naive, assume UTC
    if ts.tz is None:
        ts = ts.tz_localize(UTC)

    return ts.tz_convert(KST)


def to_utc(dt: datetime | pd.Timestamp | str) -> pd.Timestamp:
    """Convert datetime to UTC timezone.

    Args:
        dt: Input datetime (can be naive or timezone-aware)

    Returns:
        Timezone-aware timestamp in UTC
    """
    if isinstance(dt, str):
        dt = pd.to_datetime(dt)

    ts = pd.Timestamp(dt)

    # If naive, assume KST
    if ts.tz is None:
        ts = ts.tz_localize(KST)

    return ts.tz_convert(UTC)


def now_kst() -> pd.Timestamp:
    """Get current time in KST.

    Returns:
        Current timestamp in KST
    """
    return pd.Timestamp.now(tz=KST)


def now_utc() -> pd.Timestamp:
    """Get current time in UTC.

    Returns:
        Current timestamp in UTC
    """
    return pd.Timestamp.now(tz=UTC)


def kst_market_open(date: datetime | pd.Timestamp | str) -> pd.Timestamp:
    """Get KRX market open time for a date (09:00 KST).

    Args:
        date: Date

    Returns:
        Market open timestamp in KST
    """
    if isinstance(date, str):
        date = pd.to_datetime(date)

    ts = pd.Timestamp(date)
    return ts.replace(hour=9, minute=0, second=0, microsecond=0).tz_localize(KST)


def kst_market_close(date: datetime | pd.Timestamp | str) -> pd.Timestamp:
    """Get KRX market close time for a date (15:30 KST).

    Args:
        date: Date

    Returns:
        Market close timestamp in KST
    """
    if isinstance(date, str):
        date = pd.to_datetime(date)

    ts = pd.Timestamp(date)
    return ts.replace(hour=15, minute=30, second=0, microsecond=0).tz_localize(KST)


def is_market_hours(dt: datetime | pd.Timestamp | None = None) -> bool:
    """Check if current time (or given time) is during market hours.

    Args:
        dt: Datetime to check (defaults to now)

    Returns:
        True if during market hours (09:00-15:30 KST)
    """
    if dt is None:
        dt = now_kst()
    elif isinstance(dt, str):
        dt = pd.to_datetime(dt)

    ts = to_kst(dt)

    market_open = kst_market_open(ts)
    market_close = kst_market_close(ts)

    return market_open <= ts <= market_close
