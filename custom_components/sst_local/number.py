from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SSTLocalConfigEntry
from .entity import SSTLocalEntity
from .protocol import MAX_CHART_TEMP, MIN_CHART_TEMP, POINTS_PER_DAY


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SSTLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(SSTSchedulePointTemperature(coordinator, i) for i in range(POINTS_PER_DAY))


class SSTSchedulePointTemperature(SSTLocalEntity, NumberEntity):
    """Температура точки расписания выбранного дня."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = MIN_CHART_TEMP
    _attr_native_max_value = MAX_CHART_TEMP
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, point: int) -> None:
        super().__init__(coordinator, f"schedule_point_{point + 1}_temperature")
        self._point = point
        self._attr_name = f"Расписание: точка {point + 1}, температура"

    @property
    def _index(self) -> int:
        return self.coordinator.selected_day * POINTS_PER_DAY + self._point

    @property
    def native_value(self) -> float | None:
        chart = self.coordinator.data.chart
        if self.coordinator.selected_day is None or self._index >= len(chart):
            return None
        return chart[self._index][1]

    async def async_set_native_value(self, value: float) -> None:
        index = self._index

        def mutate(chart: list[tuple[int, int]]) -> None:
            chart[index] = (chart[index][0], int(value))

        await self.coordinator.async_write_chart(mutate)
