# AGENTS.md — 给 AI/协作者的作业指南

DELTARUNE **Android 移植版**（`org.hndteam.deltarune`，8.5.0-CI，ch0–ch5）的简体中文化工程。
本文件是**工作仓库**（私有）的作业说明：读完它应当能独立重建、修改、验证整个汉化管线，而不必重新踩一遍已经踩过的坑。

公开仓库（只有文本与工具，用于分发）：<https://github.com/cyf112233/DeltaruneAndroidChinese>

---

## 0. 环境与路径

| 东西 | 路径 |
| --- | --- |
| 工作目录（本仓库） | `/media/cyf112233/data/deltarune/work` |
| 移植版原始资源 | `/media/cyf112233/data/deltarune/assets/`（`ch0..ch5.win`、`game.droid`、`chN_lang/`、`vid/`、`mus/`） |
| 好人汉化组 PC 补丁（对照用） | `/media/cyf112233/data/steamgames/steamapps/common/DELTARUNE/chapter{N}_windows/` |
| 好人仓库克隆（对照用） | `/tmp/gm3dr`（`git clone --depth 1 https://github.com/gm3dr/DeltaruneChinese`） |
| UTMT CLI | `utmt/UndertaleModCli.dll`（未入库，自行下载） |
| .NET | `/home/cyf112233/.dotnet/dotnet` |
| Python | `.venv/bin/python`（Pillow） |
| 思源黑体 | `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc` |

**机器限制（很重要）**：内存 7 GB，`msedge`+`node` 常驻占 4~6 GB；`/tmp` 是 3.7 GB 的 tmpfs。
→ 并发上限 **`J=6`**。实测 `J=12` 时渲染阶段被 OOM 杀，**111 个任务全失败**（日志刷 `渲染失败`）。
→ 大文件别往 `/tmp` 写；`/tmp` 写满会让 UTMT 静默写出坏文件（曾经写过一个"看起来 73.8 MB 但读不回来"的 data.win）。

---

## 1. 一条命令重建

```bash
cd /media/cyf112233/data/deltarune/work
./fast_build4.sh 2>&1 | tee /tmp/fb.log     # 约 5~6 分钟
```

六个阶段（脚本里都有 `[时:分:秒] ###` 抬头）：

| 阶段 | 做什么 | 关键脚本 |
| --- | --- | --- |
| A | 出码位表 → 渲染 111 个「字体×章节」图集（6 并发） | `scripts_mt/gen_need.py`、`scripts_mt/build_glyphs.py` |
| B | 每章一个进程一次装完全部字体（含 `game.droid`） | `scripts/InstallAllFonts.csx` |
| C | 替换 `data.win`/`game.droid` 里 STRG 的硬编码中文 | `scripts/PatchHardcodedStrings.csx` |
| D | 好人改图打包 → 导入为纹理页 | `scripts_mt/pack_textures.py`、`scripts/ImportTextures.csx` |
| E | 中文贴图钩子（GML 反编译→替换→重汇编） | `hooks/hooks_ch*.json`、`scripts/PatchCode.csx` |
| E2 | 按**当前字宽**重排 5 章正文（修超宽行、对齐换行数） | `scripts_mt/fix_wrap.py --apply` |
| F | 打包 `Deltarune-zh-assets.zip` | 脚本内联 python |

只重跑某一段的入口：

```bash
# 只重渲染某一章某字体
.venv/bin/python scripts_mt/build_glyphs.py --chapter 1 --chars mt/need_ch1.txt --fonts fnt_main

# 只装字体（每章一个进程）
GL_DIR=$PWD/mt/gl1 CHAPTER=1 FONT_OUT=$PWD/out/ch1_final3.win \
  /home/cyf112233/.dotnet/dotnet utmt/UndertaleModCli.dll load \
  /media/cyf112233/data/deltarune/assets/ch1.win -s scripts/InstallAllFonts.csx

# 只重排文本（改完译文后）
.venv/bin/python scripts_mt/fix_wrap.py --apply
```

