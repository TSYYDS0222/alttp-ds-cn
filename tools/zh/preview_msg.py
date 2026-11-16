"""Render a translated dialogue message to PNG without an emulator.

Reads zelda3_assets.dat and draws one message with the same glyph layout the
engine uses (8x16 Latin tiles from a 2bpp atlas, 16x16 CJK glyphs as four
8x8 tiles) so text can be proof-read from the command line.

    python preview_msg.py <assets.dat> <message number> [out.png] [scale]
    python preview_msg.py <assets.dat> --list-brackets
"""
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inject_zh_assets as iz  # noqa: E402

PAGE_FIRST, PAGE_LAST, FIRST_CHAR, GLYPH_OFFSET = 0xF0, 0xF4, 111, 4096


def load(asset_path):
    assets, _, _ = iz.split_assets(Path(asset_path).read_bytes())
    glyphs, widths = iz.unpack_blocks(iz.unpack_blocks(assets[iz.FIDX])[0])
    messages = iz.unpack_blocks(iz.unpack_blocks(iz.unpack_blocks(assets[iz.DIDX])[0])[1])
    return glyphs, widths, messages


def _art(tile):
    return ["".join("#" if ((tile[y * 2] >> (7 - x)) & 1) or
                    ((tile[y * 2 + 1] >> (7 - x)) & 1) else "." for x in range(8))
            for y in range(8)]


def cjk_art(glyphs, g):
    """16 rows of 16 columns for glyph g (four 8x8 tiles: TL, TR, BL, BR)."""
    base = glyphs[GLYPH_OFFSET + g * 64:GLYPH_OFFSET + (g + 1) * 64]
    a = [_art(base[k * 16:(k + 1) * 16]) for k in range(4)]
    return [a[0][i] + a[1][i] for i in range(8)] + [a[2][i] + a[3][i] for i in range(8)]


def latin_art(glyphs, code):
    t = ((code & 0x70) * 2) + (code & 0x0F)
    return _art(glyphs[t * 16:(t + 1) * 16]) + _art(glyphs[(t + 16) * 16:(t + 17) * 16])


def cells(glyphs, widths, msg):
    out, i = [], 0
    while i < len(msg):
        b = msg[i]
        if b == 0:
            break
        if PAGE_FIRST <= b <= PAGE_LAST:
            g = (b - PAGE_FIRST) * 256 + msg[i + 1]
            i += 2
            out.append((cjk_art(glyphs, g), widths[FIRST_CHAR + g] if len(widths) > FIRST_CHAR + g else 16))
        elif b >= 0x67:
            i += 1  # text command
        else:
            out.append((latin_art(glyphs, b), widths[b] if len(widths) > b else 8))
            i += 1
    return out


def write_png(path, rows, scale=4, pad=8):
    width = sum(w for _, w in rows) * scale + pad * 2
    height = 16 * scale + pad * 2
    img = [[18] * width for _ in range(height)]
    x = pad
    for art, adv in rows:
        for y, row in enumerate(art):
            for gx, ch in enumerate(row):
                if ch != "#":
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        px, py = x + gx * scale + dx, pad + y * scale + dy
                        if 0 <= px < width and 0 <= py < height:
                            img[py][px] = 235
        x += adv * scale
    raw = b"".join(b"\x00" + bytes(r) for r in img)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    Path(path).write_bytes(png)
    return width, height


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    asset = sys.argv[1]
    glyphs, widths, messages = load(asset)
    if sys.argv[2] == "--list-brackets":
        for n, m in enumerate(messages):
            i = 0
            hits = []
            while i < len(m):
                if PAGE_FIRST <= m[i] <= PAGE_LAST:
                    i += 2
                    continue
                if m[i] in (0x5B, 0x5C, 0x5D, 0x5E):
                    hits.append((i, m[i]))
                i += 1
            if hits:
                print(n, [(hex(b), i) for i, b in hits])
        return
    n = int(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else f"msg{n}.png"
    scale = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    print(write_png(out, cells(glyphs, widths, messages[n]), scale), out)


if __name__ == "__main__":
    main()
