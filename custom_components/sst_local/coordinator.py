from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import SCAN_INTERVAL
from .protocol import POINTS_PER_DAY, SSTError, SSTThermostatClient, ThermostatState

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
        # День расписания, который правят сущности select/time/number (пн = 0)
        self.selected_day: int | None = None

    async def _async_update_data(self) -> ThermostatState:
        try:
            state = await self.client.read_state()
        except SSTError as err:
            raise UpdateFailed(str(err)) from err
        if self.selected_day is None:
            self.selected_day = state.day_of_week
        return state

    def set_selected_day(self, day: int) -> None:
        self.selected_day = day
        self.async_update_listeners()

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

    async def async_write_chart(self, mutate: Callable[[list[tuple[int, int]]], None]) -> None:
        """Read fresh schedule, apply mutate(list), check point order, write it back, refresh."""
        try:
            state = await self.client.read_state()
            chart = list(state.chart)
            mutate(chart)
            for day in range(len(chart) // POINTS_PER_DAY):
                times = [t for t, _ in chart[day * POINTS_PER_DAY:(day + 1) * POINTS_PER_DAY]]
                if times != sorted(times):
                    raise HomeAssistantError(
                        "Время точек расписания внутри дня должно идти по возрастанию"
                    )
            await self.client.write_chart(chart)
        except (SSTError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        await self.async_request_refresh()
