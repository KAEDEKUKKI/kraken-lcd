"""
Kraken Z53 USB 裝置管理與畫面旋轉模組 (monitor.device)
封裝 liquidctl 通訊、雙槽位 Ping-Pong 零閃白靜態更新、錯誤重連與冷頭安裝方向旋轉邏輯。
"""

import math
import os
import tempfile
import time
from PIL import Image

try:
    from liquidctl import find_liquidctl_devices
    LIQUIDCTL_AVAILABLE = True
except ImportError:
    LIQUIDCTL_AVAILABLE = False

# 追蹤當前使用的雙緩衝槽位 (0 或 1)，避免 liquidctl 塞滿 16 槽觸發 _delete_all_buckets 閃白
_active_bucket_slot: int | None = None


def rotate_image(img: Image.Image, orientation: int) -> Image.Image:
    if orientation == 90:
        return img.transpose(Image.ROTATE_90)
    if orientation == 180:
        return img.transpose(Image.ROTATE_180)
    if orientation == 270:
        return img.transpose(Image.ROTATE_270)
    return img


def find_kraken_device():
    if not LIQUIDCTL_AVAILABLE:
        return None
    try:
        devices = find_liquidctl_devices()
        for dev in devices:
            if hasattr(dev, "description") and "kraken" in dev.description.lower():
                return dev
    except Exception as e:
        print(f"Error finding device: {e}")
    return None


def _send_static_ping_pong(img_path: str, device) -> bool:
    """
    針對 Kraken Z3 裝置執行雙槽位 (Bucket 0 / Bucket 1) Ping-Pong 原地更新：
    固定將 Bucket 0 設於位址 0KB、Bucket 1 設於位址 512KB，每次僅覆寫非顯示中的另一個槽位再切換指標，
    永遠不會塞滿 24MB 記憶體，也永遠不會呼叫 _delete_all_buckets() 切回原廠白底畫面。
    """
    global _active_bucket_slot

    required_attrs = (
        "_write",
        "_read_until",
        "_write_then_read",
        "_prepare_static_file",
        "_delete_bucket",
        "_setup_bucket",
        "_bulk_write",
        "_switch_bucket",
        "bulk_device",
        "bulk_buffer_size",
    )
    if not all(hasattr(device, attr) for attr in required_attrs):
        device.set_screen("lcd", "static", img_path)
        return True

    # 若由 2023 V2 韌體處理則直接交由原生 set_screen
    if getattr(device, "device", None) and getattr(device.device, "product_id", None) == 0x300E:
        device.set_screen("lcd", "static", img_path)
        return True

    # 讀取目前螢幕方向
    device._write([0x30, 0x01])

    def parse_lcd_info(msg):
        device.brightness = msg[0x18]
        device.orientation = msg[0x1A]

    device._read_until({b"\x31\x01": parse_lcd_info})

    data = device._prepare_static_file(img_path, getattr(device, "orientation", 0))
    bulk_info = [0x02, 0x0, 0x0, 0x0] + list(len(data).to_bytes(4, "little"))
    header = [
        0x12, 0xFA, 0x01, 0xE8, 0xAB, 0xCD, 0xEF, 0x98, 0x76, 0x54, 0x32, 0x10
    ] + bulk_info

    data_size = math.ceil((len(header) + len(data)) / 1024)
    data_size_bytes = list(data_size.to_bytes(2, "little"))

    device._write_then_read([0x36, 0x03])

    # 初次執行時：清除非活動槽位 2..15（保留當前活動槽位避免閃白）
    if _active_bucket_slot is None:
        for b_idx in range(2, 16):
            try:
                device._delete_bucket(b_idx)
            except Exception:
                pass
        # 嘗試刪除 Bucket 1；若成功代表目前活動的不是 Bucket 1，即可寫入 Bucket 1
        if device._delete_bucket(1):
            device._delete_bucket(1)
            target_bucket = 1
        else:
            device._delete_bucket(0)
            device._delete_bucket(0)
            target_bucket = 0
    else:
        target_bucket = 1 if _active_bucket_slot == 0 else 0
        if not device._delete_bucket(target_bucket):
            # 若目標槽位意外為活動中，改用另一槽位
            target_bucket = 1 - target_bucket
            device._delete_bucket(target_bucket)
        device._delete_bucket(target_bucket)

    # 固定記憶體偏移：Bucket 0 -> 0 KB, Bucket 1 -> 512 KB (401 KB 靜態圖絕不重疊)
    mem_start = list((0 if target_bucket == 0 else 512).to_bytes(2, "little"))

    if not device._setup_bucket(target_bucket, target_bucket + 1, mem_start, data_size_bytes):
        # Fallback to standard set_screen if setup fails
        device.set_screen("lcd", "static", img_path)
        _active_bucket_slot = None
        return True

    device._write_then_read([0x36, 0x01, target_bucket])
    device._bulk_write(header)

    buf_size = device.bulk_buffer_size
    for i in range(0, len(data), buf_size):
        device._bulk_write(list(data[i : i + buf_size]))

    device._write([0x36, 0x02])
    device._switch_bucket(target_bucket)
    _active_bucket_slot = target_bucket
    return True


def send_image_to_kraken(img: Image.Image, device) -> bool:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img_path = tmp.name
        img.save(img_path, "PNG")

    try:
        if hasattr(device, "set_screen"):
            return _send_static_ping_pong(img_path, device)
        return False
    except Exception as e:
        print(f"Error sending to device: {e}")
        return False
    finally:
        try:
            os.unlink(img_path)
        except Exception:
            pass


def _dispose_usb(usbdev) -> None:
    """釋放 PyUSB 裝置所有已宣告介面並關閉 libusb handle (釋放檔案描述元)。"""
    import usb.util

    usb.util.dispose_resources(usbdev)


def close_device(device) -> None:
    """
    完整關閉 Kraken 裝置。
    liquidctl 的 KrakenZ3 會在建構時另外開啟一個 PyUSB bulk handle (用於 LCD 傳圖)，
    但 disconnect() 只會關閉 HID 介面，bulk handle 不會被釋放：
    - 舊 handle 持續佔用 USB 介面 -> 新連線寫入時出現 [Errno 16] Resource busy
    - 每次重連都洩漏 libusb 檔案描述元 -> 最終 [Errno 24] Too many open files，螢幕停住
    因此這裡必須手動釋放並 dispose bulk handle。
    """
    if device is None:
        return
    try:
        device.disconnect()
    except Exception:
        pass
    bulk = getattr(device, "bulk_device", None)
    if bulk is not None:
        try:
            bulk.release()
        except Exception:
            pass
        usbdev = getattr(bulk, "usbdev", None)
        if usbdev is not None:
            try:
                _dispose_usb(usbdev)
            except Exception:
                pass
        try:
            device.bulk_device = None
        except Exception:
            pass


def reconnect_device(old_device):
    global _active_bucket_slot
    _active_bucket_slot = None
    close_device(old_device)
    time.sleep(2)
    device = find_kraken_device()
    if device is None:
        print("Device lost, exiting for service restart")
        return None
    try:
        device.connect()
        device.initialize()
        device.set_screen("lcd", "brightness", 100)
        print("Reconnected.")
        return device
    except Exception as e:
        print(f"Reconnect failed: {e}")
        close_device(device)
        return None
