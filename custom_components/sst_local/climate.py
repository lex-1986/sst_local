from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    PRESET_AWAY,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
import voluptuous as vol

from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, ServiceResponse, SupportsResponse
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SSTLocalConfigEntry
from .const import (
    ATTR_PERIOD,
    ATTR_POINTS,
    ATTR_TIME,
    MAX_MANUAL_TEMP,
    MAX_VACATION_TEMP,
    MIN_MANUAL_TEMP,
    MIN_VACATION_TEMP,
    PERIODS,
    SERVICE_GET_SCHEDULE,
    SERVICE_SET_SCHEDULE,
)
from .entity import SSTLocalEntity
from .protocol import (
    MAX_CHART_TEMP,
    MIN_CHART_TEMP,
    MODE_CHART,
    MODE_MANUAL,
    MODE_VACATION,
    POINTS_PER_DAY,
)
from .schedule import chart_as_dict, time_to_minutes

SET_SCHEDULE_SCHEMA = {
    vol.Required(ATTR_PERIOD): vol.In(list(PERIODS)),
    vol.Required(ATTR_POINTS): vol.All(
        cv.ensure_list,
        [
            vol.Schema(
                {
                    vol.Required(ATTR_TIME): cv.time,
                    vol.Required(ATTR_TEMPERATURE): vol.All(
                        vol.Coerce(int), vol.Range(MIN_CHART_TEMP, MAX_CHART_TEMP)
                    ),
                }
            )
        ],
        vol.Length(min=POINTS_PER_DAY, max=POINTS_PER_DAY),
    ),
}

# Индексы в 7-байтовом блоке S
S_STATUS = 0
S_MODE = 1
S_TEMP_MANUAL = 3
S_TEMP_VACATION = 4


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SSTLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([SSTLocalClimate(entry.runtime_data)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_SCHEDULE, SET_SCHEDULE_SCHEMA, "async_set_schedule"
    )
    platform.async_register_entity_service(
        SERVICE_GET_SCHEDULE, None, "async_get_schedule", supports_response=SupportsResponse.ONLY
    )


class SSTLocalClimate(SSTLocalEntity, ClimateEntity):
    """HEAT = ручной режим, AUTO = по расписанию, пресет away = отпуск."""

    _attr_name = None
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]
    _attr_preset_modes = [PRESET_NONE, PRESET_AWAY]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "climate")

    @property
    def _state(self):
        return self.coordinator.data

    @property
    def hvac_mode(self) -> HVACMode:
        if not self._state.status:
            return HVACMode.OFF
        if self._state.mode == MODE_MANUAL:
            return HVACMode.HEAT
        return HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction:
        if not self._state.status:
            return HVACAction.OFF
        return HVACAction.HEATING if self._state.heating else HVACAction.IDLE

    @property
    def preset_mode(self) -> str:
        return PRESET_AWAY if self._state.mode == MODE_VACATION else PRESET_NONE

    @property
    def current_temperature(self) -> float | None:
        state = self._state
        if state.uses_floor_sensor and state.temp_floor is not None:
            return state.temp_floor
        return state.temp_air

    @property
    def target_temperature(self) -> float | None:
        return self._state.target_temperature

    @property
    def min_temp(self) -> float:
        return MIN_VACATION_TEMP if self._state.mode == MODE_VACATION else MIN_MANUAL_TEMP

    @property
    def max_temp(self) -> float:
        return MAX_VACATION_TEMP if self._state.mode == MODE_VACATION else MAX_MANUAL_TEMP

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self._state
        return {
            "temperature_manual": state.temp_manual,
            "temperature_vacation": state.temp_vacation,
            "temperature_chart": state.chart_temperature,
            "temperature_air_limit": state.temp_air_limit,
            "schedule": chart_as_dict(state.chart),
        }

    async def async_set_schedule(self, period: str, points: list[dict[str, Any]]) -> None:
        new_points = sorted(
            (time_to_minutes(p[ATTR_TIME]), p[ATTR_TEMPERATURE]) for p in points
        )

        def mutate(current: list[tuple[int, int]]) -> None:
            current[:] = new_points

        await self.coordinator.async_write_period(period, mutate)

    async def async_get_schedule(self) -> ServiceResponse:
        return chart_as_dict(self.coordinator.data.chart)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        def mutate(s: bytearray) -> None:
            if hvac_mode == HVACMode.OFF:
                s[S_STATUS] = 0
                return
            s[S_STATUS] = 1
            s[S_MODE] = MODE_MANUAL if hvac_mode == HVACMode.HEAT else MODE_CHART

        await self.coordinator.async_write_settings(mutate)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        def mutate(s: bytearray) -> None:
            if preset_mode == PRESET_AWAY:
                s[S_MODE] = MODE_VACATION
            elif s[S_MODE] == MODE_VACATION:
                s[S_MODE] = MODE_CHART

        await self.coordinator.async_write_settings(mutate)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        temperature = int(round(temperature))

        def mutate(s: bytearray) -> None:
            if s[S_MODE] == MODE_VACATION:
                s[S_TEMP_VACATION] = max(MIN_VACATION_TEMP, min(MAX_VACATION_TEMP, temperature))
            else:
                # В режиме расписания уставку задать нельзя — переходим в ручной режим
                s[S_MODE] = MODE_MANUAL
                s[S_TEMP_MANUAL] = max(MIN_MANUAL_TEMP, min(MAX_MANUAL_TEMP, temperature))

        await self.coordinator.async_write_settings(mutate)

    async def async_turn_on(self) -> None:
        await self.coordinator.async_write_settings(lambda s: s.__setitem__(S_STATUS, 1))

    async def async_turn_off(self) -> None:
        await self.coordinator.async_write_settings(lambda s: s.__setitem__(S_STATUS, 0))
