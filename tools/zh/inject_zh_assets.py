#!/usr/bin/env python3
"""Make a Chinese zelda3_assets.dat for the NDS build.

Port of AddLanguagePackToAssets / AppendLanguageToAssets from the 3DS port
(platform/3ds/source/platform_3ds.c), with only_language: the asset blob keeps
one language only, Chinese, so ZeldaSetLanguage(NULL) picks it up and the game
has no English text left to fall back to.

    zelda3_assets.dat <rom>          produced by vendor/zelda3/assets/restool.py
    zh.bps from the 3DS release      applied to the USA ROM -> pack
    pack                             'ZCNB', dialogue block, font block

Usage:
  inject_zh_assets.py zelda3_assets.dat zh_pack.bin zelda3_assets.zh.dat
"""
import struct
import sys
from pathlib import Path

SIGNATURE = b'Zelda3_v0 '
ASSET_COUNT_EXPECTED = 165
DIDX, FIDX, MIDX = 94, 95, 96          # dialogues, fonts, language map
LANGUAGE = b'zh'
# bit 2: page-coded text; bit 3: 16x16 glyphs with their own width. 1 and 2 are
# what the 3DS port writes; Text_DecodeCmd checks the CJK bit first.
PACK_FLAGS = 1 | 2 | 4 | 8


def die(msg):
    sys.stderr.write(msg.rstrip() + '\n')
    sys.exit(1)


def pack_blocks(blocks):
    """PackBlocks from platform_3ds.c: data, then offsets, then count - 1."""
    if not blocks:
        raise ValueError('no blocks')
    data_size = sum(len(b) for b in blocks)
    wide = data_size >= 65536 or len(blocks) > 8192
    width = 4 if wide else 2
    header = (len(blocks) - 1) * width
    out = bytearray(header)
    cumulative = 0
    for i, block in enumerate(blocks):
        if i != 0:
            struct.pack_into('<I' if wide else '<H', out, (i - 1) * width, cumulative)
        out += block
        cumulative += len(block)
    out += struct.pack('<H', (len(blocks) - 1) + (8192 if wide else 0))
    return bytes(out)


def unpack_blocks(data):
    """UnpackBlocks from platform_3ds.c."""
    if len(data) < 2:
        raise ValueError('block list too short')
    end = len(data) - 2
    trailer = struct.unpack_from('<H', data, end)[0]
    width, count = 2, trailer + 1
    if trailer >= 8192:
        width, count = 4, trailer - 8192 + 1
    base = (count - 1) * width
    if base > end:
        raise ValueError('offsets do not fit')
    blocks, previous = [], 0
    for i in range(count):
        following = (end - base) if i == count - 1 else \
            struct.unpack_from('<I' if width == 4 else '<H', data, i * width)[0]
        blocks.append(data[base + previous:base + following])
        previous = following
    return blocks


def read_pack(pack):
    if len(pack) < 12 or pack[:4] != b'ZCNB':
        raise ValueError('not a ZCNB language pack')
    dialogue_size = struct.unpack_from('<I', pack, 4)[0]
    font_at = 8 + dialogue_size + 4
    if dialogue_size == 0 or font_at > len(pack):
        raise ValueError('dialogue block does not fit')
    font_size = struct.unpack_from('<I', pack, 8 + dialogue_size)[0]
    if font_size == 0 or font_at + font_size != len(pack):
        raise ValueError('font block does not fit')
    return pack[8:8 + dialogue_size], pack[font_at:]


def split_assets(data):
    if data[:len(SIGNATURE)] != SIGNATURE:
        raise ValueError('not a zelda3_assets.dat')
    # The runtime checks the whole 48-byte signature block, so keep it verbatim.
    header = data[:88]
    count, names_size = struct.unpack_from('<II', data, 80)
    if count != ASSET_COUNT_EXPECTED:
        raise ValueError(f'{count} assets, expected {ASSET_COUNT_EXPECTED}')
    sizes = struct.unpack_from('<%dI' % count, data, 88)
    names_at = 88 + count * 4
    names = data[names_at:names_at + names_size]
    assets, offset = [], names_at + names_size
    for size in sizes:
        offset = (offset + 3) & ~3
        assets.append(data[offset:offset + size])
        offset += size
    return assets, names, header


def build_blob(assets, names, header):
    count = len(assets)
    total = 88 + count * 4 + len(names)
    for asset in assets:
        total = ((total + 3) & ~3) + len(asset)
    out = bytearray(total)
    out[:88] = header
    struct.pack_into('<II', out, 80, count, len(names))
    struct.pack_into('<%dI' % count, out, 88, *[len(a) for a in assets])
    out[88 + count * 4:88 + count * 4 + len(names)] = names
    offset = 88 + count * 4 + len(names)
    for asset in assets:
        offset = (offset + 3) & ~3
        out[offset:offset + len(asset)] = asset
        offset += len(asset)
    return bytes(out)


def main():
    if len(sys.argv) != 4:
        die(__doc__)
    source, pack_path, dest = (Path(p) for p in sys.argv[1:4])
    data = source.read_bytes()
    dialogue, font = read_pack(pack_path.read_bytes())
    assets, names, header = split_assets(data)

    # only_language: one dialogue, one font, one map entry, at index 0.
    assets[DIDX] = pack_blocks([dialogue])
    assets[FIDX] = pack_blocks([font])
    entry = pack_blocks([LANGUAGE, bytes([0, 0, PACK_FLAGS])])
    assets[MIDX] = pack_blocks([entry])

    blob = build_blob(assets, names, header)

    # Read it back the way the engine will: ZeldaSetLanguage(NULL) walks
    # kDialogueMap for an entry whose conf starts at dialogue 0.
    check, _, _ = split_assets(blob)
    map_entry = unpack_blocks(check[MIDX])[0]
    name, conf = unpack_blocks(map_entry)
    dialogues = unpack_blocks(check[DIDX])
    fonts = unpack_blocks(check[FIDX])
    if name != LANGUAGE or len(conf) != 3:
        die('language map did not round-trip')
    dialogue_index, font_index, flags = conf
    if dialogue_index >= len(dialogues) or font_index >= len(fonts):
        die('language map points outside the dialogue or font list')
    dictionary_and_messages = unpack_blocks(dialogues[dialogue_index])
    messages = unpack_blocks(dictionary_and_messages[1])
    glyph_block, width_block = unpack_blocks(fonts[font_index])
    glyph_count = (len(glyph_block) - 4096) // 64
    if len(width_block) != 111 + glyph_count:
        die(f'{len(width_block)} widths for {glyph_count} glyphs')

    dest.write_bytes(blob)
    print(f'{dest}: {len(blob)} bytes')
    print(f'  language {name.decode()} flags {flags:#x}, dialogue {dialogue_index}, '
          f'font {font_index}')
    print(f'  {len(messages)} messages, {glyph_count} 16x16 glyphs')


if __name__ == '__main__':
    main()