---

## 2. 铁律（改之前先读，每条都对应一次事故）

1. **字号表**：`build_glyphs.py` 的 `FONTS` 表 = 好人 `workspace/global/font/fonts.cfg` 的 `char_size` **+2**。
   汉字步进 = `char_size + SHIFT_PAD(=2)`；`fnt_main` 当前 `char_size=14` → 步进 **16px**，一行 `264/16 ≈ 16.5` 个汉字。
2. **偏移一律 `(0,0)`**。好人 `fonts.cfg` 里的 `offset_en/offset_cn` 是给**他们那款汉字**修垂直落差的
   （他们拉丁来自原版点阵字体、汉字来自另一款字体，基线不齐，例如 `fnt_8bit` 是 en(1,4)/cn(2,-4)，差 8px）。
   我们拉丁和汉字**都出自同一套思源**，基线天然一致 → 抄他们的偏移就是把中文整体抬高 2~8px，
   表现就是"中英文高低不齐/字高低间距乱"。
3. **每个字形独占一列，矩形只装自己的墨迹**：`adv = max(char_size+2, ink_w+2)`，`x += adv`。
   曾经把矩形宽度统一成固定值 → 相邻字形墨迹串进来，表现为"每个字右边一抹白"。
4. **精灵画布能装下就绝对不要改画布**：改 `sprite.Width/Height` 会让 `CollisionMasks` 失配，
   UTMT 直接抛 `UndertaleSerializationException: Invalid mask data for sprite`，**整个文件写不出来**
   （ch3 就这么只写出 0.5 MB）。正确做法：按"墨迹对齐"改目标矩形（见 §5）。
5. **换行**：引擎里 `&` 与真换行**完全等价**（`obj_writer_Draw_0` 第 235 行 `thischar == "&" || thischar == "\n"`）。
   断行后若该行出现过 `*`，引擎会自动给续行补 `* `，并按 `hspace*2 = 16px` 计入行宽 →
   排版时续行可用宽度只能是 `264-16`；整条文本里没有 `*` 时不用留。
6. **不要改 `charline` / `hspace`**。字号对齐到好人之后（步进 16 与 14 同量级）引擎换行宽度 264px 够用，
   改宽了英文行会变长、可能溢出对话框。（历史上有过 `PatchCharline.csx`，已废弃。）
7. **贴图钩子走 `global.chemg_sprite_map`**（引擎自带，日语分支在用）：
   `scr_84_get_sprite("spr_xxx")` = `ds_map_find_value(global.chemg_sprite_map, "spr_xxx")`。
   把映射值换成 `spr_zhname_*` 就全局生效，**绝大多数调用点不用动**。
8. **`game.droid` 是独立 data 文件**：启动器（章节选择/FAQ/免责声明/制作名单）读它自己的
   `fnt_maintext`（唯一字体，度量 = em10、拉丁步进 7、页 256×256）。**只打文本补丁不装字体 = 全是方格**。
9. **`fontsrc/ch<章>/font_spec.json` 命名**：脚本按 `fontsrc/ch{chapter}/` 找 spec，
   所以启动器那一"章"必须叫 **`chdroid`**（`fontsrc/chdroid/font_spec.json`），否则渲染全失败。
   码位表命名同理：`mt/need_ch<N>.txt` 或 `mt/need_droid.txt`。
10. **`/tmp` 只有 3.7 GB**，大文件放数据盘；写盘前先看 `df -h /tmp`。

---

## 3. 引擎关键事实（读反编译确认过，别凭感觉）

* **语言**：`scr_84_init_localization()` 里硬编码 `global.lang = "en"`；`scr_84_lang_load()` 读
  `"lang_" + global.lang + ".json"`，但 **ch2 实际读 `ch2_lang/lang_ja.json`**（其余章读 `lang_en.json`）。
* **字体角色** → `global.font_map`（`scr_84_get_font(role)`）。`fnt_ja_*` 是菜单/存档界面硬编码用到的，
  即使语言是 en 也会被引用，所以必须一起做字。
