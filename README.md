<div align="center">

# 🎮 Kraken Z53 LCD Monitor — Neon Gaming Girl HUD

**[English](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)**

A custom system monitor for the **NZXT Kraken Z53** (`320x320` circular LCD) on Linux, featuring an arcade/street-graffiti **Neon Gaming Girl HUD**, pre-baked oversized graffiti number sprites, 3-stage dynamic character expressions (`IDLE` / `GAMING` / `OVERHEAT`), and **Ping-Pong Zero-Flash** hardware framebuffer updates via `liquidctl`.

![Neon Gaming Girl HUD - 3 States Preview](assets/preview_states.png)

</div>

---

## ✨ Features

- **🎨 3-Stage Dynamic Character Expressions (with Hysteresis)**
  Automatically switches the character's expression based on real-time CPU/GPU load and temperature, with built-in hysteresis buffers to prevent rapid flickering at threshold boundaries:
  - **🟢 `IDLE` (Relaxed Smile)**: Normal desktop / low load (`Usage < 50%`, `Temp < 65°C`)
  - **🟣 `GAMING` (Playful Tongue-Out)**: Active gaming / medium-high load (`Usage >= 50%` or `Temp >= 65°C`)
  - **🔴 `OVERHEAT` (Flushed & Steaming)**: Heavy thermal / full load (`Temp >= 80°C` or `Usage >= 90%`)
- **⚡ Pre-Baked Oversized Graffiti Sprite Sheets**
  Uses pre-rendered `1254x1254`-scale street-graffiti glyph sprites (`assets/sprites/{cpu,gpu,mem}/`) with heavy dark strokes, hard neon offset shadows, and dual-layer spray-paint outer glow—achieving **near-zero runtime CPU overhead**.
- **🛡️ Ping-Pong Zero-Flash USB Updates & Smart Skip**
  Works around `liquidctl`'s 16-bucket exhaustion bug (`_delete_all_buckets` white screen flash) by alternating strictly between **Bucket 0 (`0 KB`)** and **Bucket 1 (`512 KB`)** in-place, and skips USB writes when metrics fluctuate by `< 1%` / `< 1°C`.
- **🔄 Hardware Orientation Support**
  Supports `0°`, `90°`, `180°`, and `270°` rotation to match any physical pump mounting angle.

---

## 📁 Project Structure

```text
kraken-lcd/
├── kraken_monitor.py          # Main CLI entry point & monitoring loop
├── config.py                  # Centralized configuration, thresholds & panel geometry
├── build_assets.py            # Offline asset & graffiti sprite sheet builder
├── kraken-lcd.service         # Systemd service unit file
├── install-service.sh         # One-step systemd service installer
├── run.sh                     # Convenience launcher script
├── requirements.txt           # Python dependencies
├── monitor/
│   ├── collector.py           # CPU (psutil), RAM, and GPU (nvidia-smi / sysfs) collector
│   ├── state.py               # 3-state machine with hysteresis
│   ├── renderer.py            # Tilted HUD panel compositor & sprite renderer
│   └── device.py              # liquidctl USB manager & Ping-Pong double-buffer sender
├── assets/
│   ├── backgrounds/           # Clean 1254x1254 state backgrounds (idle, gaming, overheat)
│   ├── sprites/               # Pre-baked graffiti digit sprites (cpu/, gpu/, mem/)
│   └── fonts/                 # Bundled display fonts
└── tests/                     # Unit & integration test suite
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Linux with Python **3.10+**
- `libusb` / `hidapi` (required by `liquidctl` to communicate with the NZXT Kraken Z53)
- NVIDIA proprietary drivers (`nvidia-smi`) or AMD/Intel `hwmon`/`drm` sysfs for GPU metrics

### 2. Installation
```bash
git clone https://github.com/KAEDEKUKKI/kraken-lcd.git
cd kraken-lcd

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Usage

```bash
# Dry-run mode (renders a 320x320 preview PNG without touching hardware)
.venv/bin/python kraken_monitor.py --dry-run --output /tmp/kraken_lcd.png

# Force a specific character expression state (idle / gaming / overheat)
.venv/bin/python kraken_monitor.py --dry-run --force-state overheat --output /tmp/overheat.png

# Run live on the Kraken Z53 LCD (continuous loop, 3s interval, rotated 90°)
sudo .venv/bin/python kraken_monitor.py --loop --interval 3 --orientation 90
```

#### CLI Options

| Option | Default | Description |
|---|---|---|
| `--loop` | off | Run continuously instead of rendering a single frame |
| `--interval <sec>` | `3` | Update interval in seconds (loop mode) |
| `--dry-run` | off | Save the rendered frame to a PNG instead of sending it to the device |
| `--output <path>` | `/tmp/kraken_lcd.png` | Output path used in dry-run mode |
| `--no-gpu` | off | Skip GPU detection |
| `--orientation {0,90,180,270}` | `0` | Rotate the image to match the pump's mounting angle |
| `--force-state {idle,gaming,overheat}` | auto | Force a character expression instead of automatic switching |

### 4. Deploy as a Systemd Service (Auto-Start on Boot)
```bash
sudo ./install-service.sh
```
Useful service management commands:
```bash
sudo systemctl status kraken-lcd.service
sudo journalctl -u kraken-lcd.service -f
sudo systemctl restart kraken-lcd.service
```

> [!NOTE]
> `kraken-lcd.service` uses `/home/kukki/kraken-lcd` as a placeholder path. `install-service.sh` automatically rewrites it to the directory you cloned into. Edit `ExecStart` in the service file to change the interval or orientation.

---

## ⚙️ Configuration

All tunables live in [`config.py`](config.py):

- `STATE_THRESHOLDS` — enter/exit thresholds (usage % and °C) for the `GAMING` / `OVERHEAT` states, including hysteresis gaps
- `PANEL_CONFIGS` — position, tilt angle, font sizes, neon colors and glow of each CPU / GPU / MEMORY panel
- Color constants (`COLOR_PINK`, `COLOR_CYAN`, `COLOR_GOLD`, ...)

## 🖌️ Rebuilding Assets

The pre-baked backgrounds and sprites in `assets/` are already included, so **no build step is needed** to run the monitor.
`build_assets.py` regenerates them from raw source artwork in `assets/backgrounds/_raw/`, which is **not included in this repository**. Provide your own raw images there if you want to re-generate or customize the artwork:

```bash
.venv/bin/python build_assets.py
```

---

## 🧪 Running Tests
```bash
.venv/bin/python -m unittest discover -s tests -v
```
