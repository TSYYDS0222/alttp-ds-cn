# 中文化（简体中文）说明

`alttp-ds` 是 zelda3 重制工程的 NDS 移植（ARM9 原生运行游戏逻辑）。本目录把它
接到 3DS 汉化版（frilxy/zelda-alttp-3ds-cn）的中文数据与文字渲染上。

## 中文是怎么工作的

原版卡带的文本引擎只能画卡带自带的 8×16 字母字库，画不了 16×16 汉字。所以
3DS 汉化版把中文做成一个"语言包"（pack），并在 BPS 补丁里把 pack 追加到美版
ROM 后面：

```
0 .. 0x100000   美版 ROM（未改动）
之后            'ZCNB' + u32 对白块长度 + 对白块 + u32 字模块长度 + 字模块
最后            'ZCNP' + u32 pack 长度
```

- **对白块**：397 条消息，字形用"页字节 + 序号"两个字节表示（页 0xf0..0xf4，
  每页 256 个字形，共 1280 个位置，实际用了 1163 个字形）。
- **字模块**：256 个 8×16 字母图块（4096 字节）+ 1163 个 16×16 字形（每个 64
  字节）+ 1274 个宽度字节（99 个字母宽度 + 每个字形一个）。

引擎侧只需要三处改动（见 `vendor/zelda3/src/messaging.c` 与
`vendor/zelda3/src/dialogue_cjk.c`，后者与 3DS 版逐字节相同）：

1. `Text_DecodeCmd`：页字节 + 序号 → 字形编号；
2. `Text_LoadCharacterBuffer`：页字节不能被当成"词典引用"吞掉（0x88 以上原本是
   词典索引），要原样透传；
3. `VWF_RenderSingle`：字形走 16×16 渲染（`DialogueCjk_Render`），不查 99 字母
   宽度表。

NDS 版没有 romfs，资源是构建时用 restool 从 ROM 抽出 `zelda3_assets.dat` 再
incbin 进 .nds 的，所以中文是以"替换资源里的语言表"的方式进去的：
`inject_zh_assets.py` 把 assets 94/95/96（对白、字模、语言表）换成一个只有中文
的条目（flags = 0xf）。NDS 分支的 `ZeldaSetLanguage(NULL)` 没有"取第一条语言"的
回退逻辑（会退回卡带自带的 flags = 0），所以 `platform/nds/source/zelda_host.c`
里改成显式 `ZeldaSetLanguage("zh")`。这一行是必须的：漏掉它汉字会被当成字母画出
一堆乱码。

## 构建

前提：devkitPro（含 `nds-dev`：libnds 2.0、libfat、calico、ndstool）与
Python 3.8+（Pillow、PyYAML）。

```
python tools/zh/build_zh.py --rom "path/to/zelda3.sfc"
```

工具会：打补丁 → 取 pack → 抽资源（首次）→ 注入中文 → 编译，产出
`lttp-ds.nds`。只想看前四步加 `--no-build`。

## 数据来源

`zh.bps` 取自 3DS 汉化版发布包（`zelda3-3ds-v4.1.7.3dsx` 内 romfs 的
`languages/zh.bps`），只包含翻译文本与字模，不含任何 ROM 数据；补丁头部记录了
美版卡带的 CRC32（0x777aac2f），换别的 ROM 会拒绝。翻译与字模版权归
frilxy/zelda-alttp-3ds-cn 及其译者，引擎代码仍是 zelda3 的 MIT 许可。

## 字母字库与标点的一个坑

3DS 汉化包自带一套拉丁字库，把一段槽位改成了中文标点：「，」占 code `0x5f`
（tile `0xaf`），「。」占 code `0x60`。而卡带的改名界面字母表恰好按 tile 索引
把 `0xaf` 当字母 **I** 用 —— 这就是 I 显示成逗号的根因。

只把字库换回美版并不够：对白里那些 `0x5f`/`0x60` 会变成字母。最终做法是两件事
一起做：

1. 字库数据区前 4096 字节整体换回美版原版（CJK 字形从偏移 4096 开始，宽度表
   是独立块，都不动），I 与小写字母全部回来。
2. 对白文本里把 `0x5f`/`0x60` 换成卡带自己的英文标点码。**这个引擎不用 ASCII**：
   字形 tile 是 `(code & 0x70) * 2 + (code & 0xf)`，所以 `,` 是 `0x42`（tile
   `0x82`）、`.` 是 `0x41`（tile `0x81`）；写成 ASCII 的 `0x2c`/`0x2e` 会画成
   字母 `s` 和 `t`。CJK 页字节后面的字形序号跳过不动。

改名界面字母表里的 `.` `,` 两格本来就指向 `0x81`/`0x82`，字库换回美版后自动
显示为英文标点，不需要额外覆盖。

同理，汉化对白里的 `[` `]` 用 `0x5b`/`0x5d`，而这两格在美版字库和汉化包里都是
没填充的实心块（「按 A 键」这类提示里会看到黑方块）。`draw_brackets()` 在换回
美版字库后往这两个槽位直接画 8×16 的方括号，不改对白字节。

`tools/zh/preview_msg.py` 可以把某条对白按引擎的字形布局画成 PNG，不用模拟器
就能检查标点和汉字：

