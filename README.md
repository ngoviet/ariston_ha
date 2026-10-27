# Ariston NET for Home Assistant

<!-- readme-axi type=ha -->

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![GitHub release](https://img.shields.io/github/v/release/ngoviet/ariston_ha)](https://github.com/ngoviet/ariston_ha/releases)
[![Validate](https://github.com/ngoviet/ariston_ha/actions/workflows/validate.yml/badge.svg)](https://github.com/ngoviet/ariston_ha/actions/workflows/validate.yml)
[![Test](https://github.com/ngoviet/ariston_ha/actions/workflows/test.yml/badge.svg)](https://github.com/ngoviet/ariston_ha/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/github/license/ngoviet/ariston_ha)](LICENSE)

**English** · [Tiếng Việt](README.vi.md)

A **Home Assistant custom integration** to control and monitor an **Ariston electric water
heater** of the **Velis "Med"** family — **Slim3 Top Wi-Fi**, and likely Lydos / Velis Evo —
through the **Ariston NET cloud**. Installs via **HACS**, sets up from the UI, and covers
everything the official Ariston NET app offers for this model in **one device**: temperature,
MANUAL / PROGRAM mode, power, ECO, anti-legionella, the auto power-off timer, and the weekly
schedule.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ngoviet&repository=ariston_ha&category=integration)

> 🇻🇳 Built and maintained by one person in Việt Nam — if it saves you time, please
> [support the project](#support-the-project).

## Contents

- [Features](#features)
- [Supported devices](#supported-devices)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [Services](#services)
- [Troubleshooting](#troubleshooting)
- [How it works](#how-it-works)
- [Development](#development)

## Features

- **Water heater** — current / target temperature, `MANUAL` / `PROGRAM` mode, on/off.
- **Switches** — power, ECO, anti-legionella.
- **Auto power-off timer** — the app's 15 / 30 / 60 / 90-minute timer, as a `select`.
- **Weekly program** — the per-day hot-water schedule, exposed as a sensor and editable with
  the `ariston_ha.set_time_program` service.
- **Sensors** — requested temperature, average showers, time to setpoint, error count, and
  the cloud energy figures (reference only).
- **Maximum temperature** — the device's max setpoint limit, as a `number`.
- **No extra dependencies** — talks to the cloud with Home Assistant's own `aiohttp`.
- UI setup (config flow), re-login on token expiry, options (poll interval), diagnostics,
  English and Vietnamese UI.

## Supported devices

Built for and tested on **Ariston Slim3 Top Wi-Fi** (`sys=4` VELIS, `wheType=3`,
`wheModelType=32`). Other Velis "Med" heaters (Evo, Lydos family) share the same API and are
likely to work, but are untested here. Requires **Home Assistant 2026.9** or newer.

## Installation

**HACS (one click):** click the button and confirm — it opens *Custom repositories* on your
own Home Assistant pre-filled for this repo.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ngoviet&repository=ariston_ha&category=integration)

**HACS (manual):** HACS → ⋮ → *Custom repositories* → add
`https://github.com/ngoviet/ariston_ha`, category *Integration* → install → restart HA.

**Manual:** copy `custom_components/ariston_ha/` into your HA `config/custom_components/`
folder and restart HA.

**Removal:** *Settings → Devices & Services → Ariston NET → ⋮ → Delete*.

## Configuration

*Settings → Devices & Services → Add Integration → **Ariston NET***. Enter the **same email
and password** you use in the Ariston NET app. If the account has more than one supported
heater, pick one; add the integration again for each additional heater.

The poll interval for the live state (power, temperature, mode) is configurable in the
integration's *Options* (default 60 s; settings, schedule and energy are read every 30 min).

## Entities

| Entity | Type | Notes |
|---|---|---|
| Water heater | `water_heater` | Target temp, `MANUAL`/`PROGRAM`, on/off |
| Power | `switch` | Heater power |
| ECO | `switch` | ECO mode |
| Anti-legionella | `switch` | Enable the disinfection setting |
| Auto power-off | `select` | `off` / `15` / `30` / `60` / `90` minutes |
| Maximum temperature | `number` | Max setpoint limit (65–80 °C) |
| Heating | `binary_sensor` | Element currently heating |
| Anti-legionella cycle | `binary_sensor` | Disinfection cycle running |
| Requested temperature | `sensor` | What the heater is working toward |
| Average showers | `sensor` | App's "available showers" estimate |
| Remaining time | `sensor` | Minutes to the setpoint |
| Error count | `sensor` | Bus errors (may be unavailable, see Troubleshooting) |
| Total energy (cloud) | `sensor` | Cloud figure, reference only |
| Energy today (cloud) | `sensor` | Cloud figure, reference only |
| Weekly program | `sensor` | Showers/week; `schedule` & `plans` attributes |
| Plant mode (raw) | `sensor` | Diagnostic: raw mode + flags |

## Services

The weekly schedule only takes effect while the water heater is in **PROGRAM** mode.
Overwrite it with `ariston_ha.set_time_program`:

```yaml
action: ariston_ha.set_time_program
data:
  plans:
    - days: [1, 2, 3, 4, 5]        # 0 = Sunday … 6 = Saturday (or English day names)
      shws: [{ time: "06:00", temp: 60 }]
    - days: [6, 0]
      shws: [{ time: "08:00", temp: 65 }]
```

Each day may appear in only one plan (the service rejects duplicates). Use
`ariston_ha.refresh_time_program` to re-read the schedule and settings from the cloud.

## Troubleshooting

- **Cloud only** — needs internet and the Ariston cloud to be up; there is no local control.
- **Writes are confirmed by read-back** — after each command the integration waits a few
  seconds and re-reads the heater, so the state reflects the cloud, not an optimistic guess.
- **Energy sensors are reference only** — the cloud updates them coarsely; for the Energy
  dashboard, measure consumption at the socket instead.
- **Error count can be unavailable** — the cloud `busErrors` endpoint has been returning
  HTTP 500; the sensor is then `unavailable` rather than guessing.
- **Boost is intentionally not offered** — the app hides it for this model.
- When reporting an issue, attach the integration's **diagnostics** (*Devices & Services →
  Ariston NET → ⋮ → Download diagnostics*).

## How it works

The heater's Wi-Fi module talks to AWS IoT over **mutual TLS** (it validates the server's CA
chain and presents its own client certificate), opens **no local API**, and keeps its private
key in encrypted flash. Capturing the Wi-Fi traffic or spoofing the cloud is therefore not
viable; the only fully-local path is a hardware UART tap inside the unit. This integration
uses the same cloud API as the official app; the register/body details were derived from the
Ariston NET app and verified against the real heater.

## Development

Tests mock the cloud with `aioclient_mock`; fixtures use payload shapes captured from a real
Slim3. Run them with:

```bash
pip install -r requirements_test.txt
pytest -q
```

<!-- support:start -->
## Support the project

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

<p align="center"><sub>🇻🇳 VietQR: scan with any Vietnamese banking app, transfer note <code>Ung ho ariston_ha</code>. Thank you for keeping this project alive!</sub></p>
<p align="center"><sub>Crypto (BEP20 network): <code>0x57f07d44fb581cddc028a0c67d63a8cc05aa6caa</code> · USDT · USDC · BNB · ETH · BTC</sub></p>
<!-- support:end -->

## License

MIT © Ngô Đức Việt. Not affiliated with or endorsed by Ariston.
