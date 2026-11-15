#!/usr/bin/env python3
"""Bake the menu overlay's Chinese text into 16x16 bitmaps.

The overlay (settings, button mapping) draws with the cartridge's 8x16 letter
font, which has no CJK. Rather than guess the dialogue pack's glyph encoding,
this bakes a small font of its own: one 16x16 1bpp bitmap per character, plus
one array per string. The game links both in; the drawing code lives in
platform/nds/source/zelda_video.c (ZeldaVideoMenuTextZh).

    python tools/zh/make_ui_font.py --ttf <path to a CJK ttf>
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "platform" / "nds" / "include" / "zh_ui_font.h"
SOURCE = ROOT / "platform" / "nds" / "source" / "zh_ui_font.c"

# name -> (string, comment). One array per entry, in this order.
TEXTS = [
    ("settings_title", "设置", "settings panel title"),
    ("hud", "状态栏", "row HUD"),
    ("hud_top", "上屏", "value"),
    ("hud_bottom", "下屏", "value"),
    ("low_hp", "低血提示", "row"),
    ("on", "开", "value"),
    ("off", "关", "value"),
    ("spawn", "重生位置", "row"),
    ("spawn_normal", "普通", "value"),
    ("spawn_dungeon", "迷宫", "value"),
    ("mirror", "魔法镜限制", "row"),
    ("mirror_free", "自由", "value"),
    ("mirror_normal", "正常", "value"),
    ("bomb", "炸弹上限", "row"),
    ("arrow", "箭矢上限", "row"),
    ("speed", "移动速度", "row"),
    ("speed_normal", "正常", "value"),
    ("speed_double", "两倍", "value"),
    ("speed_triple", "三倍", "value"),
    ("dark", "黑暗房间", "row"),
    ("dark_bright", "明亮", "value"),
    ("hair", "头发颜色", "row"),
    ("hair_pink", "粉色", "value"),
    ("hair_blonde", "金色", "value"),
    ("buttons_row", "按键设置", "row, and the mapping page title"),
    ("save", "保存", "button"),
    ("cancel", "取消", "button"),
    ("btn_a", "A键", "row"),
    ("btn_b", "B键", "row"),
    ("btn_x", "X键", "row"),
    ("btn_y", "Y键", "row"),
    ("btn_l", "L键", "row"),
    ("btn_r", "R键", "row"),
    ("btn_start", "开始", "row"),
    ("btn_select", "选择", "row"),
    ("dp_up", "上", "row"),
    ("dp_down", "下", "row"),
    ("dp_left", "左", "row"),
    ("dp_right", "右", "row"),
    ("ds_up", "十字上", "value"),
    ("ds_down", "十字下", "value"),
    ("ds_left", "十字左", "value"),
    ("ds_right", "十字右", "value"),
    ("n99", "99", "value"),
    ("n10", "10", "value"),
    ("n30", "30", "value"),
    # Bottom-screen HUD labels (zelda_bottom.c).
    ("gear_bottles", "瓶子", "gear panel label"),
    ("gear_pendants", "吊坠", "gear panel label"),
    ("gear_crystals", "水晶", "gear panel label"),
    ("gear_pieces", "心之碎片", "gear panel label"),
    ("gear_keys", "钥匙", "gear panel label"),
    ("gear_title", "装备", "bottom button / gear panel title"),
    ("items_title", "道具", "bottom button / items panel title"),
    ("life_title", "生命", "LIFE text"),
    # File-select / name-entry screens (zh_select.c writes these into BG3).
    ("fs_select", "选择存档", "PLAYER SELECT"),
    ("fs_copy", "复制文件", "COPY FILE"),
    ("fs_erase", "删除文件", "ERASE FILE"),
    ("fs_copy_player", "复制玩家", "COPY PLAYER"),
    ("fs_erase_player", "删除玩家", "ERASE PLAYER"),
    ("fs_quit", "退出", "QUIT"),
    ("fs_name", "请输入玩家姓名", "REGISTER YOUR NAME"),
    ("fs_which", "要删除哪位玩家", "WHICH PLAYER DO YOU WANT"),
    ("fs_confirm", "确认删除", "TO ERASE"),
    ("empty", "", "no text"),
]

CELL = 16


def bake(font, ch):
    """One 16x16 cell: 16 rows of two bytes, most significant bit leftmost."""
    img = Image.new("L", (CELL, CELL), 0)
    if ch != " ":
        draw = ImageDraw.Draw(img)
        # Left aligned and proportionally spaced: a narrow glyph like "1" would
        # otherwise sit in the middle of its cell and leave a gap after it.
        box = draw.textbbox((0, 0), ch, font=font)
        h = box[3] - box[1]
        draw.text((-box[0], (CELL - h) // 2 - box[1]), ch, fill=255, font=font)
    px = img.load()
    rows, ink_right, ink_left = [], -1, CELL
    for y in range(CELL):
        lo = hi = 0
        for x in range(CELL):
            if px[x, y] > 110:
                if x < 8:
                    lo |= 1 << (7 - x)
                else:
                    hi |= 1 << (15 - x)
                ink_right = max(ink_right, x)
                ink_left = min(ink_left, x)
        rows.append(lo)
        rows.append(hi)
    if ink_right < 0:
        return rows, 6
    width = max(4, min(CELL, ink_right + 2))
    return rows, width


def c_string(text):
    return "".join(f"\\x{ch}" for ch in text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ttf", default="D:/tsyyds/SpaceCadetPinball/DreamHanSans.ttf")
    args = ap.parse_args()
    font = ImageFont.truetype(args.ttf, 15)

    order, index = [], {}
    for name, text, _ in TEXTS:
        for ch in text:
            if ch not in index:
                index[ch] = len(order)
                order.append(ch)

    bitmaps, widths = [], []
    for ch in order:
        bits, width = bake(font, ch)
        bitmaps.append(bits)
        widths.append(width)

    src = [
        "/* Generated by tools/zh/make_ui_font.py. Do not edit. */",
        '#include "zh_ui_font.h"',
        "",
        "/* One 16x16 cell per glyph: 16 rows of two bytes, bit 7 leftmost. */",
        "const unsigned char zh_ui_font_bits[][32] = {",
    ]
    for ch, bits in zip(order, bitmaps):
        src.append("  { " + ", ".join("0x%02x" % b for b in bits) + " },  /* %s */" % ch)
    src.append("};")
    src.append("")
    src.append("const unsigned char zh_ui_font_width[] = {")
    for i in range(0, len(widths), 16):
        src.append("  " + ", ".join(str(w) for w in widths[i:i + 16]) + ",")
    src.append("};")
    src.append("")
    src.append("const unsigned int zh_ui_font_count = %d;" % len(order))
    src.append("")
    for name, text, comment in TEXTS:
        ids = [index[ch] for ch in text]
        src.append("/* %s */" % comment)
        parts = [str(i) for i in ids] + ["0xffff"]
        src.append("const unsigned short zh_ui_%s[] = { %s };" %
                   (name, ", ".join(parts)))
    SOURCE.write_text("\n".join(src) + "\n")

    decls = [
        "/* Generated by tools/zh/make_ui_font.py. Do not edit. */",
        "#ifndef ZH_UI_FONT_H_",
        "#define ZH_UI_FONT_H_",
        "",
        "extern const unsigned char zh_ui_font_bits[][32];",
        "extern const unsigned char zh_ui_font_width[];",
        "extern const unsigned int zh_ui_font_count;",
        "",
    ]
    for name, text, comment in TEXTS:
        decls.append("extern const unsigned short zh_ui_%s[];  /* %s */" % (name, text))
    decls += ["", "#endif  // ZH_UI_FONT_H_", ""]
    HEADER.write_text("\n".join(decls))

    print(f"{len(order)} glyphs, {len(TEXTS)} strings")
    print(f"  {SOURCE.relative_to(ROOT)}")
    print(f"  {HEADER.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
