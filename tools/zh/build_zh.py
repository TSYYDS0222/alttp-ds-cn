#!/usr/bin/env python3
"""Build lttp-ds.nds with the Chinese translation.

The translation is not a ROM hack: the cartridge's own text engine cannot draw
a 16x16 glyph. The 3DS port carries it as a pack ('ZCNB', dialogue block, font
block) and appends that pack to the USA cartridge as a BPS patch. This script
takes the pack out of that patch and merges it into the assets blob the NDS
build links in, so the game has one language: Chinese.

Steps
  1. apply tools/zh/zh.bps to the USA ROM, check the CRC the patch records
  2. cut the pack out of the patched cartridge ('ZCNP' footer)
  3. extract zelda3_assets.dat from the clean ROM with restool (once)
  4. replace its languages with the Chinese one (inject_zh_assets.py)
  5. run build.py, which compiles and links the .nds

Usage:  python tools/zh/build_zh.py --rom path/to/zelda3.sfc [--no-build]
"""
import argparse
import hashlib
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ZH = ROOT / "tools" / "zh"
WORK = ROOT / "build" / "zh"
ROM_SHA256 = "66871d66be19ad2c34c927d6b14cd8eb6fc3181965b6e517cb361f7316009cfb"
PACK_MAGIC = b"ZCNB"
FOOTER_MAGIC = b"ZCNP"

# The 3DS pack reuses two Latin font slots for the Chinese comma and full
# stop. With the original Latin font restored those byte values draw the
# letter "I", so translate them to the cartridge's own punctuation codes in
# the dialogue text. This engine does not use ASCII: the glyph tile is
# (code & 0x70) * 2 + (code & 0xf), so "," is 0x42 (tile 0x82) and "." is
# 0x41 (tile 0x81); 0x2c/0x2e would draw "s" and "t". Bytes after a CJK page
# marker are glyph indices: leave those alone, they are not characters.
PUNCT = {0x5F: 0x42, 0x60: 0x41}  # ，-> ,  and  。-> .
CJK_PAGES = range(0xF0, 0xF5)
DIALOGUE_OFFSETS = 397 * 2  # u16 message offsets at the start of the block

# The 3DS translation writes [ and ] into those two character codes. Both the
# USA font and the translation pack leave the slots as filled blocks, so the
# NDS build showed black rectangles in dialogue. Draw the brackets ourselves
# in the restored Latin atlas (2bpp, one 8x8 tile plus the tile 16 slots on).
BRACKET_ROWS = {
    0x5B: [".######."] + [".#......"] * 14 + [".######."],
    0x5D: [".######."] + ["......#."] * 14 + [".######."],
}


def tile_no(code):
    return ((code & 0x70) * 2) + (code & 0x0F)


def draw_brackets(latin):
    out = bytearray(latin)
    for code, rows in BRACKET_ROWS.items():
        assert len(rows) == 16 and all(len(r) == 8 for r in rows)
        for half in range(2):
            tile = tile_no(code) + half * 16
            for y in range(8):
                bits = 0
                for x, ch in enumerate(rows[half * 8 + y]):
                    if ch == "#":
                        bits |= 0x80 >> x
                out[(tile * 16) + y * 2] = bits
                out[(tile * 16) + y * 2 + 1] = 0
    return bytes(out)


def to_ascii_punctuation(text):
    out = bytearray(text)
    i = DIALOGUE_OFFSETS
    while i < len(out):
        if out[i] in CJK_PAGES:
            i += 2          # page byte + glyph index, copied verbatim
            continue
        if out[i] in PUNCT:
            out[i] = PUNCT[out[i]]
        i += 1
    return bytes(out)


def fail(message):
    sys.stderr.write("zh: " + message.rstrip() + "\n")
    sys.exit(1)


def find_rom(explicit):
    candidates = [Path(explicit)] if explicit else []
    candidates += [
        ROOT / "vendor" / "zelda3" / "assets" / "zelda3.sfc",
        ROOT / "vendor" / "zelda3" / "zelda3.sfc",
        ROOT / "zelda3.sfc",
    ]
    for path in candidates:
        if path.is_file():
            return path
    fail("no ROM found; pass --rom path/to/zelda3.sfc")


