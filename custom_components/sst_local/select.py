from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SSTLocalConfigEntry
from .const import DAY_NAMES
from .entity import SSTLocalEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SSTLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([SSTScheduleDaySelect(entry.runtime_data)])


class SSTScheduleDaySelect(SSTLocalEntity, SelectEntity):
    """День расписания, который показывают и меняют сущности точек."""

    _attr_name = "Расписание: день"
    _attr_icon = "mdi:calendar-week"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = DAY_NAMES

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "schedule_day")

    @property
    def current_option(self) -> str | None:
        day = self.coordinator.selected_day
        return DAY_NAMES[day] if day is not None else None

    async def async_select_option(self, option: str) -> None:
        self.coordinator.set_selected_day(DAY_NAMES.index(option))