* **换行公式**：`if (current_line_width + char_width) > (charline * hspace)`，
  `charline=33`、`hspace=8` → **264px**；`charline_face=26` → 208px（脸图文字）。
  自动换行时优先在空格处断（`remspace > 2`），否则在字间断，两种都会调 `scr_asterskip()` 补星号。
* **字符串数据块**：`STRG` 里的中文是我们写进去的；`data.win` 有 66 条 EMBI 声音（17.4 MB），
  每章 9 条 `Type=External`（`File=snd_*.ogg`）；安卓 `mus/` 339 个 ogg（**未使用好人的音频**）。
* **贴图页**：新增页 `TextureWidth/Height` 字段留 0 也能正常显示（字体页就是这么加的）；
  页尺寸不必是 2 的幂（我们用 2048×N）。

---

## 4. 字体管线（`scripts_mt/build_glyphs.py`）

照好人 `atlas_packer/generate_font.js` 的做法，字体用思源：

```
face = truetype(TTF, char_size)                 # 逐字体字号，见 FONTS 表
bb   = face.getbbox(ch)                         # 墨迹框
绘制灰度图 → 裁到墨迹框 → tanp = (char_size - bitmapTop) + offset_y
adv  = max(char_size + 2, ink_w + 2)            # 汉字 / 拉丁
每字一列，矩形首尾相接不重叠；整行高度 cell = max(ink_h + top_align) + 2
```

* **抗锯齿**：保留 FreeType 的灰度覆盖度当 alpha（只丢 `<8` 的噪点）。
  早期照好人用 `monochrome:true` 做 1-bit，汉字 12px 下墨宽从 12 缩到 10，"又小又糙"。
* **负 `top_align`**：整行下移 `rowshift` 之后再算 cell，**不要**把那个字压到行顶
  （压顶会让它相对基线跑偏；曾经还因为守卫条件直接把这个字丢掉，表现是 ch4 少一个「、」）。
* **码位来源**：`gen_need.py` 从「游戏最终会读到的全部文本」取：
  `out/ch<N>_lang/lang_en.json` + `zh/cyr/merged_ch<N>.json` + `zh/cyr/merged_droid.json`。
  漏掉任何一处 → 图集缺字。
* **度量对照**（`char_size`，2024 版口径）：

| 字体 | 好人 char_size | 我们（+2） | 备注 |
| --- | --- | --- | --- |
| fnt_main | 12 | **14** | 正文；步进 16 |
| fnt_mainbig | 24 | 26 | 大标题 |
| fnt_8bit | 20 | 22 | 点阵风 |
| fnt_comicsans / fnt_dotumche | 14 | 16 | |
| fnt_legend | 16 | 18 | |
| fnt_tinynoelle | 9 | 11 | 最小 |
| fnt_maintext | — | 14 | **仅 game.droid（启动器）** |

---

## 5. 贴图管线

1. `scripts_mt/pack_textures.py <章>`：把好人 `workspace/ch<N>/imports/pics`、`pics_zhname` 里的改图
   按货架算法打进 2048 宽的页，产 `mt/tex<N>/page_<N>_<k>.png` + `cfg_<N>_<k>.txt`
   （格式与好人一致：`精灵名_帧号,源X,源Y,宽,高,目标X,目标Y,目标宽,目标高`）。
   * 页内矩形**必须无重叠**（脚本后会自检）；`pics` 与 `pics_zhname` 重名取先出现的。
2. `scripts/ImportTextures.csx`：三种情况
   * **尺寸一致** → 只换源矩形（画布、位置、掩码全不动）；
   * **装得下画布** → 只改目标矩形（目标位置由 python 按"墨迹对齐"算好：`tx = 原tx - 图片墨迹左边界`，
     越界就居中兜底）→ origin/掩码不受影响；
   * **比画布大**（1559 张里只有 58 张，都是 funnytext/电视字幕那种长条）→ 只能改画布 + 按比例挪 origin，
     此时若该精灵有碰撞掩码就丢弃并警告。
