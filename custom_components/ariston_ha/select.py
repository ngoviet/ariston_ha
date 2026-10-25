"""select: hẹn giờ tắt (app: Home → Auto Power Off → 15/30/60/90 phút).

Bật: POST mode = 12 (nếu chưa ở 12), rồi powerOffTimer {new, old, prevMode}.
Huỷ: POST mode = 1 (Manual) — đúng như app bấm Manual.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AristonConfigEntry
from .const import AUTO_POWER_OFF_MINUTES, MODE_AUTO_POWER_OFF, MODE_MANUAL
from .entity import AristonEntity

OFF = "off"
OPTIONS = [OFF, *(str(m) for m in AUTO_POWER_OFF_MINUTES)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AristonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([AutoPowerOffSelect(entry.runtime_data)])


class AutoPowerOffSelect(AristonEntity, SelectEntity):
    _attr_options = OPTIONS
    _attr_icon = "mdi:timer-off-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "auto_power_off")

    @property
    def current_option(self) -> str | None:
        if self.plant.get("mode") != MODE_AUTO_POWER_OFF:
            return OFF
        minutes = str(self.plant.get("pwrOffTime"))
        return minutes if minutes in OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        gw = self.coordinator.gw
        api = self.coordinator.api
        prev_mode = int(self.plant.get("mode") or MODE_MANUAL)
        prev_timer = self.plant.get("pwrOffTime")
        prev_timer = int(prev_timer) if prev_timer is not None else None

        async def _do() -> None:
            if option == OFF:
                if prev_mode == MODE_AUTO_POWER_OFF:
                    await api.async_set_mode(gw, new=MODE_MANUAL, old=prev_mode)
                return
            if prev_mode != MODE_AUTO_POWER_OFF:
                await api.async_set_mode(gw, new=MODE_AUTO_POWER_OFF, old=prev_mode)
            await api.async_set_power_off_timer(
                gw, int(option), old=prev_timer, prev_mode=prev_mode
            )

        await self.coordinator.async_write_then_refresh(_do())
