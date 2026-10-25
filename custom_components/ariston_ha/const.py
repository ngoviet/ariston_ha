"""Hằng số cho Ariston NET.

Endpoint và body lấy từ app Ariston NET 7.0.2.40360 (`WheMedPlantDataProxy`,
`WheTimeProgProxy`, DTO `ChangeMedTemperatureDto` / `ChangeValueDto` /
`ChangeMedPowerOffTimerDto`) và đối chiếu bằng request thật trên bình Slim3.
"""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "ariston_ha"

API_URL = "https://www.ariston-net.remotethermo.com/api/v2/"
# Cloud chấp nhận User-Agent này (thư viện fustom dùng từ lâu); không cần giả app Android.
USER_AGENT = "RestSharp/106.11.7.0"
REQUEST_TIMEOUT = 30

CONF_GATEWAY = "gw"
CONF_SCAN_INTERVAL = "scan_interval"

# Trạng thái bình (medPlantData) — automation PV cần thấy bật/tắt nhanh.
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 600
# Cài đặt, lịch tuần, điện năng, lỗi bus: đổi chậm, cloud cập nhật thưa.
SLOW_INTERVAL = timedelta(minutes=30)
# Bị HTTP 429 thì lùi hẳn một quãng trước khi hỏi lại.
RATE_LIMIT_BACKOFF = timedelta(minutes=5)
# Cloud cần vài giây trước khi medPlantData phản ánh lệnh vừa ghi.
WRITE_SETTLE_SECONDS = 4

# `sys` trong velis/plants
SYS_VELIS = 4
# `wheType` 3 = họ "Med" (app) — thư viện fustom gọi là Lydos.
WHE_TYPE_MED = 3
# `wheModelType` (eWheModel trong app)
WHE_MODEL_NAMES = {32: "Slim3"}

# eMedPlantMode
MODE_MANUAL = 1
MODE_PROGRAM = 5
MODE_BOOST = 9
MODE_EXTERNAL = 11
MODE_AUTO_POWER_OFF = 12
# Tên hiển thị giữ đúng chữ in hoa như integration cũ — dashboard so sánh 'MANUAL' / 'PROGRAM'.
MODE_NAMES = {
    MODE_MANUAL: "MANUAL",
    MODE_PROGRAM: "PROGRAM",
    MODE_BOOST: "BOOST",
    MODE_EXTERNAL: "EXTERNAL",
    MODE_AUTO_POWER_OFF: "AUTO_POWER_OFF",
}
# App ẩn Boost với Slim3 ⇒ chỉ cho chọn 2 chế độ này.
SELECTABLE_MODES = (MODE_MANUAL, MODE_PROGRAM)

# Hẹn giờ tắt — đúng 4 mức của app (HomeVelisActivity.btnAutoPowerOffClick).
AUTO_POWER_OFF_MINUTES = (15, 30, 60, 90)

# plantSettings (ePlantSettingIdDto) — giá trị trên dây là số thực.
SETTING_MAX_TEMP = "MedMaxSetpointTemperature"
SETTING_MAX_TEMP_MIN = "MedMaxSetpointTemperatureMin"
SETTING_MAX_TEMP_MAX = "MedMaxSetpointTemperatureMax"
SETTING_ANTI_LEGIONELLA = "MedAntilegionellaOnOff"
SETTING_HEATING_RATE = "MedHeatingRate"

MIN_TEMP = 40.0
DEFAULT_MAX_TEMP = 80.0

# timeProgs: `days` trên dây là số .NET DayOfWeek (Chủ nhật = 0), KHÔNG phải tên enum Kotlin.
DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")

# consSequencesApi8: k = loại (2 = nước nóng), p = kỳ; phần tử cuối = hiện tại.
CONSUMPTION_DHW = 2
PERIOD_24H = 1
PERIOD_7D = 2