```sh
python tools/zh/preview_msg.py zelda3_assets.dat 16 line16.png 4
python tools/zh/preview_msg.py zelda3_assets.dat --list-brackets
```

## 界面文案（设置 / 按键映射）

投影片层（`settings_draw`、`buttons_draw`）原本用卡带的 8×16 字母字库画英文。汉字
走不了那条路，所以另做一套：

- `tools/zh/make_ui_font.py` 用任意 CJK TTF 现场烘焙 16×16 点阵（左对齐、按实际
  笔画宽度定宽，数字不会拖着空格），生成 `platform/nds/include/zh_ui_font.h` 和
  `platform/nds/source/zh_ui_font.c`（76 个字、47 条文案）。
- `platform/nds/source/zelda_video.c` 增加 `ZeldaVideoMenuTextZh` /
  `ZeldaVideoMenuWidthZh`，从这套点阵画字；`ZeldaVideoMenuText`（字母）保留。
- `platform/nds/source/zelda_host.c` 的标签/选项表改成指向中文数组，列宽按中文
  最宽行重新计算。

改文案只要改脚本里的 `TEXTS` 表再跑一次：

```
python tools/zh/make_ui_font.py --ttf D:/tsyyds/SpaceCadetPinball/DreamHanSans.ttf
```

## 文件选择 / 改名界面

这几屏的文字也不在 397 条对白里，而是 BG3 的 tilemap 条带：主 / 复制 /
删除三屏的条带是 `vendor/zelda3/src/select_file.c` 里的常量表，改名屏的
条带是资源 100。BG3 用 2bpp 8×8 tile（VRAM 字地址 0x7000 起）和 0x6000 的
tilemap；英文字母是上下两半各一个 tile，调色板 6。

`platform/nds/source/zh_select.c` 在每帧 PPU 呈现前做两件事：

1. 把 16×16 中文字形写进空闲的 BG3 tile 0x160..0x1ff（VRAM 0x7b00 起；
   字库占 0x7000..0x77ff，界面图形占 0x7800..0x7aff），一个字四个象限 tile；
2. 用空格 tile 清掉英文条带，再把上下两行 tilemap 指向这四个 tile。

字形用两个位面画成「白色主体 + 深色描边」：plane 1 是白色（调色板第 2 色），
plane 0 是主体之外一圈的深色描边（第 1 色）。两者互斥，因此不会出现会发红的
第 3 色。调用点在 `ZeldaVideoComposeSprites()`，排在游戏自己每帧重传英文
条带之后，所以不会被覆盖。

译文对应关系：PLAYER SELECT→选择存档、COPY FILE→复制文件、ERASE FILE→删除
文件、COPY PLAYER→复制玩家、ERASE PLAYER→删除玩家、QUIT→退出、
REGISTER YOUR NAME→请输入玩家姓名、删除确认问句→要删除哪位玩家 / 确认删除。
改名界面字母表里的 END 保留英文：它夹在字母网格中间，一个 16×16 汉字要占
两行 tile，会把网格挤乱。

## 下屏装备栏

`zelda_bottom.c` 的五个标签原本用 5×7 英文小字库现画，GEAR / ITEMS / LIFE
是三张 PNG 位图。现在都改用 `zh_ui_font` 的 16×16 点阵：标签整体上移 6px，
正好占满「标签行到图标行」之间的 16 行，用原始点阵不缩放；面板标题按 12 行
降采样，缩放时对一个目标像素覆盖的所有源像素取或，避免细笔画被采样丢弃。

## 仍是英文的部分

- 改名界面的字母表与 END：玩家自己输入名字，保留拉丁字母、标点与该按钮
- 存档框的序号、心数、HUD 图标等数字与图形
- 复制 / 删除两屏按同一套机制汉化，条带坐标已按源码核对，但这两屏未在
  实机上单独截图确认（无头仿真里 START 没能从「复制文件 / 删除文件」切进去）

改文案统一改 `tools/zh/make_ui_font.py` 的 `TEXTS` 表再跑一次生成脚本。

## 开源发布前要注意

- 上游 `JimmyGlasscock/alttp-ds` 根目录没有 LICENSE：再分发整个工程前要先
  向原作者确认授权，或在自己的 fork 里补一份 LICENSE。`vendor/zelda3` 是
  snesrev / elzo_d 的 MIT（见 `vendor/zelda3/LICENSE.txt`），引擎代码沿用该许可。
- `tools/zh/zh.bps` 取自 `frilxy/zelda-alttp-3ds-cn` 的发布包，翻译与字模的
  版权归原译者；仓库的 `.gitignore` 也忽略了 `*.bps`，所以它默认不会进
  git。发布前要么取得原汉化项目的再分发许可并显式加入仓库，要么把它从仓库
  移除、在构建说明里写「自行从该项目的 release 下载后放到 tools/zh/」。
- 不要提交美版 ROM、`zelda3_assets.dat`、`*.nds` / `*.elf` / `*.o` 等构建产物，
  `.gitignore` 已覆盖；构建脚本在缺少 assets 时会用 restool 从 ROM 现场抽取。
- `vendor/zelda3` 是子模块，本工程改了 `src/messaging.c` 并新增
  `src/dialogue_cjk.c/h`。开源时把这三点提交到自己的 zelda3 fork，并在
  `.gitmodules` 里把 URL 指向该 fork，否则别人拉不到中文渲染代码。
