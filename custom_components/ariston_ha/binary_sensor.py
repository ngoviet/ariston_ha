"""binary_sensor: đang đun, đang chạy chu kỳ diệt khuẩn."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AristonConfigEntry
from .coordinator import AristonCoordinator
from .entity import AristonEntity


@dataclass(frozen=True, kw_only=True)
class AristonBinaryDescription(BinarySensorEntityDescription):
    is_on: Callable[[AristonCoordinator], bool | None]


def _bool(value) -> bool | None:
    return None if value is None else bool(value)


BINARY_SENSORS: tuple[AristonBinaryDescription, ...] = (
    AristonBinaryDescription(
        key="is_heating",
        translation_key="is_heating",
        device_class=BinarySensorDeviceClass.HEAT,
        is_on=lambda c: _bool(c.data.plant.get("heatReq")),
    ),
    AristonBinaryDescription(
        key="anti_legionella_cycle",
        translation_key="anti_legionella_cycle",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:bacteria",
        is_on=lambda c: _bool(c.data.plant.get("antiLeg")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AristonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    c = entry.runtime_data
    async_add_entities(AristonBinarySensor(c, d) for d in BINARY_SENSORS)


class AristonBinarySensor(AristonEntity, BinarySensorEntity):
    entity_description: AristonBinaryDescription

    def __init__(self, coordinator, description: AristonBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on(self.coordinator)
