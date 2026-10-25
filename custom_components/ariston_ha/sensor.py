"""sensor: nhiệt độ yêu cầu, số lượt tắm, thời gian còn lại, lỗi, điện năng, lịch, chẩn đoán."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AristonConfigEntry
from .const import (
    DAYS,
    MODE_NAMES,
    PERIOD_7D,
    PERIOD_24H,
    SETTING_HEATING_RATE,
)
from .coordinator import consumption_sequence, schedule_by_day
from .entity import AristonEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AristonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    c = entry.runtime_data
    async_add_entities(
        [
            ProcReqTempSensor(c),
            AverageShowersSensor(c),
            RemainingTimeSensor(c),
            ErrorsCountSensor(c),
            EnergyTotalSensor(c),
            EnergyTodaySensor(c),
            TimeProgramSensor(c),
            PlantModeSensor(c),
        ]
    )


class ProcReqTempSensor(AristonEntity, SensorEntity):
    _attr_translation_key = "proc_req_temp"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-auto"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "proc_req_temp")

    @property
    def native_value(self) -> float | None:
        value = self.plant.get("procReqTemp")
        return float(value) if value is not None else None


class AverageShowersSensor(AristonEntity, SensorEntity):
    _attr_translation_key = "average_showers"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:shower-head"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "average_showers")

    @property
    def native_value(self) -> int | None:
        value = self.plant.get("avShw")
        return int(value) if value is not None else None


class RemainingTimeSensor(AristonEntity, SensorEntity):
    """rmTm = "HH:MM:SS" còn lại tới nhiệt đặt → phút."""

    _attr_translation_key = "remaining_time"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:timer"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "remaining_time")

    @property
    def native_value(self) -> int | None:
        raw = self.plant.get("rmTm")
        if not raw:
            return None
        try:
            h, m, s = (int(x) for x in str(raw).split(":"))
        except (ValueError, TypeError):
            return None
        return h * 60 + m + round(s / 60)


class ErrorsCountSensor(AristonEntity, SensorEntity):
    """Số lỗi bus. Cloud busErrors đang trả HTTP 500 → None (unavailable)."""

    _attr_translation_key = "errors_count"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:alert-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "errors_count")

    @property
    def available(self) -> bool:
        # Chưa đọc được busErrors (cloud 500) ⇒ unavailable, giống entity cũ.
        return super().available and self.coordinator.data.bus_errors is not None

    @property
    def native_value(self) -> int | None:
        errors = self.coordinator.data.bus_errors
        return len(errors) if errors is not None else None


class EnergyTotalSensor(AristonEntity, SensorEntity):
    """Điện năng nước nóng theo cloud — phần tử cuối của dãy 12 tháng (tham khảo).

    Automation PV & Energy dashboard dùng sensor đo tại chỗ (sensor.binh_nong_t3_dien_nang),
    không dùng sensor này — giữ để tương thích id cũ.
    """

    _attr_translation_key = "energy_total"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "energy_total")

    @property
    def native_value(self) -> float | None:
        from .const import CONSUMPTION_DHW

        for seq in self.coordinator.data.consumption or []:
            if seq.get("k") == CONSUMPTION_DHW and seq.get("p") == 4:
                values = seq.get("v") or []
                return float(values[-1]) if values else None
        return None


class EnergyTodaySensor(AristonEntity, SensorEntity):
    """Điện năng hôm nay = phần tử cuối dãy Last7Days (p=2). Chỉ tham khảo."""

    _attr_translation_key = "energy_today"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "energy_today")

    @property
    def available(self) -> bool:
        return super().available and consumption_sequence(
            self.coordinator.data.consumption, PERIOD_7D
        ) is not None

    @property
    def native_value(self) -> float | None:
        days = consumption_sequence(self.coordinator.data.consumption, PERIOD_7D)
        return days[-1] if days else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "last_24h_hourly": consumption_sequence(self.coordinator.data.consumption, PERIOD_24H),
            "last_7_days": consumption_sequence(self.coordinator.data.consumption, PERIOD_7D),
        }


class TimeProgramSensor(AristonEntity, SensorEntity):
    """State = số khung tắm/tuần; thuộc tính `schedule` dễ đọc + `plans` thô."""

    _attr_translation_key = "time_program"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "time_program")

    @property
    def _plans(self) -> list[dict[str, Any]]:
        prog = self.coordinator.data.time_prog or {}
        return prog.get("plans") or []

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.time_prog is not None

    @property
    def native_value(self) -> int:
        return sum(len(p.get("days") or []) * len(p.get("shws") or []) for p in self._plans)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        by_day = schedule_by_day(self._plans, DAYS)
        ordered = {d: by_day[d] for d in (*DAYS[1:], DAYS[0]) if d in by_day}
        return {"schedule": ordered, "plans": self._plans}


class PlantModeSensor(AristonEntity, SensorEntity):
    """Chẩn đoán: mode thô + các cờ của medPlantData."""

    _attr_translation_key = "plant_mode"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "plant_mode")

    @property
    def native_value(self) -> str | None:
        mode = self.plant.get("mode")
        if mode is None:
            return None
        return MODE_NAMES.get(mode, f"mode_{mode}")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        keys = ("mode", "on", "eco", "pwrOpt", "pwrOffTime", "rmTm", "eco_version")
        return {k: self.plant.get(k) for k in keys} | {
            "heating_rate": self.settings.get(SETTING_HEATING_RATE)
        }
