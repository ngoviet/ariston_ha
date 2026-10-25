"""Client cloud Ariston NET (`https://www.ariston-net.remotethermo.com/api/v2/`).

Đặc điểm đo thật (bình Slim3, 2026-10):

- Đăng nhập `POST accounts/login {"usr", "pwd"}` → `{"token": ...}`; mọi request sau gửi header
  `ar.authToken`.
- Token hết hạn thì cloud trả **HTTP 405** (không phải 401) ⇒ đăng nhập lại một lần rồi gửi lại.
- 404 = không có dữ liệu (không phải lỗi); 429 = bị giới hạn tần suất.
- Lệnh ghi trả rỗng; muốn biết kết quả phải đọc lại `medPlantData`.
- `busErrors` trả HTTP 500 từ 2026-10-22 ⇒ coi là tuỳ chọn.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import API_URL, REQUEST_TIMEOUT, USER_AGENT

_LOGGER = logging.getLogger(__name__)


class AristonApiError(Exception):
    """Lỗi mạng hoặc cloud trả lỗi."""


class AristonAuthError(AristonApiError):
    """Sai tài khoản / mật khẩu (hoặc mật khẩu đã đổi)."""


class AristonRateLimitError(AristonApiError):
    """Cloud trả HTTP 429."""


AUTH_STATUSES = (400, 401, 403, 405)


class AristonApi:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        base_url: str = API_URL,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._base = base_url
        self._token: str | None = None
        self._login_lock = asyncio.Lock()

    # -- tầng HTTP ------------------------------------------------------------

    async def async_login(self) -> None:
        """Lấy token mới. Sai mật khẩu ⇒ AristonAuthError."""
        async with self._login_lock:
            try:
                async with self._session.post(
                    self._base + "accounts/login",
                    json={"usr": self._username, "pwd": self._password},
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as resp:
                    if resp.status in AUTH_STATUSES:
                        raise AristonAuthError(f"login rejected (HTTP {resp.status})")
                    if resp.status == 429:
                        raise AristonRateLimitError("login rate limited")
                    if resp.status >= 400:
                        raise AristonApiError(f"login HTTP {resp.status}")
                    data = await resp.json(content_type=None)
            except (aiohttp.ClientError, TimeoutError) as err:
                raise AristonApiError(f"login: {err}") from err
            token = (data or {}).get("token") if isinstance(data, dict) else None
            if not token:
                raise AristonAuthError("login returned no token")
            self._token = token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        retry: bool = True,
    ) -> Any:
        if self._token is None:
            await self.async_login()
        try:
            async with self._session.request(
                method,
                self._base + path,
                json=body,
                headers={"User-Agent": USER_AGENT, "ar.authToken": self._token or ""},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status in (401, 405):
                    if not retry:
                        raise AristonAuthError(f"{path}: token rejected after re-login")
                    _LOGGER.debug("Token hết hạn (HTTP %s) — đăng nhập lại", resp.status)
                    self._token = None
                    await self.async_login()
                    return await self._request(method, path, body=body, retry=False)
                if resp.status == 404:
                    return None
                if resp.status == 429:
                    raise AristonRateLimitError(f"{path}: HTTP 429")
                if resp.status >= 400:
                    raise AristonApiError(f"{path}: HTTP {resp.status}")
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise AristonApiError(f"{path}: {err}") from err
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError as err:
            raise AristonApiError(f"{path}: invalid JSON") from err

    async def _get(self, path: str) -> Any:
        return await self._request("GET", path)

    async def _post(self, path: str, body: Any) -> Any:
        _LOGGER.debug("POST %s %s", path, body)
        return await self._request("POST", path, body=body)

    # -- đọc ----------------------------------------------------------------

    async def async_get_plants(self) -> list[dict[str, Any]]:
        """Danh sách bình nóng lạnh Velis của tài khoản (`velis/plants`)."""
        return list(await self._get("velis/plants") or [])

    async def async_get_plant_data(self, gw: str) -> dict[str, Any]:
        return dict(await self._get(f"velis/medPlantData/{gw}") or {})

    async def async_get_plant_settings(self, gw: str) -> dict[str, Any]:
        return dict(await self._get(f"velis/medPlantData/{gw}/plantSettings") or {})

    async def async_get_time_program(self, gw: str) -> dict[str, Any] | None:
        return await self._get(f"velis/timeProgs/{gw}")

    async def async_get_consumption(self, gw: str) -> list[dict[str, Any]]:
        return list(
            await self._get(f"remote/reports/{gw}/consSequencesApi8?usages=Dhw") or []
        )

    async def async_get_bus_errors(self, gw: str) -> list[dict[str, Any]]:
        return list(
            await self._get(
                f"busErrors?gatewayId={gw}&blockingOnly=False&culture=en-US"
            )
            or []
        )

    # -- ghi (body đúng như app) -----------------------------------------------

    async def async_set_power(self, gw: str, on: bool) -> None:
        await self._post(f"velis/medPlantData/{gw}/switch", bool(on))

    async def async_set_temperature(
        self, gw: str, new: float, old: float | None, eco: bool
    ) -> None:
        # ChangeMedTemperatureDto: {"eco": bool, "new": double, "old": double}
        await self._post(
            f"velis/medPlantData/{gw}/temperature",
            {"eco": bool(eco), "new": float(new), "old": float(old if old is not None else new)},
        )

    async def async_set_mode(self, gw: str, new: int, old: int | None) -> None:
        await self._post(
            f"velis/medPlantData/{gw}/mode",
            {"new": int(new), "old": int(old if old is not None else new)},
        )

    async def async_set_eco(self, gw: str, on: bool) -> None:
        await self._post(f"velis/medPlantData/{gw}/switchEco", bool(on))

    async def async_set_power_off_timer(
        self, gw: str, minutes: int, old: int | None, prev_mode: int
    ) -> None:
        # ChangeMedPowerOffTimerDto: {"new", "old", "prevMode"}
        await self._post(
            f"velis/medPlantData/{gw}/powerOffTimer",
            {"new": int(minutes), "old": old, "prevMode": int(prev_mode)},
        )

    async def async_set_plant_setting(
        self, gw: str, setting: str, new: float, old: float | None
    ) -> None:
        # Map<ePlantSettingIdDto, ChangeValueDto<Double>>
        await self._post(
            f"velis/medPlantData/{gw}/plantSettings",
            {setting: {"new": float(new), "old": float(old if old is not None else new)}},
        )

    async def async_set_time_program(self, gw: str, plans: list[dict[str, Any]]) -> None:
        await self._post(f"velis/timeProgs/{gw}", {"plans": plans})
