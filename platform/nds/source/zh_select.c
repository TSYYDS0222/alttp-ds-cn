/* Chinese titles for the file-select, copy, erase and name-entry screens.
 *
 * Those screens are not part of the 397 translated dialogue messages: their
 * text is a set of BG3 tilemap stripes (three of them hardcoded here in the
 * port, one extracted from the cartridge as asset 100). BG3 uses 2bpp 8x8
 * tiles starting at VRAM word 0x7000 and a 32x32 tilemap at 0x6000; the
 * letters are pairs of tiles, top half on one row and bottom half on the
 * next, with palette 6 and low priority.
 *
 * A Chinese glyph is 16x16, so it takes four 8x8 tiles. Tile indices
 * 0x160..0x1ff are unused on these screens (the font occupies 0x1000
 * words from 0x7000, the file-select graphics another 0x300 from 0x7800),
 * leaving VRAM 0x7b00..0x7fff. This writes the glyph pixels there and
 * points both tilemap rows at them.
 *
 * tools/zh/make_ui_font.py bakes the glyphs; this file only lays them out.
 */
#include <nds.h>

#include "types.h"
#include "zelda_rtl.h"
#include "variables.h"
#include "zh_ui_font.h"
#include "zh_select.h"

/* Word addresses in the emulated SNES VRAM (uint16 array). */
enum {
	kZhMap = 0x6000,       /* BG3 tilemap, 32 words per row */
	kZhTiles = 0x7000,     /* BG3 tile 0 */
	kZhBank = 0x160,       /* first free tile index -> 0x7b00 */
	kZhBankEnd = 0x200,    /* tile 0x200 would wrap to VRAM 0 */
	kZhAttr = 0x1800,      /* palette 6, low priority */
	kZhSpaceTop = 0x18a9,  /* the font's blank tile, top half */
	kZhSpaceBot = 0x18b9   /* ... and its bottom half */
};

typedef struct {
	uint8 row;             /* first of the two 8-pixel rows */
	uint8 col;             /* first column of the original English stripe */
	uint8 width;           /* original stripe width, in tiles */
	const unsigned short *text;
} ZhLine;

static const ZhLine kLinesSelect[] = {
	{ 3,  5, 14, zh_ui_fs_select },
	{ 22, 6,  9, zh_ui_fs_copy },
	{ 22, 18, 10, zh_ui_fs_erase },
};

static const ZhLine kLinesCopy[] = {
	{ 3,  5, 12, zh_ui_fs_copy_player },
	{ 22, 6,  4, zh_ui_fs_quit },
};

static const ZhLine kLinesErase[] = {
	{ 3,  5, 12, zh_ui_fs_erase_player },
	{ 8,  4, 24, zh_ui_fs_which },
	{ 10, 4, 10, zh_ui_fs_confirm },
	{ 22, 6,  4, zh_ui_fs_quit },
};

/* Only the banner is translated. END sits inside the letter grid; a 16x16
 * cell needs two tile rows there and breaks the grid layout. */
static const ZhLine kLinesName[] = {
	{ 5,  4, 22, zh_ui_fs_name },
};

/* White glyphs with a dark outline. BG3's palette 6 gives colour 1 (dark
 * blue) and colour 2 (white) from the two bitplanes; colour 3 is red and
 * must never appear, so the outline excludes the glyph itself.
 * One glyph = four consecutive 8x8 tiles: top-left, top-right, bottom-left,
 * bottom-right. Each 2bpp tile is eight words, low byte = plane 0. */
static void zh_glyph_tiles(unsigned int id, int tile, uint16 *vram)
{
	const unsigned char *bits = zh_ui_font_bits[id];
	uint16 *dst = vram + kZhTiles + tile * 8;
	uint16 cell[16], edge[16];
	int r, q, row;

	for (r = 0; r < 16; r++)
		cell[r] = (uint16)(((uint16)bits[r * 2] << 8) | bits[r * 2 + 1]);
	for (r = 0; r < 16; r++) {
		uint16 a = cell[r];
		uint16 up = r ? cell[r - 1] : 0;
		uint16 dn = r < 15 ? cell[r + 1] : 0;
		uint16 around = (uint16)(a | (a << 1) | (a >> 1) |
			up | (up << 1) | (up >> 1) |
			dn | (dn << 1) | (dn >> 1));

		edge[r] = (uint16)(around & ~a);
	}
	for (q = 0; q < 4; q++) {
		int qx = q & 1;
		int qy = q >> 1;
		uint16 *d = dst + q * 8;

		for (row = 0; row < 8; row++) {
			int src = qy * 8 + row;
			unsigned int white = cell[src];
			unsigned int outline = edge[src];
			unsigned char p0 = 0, p1 = 0;
			int col;

			for (col = 0; col < 8; col++) {
				unsigned int m = 0x8000u >> (qx * 8 + col);
				unsigned char bit = (unsigned char)(0x80u >> col);

				if (white & m)
					p1 |= bit;          /* colour 2: white */
				else if (outline & m)
					p0 |= bit;          /* colour 1: dark edge */
			}
			d[row] = (uint16)((uint16)p0 | ((uint16)p1 << 8));
		}
	}
}

static void zh_line(const ZhLine *l, int *next_tile, uint16 *vram)
{
	uint16 *top = vram + kZhMap + l->row * 32;
	uint16 *bot = top + 32;
	int n = 0;
	int start, c, i;

	while (l->text[n] != 0xffff)
		n++;
	start = l->col + (l->width - n * 2) / 2;
	if (start < l->col)
		start = l->col;

	/* Erase the English stripe. Both rows get the font's blank tile so the
	 * panel background behind it is left completely untouched. */
	for (c = 0; c < l->width; c++) {
		top[l->col + c] = kZhSpaceTop;
		bot[l->col + c] = kZhSpaceBot;
	}
	for (i = 0; i < n; i++) {
		int tile = *next_tile;

		if (tile + 4 > kZhBankEnd)
			break;
		*next_tile = tile + 4;
		zh_glyph_tiles(l->text[i], tile, vram);
		c = start + i * 2;
		top[c] = (uint16)(kZhAttr | tile);
		top[c + 1] = (uint16)(kZhAttr | (tile + 1));
		bot[c] = (uint16)(kZhAttr | (tile + 2));
		bot[c + 1] = (uint16)(kZhAttr | (tile + 3));
	}
}

static void zh_screen(const ZhLine *lines, int count, uint16 *vram)
{
	int next_tile = kZhBank;
	int i;

	for (i = 0; i < count; i++)
		zh_line(&lines[i], &next_tile, vram);
}

void ZeldaZhSelectPatch(void)
{
	uint16 *vram = g_zenv.vram;

	if (!g_zenv.ppu || !vram)
		return;
	/* Modules 1..4 are file select, copy, erase and name entry. Every other
	 * module owns a different BG3 layout, so leave its tilemap alone. */
	switch (main_module_index) {
	case 1:
		zh_screen(kLinesSelect, sizeof kLinesSelect / sizeof kLinesSelect[0], vram);
		break;
	case 2:
		zh_screen(kLinesCopy, sizeof kLinesCopy / sizeof kLinesCopy[0], vram);
		break;
	case 3:
		zh_screen(kLinesErase, sizeof kLinesErase / sizeof kLinesErase[0], vram);
		break;
	case 4:
		zh_screen(kLinesName, sizeof kLinesName / sizeof kLinesName[0], vram);
		break;
	default:
		break;
	}
}
