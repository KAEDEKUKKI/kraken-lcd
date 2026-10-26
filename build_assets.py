#!/usr/bin/env python3
"""
Kraken Z53 HUD 資產建置腳本 (build_assets.py - Pre-baked Graffiti Sprite Edition)
負責：
1. 載入原始設計圖與 AI 產製的三階段表情素材，精準清除左側 CPU / GPU / MEMORY 面板中的固定範本數字。
2. 保留面板標題 (`CPU`, `GPU`, `MEMORY`)、硬體圖示、小溫度計圖示與霓虹邊框，輸出三階段高解析底圖 (`idle`, `gaming`, `overheat`)。
3. 離線預先烘焙 (Pre-bake) 超大號街頭塗鴉字元圖集 (`assets/sprites/{cpu,gpu,mem}/`)，含濃黑描邊、硬邊色塊陰影與多層噴漆外光暈。
"""

from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
import config

RAW_ASSETS_DIR = config.ASSETS_DIR / "backgrounds" / "_raw"


def _clean_memory_bar_outline(img: Image.Image) -> Image.Image:
    """清除 MEMORY 面板最底部殘留的空心細黃框 (x:475..785, y:1075..1192)，讓動態分段進度條繪製更乾淨。"""
    out = img.copy().convert("RGBA")
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    poly = [(485, 1128), (780, 1072), (790, 1134), (495, 1192)]
    draw.polygon(poly, fill=(0, 0, 0, 255))
    return Image.alpha_composite(out, layer).convert("RGB")


def _build_panel_clean_mask(size: tuple[int, int]) -> Image.Image:
    """建立涵蓋左側三個面板內部所有數字與光暈區域的精準遮罩（避開原圖右側人物手指與臉部）。"""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    cpu_poly = [
        (205, 465),
        (365, 420),
        (485, 375),
        (560, 410),
        (595, 515),
        (465, 625),
        (340, 650),
        (205, 625),
    ]
    gpu_poly = [
        (495, 630),
        (710, 545),
        (825, 695),
        (745, 890),
        (585, 905),
        (425, 905),
        (435, 680),
    ]
    mem_poly = [
        (465, 920),
        (765, 855),
        (805, 1140),
        (475, 1195),
    ]
    draw.polygon(cpu_poly, fill=255)
    draw.polygon(gpu_poly, fill=255)
    draw.polygon(mem_poly, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=5))


