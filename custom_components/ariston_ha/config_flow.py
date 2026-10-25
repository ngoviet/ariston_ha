"""Config flow: đăng nhập Ariston NET, chọn bình Velis "Med" (wheType 3), tuỳ chọn chu kỳ đọc."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AristonApi, AristonApiError, AristonAuthError
from .const import (
    CONF_GATEWAY,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SYS_VELIS,
    WHE_MODEL_NAMES,
    WHE_TYPE_MED,
)

LOGIN_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)


def _is_med(plant: dict[str, Any]) -> bool:
    return plant.get("sys") == SYS_VELIS and plant.get("wheType") == WHE_TYPE_MED


class AristonConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._creds: dict[str, str] = {}
        self._plants: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api = AristonApi(
                async_get_clientsession(self.hass),
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                await api.async_login()
                plants = [p for p in await api.async_get_plants() if _is_med(p)]
            except AristonAuthError:
                errors["base"] = "invalid_auth"
            except AristonApiError:
                errors["base"] = "cannot_connect"
            else:
                if not plants:
                    errors["base"] = "no_med_device"
                else:
                    self._creds = user_input
                    self._plants = plants
                    return await self.async_step_device()
        return self.async_show_form(
            step_id="user", data_schema=LOGIN_SCHEMA, errors=errors
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if len(self._plants) == 1:
            return await self._create(self._plants[0])
        choices = {
            p["gw"]: p.get("name") or p["gw"] for p in self._plants
        }
        if user_input is not None:
            plant = next(p for p in self._plants if p["gw"] == user_input[CONF_GATEWAY])
            return await self._create(plant)
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_GATEWAY): vol.In(choices)}),
        )

    async def _create(self, plant: dict[str, Any]) -> ConfigFlowResult:
        gw = plant["gw"]
        await self.async_set_unique_id(gw)
        self._abort_if_unique_id_configured()
        model = WHE_MODEL_NAMES.get(plant.get("wheModelType"), "Velis")
        return self.async_create_entry(
            title=plant.get("name") or f"Ariston {model}",
            data={**self._creds, CONF_GATEWAY: gw, "device": plant},
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return AristonOptionsFlow()


class AristonOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    )
                }
            ),
        )
