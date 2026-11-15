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

    # The 3DS pack ships its own 4096-byte Latin font: 383 bytes differ from
    # the USA cartridge's, and tile 0xaf (the "I" of the cartridge's name
    # entry keyboard) is a comma there. The ROM's own UI reads those tiles
    # by index, so keep the original Latin tiles and take only the pack's
    # CJK glyphs, which start at offset 4096 of the wide block, plus its
    # width table. Nothing after the Latin area moves, so CJK rendering is
    # untouched. The original asset is PackBlocks: 2-byte offset table,
    # 4096 Latin bytes, 99 widths, 2-byte trailer.
    latin = inject_zh_assets.unpack_blocks(
        assets[inject_zh_assets.FIDX])[0][2:4098]
    if len(latin) != 4096 or len(font) <= 4100:
        fail("unexpected font block layout")
    font = font[:4] + latin + font[4100:]

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
