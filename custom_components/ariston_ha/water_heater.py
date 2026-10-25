"""water_heater: nhiệt độ đặt, chế độ MANUAL/PROGRAM, bật/tắt."""

from __future__ import annotations

from typing import Any, ClassVar

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AristonConfigEntry
from .const import (
    DEFAULT_MAX_TEMP,
    MIN_TEMP,
    MODE_NAMES,
    SELECTABLE_MODES,
    SETTING_MAX_TEMP,
)
from .entity import AristonEntity

_NAME_TO_MODE = {MODE_NAMES[m]: m for m in SELECTABLE_MODES}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AristonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([AristonWaterHeater(entry.runtime_data)])


class AristonWaterHeater(AristonEntity, WaterHeaterEntity):
    _attr_name = None  # entity = thiết bị
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list: ClassVar[list[str]] = [MODE_NAMES[m] for m in SELECTABLE_MODES]
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.ON_OFF
    )
    _attr_min_temp = MIN_TEMP

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "water_heater")

    @property
    def max_temp(self) -> float:
        return float(self.settings.get(SETTING_MAX_TEMP) or DEFAULT_MAX_TEMP)

    @property
    def current_temperature(self) -> float | None:
        temp = self.plant.get("temp")
        return float(temp) if temp is not None else None

    @property
    def target_temperature(self) -> float | None:
        temp = self.plant.get("reqTemp")
        return float(temp) if temp is not None else None

    @property
    def current_operation(self) -> str | None:
        # Chế độ ngoài MANUAL/PROGRAM (vd 12 = hẹn giờ tắt) không nằm trong operation_list → None.
        return MODE_NAMES.get(self.plant.get("mode")) if self.plant.get("mode") in SELECTABLE_MODES else None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs[ATTR_TEMPERATURE]
        await self.coordinator.async_write_then_refresh(
            self.coordinator.api.async_set_temperature(
                self.coordinator.gw,
                new=temp,
                old=self.plant.get("reqTemp"),
                eco=bool(self.plant.get("eco")),
            )
        )

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        mode = _NAME_TO_MODE[operation_mode]
        await self.coordinator.async_write_then_refresh(
            self.coordinator.api.async_set_mode(
                self.coordinator.gw, new=mode, old=self.plant.get("mode")
            )
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_then_refresh(
            self.coordinator.api.async_set_power(self.coordinator.gw, True)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_then_refresh(
            self.coordinator.api.async_set_power(self.coordinator.gw, False)
        )
