"""Entity gốc: một thiết bị cho cả bình, mọi entity dùng chung coordinator."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, WHE_MODEL_NAMES
from .coordinator import AristonCoordinator


class AristonEntity(CoordinatorEntity[AristonCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AristonCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.gw}_{key}"
        model = WHE_MODEL_NAMES.get(
            coordinator.device_info.get("wheModelType"), "Velis"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.gw)},
            name=coordinator.config_entry.title,
            manufacturer="Ariston",
            model=model,
            sw_version=(coordinator.device_info.get("gwFwVer") or {}).get("FwVer1"),
        )

    @property
    def plant(self) -> dict[str, Any]:
        return self.coordinator.data.plant

    @property
    def settings(self) -> dict[str, Any]:
        return self.coordinator.data.settings
