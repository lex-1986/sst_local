from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SSTLocalConfigEntry
from .const import PERIODS
from .entity import SSTLocalEntity
from .protocol import MAX_CHART_TEMP, MIN_CHART_TEMP, POINTS_PER_DAY
from .schedule import period_points


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SSTLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SSTSchedulePointTemperature(coordinator, period, i)
        for period in PERIODS
        for i in range(POINTS_PER_DAY)
    )


class SSTSchedulePointTemperature(SSTLocalEntity, NumberEntity):
    """Температура точки расписания периода (будни / выходные)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = MIN_CHART_TEMP
    _attr_native_max_value = MAX_CHART_TEMP
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, period: str, point: int) -> None:
        super().__init__(coordinator, f"{period}_point_{point + 1}_temperature")
        self._period = period
        self._point = point
        self._attr_name = f"{PERIODS[period][0]}: точка {point + 1}, температура"

    @property
    def native_value(self) -> float | None:
        points = period_points(self.coordinator.data.chart, self._period)
        if self._point >= len(points):
            return None
        return points[self._point][1]

    async def async_set_native_value(self, value: float) -> None:
        def mutate(points: list[tuple[int, int]]) -> None:
            points[self._point] = (points[self._point][0], int(value))

        await self.coordinator.async_write_period(self._period, mutate)
