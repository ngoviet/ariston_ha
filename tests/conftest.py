"""Fixture chung. Payload mô phỏng ĐÚNG response cloud Ariston NET đo trên bình Slim3 thật
(2026-10-25): medPlantData, plantSettings, consSequencesApi8, timeProgs, login. Tài khoản/gw là giả.
"""

from __future__ import annotations

import sys

import pytest

if sys.platform == "win32":
    # HA 2026.9 import `fcntl` khi nạp runner.py (POSIX-only). Chèn shim no-op TRƯỚC khi
    # PHACC nạp để chạy được test trên Windows (CI Linux không cần). Test không khoá file thật.
    import types

    if "fcntl" not in sys.modules:
        _fcntl = types.ModuleType("fcntl")
        _fcntl.LOCK_EX = _fcntl.LOCK_NB = _fcntl.LOCK_UN = _fcntl.LOCK_SH = 0
        _fcntl.flock = lambda *a, **k: None
        _fcntl.fcntl = lambda *a, **k: 0
        _fcntl.ioctl = lambda *a, **k: 0
        sys.modules["fcntl"] = _fcntl

    # PHACC chặn socket; Windows không có AF_UNIX nên self-pipe dùng AF_INET → bị chặn.
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None

pytest_plugins = "pytest_homeassistant_custom_component"

BASE = "https://www.ariston-net.remotethermo.com/api/v2/"
GW = "AA11BB22CC33"
USER_INPUT = {"username": "tester@example.com", "password": "pw"}

PLANT = {
    "gw": GW,
    "on": False,
    "mode": 1,
    "temp": 43.0,
    "procReqTemp": 80.0,
    "reqTemp": 80.0,
    "antiLeg": False,
    "heatReq": False,
    "eco": False,
    "rmTm": "00:00:00",
    "avShw": 0,
    "pwrOpt": False,
    "pwrOffTime": 15,
    "eco_version": 0,
}
SETTINGS = {
    "MedMaxSetpointTemperature": 80.0,
    "MedMaxSetpointTemperatureMin": 65.0,
    "MedMaxSetpointTemperatureMax": 80.0,
    "MedAntilegionellaOnOff": 0.0,
    "MedHeatingRate": 107.0,
}
CONSUMPTION = [
    {"k": 2, "p": 1, "v": [0.0] * 15 + [0.008] + [0.0] * 8},
    {"k": 2, "p": 2, "v": [0.608, 0.355, 0.436, 0.297, 0.866, 0.0, 0.008]},
    {"k": 2, "p": 3, "v": [0.0] * 54},
    {"k": 2, "p": 4, "v": [0.0] * 21},
]
TIME_PROG = {
    "plans": [
        {"days": [1, 2, 3, 4, 5], "shws": [{"time": "06:00:00", "qty": -1, "temp": 60.0}]},
        {"days": [6, 0], "shws": [{"time": "08:00:00", "qty": -1, "temp": 65.0}]},
    ]
}
PLANTS = [
    {"gw": GW, "name": "Tầng 3", "sys": 4, "wheType": 3, "wheModelType": 32,
     "gwFwVer": {"FwVer1": "01.04.00", "FwVer2": "014.115.24"}},
    {"gw": "DEADBEEF0000", "name": "Khác", "sys": 4, "wheType": 1},  # Evo → bị loại
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def mock_cloud(aioclient_mock, *, plant=None, login_status=200):
    """Đăng ký mọi endpoint đọc; trả bản copy để test sửa thoải mái."""
    aioclient_mock.post(
        BASE + "accounts/login",
        status=login_status,
        json={"token": "tok-123"} if login_status == 200 else {},
    )
    aioclient_mock.get(BASE + "velis/plants", json=PLANTS)
    aioclient_mock.get(f"{BASE}velis/medPlantData/{GW}", json=dict(plant or PLANT))
    aioclient_mock.get(f"{BASE}velis/medPlantData/{GW}/plantSettings", json=dict(SETTINGS))
    aioclient_mock.get(
        f"{BASE}remote/reports/{GW}/consSequencesApi8?usages=Dhw", json=list(CONSUMPTION)
    )
    aioclient_mock.get(f"{BASE}velis/timeProgs/{GW}", json=dict(TIME_PROG))
    # busErrors đang 500 ở cloud thật — mô phỏng đúng vậy
    aioclient_mock.get(
        f"{BASE}busErrors?gatewayId={GW}&blockingOnly=False&culture=en-US", status=500
    )
    return aioclient_mock


@pytest.fixture
def cloud(aioclient_mock):
    return mock_cloud(aioclient_mock)
