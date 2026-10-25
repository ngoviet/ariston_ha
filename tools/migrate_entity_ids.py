"""Đổi entity_id của ariston_ha về đúng id của integration cũ (`ariston` của fustom + `ariston_slim3`).

Mục đích: dashboard / automation không phải sửa, lịch sử recorder nối tiếp id cũ.
Chạy SAU KHI đã xoá hai config entry cũ (`ariston`, `ariston_slim3`) để các id cũ được giải phóng.

    python tools/migrate_entity_ids.py           # chạy thử: chỉ in kế hoạch
    python tools/migrate_entity_ids.py --apply    # đổi thật

Cần `.env` có HA_URL (vd http://192.168.10.15:8123) và HA_TOKEN (long-lived token).

⚠ Tiền tố id cũ là tên device khi cài: bình tên "Tầng 3" → slug `tang_3`. Nếu bình anh tên khác,
sửa PREFIX bên dưới (hoặc đối chiếu bảng in ra trước khi --apply).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import websockets

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DOMAIN = "ariston_ha"
PREFIX = "tang_3"  # slug tên device cũ — đổi nếu bình của anh tên khác

# key (phần unique_id sau "<gw>_") → entity_id cũ (của `ariston` fustom + `ariston_slim3`)
FIXED = {
    "water_heater": f"water_heater.{PREFIX}",
    "power": f"switch.{PREFIX}_ariston_power",
    "eco": f"switch.{PREFIX}_ariston_eco_mode",
    "anti_legionella": f"switch.{PREFIX}_ariston_anti_legionella",
    "is_heating": f"binary_sensor.{PREFIX}_ariston_is_heating",
    "anti_legionella_cycle": f"binary_sensor.{PREFIX}_ariston_anti_legionella_cycle",
    "max_setpoint_temperature": f"number.{PREFIX}_ariston_max_setpoint_temperature",
    "proc_req_temp": f"sensor.{PREFIX}_ariston_proc_req_temp",
    "average_showers": f"sensor.{PREFIX}_ariston_average_showers",
    "remaining_time": f"sensor.{PREFIX}_ariston_remaining_time",
    "errors_count": f"sensor.{PREFIX}_ariston_errors_count",
    "energy_total": f"sensor.{PREFIX}_ariston_domestic_hot_water_total_energy_consumption",
    "auto_power_off": f"select.{PREFIX}_slim3_auto_power_off",
    "time_program": f"sensor.{PREFIX}_slim3_time_program",
    "plant_mode": f"sensor.{PREFIX}_slim3_plant_mode",
    "energy_today": f"sensor.{PREFIX}_slim3_energy_today",
}


def load_env() -> dict[str, str]:
    return dict(
        line.strip().split("=", 1)
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )


async def main(apply: bool) -> int:
    env = load_env()
    url = env["HA_URL"].rstrip("/").replace("http", "ws", 1) + "/api/websocket"
    async with websockets.connect(url, max_size=None) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": env["HA_TOKEN"]}))
        if json.loads(await ws.recv())["type"] != "auth_ok":
            print("Token bị từ chối")
            return 1
        msg_id = 0

        async def call(payload: dict) -> dict:
            nonlocal msg_id
            msg_id += 1
            await ws.send(json.dumps({"id": msg_id, **payload}))
            while True:
                res = json.loads(await ws.recv())
                if res.get("id") == msg_id:
                    return res

        entries = (await call({"type": "config/entity_registry/list"}))["result"]
        in_use = {e["entity_id"] for e in entries}
        ours = [e for e in entries if e["platform"] == DOMAIN]
        if not ours:
            print("Chưa có entity ariston_ha nào — thêm integration trước.")
            return 1
        if any(e["platform"] in ("ariston", "ariston_slim3") for e in entries):
            print("⚠ Vẫn còn entity ariston/ariston_slim3 — xoá 2 config entry cũ trước rồi chạy lại.")

        failed = 0
        for e in sorted(ours, key=lambda e: e["entity_id"]):
            key = e["unique_id"].split("_", 1)[1]
            target = FIXED.get(key)
            if target is None or target == e["entity_id"]:
                continue
            if target in in_use:
                print(f"  BỎ QUA  {e['entity_id']} → {target} (id đích đang có người dùng)")
                continue
            print(f"  {'ĐỔI' if apply else 'SẼ ĐỔI'}  {e['entity_id']} → {target}")
            if apply:
                res = await call(
                    {
                        "type": "config/entity_registry/update",
                        "entity_id": e["entity_id"],
                        "new_entity_id": target,
                    }
                )
                if not res.get("success"):
                    failed += 1
                    print(f"     lỗi: {res.get('error')}")
        if not apply:
            print("\nChạy thử xong. Thêm --apply để đổi thật.")
        return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="đổi thật (mặc định chỉ in)")
    raise SystemExit(asyncio.run(main(parser.parse_args().apply)))
