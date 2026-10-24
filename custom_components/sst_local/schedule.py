"""Helpers to convert the thermostat schedule to/from Home Assistant data."""

from __future__ import annotations

from datetime import time

from .const import DAY_KEYS
from .protocol import POINTS_PER_DAY


def minutes_to_time(minutes: int) -> time:
    minutes = min(max(minutes, 0), 24 * 60 - 1)
    return time(minutes // 60, minutes % 60)


def time_to_minutes(value: time | str) -> int:
    if isinstance(value, str):
        parts = value.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    return value.hour * 60 + value.minute


def day_points(chart: list[tuple[int, int]], day: int) -> list[tuple[int, int]]:
    return chart[day * POINTS_PER_DAY:(day + 1) * POINTS_PER_DAY]


def chart_as_dict(chart: list[tuple[int, int]]) -> dict[str, list[dict[str, str | int]]]:
    """{"mon": [{"time": "06:00", "temperature": 26}, ...], ...}"""
    return {
        key: [
            {"time": minutes_to_time(t).strftime("%H:%M"), "temperature": temp}
            for t, temp in day_points(chart, day)
        ]
        for day, key in enumerate(DAY_KEYS)
        if len(chart) >= (day + 1) * POINTS_PER_DAY
    }
