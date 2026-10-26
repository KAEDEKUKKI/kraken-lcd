import unittest
from PIL import Image, ImageChops, ImageStat
import config
from monitor.state import SystemState
from monitor.renderer import HUDRenderer


class TestHUDRenderer(unittest.TestCase):
    def setUp(self):
        self.renderer = HUDRenderer()

    def test_single_and_double_digit_preserve_natural_aspect_ratio(self):
        # 驗證個位數 "3" 的渲染寬度明顯小於雙位數 "42" 的渲染寬度（不會被硬拉成一樣寬）
        font = self.renderer.get_font(120, italic=True)
        img_single = self.renderer.render_neon_text("3", font, (255, 255, 255), (255, 47, 158), (-8, 8))
        img_double = self.renderer.render_neon_text("42", font, (255, 255, 255), (255, 47, 158), (-8, 8))
        self.assertLess(img_single.width, img_double.width * 0.72)

    def test_render_frame_outputs_320x320_and_handles_missing_sensors(self):
        cpu = {"usage": None, "temp": None}
        mem = {"used_gb": 5.7, "total_gb": 62.0, "percent": 9.2}
        gpu = {"usage": None, "temp": None}
        out = self.renderer.render_frame(cpu, mem, gpu, state=SystemState.IDLE)
        self.assertEqual(out.size, (320, 320))
        self.assertEqual(out.mode, "RGB")

    def test_render_frame_handles_nan_and_out_of_range_values(self):
        cpu = {"usage": float("nan"), "temp": "N/A"}
        mem = {"used_gb": "invalid", "total_gb": 62.0, "percent": 115.0}
        gpu = {"usage": -12.0, "temp": float("inf")}
        out = self.renderer.render_frame(cpu, mem, gpu, state=SystemState.IDLE)
        self.assertEqual(out.size, (320, 320))
        self.assertEqual(out.mode, "RGB")

    def test_render_frame_100_percent_and_normal_values_modify_panel_regions(self):
        cpu = {"usage": 100.0, "temp": 85.0}
        mem = {"used_gb": 58.4, "total_gb": 62.0, "percent": 94.0}
        gpu = {"usage": 99.0, "temp": 82.0}
        full_img = self.renderer.render_frame(
            cpu, mem, gpu, state=SystemState.OVERHEAT, size=(config.ART_SIZE, config.ART_SIZE)
        )
        with Image.open(config.BG_PATHS["overheat"]) as bg:
            diff = ImageChops.difference(full_img, bg)
            # 確認三個面板區域都有被繪製上明亮的新數值
            self.assertGreater(sum(ImageStat.Stat(diff.crop((220, 400, 520, 580))).mean) / 3.0, 15.0)
            self.assertGreater(sum(ImageStat.Stat(diff.crop((440, 660, 740, 860))).mean) / 3.0, 15.0)
            self.assertGreater(sum(ImageStat.Stat(diff.crop((440, 930, 740, 1130))).mean) / 3.0, 15.0)


if __name__ == "__main__":
    unittest.main()
