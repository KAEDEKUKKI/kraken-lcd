#!/usr/bin/env python3
"""
Kraken Z53 LCD System Monitor (Neon Gaming Girl HUD - Pre-baked Graffiti Sprite Edition)
將 CPU/GPU 使用率、溫度與記憶體使用狀態渲染於 Kraken Z53 圓形螢幕上，
支援：
- 預製超大號街頭塗鴉字元圖集 (Sprite Sheet) 瞬間拼貼，1:1 還原原圖尺寸
- 三階段原畫表情自動切換 (idle / gaming / overheat，含遲滯緩衝)
- 雙緩衝區 Ping-Pong 零閃白靜態更新 + 智慧略過 (Smart Skip)

Usage:
    python kraken_monitor.py                        # 單次執行
    python kraken_monitor.py --loop                 # 持續監控更新 (預設每 3 秒)
    python kraken_monitor.py --dry-run              # 僅輸出預覽圖檔，不連線水冷頭
    python kraken_monitor.py --force-state overheat # 強制指定特定人物表情狀態
"""

import argparse
import math
import sys
import time
from PIL import Image

import config
from monitor.collector import get_cpu_info, get_memory_info, get_gpu_info
from monitor.device import (
    LIQUIDCTL_AVAILABLE,
    find_kraken_device,
    reconnect_device,
    rotate_image,
    send_image_to_kraken,
)
from monitor.renderer import HUDRenderer
from monitor.state import StateMachine, SystemState

_renderer_instance: HUDRenderer | None = None


def _get_renderer() -> HUDRenderer:
    global _renderer_instance
    if _renderer_instance is None:
        _renderer_instance = HUDRenderer()
    return _renderer_instance


def create_info_image(
    cpu_info: dict,
    mem_info: dict,
    gpu_info: dict,
    state: SystemState = SystemState.GAMING,
    size: tuple[int, int] = config.LCD_SIZE,
) -> Image.Image:
    """單幀渲染函式介面。"""
    return _get_renderer().render_frame(
        cpu_info, mem_info, gpu_info, state=state, size=size
    )


def _metric_diff_exceeds(v1, v2, threshold: float) -> bool:
    if v1 is None and v2 is None:
        return False
    if v1 is None or v2 is None:
        return True
    try:
        f1 = float(v1)
        f2 = float(v2)
        if math.isnan(f1) and math.isnan(f2):
            return False
        if math.isnan(f1) or math.isnan(f2):
            return True
        return abs(f1 - f2) >= threshold
    except (TypeError, ValueError):
        return True


def should_update_frame(
    last_metrics: dict | None,
    curr_metrics: dict,
    last_state: SystemState | None,
    curr_state: SystemState,
    threshold: float = config.FRAME_UPDATE_THRESHOLD,
) -> bool:
    """
    當狀態改變或任一項指標變化 >= threshold 時才傳送新畫面至水冷頭，避免無意義重複寫入。
    """
    if last_metrics is None or last_state is None:
        return True
    if last_state != curr_state:
        return True

    l_cpu = last_metrics.get("cpu") or {}
    c_cpu = curr_metrics.get("cpu") or {}
    if _metric_diff_exceeds(l_cpu.get("usage"), c_cpu.get("usage"), threshold):
        return True
    if _metric_diff_exceeds(l_cpu.get("temp"), c_cpu.get("temp"), threshold):
        return True

    l_gpu = last_metrics.get("gpu") or {}
    c_gpu = curr_metrics.get("gpu") or {}
    if _metric_diff_exceeds(l_gpu.get("usage"), c_gpu.get("usage"), threshold):
        return True
    if _metric_diff_exceeds(l_gpu.get("temp"), c_gpu.get("temp"), threshold):
        return True

    l_mem = last_metrics.get("mem") or {}
    c_mem = curr_metrics.get("mem") or {}
    if _metric_diff_exceeds(l_mem.get("percent"), c_mem.get("percent"), threshold):
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Kraken Z53 LCD System Monitor")
    parser.add_argument("--loop", action="store_true", help="Run in a loop")
    parser.add_argument("--interval", type=int, default=3, help="Update interval in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Save image to file without device")
    parser.add_argument("--output", type=str, default="/tmp/kraken_lcd.png", help="Output path for dry-run")
    parser.add_argument("--no-gpu", action="store_true", help="Skip GPU detection")
    parser.add_argument(
        "--orientation",
        type=int,
        choices=[0, 90, 180, 270],
        default=0,
        help="Rotate image: 0 (default), 90 (90° counter-clockwise), 180, 270 (90° clockwise)",
    )
    parser.add_argument(
        "--force-state",
        type=str,
        choices=["idle", "gaming", "overheat"],
        default=None,
        help="Force character expression state instead of automatic hysteresis switching",
    )
    args = parser.parse_args()

    print("=" * 55)
    print("Kraken Z53 LCD System Monitor (Neon HUD Edition)")
    print("=" * 55)

    if args.dry_run:
        print("Mode: DRY RUN")
    else:
        print("Mode: DEVICE (Static Ping-Pong Zero-Flash)")
        if not LIQUIDCTL_AVAILABLE:
            print("ERROR: liquidctl not installed")
            sys.exit(1)

    print(f"Interval: {args.interval}s")
    print(f"Orientation: {args.orientation}")
    if args.force_state:
        print(f"Forced State: {args.force_state}")
    print("-" * 55)

    device = None
    if not args.dry_run:
        device = find_kraken_device()
        if device is None:
            print("ERROR: No Kraken device found")
            sys.exit(1)

    if device:
        print("Connecting to device...")
        device.connect()
        device.initialize()
        print("Setting brightness to 100...")
        device.set_screen("lcd", "brightness", 100)
        print("Device ready.")
        print("-" * 55)

    state_machine = StateMachine()
    last_state: SystemState | None = None
    last_metrics: dict | None = None

    try:
        while True:
            try:
                print("Gathering info...", end=" ", flush=True)
                cpu_info = get_cpu_info()
                mem_info = get_memory_info()
                gpu_info = {"usage": None, "temp": None, "vram_percent": None} if args.no_gpu else get_gpu_info()
                curr_metrics = {"cpu": cpu_info, "mem": mem_info, "gpu": gpu_info}

                if args.force_state:
                    current_state = SystemState(args.force_state)
                else:
                    current_state = state_machine.update(cpu_info, gpu_info)
                    if last_state is not None and current_state != last_state:
                        print(f"[State transition: {last_state.value} -> {current_state.value}]", end=" ")

                print(f"Done (state={current_state.value})")

                if not args.dry_run and not should_update_frame(
                    last_metrics, curr_metrics, last_state, current_state
                ):
                    print("Metrics unchanged, skipping LCD update")
                else:
                    img = create_info_image(cpu_info, mem_info, gpu_info, state=current_state)
                    img = rotate_image(img, args.orientation)

                    if args.dry_run:
                        img.save(args.output, "PNG")
                        print(f"Saved: {args.output}")
                    else:
                        success = send_image_to_kraken(img, device)
                        if success:
                            print("LCD updated")
                            last_metrics = curr_metrics
                            last_state = current_state
                        else:
                            print("Send failed, reconnecting...")
                            device = reconnect_device(device)
                            if device is None:
                                sys.exit(1)

            except Exception as e:
                print(f"\nError in monitor iteration: {e}")
                if not args.loop:
                    raise

            if not args.loop:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if device:
            print("Disconnecting...")
            device.disconnect()

    print("-" * 55)
    print("Monitor stopped.")


if __name__ == "__main__":
    main()
