"""
Kraken Z53 LCD 系統監控設定檔 (Neon Gaming Girl HUD - Pre-baked Graffiti Sprite Edition)
集中管理畫布尺寸、預製塗鴉圖集路徑、人物表情狀態門檻（含遲滯緩衝）與各傾斜面板參數。
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "Templates"

# 原始設計圖與水冷頭目標螢幕尺寸
ART_SIZE = 1254
CENTER = (627, 627)
LCD_WIDTH = 320
LCD_HEIGHT = 320
LCD_SIZE = (LCD_WIDTH, LCD_HEIGHT)

# 原始模板參考路徑
TEMPLATE_NEON_GIRL = TEMPLATES_DIR / "ネオンゲーミング少女の円形HUD.png"

# 三階段狀態底圖路徑
BG_PATHS = {
    "idle": ASSETS_DIR / "backgrounds" / "idle.png",
    "gaming": ASSETS_DIR / "backgrounds" / "gaming.png",
    "overheat": ASSETS_DIR / "backgrounds" / "overheat.png",
}

# 預製超大號街頭塗鴉圖集目錄與智慧防閃門檻
SPRITES_DIR = ASSETS_DIR / "sprites"
FRAME_UPDATE_THRESHOLD = 1.0  # 當狀態未變且 CPU/GPU/MEM 變化 < 1% / 1°C 時略過 USB 重傳

# 專案內建字型路徑
FONT_DISPLAY_ITALIC = ASSETS_DIR / "fonts" / "Display-BlackItalic.ttf"
FONT_DISPLAY_BOLD = ASSETS_DIR / "fonts" / "Display-Bold.ttf"

# 色彩定義 (RGB)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK_STROKE = (10, 8, 16)     # 濃黑外描邊 (使超大號數字壓過標題與邊框時仍銳利分明)
COLOR_PINK = (255, 36, 152)         # CPU 主霓虹粉紅 (陰影與光暈)
COLOR_PINK_TEXT = (255, 72, 162)    # CPU 溫度副標字色
COLOR_CYAN = (0, 232, 255)          # GPU 主霓虹青藍 (陰影與光暈)
COLOR_CYAN_TEXT = (56, 236, 255)    # GPU 溫度副標字色
COLOR_GOLD = (255, 230, 0)          # MEMORY 主霓虹金黃 (陰影、光暈與進度條)
COLOR_GOLD_TEXT = (255, 242, 130)   # MEMORY 副標字色

# 狀態機門檻與遲滯緩衝 (Hysteresis)
STATE_THRESHOLDS = {
    "gaming_enter_usage": 50.0,
    "gaming_enter_temp": 65.0,
    "gaming_exit_usage": 45.0,
    "gaming_exit_temp": 60.0,
    "overheat_enter_temp": 80.0,
    "overheat_enter_usage": 90.0,
    "overheat_exit_temp": 75.0,
    "overheat_exit_usage": 85.0,
}

# 各傾斜面板局部畫布與超大號街頭塗鴉字體排版參數 (1:1 還原原圖視覺比例)
# 原圖三個面板皆為「左低右高」（逆時針傾斜），Pillow rotate(+angle) 為逆時針旋轉。
PANEL_CONFIGS = {
    "cpu": {
        "angle": 11.5,
        "canvas_size": (540, 340),
        "center_pos": (368, 502),
        "main_font_size": 172,
        "pct_font_size": 96,
        "sec_font_size": 46,
        "stroke_width": 6,
        "main_color": COLOR_WHITE,
        "shadow_color": COLOR_PINK,
        "shadow_offset": (-11, 10),
        "glow_radius": 15,
        "shear": 0.13,
        # 在局部畫布 (540x340) 內的對齊基準：
        "digits_anchor": (305, 152),  # 超大號主數字與 % 組合中心點 (自然貼在 CPU 標題右下緣)
        "sec_pos": (282, 268),        # 溫度文字中心點 (精準對齊左側溫度計圖示右方)
        "sec_color": COLOR_PINK_TEXT,
    },
    "gpu": {
        "angle": 10.5,
        "canvas_size": (560, 350),
        "center_pos": (568, 755),
        "main_font_size": 182,
        "pct_font_size": 100,
        "sec_font_size": 48,
        "stroke_width": 6,
        "main_color": COLOR_WHITE,
        "shadow_color": COLOR_CYAN,
        "shadow_offset": (-12, 11),
        "glow_radius": 16,
        "shear": 0.13,
        "digits_anchor": (322, 150),
        "sec_pos": (342, 274),
        "sec_color": COLOR_CYAN_TEXT,
    },
    "mem": {
        "angle": 10.5,
        "canvas_size": (540, 350),
        "center_pos": (598, 1048),
        "main_font_size": 154,
        "pct_font_size": 88,
        "sub_font_size": 38,
        "stroke_width": 5,
        "main_color": COLOR_WHITE,
        "shadow_color": COLOR_GOLD,
        "shadow_offset": (-10, 9),
        "glow_radius": 14,
        "shear": 0.13,
        "digits_anchor": (315, 134),
        "sub_pos": (280, 226),
        "sub_color": COLOR_WHITE,
        "bar_box": (115, 260, 425, 290),
        "bar_cells": 10,
        "bar_gap": 5,
        "bar_slant": 6,
    },
}
