from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SSTLocalConfigEntry
from .entity import SSTLocalEntity
from .protocol import ThermostatState


@dataclass(frozen=True, kw_only=True)
class SSTBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[ThermostatState], bool]


BINARY_SENSORS = (
    SSTBinarySensorDescription(
        key="heating",
        name="Нагрев",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda s: s.heating,
    ),
    SSTBinarySensorDescription(
        key="floor_sensor_error",
        name="Ошибка датчика пола",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.floor_sensor_error,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SSTLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(SSTLocalBinarySensor(coordinator, d) for d in BINARY_SENSORS)


class SSTLocalBinarySensor(SSTLocalEntity, BinarySensorEntity):
    entity_description: SSTBinarySensorDescription

    def __init__(self, coordinator, description: SSTBinarySensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data)
