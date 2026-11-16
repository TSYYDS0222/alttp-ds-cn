# A Link To The Past DS

*The Legend of Zelda: A Link to the Past* Dual Screen port for the Nintendo DS / DS Lite.

<p align="center">
  <img width="1200" alt="alttp" src="docs/images/showcase.jpg" />
</p>

## 简体中文汉化版

本仓库的 [`zh-cn`](https://github.com/TSYYDS0222/alttp-ds-cn/tree/zh-cn) 分支是 [JimmyGlasscock/alttp-ds](https://github.com/JimmyGlasscock/alttp-ds) 的简体中文汉化：游戏逻辑原样保留，只替换对白文本、字库和界面标签。

- **只发布源码**：本仓库和 [Releases](https://github.com/TSYYDS0222/alttp-ds-cn/releases/latest) 都不提供编译好的 `.nds`，因为成品里内嵌了游戏数据。请自备美版 ROM 编译。
- **已汉化**：全部对白与开场故事、设置菜单、按键说明、文件选择 / 复制 / 删除 / 改名界面、下屏装备栏（道具、瓶子、吊坠、水晶、心之碎片、钥匙）。
- **保留英文**：改名界面的 `END` 按钮和拉丁字母表、数字 —— 受卡带原有字母网格限制，改动会挤乱整个页面。标点用英文 `,` `.`。
- **自己编译**：`git clone -b zh-cn`（或下载 Releases 里的源码包），把美版 `zelda3.sfc` 放进 `vendor/zelda3/assets/`，然后 `python3 build.py`（devkitPro + libnds）。
- **汉化实现与踩坑记录**：[`tools/zh/README.md`](tools/zh/README.md)（字库块布局、字符码到字形的映射、UI 点阵字的烘焙方式）。
- **字体与文本来源**：[frilxy/zelda-alttp-3ds-cn](https://github.com/frilxy/zelda-alttp-3ds-cn)（3DS 汉化包 `zh.bps`），汉化作者 [sxunix/zelda3](https://github.com/sxunix/zelda3)。

以下为上游英文说明。

ALTTP DS is a port of [snesrev/zelda3](https://github.com/snesrev/zelda3), a C reimplementation of the SNES game. The game logic runs natively on the DS's ARM9. The game has been optimized for the DS hardware, and has options to use the touchscreen for the HUD and map.

> **You supply the ROM.** This repo contains no Nintendo ROM and no game assets. Put a legally obtained USA `zelda3.sfc` in `vendor/zelda3/assets` and run `build.py`. This project is not affiliated with or endorsed by Nintendo.

## Features

### A native port

- **Full game.** The entire game is playable, running zelda3's reimplemented game logic.
- **Optimized for DS screen size.** The SNES picture is 224 lines and the DS screen is 192. The overworld and dungeon cameras scroll a little past room and area edges, so Link and the action stay in view.
- **Lid handling.** Closing the DS lid pauses the game.

### Bottom-screen HUD and touch controls

Set **HUD** to **Bottom Screen** in Settings and the status bar moves off the top screen, so the whole top screen is the game. The bottom screen then shows:

- Hearts, magic meter, rupee, bomb and arrow counters, and the equipped item.
- A **live map**: the world map outdoors and the dungeon map inside a dungeon. It stays black in caves and houses.
- An **Items** button, which opens and closes the game's item menu.
- A **Gear** button, which opens a panel with your equipment, bottles, pendants, crystals, hearts, and heart pieces.
- **Touch to equip.** Tap an item on the item panel to equip it.

When no game is running (title, file select, boot), the bottom screen shows a Triforce idle picture.

### Quality-of-life additions

- **Settings menu.** Open it by pressing select (see [Settings](#settings)).
- **Title skip.** Pressing a button during the intro jumps to the sword drop, just like the GBA version.
- **Fast dialogue.** Hold **A** to fast forward through cutscene dialogue.

### Settings

Press **Select** in game to open the save menu. It has three rows: **Continue**, **Save and Quit**, and **Settings**. Settings are saved in your `.sav` file.

| Setting | Options | What it does |
|---|---|---|
| HUD | Top Screen / Bottom Screen | Where the HUD lives (life, magic meter, etc) |
| Low HP Indicator | On / Off | The low-health beep |
| Spawn | Normal / Dungeon | A save made inside a dungeon loads at that dungeon's entrance |
| Magic Mirror | Normal / Free | Removes magic mirror use restrictions |
| Bomb Capacity | 10 / 99 | Maximum bombs you can carry |
| Arrow Capacity | 30 / 99 | Maximum arrows you can carry |
| Run Speed | Normal / Double / Triple | How fast Link walks, dashes, and swims |
| Dark Rooms | Normal / Bright | Bright keeps dark rooms lit, so the lantern is optional |
| Hair Color | Pink / Blonde | Link's hair color |
| Button Mapping | | Allows you to remap the controls |

## Controls
You can remap the controls however you like in the settings menu.

## Getting started

### What you need

- A legally obtained **USA** *A Link to the Past* ROM, named `zelda3.sfc`.
  SHA-256: `66871d66be19ad2c34c927d6b14cd8eb6fc3181965b6e517cb361f7316009cfb`
- [devkitPro](https://devkitpro.org/) with the **nds-dev** group: libnds 2.0, libfat, calico, and ndstool. On macOS and Linux, after the installer:

  ```sh
  sudo dkp-pacman -S nds-dev
  ```

  On Windows, select nds-dev in the installer, or run `dkp-pacman -S nds-dev` from a devkitPro shell. `build.py` looks at `DEVKITPRO`, then `C:\devkitPro` or `/opt/devkitpro`, then `~/devkitpro`. Set `DEVKITPRO` if you installed it somewhere else.
- [Python 3.8](https://www.python.org/) or newer, with `Pillow` and `PyYAML`. Homebrew Python blocks a normal `pip install`, so from the project root:

  ```sh
  python3 -m venv .venv
  .venv/bin/pip install Pillow PyYAML
  ```

  On Windows: `py -3 -m venv .venv`, then `.venv\Scripts\pip install Pillow PyYAML`. `python3 build.py` uses that `.venv` when the Python on `PATH` does not already have those libraries. On a very new Python, PyYAML may compile from source. On macOS that needs the Xcode command line tools (`xcode-select --install`).
- Git.
- To run it: [melonDS](https://melonds.melonemu.org/), or a DS, DS Lite, or DSi with a DLDI flashcart or Twilight Menu++.

### 1. Clone

This Chinese branch vendors the zelda3 sources directly, so no submodule checkout is needed:

```sh
git clone -b zh-cn https://github.com/TSYYDS0222/alttp-ds-cn.git
cd alttp-ds-cn
```

The upstream port is [JimmyGlasscock/alttp-ds](https://github.com/JimmyGlasscock/alttp-ds).

### 2. Add your ROM

Copy `zelda3.sfc` to `vendor/zelda3/assets/`.

### 3. Build

From the project root:

```sh
python3 build.py
```

On Windows, `py build.py` does the same thing. Either command uses `.venv` when the default Python is missing Pillow or PyYAML. `python3 build.py -j8` compiles in parallel. When it finishes, **`lttp-ds.nds`** is in the project root. If `zelda3.sfc` is missing, the build stops and does not write that file. Double-clicking `build.py` on Windows leaves the window open so you can read the error.

### 4. Run

`lttp-ds.nds` is generated with the game data inside it. If that data is not from a USA ROM, the bottom screen says `Invalid assets file` and the game waits there.

## Simplified Chinese build

This branch adds a Simplified Chinese translation; see `tools/zh/README.md` for the full notes. Build with:

```sh
python3 tools/zh/build_zh.py --rom path/to/zelda3.sfc
```

`tools/zh/zh.bps` (the translated dialogue and font pack) is **not committed**: download it from the [frilxy/zelda-alttp-3ds-cn](https://github.com/frilxy/zelda-alttp-3ds-cn) releases and put it in `tools/zh/` before building. The ROM and all extracted assets are likewise not in this repository.

## Saves

- On a flashcart the save is an 8 KB `.sav` in TWiLight Menu++'s save location, named after the ROM. It holds the three game slots and your Settings. melonDS folder sync still writes `lttp-ds.sav` in the synced folder.
- Settings are stored in unused space past the save slots, so they travel with the file.
- A save from an older build at the card root, or in `saves/sram.dat`, is still read and written to that location on the next save.

## Not included

These zelda3 extras are left out on purpose, because the DS cannot run them or has no use for them: shaders, widescreen, 240-line mode, hi-res Mode 7, MSU-1 / Opus audio, OpenGL, and the ROM comparison mode.

## Project layout

```
alttp-ds/
  vendor/zelda3/        game logic, PPU and audio code (vendored sources)
  platform/nds/
    source/             ARM9: host, video, HUD, map, save, audio
    arm7/               ARM7: sound-channel driver
    bottom-screen/      HUD artwork (PNG + grit)
    include/            stubs that replace SDL / Opus
    prepare_assets.py   reads vendor/zelda3/assets/zelda3.sfc and stages the game data for the link
  build.py, Makefile    build. The game data is linked into lttp-ds.nds
```

## Credits

- [snesrev/zelda3](https://github.com/snesrev/zelda3) and its contributors, for the C reimplementation, the asset tool, and the PPU and DSP code this port builds on.
- [JimmyGlasscock/alttp-ds](https://github.com/JimmyGlasscock/alttp-ds), the NDS port this repository is forked from.
- [frilxy/zelda-alttp-3ds-cn](https://github.com/frilxy/zelda-alttp-3ds-cn), for the Simplified Chinese translation and the 16x16 font pack (`zh.bps`) used by this branch.
- [sxunix/zelda3](https://github.com/sxunix/zelda3) — 汉化作者 (the Chinese translation author); the CJK text rendering in this branch follows that work.
- [zelda-alttp-3ds](https://github.com/EstebanPdN/zelda-alttp-3ds) I based much of my UI off the designs in this port.
- [devkitPro](https://devkitpro.org/), libnds, and Calico, for the DS toolchain.
- [melonDS](https://melonds.melonemu.org/), for the emulator used throughout development.

*The Legend of Zelda* and *A Link to the Past* are trademarks of Nintendo. No Nintendo code or assets are distributed with this project.
