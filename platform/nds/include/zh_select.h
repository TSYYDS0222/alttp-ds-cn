#pragma once

/* Rewrite the file-select / name-entry text with 16x16 Chinese glyphs.
 * Call once per frame, after the game has run but before the PPU is
 * presented: the game itself keeps uploading BG3 stripes every frame. */
void ZeldaZhSelectPatch(void);
