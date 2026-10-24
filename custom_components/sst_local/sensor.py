from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SSTLocalConfigEntry
from .entity import SSTLocalEntity
from .protocol import ThermostatState


@dataclass(frozen=True, kw_only=True)
class SSTSensorDescription(SensorEntityDescription):
    value_fn: Callable[[ThermostatState], float | int | None]


SENSORS = (
    SSTSensorDescription(
        key="temperature_floor",
        name="Температура пола",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda s: s.temp_floor,
    ),
    SSTSensorDescription(
        key="temperature_air",
        name="Температура воздуха",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda s: s.temp_air,
    ),
    SSTSensorDescription(
        key="heating_time",
        name="Время работы нагрева",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda s: s.relay_minutes,
    ),
    SSTSensorDescription(
        key="wifi_level",
        name="Уровень Wi-Fi",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.wifi_level,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SSTLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(SSTLocalSensor(coordinator, description) for description in SENSORS)


class SSTLocalSensor(SSTLocalEntity, SensorEntity):
    entity_description: SSTSensorDescription

    def __init__(self, coordinator, description: SSTSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)
