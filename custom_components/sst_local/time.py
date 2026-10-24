from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SSTLocalConfigEntry
from .const import PERIODS
from .entity import SSTLocalEntity
from .protocol import POINTS_PER_DAY
from .schedule import minutes_to_time, period_points, time_to_minutes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SSTLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SSTSchedulePointTime(coordinator, period, i)
        for period in PERIODS
        for i in range(POINTS_PER_DAY)
    )


class SSTSchedulePointTime(SSTLocalEntity, TimeEntity):
    """Время начала точки расписания периода (будни / выходные)."""

    _attr_icon = "mdi:clock-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, period: str, point: int) -> None:
        super().__init__(coordinator, f"{period}_point_{point + 1}_time")
        self._period = period
        self._point = point
        self._attr_name = f"{PERIODS[period][0]}: точка {point + 1}, время"

    @property
    def native_value(self) -> time | None:
        points = period_points(self.coordinator.data.chart, self._period)
        if self._point >= len(points):
            return None
        return minutes_to_time(points[self._point][0])

    async def async_set_value(self, value: time) -> None:
        def mutate(points: list[tuple[int, int]]) -> None:
            points[self._point] = (time_to_minutes(value), points[self._point][1])

        await self.coordinator.async_write_period(self._period, mutate)
