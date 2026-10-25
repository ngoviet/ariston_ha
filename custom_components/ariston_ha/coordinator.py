"""Coordinator: đọc trạng thái bình nhanh, cài đặt/lịch/điện năng chậm hơn."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AristonApi, AristonAuthError, AristonRateLimitError
from .const import (
    CONF_GATEWAY,
    CONF_SCAN_INTERVAL,
    CONSUMPTION_DHW,
    DEFAULT_SCAN_INTERVAL,
    RATE_LIMIT_BACKOFF,
    SLOW_INTERVAL,
    WRITE_SETTLE_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class AristonData:
    """Ảnh chụp mỗi chu kỳ. `plant` luôn có; phần chậm giữ giá trị cũ khi chưa tới hạn."""

    plant: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    time_prog: dict[str, Any] | None = None
    consumption: list[dict[str, Any]] = field(default_factory=list)
    # None = chưa đọc được (cloud busErrors trả HTTP 500 từ 2026-10-22) → errors_count unavailable
    bus_errors: list[dict[str, Any]] | None = None


def consumption_sequence(
    consumption: list[dict[str, Any]], period: int
) -> list[float] | None:
    """Dãy điện năng nước nóng (k=2) cho kỳ `period`, hoặc None."""
    for seq in consumption or []:
        if seq.get("k") == CONSUMPTION_DHW and seq.get("p") == period:
            values = seq.get("v")
            if isinstance(values, list):
                return [float(x) for x in values]
    return None


def schedule_by_day(plans: list[dict[str, Any]], days: tuple[str, ...]) -> dict[str, list[str]]:
    """{Tên ngày: ['HH:MM 60°C', ...]} từ các plan của timeProgs (days = số .NET, CN=0)."""
    out: dict[str, list[str]] = {}
    for plan in plans or []:
        slots = [
            f"{str(s.get('time', ''))[:5]} {float(s.get('temp', 0)):g}°C"
            for s in plan.get("shws") or []
        ]
        for day in plan.get("days") or []:
            if isinstance(day, int) and 0 <= day < len(days):
                out[days[day]] = slots
    return out


class AristonCoordinator(DataUpdateCoordinator[AristonData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: AristonApi) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )
        self.api = api
        self.gw: str = entry.data[CONF_GATEWAY]
        self.device_info: dict[str, Any] = dict(entry.data.get("device") or {})
        self._data = AristonData()
        self._slow_due: datetime | None = None
        self._rate_limited_until: datetime | None = None

    async def _async_update_data(self) -> AristonData:
        now = dt_util.utcnow()
        if self._rate_limited_until and now < self._rate_limited_until:
            # Đang bị 429 — trả ảnh cũ, không gọi mạng.
            return self._data
        try:
            self._data.plant = await self.api.async_get_plant_data(self.gw)
            if not self._data.plant:
                raise UpdateFailed("Cloud không trả medPlantData")
            if self._slow_due is None or now >= self._slow_due:
                await self._update_slow()
                self._slow_due = now + SLOW_INTERVAL
        except AristonAuthError as err:
            raise UpdateFailed(f"Đăng nhập Ariston thất bại: {err}") from err
        except AristonRateLimitError as err:
            self._rate_limited_until = now + RATE_LIMIT_BACKOFF
            _LOGGER.warning("Ariston 429 — lùi %s", RATE_LIMIT_BACKOFF)
            if not self._data.plant:
                raise UpdateFailed(str(err)) from err
        return self._data

    async def _update_slow(self) -> None:
        self._data.settings = await self.api.async_get_plant_settings(self.gw)
        self._data.consumption = await self.api.async_get_consumption(self.gw)
        try:
            self._data.time_prog = await self.api.async_get_time_program(self.gw)
        except AristonRateLimitError:
            raise
        except Exception as err:  # noqa: BLE001 - lịch hỏng không được chặn phần còn lại
            _LOGGER.warning("Đọc lịch tuần lỗi: %s", err)
        try:
            self._data.bus_errors = await self.api.async_get_bus_errors(self.gw)
        except AristonRateLimitError:
            raise
        except Exception as err:  # noqa: BLE001 - busErrors đang 500 ở cloud; để None, không ồn log
            _LOGGER.debug("Đọc bus errors lỗi (bỏ qua): %s", err)

    async def async_write_then_refresh(self, coro) -> None:
        """Chạy một lệnh ghi rồi đọc lại sau WRITE_SETTLE_SECONDS để state là dữ liệu cloud thật."""
        await coro
        await asyncio.sleep(WRITE_SETTLE_SECONDS)
        self._data.plant = await self.api.async_get_plant_data(self.gw)
        self.async_set_updated_data(self._data)

    async def async_refresh_slow(self) -> None:
        await self._update_slow()
        self.async_set_updated_data(self._data)
