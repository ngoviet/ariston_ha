"""switch: nguồn bình, ECO, diệt khuẩn."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AristonConfigEntry
from .const import SETTING_ANTI_LEGIONELLA
from .coordinator import AristonCoordinator
from .entity import AristonEntity


@dataclass(frozen=True, kw_only=True)
class AristonSwitchDescription(SwitchEntityDescription):
    is_on: Callable[[AristonCoordinator], bool | None]
    turn: Callable[[AristonCoordinator, bool], Awaitable[None]]


def _anti_leg_is_on(c: AristonCoordinator) -> bool | None:
    # Công tắc = cài đặt bật/tắt diệt khuẩn (plantSettings); chu kỳ ĐANG chạy là binary_sensor.
    value = c.data.settings.get(SETTING_ANTI_LEGIONELLA)
    return bool(value) if value is not None else None


SWITCHES: tuple[AristonSwitchDescription, ...] = (
    AristonSwitchDescription(
        key="power",
        translation_key="power",
        icon="mdi:power",
        is_on=lambda c: (None if c.data.plant.get("on") is None else bool(c.data.plant.get("on"))),
        turn=lambda c, on: c.api.async_set_power(c.gw, on),
    ),
    AristonSwitchDescription(
        key="eco",
        translation_key="eco",
        icon="mdi:leaf",
        is_on=lambda c: (None if c.data.plant.get("eco") is None else bool(c.data.plant.get("eco"))),
        turn=lambda c, on: c.api.async_set_eco(c.gw, on),
    ),
    AristonSwitchDescription(
        key="anti_legionella",
        translation_key="anti_legionella",
        icon="mdi:bacteria-outline",
        is_on=_anti_leg_is_on,
        turn=lambda c, on: c.api.async_set_plant_setting(
            c.gw, SETTING_ANTI_LEGIONELLA, 1.0 if on else 0.0,
            c.data.settings.get(SETTING_ANTI_LEGIONELLA),
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AristonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    c = entry.runtime_data
    async_add_entities(AristonSwitch(c, d) for d in SWITCHES)


class AristonSwitch(AristonEntity, SwitchEntity):
    entity_description: AristonSwitchDescription

    def __init__(self, coordinator, description: AristonSwitchDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on(self.coordinator)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_then_refresh(
            self.entity_description.turn(self.coordinator, True)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_then_refresh(
            self.entity_description.turn(self.coordinator, False)
        )
