from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import SCAN_INTERVAL
from .protocol import SSTError, SSTThermostatClient, ThermostatState
from .schedule import Points, period_points, set_period_points

_LOGGER = logging.getLogger(__name__)


class SSTLocalCoordinator(DataUpdateCoordinator[ThermostatState]):
    """Single polling loop for one thermostat."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: SSTThermostatClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> ThermostatState:
        try:
            return await self.client.read_state()
        except SSTError as err:
            raise UpdateFailed(str(err)) from err

    async def async_write_settings(self, mutate) -> None:
        """Read fresh S block, apply mutate(bytearray), write it back, refresh."""
        try:
            state = await self.client.read_state()
            settings = state.settings_bytes()
            mutate(settings)
            await self.client.write_settings(settings)
        except SSTError as err:
            raise HomeAssistantError(str(err)) from err
        await self.async_request_refresh()

    async def async_write_period(self, period: str, mutate: Callable[[Points], None]) -> None:
        """Read fresh schedule, apply mutate() to the 4 points of the period, write them to all its days."""
        try:
            state = await self.client.read_state()
            chart = list(state.chart)
            points = list(period_points(chart, period))
            mutate(points)
            times = [t for t, _ in points]
            if times != sorted(times):
                raise HomeAssistantError(
                    "Время точек расписания должно идти по возрастанию"
                )
            set_period_points(chart, period, points)
            await self.client.write_chart(chart)
        except (SSTError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        await self.async_request_refresh()
