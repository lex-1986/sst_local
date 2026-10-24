from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SSTLocalConfigEntry
from .entity import SSTLocalEntity
from .protocol import POINTS_PER_DAY
from .schedule import minutes_to_time, time_to_minutes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SSTLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(SSTSchedulePointTime(coordinator, i) for i in range(POINTS_PER_DAY))


class SSTSchedulePointTime(SSTLocalEntity, TimeEntity):
    """Время начала точки расписания выбранного дня."""

    _attr_icon = "mdi:clock-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, point: int) -> None:
        super().__init__(coordinator, f"schedule_point_{point + 1}_time")
        self._point = point
        self._attr_name = f"Расписание: точка {point + 1}, время"

    @property
    def _index(self) -> int:
        return self.coordinator.selected_day * POINTS_PER_DAY + self._point

    @property
    def native_value(self) -> time | None:
        chart = self.coordinator.data.chart
        if self.coordinator.selected_day is None or self._index >= len(chart):
            return None
        return minutes_to_time(chart[self._index][0])

    async def async_set_value(self, value: time) -> None:
        index = self._index

        def mutate(chart: list[tuple[int, int]]) -> None:
            chart[index] = (time_to_minutes(value), chart[index][1])

        await self.coordinator.async_write_chart(mutate)
