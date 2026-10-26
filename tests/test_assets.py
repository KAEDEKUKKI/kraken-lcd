import unittest
from PIL import Image, ImageChops, ImageStat
import config


class TestBackgroundAssets(unittest.TestCase):
    def test_all_three_backgrounds_exist_and_match_size(self):
        for state_name, path in config.BG_PATHS.items():
            self.assertTrue(path.exists(), f"Missing background for {state_name}: {path}")
            with Image.open(path) as img:
                self.assertEqual(img.size, (config.ART_SIZE, config.ART_SIZE))
                self.assertEqual(img.mode, "RGB")

    def test_panel_digit_slots_are_cleaned(self):
        # 根據原圖實測大數字核心座標（避開左上標題與右上斜切油漆筆觸）：
        # CPU '42%': (240, 440, 460, 520)
        # GPU '78%': (460, 680, 680, 790)
        # MEM '56%': (480, 950, 680, 1050)
        # 清理後的底圖在這些核心數字區域應為純黑背景 (平均亮度 < 15)
        slots = [
            ("cpu_digits", (240, 440, 460, 520)),
            ("gpu_digits", (460, 680, 680, 790)),
            ("mem_digits", (480, 990, 680, 1080)),
        ]
        for state_name, path in config.BG_PATHS.items():
            with Image.open(path) as img:
                for label, box in slots:
                    stat = ImageStat.Stat(img.crop(box))
                    mean_luma = sum(stat.mean) / 3.0
                    self.assertLess(
                        mean_luma, 15.0,
                        f"{state_name} slot {label} still has bright residue (mean={mean_luma:.1f})"
                    )

    def test_character_expressions_differ_across_states(self):
        # 右側人物臉部/嘴部區域 (600, 180, 900, 420) 在 idle / gaming / overheat 之間必須有明顯差異
        face_box = (600, 180, 900, 420)
        with Image.open(config.BG_PATHS["idle"]) as img_idle, \
             Image.open(config.BG_PATHS["gaming"]) as img_gaming, \
             Image.open(config.BG_PATHS["overheat"]) as img_overheat:
            diff_ig = ImageStat.Stat(ImageChops.difference(img_idle.crop(face_box), img_gaming.crop(face_box))).mean
            diff_go = ImageStat.Stat(ImageChops.difference(img_gaming.crop(face_box), img_overheat.crop(face_box))).mean
            self.assertGreater(sum(diff_ig) / 3.0, 2.0, "idle and gaming faces should differ")
            self.assertGreater(sum(diff_go) / 3.0, 5.0, "gaming and overheat faces should differ")

    def test_sprite_sheets_exist_and_have_oversized_dimensions(self):
        for panel in ("cpu", "gpu", "mem"):
            panel_dir = config.SPRITES_DIR / panel
            self.assertTrue(panel_dir.exists(), f"Missing sprite dir: {panel_dir}")
            digit_4 = panel_dir / "main_4.png"
            pct = panel_dir / "main_pct.png"
            self.assertTrue(digit_4.exists())
            self.assertTrue(pct.exists())
            with Image.open(digit_4) as im:
                self.assertEqual(im.mode, "RGBA")
                # 超大號主數字含描邊與光暈高度應超過 175px
                self.assertGreater(im.height, 175)


if __name__ == "__main__":
    unittest.main()
