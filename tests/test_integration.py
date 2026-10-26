import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import config
from monitor.collector import collect_system_metrics
from monitor.device import rotate_image, send_image_to_kraken
from monitor.state import SystemState
from kraken_monitor import should_update_frame


class TestIntegration(unittest.TestCase):
    def test_collect_system_metrics_structure(self):
        data = collect_system_metrics(include_gpu=False)
        self.assertIn("cpu", data)
        self.assertIn("mem", data)
        self.assertIn("gpu", data)
        self.assertIsInstance(data["cpu"]["usage"], (int, float))
        self.assertIsInstance(data["mem"]["percent"], (int, float))

    def test_rotate_image_orientations(self):
        img = Image.new("RGB", (320, 320), (0, 0, 0))
        img.putpixel((10, 20), (255, 0, 0))
        for deg in (0, 90, 180, 270):
            r = rotate_image(img, deg)
            self.assertEqual(r.size, (320, 320))

    def test_should_update_frame_smart_skip(self):
        m1 = {
            "cpu": {"usage": 40.0, "temp": 60.0},
            "gpu": {"usage": 50.0, "temp": 65.0},
            "mem": {"percent": 50.0},
        }
        m2_small = {
            "cpu": {"usage": 40.4, "temp": 60.2},
            "gpu": {"usage": 50.3, "temp": 64.8},
            "mem": {"percent": 50.2},
        }
        m3_big = {
            "cpu": {"usage": 42.0, "temp": 60.0},
            "gpu": {"usage": 50.0, "temp": 65.0},
            "mem": {"percent": 50.0},
        }
        self.assertTrue(should_update_frame(None, m1, None, SystemState.GAMING))
        self.assertFalse(should_update_frame(m1, m2_small, SystemState.GAMING, SystemState.GAMING))
        self.assertTrue(should_update_frame(m1, m2_small, SystemState.GAMING, SystemState.OVERHEAT))
        self.assertTrue(should_update_frame(m1, m3_big, SystemState.GAMING, SystemState.GAMING))

        m_nan = {
            "cpu": {"usage": float("nan"), "temp": 60.0},
            "gpu": {"usage": 50.0, "temp": 65.0},
            "mem": {"percent": 50.0},
        }
        self.assertTrue(should_update_frame(m_nan, m1, SystemState.GAMING, SystemState.GAMING))
        self.assertFalse(should_update_frame(m_nan, m_nan, SystemState.GAMING, SystemState.GAMING))

    def test_send_image_to_kraken_ping_pong_and_fallback(self):
        class FallbackDevice:
            def __init__(self):
                self.calls = []

            def set_screen(self, channel, mode, path):
                self.calls.append((channel, mode, Path(path).exists()))

        dev = FallbackDevice()
        img = Image.new("RGB", (320, 320), (10, 20, 30))
        self.assertTrue(send_image_to_kraken(img, dev))
        self.assertEqual(dev.calls, [("lcd", "static", True)])

        class PingPongKrakenZ3Mock:
            def __init__(self):
                self.bulk_device = True
                self.bulk_buffer_size = 64 * 1024
                self.orientation = 0
                self.switched_buckets = []
                self.setup_offsets = []

            def set_screen(self, channel, mode, path):
                pass

            def _write(self, data):
                pass

            def _read_until(self, matchers):
                for fn in matchers.values():
                    fn([0] * 32)

            def _write_then_read(self, data):
                return [0] * 32

            def _prepare_static_file(self, path, rotation):
                return [0] * (320 * 320 * 4)

            def _delete_bucket(self, idx):
                return True

            def _setup_bucket(self, start_b, end_b, mem_addr, mem_size):
                self.setup_offsets.append((start_b, int.from_bytes(mem_addr, "little")))
                return True

            def _bulk_write(self, chunk):
                pass

            def _switch_bucket(self, idx):
                self.switched_buckets.append(idx)
                return True

        z3 = PingPongKrakenZ3Mock()
        self.assertTrue(send_image_to_kraken(img, z3))
        self.assertTrue(send_image_to_kraken(img, z3))
        # 驗證雙槽位輪替 (1 -> 0) 且固定偏移 (512KB -> 0KB)
        self.assertEqual(z3.switched_buckets, [1, 0])
        self.assertEqual(z3.setup_offsets, [(1, 512), (0, 0)])

    def test_cli_dry_run_with_force_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "out.png"
            cmd = [
                sys.executable,
                str(config.BASE_DIR / "kraken_monitor.py"),
                "--dry-run",
                "--no-gpu",
                "--force-state",
                "overheat",
                "--orientation",
                "90",
                "--output",
                str(out_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            self.assertTrue(out_path.exists())
            with Image.open(out_path) as im:
                self.assertEqual(im.size, (320, 320))


if __name__ == "__main__":
    unittest.main()
