from __future__ import annotations

from collections.abc import Iterable

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SSTLocalConfigEntry
from .const import WEEKDAYS
from .entity import SSTLocalEntity
from .protocol import DAYS, POINTS_PER_DAY
from .schedule import day_points


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SSTLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            SSTCopyScheduleButton(coordinator, "copy_schedule_weekdays", "Расписание: копировать на будни", WEEKDAYS),
            SSTCopyScheduleButton(coordinator, "copy_schedule_all", "Расписание: копировать на все дни", range(DAYS)),
        ]
    )


class SSTCopyScheduleButton(SSTLocalEntity, ButtonEntity):
    """Копирует расписание выбранного дня на набор дней."""

    _attr_icon = "mdi:content-copy"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, key: str, name: str, days: Iterable[int]) -> None:
        super().__init__(coordinator, key)
        self._attr_name = name
        self._days = list(days)

    async def async_press(self) -> None:
        source = self.coordinator.selected_day

        def mutate(chart: list[tuple[int, int]]) -> None:
            points = day_points(chart, source)
            for day in self._days:
                chart[day * POINTS_PER_DAY:(day + 1) * POINTS_PER_DAY] = points

        await self.coordinator.async_write_chart(mutate)
