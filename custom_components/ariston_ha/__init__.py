"""Ariston NET — integration cloud tự viết cho bình nóng lạnh Velis "Med" (Slim3).

Thay cả HACS `ariston` (fustom) lẫn `ariston_slim3`: đăng nhập riêng, gộp mọi entity
(water_heater, các switch, sensor, hẹn giờ tắt, lịch tuần, điện năng) vào một integration.
Giao thức LAN không khả thi (bình dùng MQTT/TLS hai chiều với AWS IoT, có kiểm chứng CA) —
xem docs/ariston-local-research.md trong repo HA-Config.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AristonApi
from .coordinator import AristonCoordinator
from .services import async_setup_services

PLATFORMS = [
    Platform.WATER_HEATER,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]

type AristonConfigEntry = ConfigEntry[AristonCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AristonConfigEntry) -> bool:
    api = AristonApi(
        async_get_clientsession(hass),
        entry.data["username"],
        entry.data["password"],
    )
    coordinator = AristonCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: AristonConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AristonConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