3. `hooks/hooks_ch<N>.json` + `scripts/PatchCode.csx`：中文贴图钩子（见 §2.7、§6）。

---

## 6. 中文贴图钩子（45 处 / 14 个代码块）

`scripts_mt/make_hooks.py` 从好人代码里抽出所有 `*_zhname_*` 引用，生成三类改动：

1. **映射**（主力）：`scr_84_init_localization` 的非日语分支里
   `ds_map_add(sm, "spr_bnamekris", spr_bnamekris)` → `…, spr_zhname_bnamekris)`，
   缺条目的补一行。覆盖名字条、招牌、电视神秘招牌、Toriel 花字等。
2. **写死精灵名的调用点**：ch2 pipis 敌人/蛋弹幕、ch2 便利店、ch3 酒吧吧台、
   ch3 排行说明图（`set[0]`，编译器会解析成精灵下标）、ch5 便利店 3 处。
3. **结构改动**：ch3 Rouxls 旗子加 `else` 分支；ch1 镇子补一个中文超市招牌标记；
   ch3 沙发视频换成 `tennaIntroF1_zhname_compressed_28`（视频文件已放进 `assets/vid/`，
   按端口习惯用小写文件名 `tennaintrof1_zhname_compressed_28.mp4`）。

**注意**：好人用 `global.names >= 2` 作开关（他们设置项里的"人名汉化"），我们只有中文一套，**无条件**换。

---

## 7. 文本与换行

* `out/ch<N>_lang/lang_en.json` 是章节正文（键来自反编译对象/事件名）；
  `zh/cyr/merged_ch<N>.json`、`merged_droid.json` 是写进 data 文件的硬编码中文。
* **译文来源**：以**好人汉化组的中文**为底，用 DeepSeek 逐条做无上下文、无推理的同义改写
  （逐条完全一致率约 12.6%，≥12 字长句仅 0.85%）。**是派生作品，必须署名**（CC BY-NC-SA 4.0）。
* **换行规则**（`scripts_mt/cmp_wrap.py` 对比、`fix_wrap.py` 修正）：
  * 前后缀换行必须与好人一致（菜单/选项靠行首换行对齐，丢了整体上移一行）；
  * 中段行数尽量对齐（能合就合，不合会溢出就不动）；
  * **单行超 264px 一律拆**（否则引擎自己乱换+补星号）；行尾多余空格先删（引擎算 6px）。
* 当前状态（`char_size=14` 那版之前的统计）：对照好人中文条目 55533 条，
  换行完全一致 98.9%，我们偏多 524 条（其中 448 条合并后必然超 264px，属于译文更长的合理差异），
  单行超 264px **0 条**。重排后要重跑 `cmp_wrap.py` 复核。

---

## 8. 校验门（改完必跑）

| 检查 | 命令 | 期望 |
| --- | --- | --- |
| 图集缺字 | `.venv/bin/python scripts_mt/audit_coverage.py` | 合计缺字 **0** |
| 字体/贴图/字符串体检 | `VerifyFinal2.csx`（见下） | 汉字步进 = char_size+2、字形越界 0、同排重叠 0 |
| 换行对比 | `.venv/bin/python scripts_mt/cmp_wrap.py` | 单行超 264px = 0 |
| 西里尔残留 | `ScanCyrillic.csx` | 0 |
| 钩子精灵存在 | `CheckSprites.csx` + `SPR_LIST=` | 全部存在 |
| 代码钩子落地 | `ShowCode.csx` + `CODE_NAME=` | 能看到 `spr_zhname_*` |
| 包完整性 | `unzip -t Deltarune-zh-assets.zip` | No errors |

```bash
D=/home/cyf112233/.dotnet/dotnet; U=utmt/UndertaleModCli.dll
$D $U load out/ch5_hook.win -s scripts/VerifyFinal2.csx
SPR_LIST=/tmp/want_ch5.txt $D $U load out/ch5_hook.win -s scripts/CheckSprites.csx
CODE_NAME=gml_GlobalScript_scr_84_init_localization $D $U load out/ch5_hook.win -s scripts/ShowCode.csx
```

