"""
霓虹電競少女圓形 HUD 渲染引擎 (HUDRenderer - Pre-baked Graffiti Sprite Edition)
負責：
1. 載入預製超大號街頭塗鴉字元圖集 (assets/sprites/{cpu,gpu,mem}/)，執行期直接秒貼，1:1 還原原圖尺寸與張力。
2. 保持 1~3 位數自然字體長寬比例，三位數 ('100%') 自動等比例縮放至 0.78x 避免超出面板。
3. 在局部水平畫布完成各面板排版後，以正角度（逆時針）貼合原圖左低右高傾斜面板。
"""

import math
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
import config
from monitor.state import SystemState


def _safe_int_str(val, min_val: int | None = None, max_val: int | None = None) -> str:
    if val is None:
        return "--"
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return "--"
        n = int(round(f))
        if min_val is not None:
            n = max(min_val, n)
        if max_val is not None:
            n = min(max_val, n)
        return str(n)
    except (TypeError, ValueError):
        return "--"


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


class HUDRenderer:
    def __init__(self):
        self._font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
        self._bg_cache: dict[str, Image.Image] = {}
        self._sprite_cache: dict[tuple[str, str], Image.Image] = {}
        self._text_cache: dict[tuple, Image.Image] = {}

    def get_font(self, size: int, italic: bool = True) -> ImageFont.FreeTypeFont:
        path = str(config.FONT_DISPLAY_ITALIC if italic else config.FONT_DISPLAY_BOLD)
        key = (path, size)
        if key not in self._font_cache:
            try:
                self._font_cache[key] = ImageFont.truetype(path, size)
            except Exception:
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _get_background(self, state: SystemState) -> Image.Image:
        state_key = state.value if isinstance(state, SystemState) else str(state)
        if state_key not in self._bg_cache:
            bg_path = config.BG_PATHS.get(state_key, config.BG_PATHS["gaming"])
            self._bg_cache[state_key] = (
                Image.open(bg_path)
                .convert("RGBA")
                .resize((config.ART_SIZE, config.ART_SIZE), Image.LANCZOS)
            )
        return self._bg_cache[state_key].copy()

    def _get_sprite(self, panel_key: str, glyph_name: str) -> Image.Image:
        key = (panel_key, glyph_name)
        if key not in self._sprite_cache:
            sp_path = config.SPRITES_DIR / panel_key / f"{glyph_name}.png"
            if sp_path.exists():
                with Image.open(sp_path) as im:
                    self._sprite_cache[key] = im.convert("RGBA")
            else:
                cfg = config.PANEL_CONFIGS[panel_key]
                ch = "%" if glyph_name == "main_pct" else ("-" if glyph_name == "main_dash" else glyph_name[-1])
                fs = cfg["pct_font_size"] if glyph_name == "main_pct" else cfg["main_font_size"]
                self._sprite_cache[key] = self.render_neon_text(
                    ch,
                    self.get_font(fs, italic=True),
                    cfg["main_color"],
                    cfg["shadow_color"],
                    shadow_offset=cfg["shadow_offset"],
                    glow_radius=cfg["glow_radius"],
                    shear=cfg["shear"],
                    stroke_width=cfg.get("stroke_width", 6),
                )
        return self._sprite_cache[key]

    def render_neon_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        main_color: tuple[int, int, int],
        shadow_color: tuple[int, int, int],
        shadow_offset: tuple[int, int] = (-9, 8),
        glow_radius: int = 13,
        shear: float = 0.10,
        stroke_width: int = 4,
    ) -> Image.Image:
        """
        渲染具備原圖街頭電競風格的多層霓虹文字（含快取與濃黑描邊），保留自然字寬比例。
        """
        cache_key = (
            text,
            getattr(font, "path", ""),
            getattr(font, "size", 0),
            main_color,
            shadow_color,
            shadow_offset,
            glow_radius,
            shear,
            stroke_width,
        )
        if cache_key in self._text_cache:
            return self._text_cache[cache_key]

        dummy = Image.new("L", (1, 1), 0)
        d_draw = ImageDraw.Draw(dummy)
        bbox = d_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        text_w = max(1, bbox[2] - bbox[0])
        text_h = max(1, bbox[3] - bbox[1])

        pad = max(abs(shadow_offset[0]), abs(shadow_offset[1])) + glow_radius * 2 + stroke_width * 2 + 24
        shear_extra = int(text_h * abs(shear)) + 12
        canvas_w = text_w + pad * 2 + shear_extra
        canvas_h = text_h + pad * 2

        draw_x = pad - bbox[0] + int(text_h * max(0.0, shear))
        draw_y = pad - bbox[1]

        fill_mask = Image.new("L", (canvas_w, canvas_h), 0)
        f_draw = ImageDraw.Draw(fill_mask)
        f_draw.text((draw_x, draw_y), text, font=font, fill=255)

        stroke_mask = Image.new("L", (canvas_w, canvas_h), 0)
        s_draw = ImageDraw.Draw(stroke_mask)
        s_draw.text((draw_x, draw_y), text, font=font, fill=255, stroke_width=stroke_width, stroke_fill=255)

        if abs(shear) > 1e-4:
            cy = canvas_h / 2.0
            affine_params = (1.0, shear, -shear * cy, 0.0, 1.0, 0.0)
            fill_mask = fill_mask.transform((canvas_w, canvas_h), Image.AFFINE, affine_params, resample=Image.BICUBIC)
            stroke_mask = stroke_mask.transform((canvas_w, canvas_h), Image.AFFINE, affine_params, resample=Image.BICUBIC)

        out = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        if glow_radius > 0:
            glow_src = ImageChops.lighter(stroke_mask, fill_mask)
            glow_mask = glow_src.filter(ImageFilter.GaussianBlur(radius=glow_radius))
            glow_mask = glow_mask.point(lambda p: min(255, int(p * 0.90)))
            glow_layer = Image.new("RGBA", (canvas_w, canvas_h), (*shadow_color, 255))
            glow_layer.putalpha(glow_mask)
            out = Image.alpha_composite(out, glow_layer)

        sx, sy = shadow_offset
        if sx != 0 or sy != 0:
            shadow_mask = Image.new("L", (canvas_w, canvas_h), 0)
            shadow_mask.paste(stroke_mask, (sx, sy))
            shadow_layer = Image.new("RGBA", (canvas_w, canvas_h), (*shadow_color, 255))
            shadow_layer.putalpha(shadow_mask)
            out = Image.alpha_composite(out, shadow_layer)

        if stroke_width > 0:
            dark_layer = Image.new("RGBA", (canvas_w, canvas_h), (*config.COLOR_DARK_STROKE, 255))
            dark_layer.putalpha(stroke_mask)
            out = Image.alpha_composite(out, dark_layer)

        main_layer = Image.new("RGBA", (canvas_w, canvas_h), (*main_color, 255))
        main_layer.putalpha(fill_mask)
        out = Image.alpha_composite(out, main_layer)

        content_box = out.getbbox()
        if content_box:
            out = out.crop(content_box)
        if len(self._text_cache) >= 512:
            self._text_cache.clear()
        self._text_cache[cache_key] = out
        return out

    def _compose_percentage_group(self, num_str: str, panel_key: str, cfg: dict) -> Image.Image:
        """
        使用預製超大號街頭塗鴉字元圖集 (Sprite Sheet) 瞬間拼貼主數字與 '%' 符號。
        保留自然字體長寬比例，且將外發光邊界緊密咬合，呈現原圖 1:1 霸氣塗鴉感。
        """
        sprites: list[Image.Image] = []
        for ch in num_str:
            if ch.isdigit():
                sprites.append(self._get_sprite(panel_key, f"main_{ch}"))
            else:
                sprites.append(self._get_sprite(panel_key, "main_dash"))

        pct_sp = self._get_sprite(panel_key, "main_pct")

        # 每個獨立字元 Sprite 四周含有外光暈留白，拼貼時適度重疊讓字元緊密相連如原圖塗鴉
        digit_overlap = int(cfg["glow_radius"] * 3.1 + abs(cfg["shadow_offset"][0]) * 1.1)
        pct_overlap = int(cfg["glow_radius"] * 3.2 + abs(cfg["shadow_offset"][0]) * 1.1)

        cur_x = 0
        positions: list[tuple[Image.Image, int]] = []
        max_digit_h = 1
        for i, sp in enumerate(sprites):
            positions.append((sp, cur_x))
            cur_x += sp.width - (digit_overlap if i < len(sprites) - 1 else pct_overlap)
            if sp.height > max_digit_h:
                max_digit_h = sp.height

        pct_x = max(0, cur_x)
        total_w = max(1, pct_x + pct_sp.width)
        total_h = max(max_digit_h, pct_sp.height)

        group = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        for sp, x in positions:
            y = (total_h - sp.height) // 2
            group.alpha_composite(sp, (max(0, x), max(0, y)))

        # '%' 靠主數字基線偏中下方緊貼對齊
        pct_y = total_h - pct_sp.height - int(cfg["glow_radius"] * 0.25)
        group.alpha_composite(pct_sp, (pct_x, max(0, pct_y)))

        # 三位數 ('100%') 自動等比例縮放至 0.78x 避免超出面板右緣
        if len(num_str) >= 3:
            scale = 0.78
            new_size = (max(1, int(group.width * scale)), max(1, int(group.height * scale)))
            group = group.resize(new_size, Image.LANCZOS)

        return group

    def _draw_cpu_or_gpu_panel(self, panel_key: str, info: dict) -> Image.Image:
        cfg = config.PANEL_CONFIGS[panel_key]
        cw, ch = cfg["canvas_size"]
        panel = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))

        num_str = _safe_int_str(info.get("usage"), 0, 100)
        pct_group = self._compose_percentage_group(num_str, panel_key, cfg)

        ax, ay = cfg["digits_anchor"]
        gx = int(ax - pct_group.width / 2)
        gy = int(ay - pct_group.height / 2)
        panel.alpha_composite(pct_group, (gx, gy))

        # 溫度文字 (繪製於小溫度計圖示右側)
        temp_num = _safe_int_str(info.get("temp"), -50, 200)
        temp_str = f"{temp_num}°C"
        sec_font = self.get_font(cfg["sec_font_size"], italic=True)
        temp_img = self.render_neon_text(
            temp_str,
            sec_font,
            cfg["sec_color"],
            cfg["shadow_color"],
            shadow_offset=(-4, 4),
            glow_radius=6,
            shear=0.06,
            stroke_width=3,
        )
        sx, sy = cfg["sec_pos"]
        tx = int(sx - temp_img.width / 2)
        ty = int(sy - temp_img.height / 2)
        panel.alpha_composite(temp_img, (tx, ty))
        return panel

    def _draw_mem_panel(self, mem_info: dict) -> Image.Image:
        cfg = config.PANEL_CONFIGS["mem"]
        cw, ch = cfg["canvas_size"]
        panel = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))

        percent_f = _safe_float(mem_info.get("percent"))
        num_str = _safe_int_str(percent_f, 0, 100)
        pct_group = self._compose_percentage_group(num_str, "mem", cfg)

        ax, ay = cfg["digits_anchor"]
        gx = int(ax - pct_group.width / 2)
        gy = int(ay - pct_group.height / 2)
        panel.alpha_composite(pct_group, (gx, gy))

        # 副標：10.2 / 62 GB
        used_gb = _safe_float(mem_info.get("used_gb"))
        total_gb = _safe_float(mem_info.get("total_gb"))
        if used_gb is not None and total_gb is not None:
            sub_str = f"{used_gb:.1f} / {int(round(total_gb))} GB"
        else:
            sub_str = "-- / -- GB"

        sub_font = self.get_font(cfg["sub_font_size"], italic=False)
        sub_img = self.render_neon_text(
            sub_str,
            sub_font,
            cfg["sub_color"],
            cfg["shadow_color"],
            shadow_offset=(-3, 3),
            glow_radius=5,
            shear=0.04,
            stroke_width=3,
        )
        sx, sy = cfg["sub_pos"]
        panel.alpha_composite(
            sub_img, (int(sx - sub_img.width / 2), int(sy - sub_img.height / 2))
        )

        # 底部 10 格斜切分段進度條
        x0, y0, x1, y1 = cfg["bar_box"]
        cells = cfg["bar_cells"]
        gap = cfg["bar_gap"]
        slant = cfg["bar_slant"]
        total_bar_w = x1 - x0
        cell_w = (total_bar_w - gap * (cells - 1)) / float(cells)
        filled_count = 0 if percent_f is None else max(0, min(cells, int(round(percent_f / 10.0))))

        bar_glow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bar_glow)
        fg_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        fg_draw = ImageDraw.Draw(fg_layer)

        outer_poly = [
            (x0 - 4 + slant, y0 - 4),
            (x1 + 4 + slant, y0 - 4),
            (x1 + 4, y1 + 4),
            (x0 - 4, y1 + 4),
        ]
        fg_draw.polygon(outer_poly, fill=(18, 16, 6, 210), outline=(*config.COLOR_GOLD, 210), width=2)

        for i in range(cells):
            cx0 = x0 + i * (cell_w + gap)
            cx1 = cx0 + cell_w
            poly = [
                (cx0 + slant, y0),
                (cx1 + slant, y0),
                (cx1, y1),
                (cx0, y1),
            ]
            if i < filled_count:
                bg_draw.polygon(poly, fill=(*config.COLOR_GOLD, 180))
                fg_draw.polygon(poly, fill=(*config.COLOR_GOLD, 255), outline=(255, 250, 190, 255), width=1)
            else:
                fg_draw.polygon(poly, fill=(38, 34, 12, 180), outline=(110, 96, 20, 160), width=1)

        bar_glow = bar_glow.filter(ImageFilter.GaussianBlur(radius=6))
        panel = Image.alpha_composite(panel, bar_glow)
        panel = Image.alpha_composite(panel, fg_layer)
        return panel

    def _paste_tilted_panel(self, canvas: Image.Image, panel: Image.Image, cfg: dict) -> None:
        rotated = panel.rotate(cfg["angle"], resample=Image.BICUBIC, expand=True)
        cx, cy = cfg["center_pos"]
        px = int(cx - rotated.width / 2)
        py = int(cy - rotated.height / 2)
        canvas.alpha_composite(rotated, (px, py))

    def render_overlay(
        self,
        cpu_info: dict,
        mem_info: dict,
        gpu_info: dict,
        size: tuple[int, int] = config.LCD_SIZE,
    ) -> Image.Image:
        """合成單張透明 RGBA 左側 HUD 數據覆蓋層。"""
        overlay = Image.new("RGBA", (config.ART_SIZE, config.ART_SIZE), (0, 0, 0, 0))

        cpu_panel = self._draw_cpu_or_gpu_panel("cpu", cpu_info or {})
        gpu_panel = self._draw_cpu_or_gpu_panel("gpu", gpu_info or {})
        mem_panel = self._draw_mem_panel(mem_info or {})

        self._paste_tilted_panel(overlay, cpu_panel, config.PANEL_CONFIGS["cpu"])
        self._paste_tilted_panel(overlay, gpu_panel, config.PANEL_CONFIGS["gpu"])
        self._paste_tilted_panel(overlay, mem_panel, config.PANEL_CONFIGS["mem"])

        if overlay.size != size:
            overlay = overlay.resize(size, Image.LANCZOS)
        return overlay

    def render_frame(
        self,
        cpu_info: dict,
        mem_info: dict,
        gpu_info: dict,
        state: SystemState = SystemState.GAMING,
        size: tuple[int, int] = config.LCD_SIZE,
    ) -> Image.Image:
        canvas = self._get_background(state)
        overlay_full = self.render_overlay(
            cpu_info, mem_info, gpu_info, size=(config.ART_SIZE, config.ART_SIZE)
        )
        canvas = Image.alpha_composite(canvas, overlay_full)
        out = canvas.convert("RGB")
        if out.size != size:
            out = out.resize(size, Image.LANCZOS)
        return out
