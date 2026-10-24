"""Helpers to convert the thermostat schedule to/from Home Assistant data.

Термостат хранит 7 дней x 4 точки. Интеграция работает с двумя периодами —
будни (пн–пт) и выходные (сб–вс): период показывается по первому дню и
записывается во все свои дни одинаково.
"""

from __future__ import annotations

from datetime import time

from .const import PERIODS
from .protocol import POINTS_PER_DAY

Points = list[tuple[int, int]]


def minutes_to_time(minutes: int) -> time:
    minutes = min(max(minutes, 0), 24 * 60 - 1)
    return time(minutes // 60, minutes % 60)


def time_to_minutes(value: time | str) -> int:
    if isinstance(value, str):
        parts = value.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    return value.hour * 60 + value.minute


def day_points(chart: Points, day: int) -> Points:
    return chart[day * POINTS_PER_DAY:(day + 1) * POINTS_PER_DAY]


def period_points(chart: Points, period: str) -> Points:
    return day_points(chart, PERIODS[period][1][0])


def set_period_points(chart: Points, period: str, points: Points) -> None:
    for day in PERIODS[period][1]:
        chart[day * POINTS_PER_DAY:(day + 1) * POINTS_PER_DAY] = points


def period_is_uniform(chart: Points, period: str) -> bool:
    days = PERIODS[period][1]
    return all(day_points(chart, day) == day_points(chart, days[0]) for day in days)


def chart_as_dict(chart: Points) -> dict[str, list[dict[str, str | int]]]:
    """{"weekdays": [{"time": "06:00", "temperature": 26}, ...], "weekend": [...]}"""
    if len(chart) < 7 * POINTS_PER_DAY:
        return {}
    return {
        period: [
            {"time": minutes_to_time(t).strftime("%H:%M"), "temperature": temp}
            for t, temp in period_points(chart, period)
        ]
        for period in PERIODS
    }
