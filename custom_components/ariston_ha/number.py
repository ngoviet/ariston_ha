"""number: nhiệt độ tối đa đặt được (plantSettings MedMaxSetpointTemperature)."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AristonConfigEntry
from .const import (
    SETTING_MAX_TEMP,
    SETTING_MAX_TEMP_MAX,
    SETTING_MAX_TEMP_MIN,
)
from .entity import AristonEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AristonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MaxSetpointNumber(entry.runtime_data)])


class MaxSetpointNumber(AristonEntity, NumberEntity):
    _attr_translation_key = "max_setpoint_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 1
    _attr_mode = NumberMode.AUTO
    _attr_icon = "mdi:thermometer-high"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "max_setpoint_temperature")

    @property
    def native_min_value(self) -> float:
        return float(self.settings.get(SETTING_MAX_TEMP_MIN) or 65)

    @property
    def native_max_value(self) -> float:
        return float(self.settings.get(SETTING_MAX_TEMP_MAX) or 80)

    @property
    def native_value(self) -> float | None:
        value = self.settings.get(SETTING_MAX_TEMP)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write_then_refresh(
            self.coordinator.api.async_set_plant_setting(
                self.coordinator.gw, SETTING_MAX_TEMP, value,
                self.settings.get(SETTING_MAX_TEMP),
            )
        )
        await self.coordinator.async_refresh_slow()
