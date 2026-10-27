# Ariston NET cho Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![GitHub release](https://img.shields.io/github/v/release/ngoviet/ariston_ha)](https://github.com/ngoviet/ariston_ha/releases)
[![Validate](https://github.com/ngoviet/ariston_ha/actions/workflows/validate.yml/badge.svg)](https://github.com/ngoviet/ariston_ha/actions/workflows/validate.yml)
[![Test](https://github.com/ngoviet/ariston_ha/actions/workflows/test.yml/badge.svg)](https://github.com/ngoviet/ariston_ha/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/github/license/ngoviet/ariston_ha)](LICENSE)

[English](README.md) · **Tiếng Việt**

[![Mở Home Assistant của bạn và mở một kho trong Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ngoviet&repository=ariston_ha&category=integration)

**Integration tuỳ chỉnh cho Home Assistant** để điều khiển và theo dõi **bình nóng lạnh
Ariston** dòng **Velis "Med"** — **Slim3 Top Wi-Fi**, và nhiều khả năng cả Lydos / Velis Evo —
qua **cloud Ariston NET**. Cài qua **HACS**, thiết lập từ giao diện, gộp mọi chức năng app
chính chủ có cho dòng này trong **một thiết bị**: nhiệt độ, chế độ MANUAL / PROGRAM, nguồn,
ECO, diệt khuẩn, hẹn giờ tắt và lịch tuần.

- **Bình nóng lạnh** — nhiệt độ hiện tại/đặt, chế độ `MANUAL` / `PROGRAM`, bật/tắt.
- **Công tắc** — nguồn, ECO, diệt khuẩn.
- **Hẹn giờ tắt** — đúng 4 mức 15 / 30 / 60 / 90 phút của app, dạng `select`.
- **Lịch tuần** — lịch hâm nước từng ngày, hiện ở sensor và sửa bằng dịch vụ
  `ariston_ha.set_time_program`.
- **Cảm biến** — nhiệt độ yêu cầu, số lượt tắm, thời gian tới nhiệt, số lỗi, và điện năng từ
  cloud (chỉ tham khảo).
- **Nhiệt độ tối đa** — giới hạn nhiệt đặt, dạng `number`.
- **Không thư viện ngoài** — nói chuyện với cloud bằng `aiohttp` sẵn có của HA.
- Cài qua UI (config flow), tự đăng nhập lại khi token hết hạn, tuỳ chọn (chu kỳ đọc),
  diagnostics, giao diện Anh & Việt.

> Viết cho và đã thử trên **Ariston Slim3 Top Wi-Fi** (`sys=4` VELIS, `wheType=3`,
> `wheModelType=32`). Các bình Velis "Med" khác (Evo, họ Lydos) dùng cùng API nên nhiều khả
> năng chạy được, nhưng chưa thử ở đây. Cần **Home Assistant 2026.9** trở lên.

> **Vì sao dùng cloud mà không chạy local?** Module Wi-Fi của bình nói chuyện với AWS IoT qua
> **TLS hai chiều** (kiểm chứng chuỗi CA của máy chủ và xuất chứng chỉ client của chính nó),
> **không mở API LAN** nào, và giữ khoá riêng trong flash đã mã hoá. Bắt gói Wi-Fi hay giả
> cloud đều bất khả thi; đường local thật sự duy nhất là đấu UART bên trong bình. Integration
> này dùng chính cloud API mà app chính chủ dùng.

## Mục lục

- [1. Cài đặt](#1-cài-đặt)
- [2. Thêm integration](#2-thêm-integration)
- [Thực thể](#thực-thể)
- [Lịch tuần](#lịch-tuần)
- [Lưu ý & giới hạn](#lưu-ý--giới-hạn)
- [Gỡ](#gỡ)
- [Phát triển](#phát-triển)

## 1. Cài đặt

**HACS (một chạm):** bấm nút rồi xác nhận — nó mở *Custom repositories* trên chính Home
Assistant của bạn, đã điền sẵn kho này.

[![Mở Home Assistant của bạn và mở một kho trong Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ngoviet&repository=ariston_ha&category=integration)

**HACS (thủ công):** HACS → ⋮ → *Custom repositories* → thêm
`https://github.com/ngoviet/ariston_ha`, loại *Integration* → cài → khởi động lại HA.

**Thủ công:** chép `custom_components/ariston_ha/` vào thư mục `config/custom_components/` của
HA rồi khởi động lại.

## 2. Thêm integration

*Cài đặt → Thiết bị & Dịch vụ → Thêm tích hợp → **Ariston NET***. Nhập **đúng email và mật
khẩu** dùng trên app Ariston NET. Nếu tài khoản có nhiều bình hỗ trợ, chọn một; thêm lại
integration cho mỗi bình khác.

Chu kỳ đọc trạng thái trực tiếp (nguồn, nhiệt độ, chế độ) chỉnh trong *Tuỳ chọn* của
integration (mặc định 60 giây; cài đặt, lịch và điện năng đọc mỗi 30 phút).

## Thực thể

| Thực thể | Loại | Ghi chú |
|---|---|---|
| Bình nóng lạnh | `water_heater` | Nhiệt đặt, `MANUAL`/`PROGRAM`, bật/tắt |
| Nguồn | `switch` | Nguồn bình |
| ECO | `switch` | Chế độ ECO |
| Diệt khuẩn | `switch` | Bật cài đặt diệt khuẩn |
| Hẹn giờ tắt | `select` | `off` / `15` / `30` / `60` / `90` phút |
| Nhiệt độ tối đa | `number` | Giới hạn nhiệt đặt (65–80 °C) |
| Đang đun | `binary_sensor` | Điện trở đang đun |
| Chu kỳ diệt khuẩn | `binary_sensor` | Đang chạy chu kỳ diệt khuẩn |
| Nhiệt độ yêu cầu | `sensor` | Mức bình đang hướng tới |
| Số lượt tắm | `sensor` | Ước tính "số lượt tắm" của app |
| Thời gian còn lại | `sensor` | Số phút tới nhiệt đặt |
| Số lỗi | `sensor` | Lỗi bus (có thể unavailable, xem lưu ý) |
| Điện năng tích luỹ (cloud) | `sensor` | Số cloud, chỉ tham khảo |
| Điện năng hôm nay (cloud) | `sensor` | Số cloud, chỉ tham khảo |
| Lịch tuần | `sensor` | Số lượt/tuần; thuộc tính `schedule` & `plans` |
| Chế độ (thô) | `sensor` | Chẩn đoán: mode thô + các cờ |

## Lịch tuần

Lịch chỉ có tác dụng khi bình ở chế độ **PROGRAM**. Ghi đè bằng dịch vụ
`ariston_ha.set_time_program`:

```yaml
action: ariston_ha.set_time_program
data:
  plans:
    - days: [1, 2, 3, 4, 5]        # 0 = Chủ nhật … 6 = Thứ bảy (hoặc tên ngày tiếng Anh)
      shws: [{ time: "06:00", temp: 60 }]
    - days: [6, 0]
      shws: [{ time: "08:00", temp: 65 }]
```

Mỗi ngày chỉ được nằm trong một plan (dịch vụ từ chối nếu trùng). Dùng
`ariston_ha.refresh_time_program` để đọc lại lịch và cài đặt từ cloud.

## Lưu ý & giới hạn

- **Chỉ qua cloud** — cần Internet và cloud Ariston hoạt động; không có điều khiển local.
- **Lệnh ghi được đọc lại để xác nhận** — sau mỗi lệnh, integration chờ vài giây rồi đọc lại
  bình nên trạng thái là dữ liệu cloud thật, không phải đoán lạc quan.
- **Sensor điện năng chỉ tham khảo** — cloud cập nhật thưa; cho Energy dashboard hãy đo công
  suất tại ổ cắm.
- **Số lỗi có thể unavailable** — endpoint `busErrors` của cloud đang trả HTTP 500; khi đó
  sensor để `unavailable` thay vì đoán.
- **Không có Boost** — app ẩn Boost với dòng máy này.

## Gỡ

*Cài đặt → Thiết bị & Dịch vụ → Ariston NET → ⋮ → Xoá*.

## Phát triển

Test giả lập cloud bằng `aioclient_mock`; fixture dùng dạng payload đo từ bình Slim3 thật.
Chạy:

```bash
pip install -r requirements_test.txt
pytest -q
```

Chi tiết thanh ghi/body được rút từ app Ariston NET và kiểm chứng trên bình thật. Dự án không
liên kết hay được Ariston bảo trợ.

---

<!-- support:start -->
## Ủng hộ dự án

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/banner.svg" width="720" alt="Built and maintained by one person in Việt Nam">
</p>

<p align="center">
  <a href="https://buymeacoffee.com/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-coffee.svg" height="56" alt="Buy me a coffee"></a>
  &nbsp;
  <a href="https://github.com/sponsors/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-sponsors.svg" height="56" alt="GitHub Sponsors"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/vietqr-card.svg" width="300" alt="VietQR — MB Bank — NGO DUC VIET — 911051212">
</p>

<p align="center"><sub>🇻🇳 VietQR: quét bằng app ngân hàng bất kỳ, nội dung <code>Ung ho ariston_ha</code>. Cảm ơn bạn! · Thank you for keeping this project alive.</sub></p>
<!-- support:end -->