def render_graffiti_glyph(
    text: str,
    font: ImageFont.FreeTypeFont,
    main_color: tuple[int, int, int],
    shadow_color: tuple[int, int, int],
    shadow_offset: tuple[int, int] = (-11, 10),
    glow_radius: int = 15,
    shear: float = 0.13,
    stroke_width: int = 6,
) -> Image.Image:
    """
    離線烘焙單一超大號街頭塗鴉字元：
    1. 底層：雙層高斯模糊霓虹外光暈 (模擬噴漆光暈)
    2. 中下層：硬邊左下偏移色塊陰影
    3. 中上層：濃黑外描邊 (#0A0810, stroke_width=6) 確保壓過標題或邊框時依然銳利分明
    4. 頂層：純白斜切主字體
    """
    dummy = Image.new("L", (1, 1), 0)
    d_draw = ImageDraw.Draw(dummy)
    bbox = d_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_w = max(1, bbox[2] - bbox[0])
    text_h = max(1, bbox[3] - bbox[1])

    pad = max(abs(shadow_offset[0]), abs(shadow_offset[1])) + glow_radius * 2 + stroke_width * 2 + 24
    shear_extra = int(text_h * abs(shear)) + 16
    canvas_w = text_w + pad * 2 + shear_extra
    canvas_h = text_h + pad * 2

    draw_x = pad - bbox[0] + int(text_h * max(0.0, shear))
    draw_y = pad - bbox[1]

    fill_mask = Image.new("L", (canvas_w, canvas_h), 0)
    f_draw = ImageDraw.Draw(fill_mask)
    f_draw.text((draw_x, draw_y), text, font=font, fill=255)

    stroke_mask = Image.new("L", (canvas_w, canvas_h), 0)
    s_draw = ImageDraw.Draw(stroke_mask)
    s_draw.text(
        (draw_x, draw_y),
        text,
        font=font,
        fill=255,
        stroke_width=stroke_width,
        stroke_fill=255,
    )

    if abs(shear) > 1e-4:
        cy = canvas_h / 2.0
        affine_params = (1.0, shear, -shear * cy, 0.0, 1.0, 0.0)
        fill_mask = fill_mask.transform((canvas_w, canvas_h), Image.AFFINE, affine_params, resample=Image.BICUBIC)
        stroke_mask = stroke_mask.transform((canvas_w, canvas_h), Image.AFFINE, affine_params, resample=Image.BICUBIC)

    out = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 1. 雙層噴漆霓虹外光暈
    if glow_radius > 0:
        glow_src = ImageChops.lighter(stroke_mask, fill_mask)
        wide_glow = glow_src.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        wide_glow = wide_glow.point(lambda p: min(255, int(p * 0.95)))
        wide_layer = Image.new("RGBA", (canvas_w, canvas_h), (*shadow_color, 255))
        wide_layer.putalpha(wide_glow)
        out = Image.alpha_composite(out, wide_layer)

        core_glow = glow_src.filter(ImageFilter.GaussianBlur(radius=max(2, glow_radius // 2)))
        core_glow = core_glow.point(lambda p: min(255, int(p * 0.85)))
        core_layer = Image.new("RGBA", (canvas_w, canvas_h), (*shadow_color, 255))
        core_layer.putalpha(core_glow)
        out = Image.alpha_composite(out, core_layer)

    # 2. 硬邊左下偏移霓虹色塊陰影
    sx, sy = shadow_offset
    if sx != 0 or sy != 0:
        shadow_mask = Image.new("L", (canvas_w, canvas_h), 0)
        shadow_mask.paste(stroke_mask, (sx, sy))
        shadow_layer = Image.new("RGBA", (canvas_w, canvas_h), (*shadow_color, 255))
        shadow_layer.putalpha(shadow_mask)
        out = Image.alpha_composite(out, shadow_layer)

    # 3. 濃黑外描邊
    if stroke_width > 0:
        dark_layer = Image.new("RGBA", (canvas_w, canvas_h), (*config.COLOR_DARK_STROKE, 255))
        dark_layer.putalpha(stroke_mask)
        out = Image.alpha_composite(out, dark_layer)

    # 4. 純白主字體填充
    main_layer = Image.new("RGBA", (canvas_w, canvas_h), (*main_color, 255))
    main_layer.putalpha(fill_mask)
    out = Image.alpha_composite(out, main_layer)

    content_box = out.getbbox()
    if content_box:
        out = out.crop(content_box)
    return out


def build_sprite_sheets() -> None:
    """為 cpu, gpu, mem 三面板預先烘焙 0-9, %, - 超大號塗鴉字元圖集。"""
    for panel_key, cfg in config.PANEL_CONFIGS.items():
        out_dir = config.SPRITES_DIR / panel_key
        out_dir.mkdir(parents=True, exist_ok=True)

        main_font = ImageFont.truetype(str(config.FONT_DISPLAY_ITALIC), cfg["main_font_size"])
        pct_font = ImageFont.truetype(str(config.FONT_DISPLAY_ITALIC), cfg["pct_font_size"])

        glyphs = {f"main_{d}": (str(d), main_font) for d in range(10)}
        glyphs["main_dash"] = ("-", main_font)
        glyphs["main_pct"] = ("%", pct_font)

        for name, (ch, font) in glyphs.items():
            stroke_w = cfg.get("stroke_width", 6) if font == main_font else max(4, cfg.get("stroke_width", 6) - 1)
            ox, oy = cfg["shadow_offset"]
            s_off = (ox, oy) if font == main_font else (int(ox * 0.75), int(oy * 0.75))
            g_rad = cfg["glow_radius"] if font == main_font else max(8, int(cfg["glow_radius"] * 0.75))

            sprite = render_graffiti_glyph(
                text=ch,
                font=font,
                main_color=cfg["main_color"],
                shadow_color=cfg["shadow_color"],
                shadow_offset=s_off,
                glow_radius=g_rad,
                shear=cfg["shear"],
                stroke_width=stroke_w,
            )
            sprite.save(out_dir / f"{name}.png", "PNG")
    print(f"Built sprite sheets in: {config.SPRITES_DIR}")


def build_all_assets(raw_idle_path: Path | None = None, raw_overheat_path: Path | None = None) -> None:
    config.BG_PATHS["gaming"].parent.mkdir(parents=True, exist_ok=True)
    RAW_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    idle_src = raw_idle_path if (raw_idle_path and Path(raw_idle_path).exists()) else (RAW_ASSETS_DIR / "raw_idle.jpg")
    overheat_src = (
        raw_overheat_path
        if (raw_overheat_path and Path(raw_overheat_path).exists())
        else (RAW_ASSETS_DIR / "raw_overheat.jpg")
    )

    if idle_src.exists() and overheat_src.exists() and config.TEMPLATE_NEON_GIRL.exists():
        img_idle = Image.open(idle_src).convert("RGB").resize(
            (config.ART_SIZE, config.ART_SIZE), Image.LANCZOS
        )
        img_overheat = Image.open(overheat_src).convert("RGB").resize(
            (config.ART_SIZE, config.ART_SIZE), Image.LANCZOS
        )
        img_orig = Image.open(config.TEMPLATE_NEON_GIRL).convert("RGB").resize(
            (config.ART_SIZE, config.ART_SIZE), Image.LANCZOS
        )

        img_idle = _clean_memory_bar_outline(img_idle)
        img_overheat = _clean_memory_bar_outline(img_overheat)

        panel_mask = _build_panel_clean_mask((config.ART_SIZE, config.ART_SIZE))
        img_gaming = Image.composite(img_idle, img_orig, panel_mask)
        img_gaming = _clean_memory_bar_outline(img_gaming)

        img_idle.save(config.BG_PATHS["idle"], "PNG")
        img_gaming.save(config.BG_PATHS["gaming"], "PNG")
        img_overheat.save(config.BG_PATHS["overheat"], "PNG")
        for state_name, p in config.BG_PATHS.items():
            print(f"Built {state_name}: {p}")

    build_sprite_sheets()


if __name__ == "__main__":
    build_all_assets()