> `VerifyFinal2.csx` 里的越界检查用 `fo.Texture.TexturePage.TextureData.Image.Width`
> ——新页的 `TextureWidth` 字段是 0，直接用字段会把所有字形判成越界。

---

## 9. 脚本地图

| 脚本 | 作用 |
| --- | --- |
| `scripts_mt/build_glyphs.py` | 渲染图集（字号表 `FONTS`、灰度抗锯齿、逐字独占列） |
| `scripts_mt/gen_need.py` | 生成每章码位表 `mt/need_*.txt` |
| `scripts_mt/audit_coverage.py` | 文本码位 vs 图集覆盖审计 |
| `scripts_mt/pack_textures.py` | 好人改图 → 纹理页 + cfg（墨迹对齐摆放） |
| `scripts_mt/make_hooks.py` | 生成 `hooks/hooks_ch*.json` |
| `scripts_mt/fix_wrap.py` | 按引擎规则重排/修超宽行（`--apply` 才写盘，原件备份 `out/lang_backup_ch*.json`） |
| `scripts_mt/cmp_wrap.py` | 与好人 PC 补丁逐条对比换行数、行宽 |
| `scripts_mt/preview_font.py` | 把图集字形按引擎方式摆出来（肉眼查字号/间距，输出 `preview/*.png`） |
| `scripts/InstallAllFonts.csx` | 一次进程装完一章全部字体 |
| `scripts/ImportTextures.csx` | 导入改图（三种情况见 §5） |
| `scripts/PatchCode.csx` | 按 hooks json 改 GML（反编译→文本替换→CompileGroup 重汇编） |
| `scripts/PatchHardcodedStrings.csx` | 替换 STRG 硬编码字符串 |
| `scripts/VerifyFinal2.csx` | 最终文件体检 |
| `scripts/DumpSpriteIndex.csx` | 导出精灵索引（名字/画布/每帧源矩形）供 python 比对 |
| `fast_build4.sh` | 全量重建入口（A~F） |

---

## 10. 已知未完成 / 风险

1. **真机未验证**：字号 +2、偏移归零、启动器字体这三项改了之后还没在手机上跑过。
2. **ch4/ch5 `obj_room_town_mid` 的中文招牌标记没搬**：好人在 PC 版那段代码里新插了
   `bg_zhname_building_store` 标记并自建图层，移植版这段结构不同（`bg_building_store` 在
   ch4/ch5 的 town_mid 里根本没出现），硬插可能重复绘制。
3. `spr_zhname_green_sign_owe_money*`（ch5 赊账牌）好人没有对应改图，用的还是原图。
4. 换行"我们偏多"的 524 条里，448 条是译文更长导致，只能改译文才能压平。
5. `game.droid` 启动器的中文用 `char_size=14`，字号是否合适只有真机能定。
6. 私有仓库不含 `utmt/`、`sdk/`、`.venv/`、`out/`、资源包（走 Release）。

---

## 11. 协议与署名（不可省）

* 译文与改图均派生自 **[好人汉化组](https://github.com/gm3dr/DeltaruneChinese)** 的
  DELTARUNE 中文本地化补丁，**CC BY-NC-SA 4.0**：
  **署名**（保留本仓库与好人汉化组的署名）、**非商业**、**相同方式共享**。
* 游戏内制作名单（`zh/cyr/merged_droid.json`）已写入署名：
  `中文文本：#好人汉化组 DELTARUNE 中文本地化补丁#（CC BY-NC-SA 4.0，已获协议授权使用）`
  `Android 移植版适配与二改：#cxkcxkckx#https://space.bilibili.com/631040321`
* **音频未使用**好人任何资源；**字体**由本项目从 Noto Sans CJK（思源黑体）自行渲染；
  GML 钩子为本项目自写（仅导入逻辑参考其打包器思路）。
