"""Dịch vụ: ghi đè lịch tuần (velis/timeProgs) và đọc lại từ cloud."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DAYS, DOMAIN

ATTR_ENTRY_ID = "config_entry_id"
ATTR_PLANS = "plans"


def _time(value: Any) -> str:
    """HH:MM hoặc HH:MM:SS → HH:MM:SS (đúng dạng cloud trả)."""
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)(?::00)?", str(value))
    if not match:
        raise vol.Invalid(f"time phải là HH:MM, nhận {value!r}")
    return f"{match[1]}:{match[2]}:00"


def _day(value: Any) -> int:
    """0-6 (Chủ nhật = 0) hoặc tên ngày tiếng Anh."""
    if isinstance(value, str) and value.capitalize() in DAYS:
        return DAYS.index(value.capitalize())
    day = vol.Coerce(int)(value)
    if not 0 <= day <= 6:
        raise vol.Invalid(f"day phải 0-6 hoặc tên ngày, nhận {value!r}")
    return day


SHOWER_SCHEMA = vol.Schema(
    {
        vol.Required("time"): _time,
        vol.Optional("qty", default=-1): vol.All(vol.Coerce(int), vol.Range(min=-1, max=10)),
        vol.Required("temp"): vol.All(vol.Coerce(float), vol.Range(min=40, max=80)),
    }
)
PLAN_SCHEMA = vol.Schema(
    {
        vol.Required("days"): vol.All(cv.ensure_list, [_day]),
        vol.Required("shws"): vol.All(cv.ensure_list, [SHOWER_SCHEMA]),
    }
)
SET_TIME_PROGRAM_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Required(ATTR_PLANS): vol.All(cv.ensure_list, [PLAN_SCHEMA]),
    }
)
REFRESH_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY_ID): cv.string})


def _coordinator(hass: HomeAssistant, call: ServiceCall):
    entries = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.state is ConfigEntryState.LOADED
    ]
    wanted = call.data.get(ATTR_ENTRY_ID)
    if wanted:
        entries = [e for e in entries if e.entry_id == wanted]
    if len(entries) != 1:
        raise ServiceValidationError(
            f"Nêu rõ config_entry_id (đang có {len(entries)} entry đã nạp)"
        )
    return entries[0].runtime_data


def async_setup_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "set_time_program"):
        return

    async def set_time_program(call: ServiceCall) -> None:
        plans = call.data[ATTR_PLANS]
        used = [d for p in plans for d in p["days"]]
        if len(used) != len(set(used)):
            raise ServiceValidationError("Một ngày xuất hiện ở nhiều plan")
        coordinator = _coordinator(hass, call)
        await coordinator.async_write_then_refresh(
            coordinator.api.async_set_time_program(coordinator.gw, plans)
        )
        await coordinator.async_refresh_slow()

    async def refresh_time_program(call: ServiceCall) -> None:
        await _coordinator(hass, call).async_refresh_slow()

    hass.services.async_register(
        DOMAIN, "set_time_program", set_time_program, schema=SET_TIME_PROGRAM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "refresh_time_program", refresh_time_program, schema=REFRESH_SCHEMA
    )
