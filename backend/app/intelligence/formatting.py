"""Human-readable formatting helpers shared by scoring and explanations (Member 3)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Union


def format_inr(amount: float) -> str:
    """Rupees with Indian digit grouping: 985000 -> '₹9,85,000'.

    Rounded to whole rupees (paise are noise in an explanation).
    """
    value = int(round(float(amount)))
    sign = "-" if value < 0 else ""
    digits = str(abs(value))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return f"{sign}₹{digits}"


def format_minutes(minutes: Union[int, float, None]) -> str:
    """38 -> '38 min', 190 -> '3 h 10 min', 120 -> '2 h', 3000 -> '2 d 2 h'."""
    if minutes is None:
        return "n/a"
    total = int(round(float(minutes)))
    if total < 60:
        return f"{total} min"
    if total < 1440:
        h, m = divmod(total, 60)
        return f"{h} h {m} min" if m else f"{h} h"
    d, rest = divmod(total, 1440)
    h = rest // 60
    return f"{d} d {h} h" if h else f"{d} d"


def format_duration(delta: timedelta) -> str:
    """timedelta -> same style as format_minutes."""
    return format_minutes(delta.total_seconds() / 60)


def format_dt(dt: datetime) -> str:
    """'09 Nov 14:02'"""
    return dt.strftime("%d %b %H:%M")


def format_pct(ratio: float) -> str:
    """0.9712 -> '97%'"""
    return f"{round(ratio * 100)}%"