def extract_pack(cart):
    if cart[-8:-4] != FOOTER_MAGIC:
        fail("patched cartridge does not end with the ZCNP footer")
    size = struct.unpack("<I", cart[-4:])[0]
    if size == 0 or size + 8 > len(cart):
        fail("the pack size in the footer is out of range")
    pack = cart[-8 - size:-8]
    if pack[:4] != PACK_MAGIC:
        fail("the pack does not start with ZCNB")
    dialogue_size = struct.unpack_from("<I", pack, 4)[0]
    font_size = struct.unpack_from("<I", pack, 8 + dialogue_size)[0]
    if 8 + dialogue_size + 4 + font_size != len(pack):
        fail("the pack's block sizes do not add up")
    return pack


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom")
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("-j", "--jobs")
    args = parser.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    rom = find_rom(args.rom)
    digest = hashlib.sha256(rom.read_bytes()).hexdigest()
    if digest != ROM_SHA256:
        fail(f"{rom} is not the USA cartridge (sha256 {digest})")
    print(f"rom: {rom}")

    sys.path.insert(0, str(ZH))
    import bps_apply
    import inject_zh_assets

    # 1. patch -> the cartridge plus the pack, exactly as the 3DS port reads it
    patched = WORK / "zelda3_zh.sfc"
    patch = (ZH / "zh.bps").read_bytes()
    patched.write_bytes(bps_apply.apply(rom.read_bytes(), patch))
    print(f"patch: {patched.name} ({patched.stat().st_size} bytes)")

    # 2. cut the pack out
    pack = extract_pack(patched.read_bytes())
    (WORK / "zh_pack.bin").write_bytes(pack)
    print(f"pack: {len(pack)} bytes")

    # 3. the asset blob, from the clean ROM
    extracted = ROOT / "vendor" / "zelda3" / "zelda3_assets.dat"
    if not extracted.is_file():
        restool = ROOT / "vendor" / "zelda3" / "assets" / "restool.py"
        print("assets: extracting zelda3_assets.dat from the ROM (this takes a minute)")
        subprocess.check_call(
            [sys.executable, str(restool), "--extract-from-rom", "--rom", str(rom)],
            cwd=str(ROOT / "vendor" / "zelda3"))
        if not extracted.is_file():
            fail("restool did not write zelda3_assets.dat")

    # 4. replace its languages with Chinese
    assets, names, header = inject_zh_assets.split_assets(extracted.read_bytes())
    dialogue, font = inject_zh_assets.read_pack(pack)

    # The pack replaces part of the Latin font with Chinese punctuation,
    # including the tile the name-entry keyboard uses for "I", so "I" draws
    # as a comma and, once restored, the punctuation bytes draw letters.
    # Restore the original 4096 Latin bytes; the CJK glyphs start at
    # offset 4096 and the width table is a separate block, so neither
    # moves and Chinese dialogue is untouched. The dialogue's punctuation
    # bytes are remapped to the cartridge's own "," and "." codes above.
    latin = inject_zh_assets.unpack_blocks(
        assets[inject_zh_assets.FIDX])[0][2:4098]
    if len(latin) != 4096 or len(font) <= 4100:
        fail("unexpected font block layout")

    # The dialogue's Chinese full stop is remapped to 0x41 (the cartridge's
    # English "." code) and its question mark already uses 0x62. Both slots
    # are filled/blank in the restored USA atlas, so copy the translation
    # pack's own glyphs for "。" and "？" into them. Leaving the dialogue
    # bytes alone keeps the name-entry letter grid untouched.
    pack_glyph, _ = inject_zh_assets.unpack_blocks(font)
    latin = bytearray(latin)
    for src, dst in ((0x60, 0x41), (0x62, 0x62)):
        s, d = tile_no(src), tile_no(dst)
        for half in range(2):
            sr, dr = s + half * 16, d + half * 16
            latin[dr * 16:(dr + 1) * 16] = pack_glyph[sr * 16:(sr + 1) * 16]

    font = bytearray(font[:4] + draw_brackets(bytes(latin)) + font[4100:])
    # A Chinese full stop is full width; the English "." entry is only 4px.
    # Widths live in the font's second block, right after the glyph block.
    font[4 + len(pack_glyph) + 0x41] = 8
    font = bytes(font)

    dialogue = to_ascii_punctuation(dialogue)
    assets[inject_zh_assets.DIDX] = inject_zh_assets.pack_blocks([dialogue])
    assets[inject_zh_assets.FIDX] = inject_zh_assets.pack_blocks([font])
    entry = inject_zh_assets.pack_blocks(
        [inject_zh_assets.LANGUAGE, bytes([0, 0, inject_zh_assets.PACK_FLAGS])])
    assets[inject_zh_assets.MIDX] = inject_zh_assets.pack_blocks([entry])
    blob = inject_zh_assets.build_blob(assets, names, header)
    # prepare_assets.py copies the blob at the repo root into the link
    (ROOT / "zelda3_assets.dat").write_bytes(blob)
    print(f"assets: zelda3_assets.dat {len(blob)} bytes, language zh, flags "
          f"{inject_zh_assets.PACK_FLAGS:#x}")

    if args.no_build:
        return
    # 5. compile
    command = [sys.executable, "build.py"]
    if args.jobs:
        command += ["-j" + str(args.jobs)]
    print("build:", " ".join(command))
    subprocess.check_call(command, cwd=str(ROOT))


if __name__ == "__main__":
    main()
