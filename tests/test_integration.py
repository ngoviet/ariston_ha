"""API, config flow, setup, entity và lệnh ghi — HTTP mock bằng aioclient_mock."""

from __future__ import annotations

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ariston_ha.const import DOMAIN
from custom_components.ariston_ha.coordinator import (
    consumption_sequence,
    schedule_by_day,
)

from .conftest import BASE, GW, PLANTS, USER_INPUT, mock_cloud


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Tầng 3",
        unique_id=GW,
        data={**USER_INPUT, "gw": GW, "device": PLANTS[0]},
    )


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _eid(hass: HomeAssistant, platform: str, key: str) -> str:
    eid = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{GW}_{key}")
    assert eid, f"thiếu entity {platform} {key}"
    return eid


def _posts(mock, suffix: str) -> list:
    return [
        c for c in mock.mock_calls
        if c[0] == "POST" and str(c[1]).split("?")[0].endswith(suffix)
    ]


# --- hàm thuần ------------------------------------------------------------

def test_consumption_sequence():
    cons = [{"k": 2, "p": 2, "v": [1.0, 2.0, 3.0]}, {"k": 2, "p": 1, "v": [9.0]}]
    assert consumption_sequence(cons, 2) == [1.0, 2.0, 3.0]
    assert consumption_sequence(cons, 4) is None


def test_schedule_by_day():
    days = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
    plans = [{"days": [1, 0], "shws": [{"time": "06:00:00", "temp": 60.0}]}]
    out = schedule_by_day(plans, days)
    assert out["Monday"] == ["06:00 60°C"]
    assert out["Sunday"] == ["06:00 60°C"]


# --- config flow ----------------------------------------------------------

async def test_flow_success(hass: HomeAssistant, aioclient_mock):
    mock_cloud(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    # chỉ 1 bình Med (Evo bị loại) → tạo entry luôn
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == GW
    assert result["data"]["gw"] == GW


async def test_flow_invalid_auth(hass: HomeAssistant, aioclient_mock):
    mock_cloud(aioclient_mock, login_status=405)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


# --- setup + entity -------------------------------------------------------

async def test_setup_creates_entities(hass: HomeAssistant, cloud):
    await _setup(hass)
    wh = hass.states.get(_eid(hass, "water_heater", "water_heater"))
    # state của water_heater = chế độ hiện tại (giống entity cũ); nguồn bật/tắt ở switch.power
    assert wh.state == "MANUAL"
    assert wh.attributes["current_temperature"] == 43.0
    assert wh.attributes["temperature"] == 80.0
    assert wh.attributes["max_temp"] == 80.0
    assert wh.attributes["operation_list"] == ["MANUAL", "PROGRAM"]
    assert wh.attributes["operation_mode"] == "MANUAL"

    assert hass.states.get(_eid(hass, "switch", "power")).state == "off"
    assert hass.states.get(_eid(hass, "binary_sensor", "is_heating")).state == "off"
    assert hass.states.get(_eid(hass, "sensor", "average_showers")).state == "0"
    assert hass.states.get(_eid(hass, "select", "auto_power_off")).state == "off"
    # busErrors 500 → errors_count unavailable (giữ đúng hành vi hiện tại)
    assert hass.states.get(_eid(hass, "sensor", "errors_count")).state == "unavailable"
    energy = hass.states.get(_eid(hass, "sensor", "energy_today"))
    assert float(energy.state) == 0.008  # phần tử cuối Last7Days
    prog = hass.states.get(_eid(hass, "sensor", "time_program"))
    assert prog.state == "7"  # 5 ngày×1 + 2 ngày×1
    assert prog.attributes["schedule"]["Monday"] == ["06:00 60°C"]


async def test_auto_power_off_select(hass: HomeAssistant, cloud, aioclient_mock):
    await _setup(hass)
    sel = _eid(hass, "select", "auto_power_off")
    aioclient_mock.post(f"{BASE}velis/medPlantData/{GW}/mode", json={})
    aioclient_mock.post(f"{BASE}velis/medPlantData/{GW}/powerOffTimer", json={})
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": sel, "option": "30"}, blocking=True,
    )
    await hass.async_block_till_done()
    # mode → 12 rồi powerOffTimer
    assert _posts(aioclient_mock, "/mode")
    timer = _posts(aioclient_mock, "/powerOffTimer")
    assert timer and timer[0][2] == {"new": 30, "old": 15, "prevMode": 1}


async def test_set_temperature(hass: HomeAssistant, cloud, aioclient_mock):
    await _setup(hass)
    wh = _eid(hass, "water_heater", "water_heater")
    aioclient_mock.post(f"{BASE}velis/medPlantData/{GW}/temperature", json={})
    await hass.services.async_call(
        "water_heater", "set_temperature",
        {"entity_id": wh, "temperature": 70}, blocking=True,
    )
    await hass.async_block_till_done()
    posts = _posts(aioclient_mock, "/temperature")
    assert posts and posts[0][2] == {"eco": False, "new": 70.0, "old": 80.0}


async def test_power_switch(hass: HomeAssistant, cloud, aioclient_mock):
    await _setup(hass)
    aioclient_mock.post(f"{BASE}velis/medPlantData/{GW}/switch", json={})
    await hass.services.async_call(
        "switch", "turn_on",
        {"entity_id": _eid(hass, "switch", "power")}, blocking=True,
    )
    await hass.async_block_till_done()
    posts = _posts(aioclient_mock, "/switch")
    assert posts and posts[0][2] is True


async def test_set_time_program_service(hass: HomeAssistant, cloud, aioclient_mock):
    await _setup(hass)
    aioclient_mock.post(f"{BASE}velis/timeProgs/{GW}", json={})
    await hass.services.async_call(
        DOMAIN, "set_time_program",
        {"plans": [{"days": [1, 2], "shws": [{"time": "06:00", "temp": 60}]}]},
        blocking=True,
    )
    await hass.async_block_till_done()
    posts = _posts(aioclient_mock, f"timeProgs/{GW}")
    assert posts
    sent = posts[0][2]["plans"][0]
    assert sent["days"] == [1, 2]
    assert sent["shws"][0]["time"] == "06:00:00"


async def test_set_time_program_rejects_duplicate_day(hass: HomeAssistant, cloud):
    await _setup(hass)
    from homeassistant.exceptions import ServiceValidationError

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "set_time_program",
            {
                "plans": [
                    {"days": [1], "shws": [{"time": "06:00", "temp": 60}]},
                    {"days": [1], "shws": [{"time": "07:00", "temp": 60}]},
                ]
            },
            blocking=True,
        )
