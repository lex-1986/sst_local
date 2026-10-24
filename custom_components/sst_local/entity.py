from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SSTLocalCoordinator


class SSTLocalEntity(CoordinatorEntity[SSTLocalCoordinator]):
    """Base entity bound to the thermostat coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SSTLocalCoordinator, key: str) -> None:
        super().__init__(coordinator)
        mac = format_mac(coordinator.data.mac)
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={(CONNECTION_NETWORK_MAC, mac)},
            name=coordinator.config_entry.title,
            manufacturer="SST / Теплолюкс",
            model="MCS350",
            sw_version=coordinator.data.firmware,
        )
