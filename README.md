# DELTARUNE 中文本地化（Android 移植版）

本仓库是 **DELTARUNE Android 移植版**（`org.hndteam.deltarune`，8.5.0-CI）的中文本地化**文本与工具**。

> **来源声明**：本项目的译文与贴图来自 **[好人汉化组](https://github.com/gm3dr/DeltaruneChinese)** 的
> DELTARUNE 中文本地化补丁（CC BY-NC-SA 4.0），是非官方派生作品，详见下文「与好人汉化组的关系」。

## 协议 License

本项目（翻译文本与修改后的贴图）使用
**[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans)** 协议许可，
与 **[好人汉化组](https://github.com/gm3dr/DeltaruneChinese)** 的 DELTARUNE 中文本地化补丁**采用同一协议**。

- **署名 BY**：使用/修改请保留本仓库与好人汉化组的署名。
- **非商业 NC**：不得用于商业用途。
- **相同方式共享 SA**：修改后需以相同协议发布。

本仓库对修改后的内容不承担任何责任。

## 与好人汉化组的关系（来源说明）

**本项目是好人汉化组 [DELTARUNE 中文本地化补丁](https://github.com/gm3dr/DeltaruneChinese) 的派生作品**，
依照其 **CC BY-NC-SA 4.0** 协议使用，并在此**明确署名**。具体用了什么：

| 内容 | 来源 | 说明 |
| --- | --- | --- |
| `text/` 下的中文译文 | 好人汉化组译文 | 以其译文为底，用 DeepSeek API 逐条做无上下文、无推理的同语意改写（逐条完全一致率约 12.6%，长句 ≥12 字仅 0.85%）。**是派生作品，不是独立翻译** |
| 修改后的贴图 | 好人汉化组改图 | 直接导入 `data.win`（其仓库 `workspace/*/imports/pics`、`pics_zhname`），未作改动 |
| 字体 | 本项目自行渲染 | 从 [Noto Sans CJK（思源黑体）](https://github.com/notofonts/noto-cjk) 渲染位图图集；渲染方式（字号、步进、基线）照其 `atlas_packer` 的做法实现 |
| 音频 | **未使用** | 不含任何来自好人汉化组的音频 |
| GML 代码 | 本项目自写 | 仅「导入逻辑」参考其打包器思路，未引入其 GML 改动 |

译名体系（人物名保留英文原文、物品/菜单/地名依 DELTARUNE 中文 Wiki 与其既定译法）同样沿用其成果，
以保证玩家在两版汉化之间切换时观感一致。

> **BY**：以任何形式分发本项目的文本或贴图，请保留本仓库与**好人汉化组**的署名，并注明是派生作品。
> **NC**：不得用于商业用途。**SA**：修改后须以 CC BY-NC-SA 4.0 发布。

## 目录结构

```
text/
  ch1/lang_en.json          第 1 章正文（11018 条）
  ch2/lang_en.json          第 2 章正文（13031 条）
  ch2/lang_ja.json          第 2 章的 lang_ja 槽位（移植版从该槽位读取文本）
  ch3/lang_en.json          第 3 章正文（13689 条）
  ch4/lang_en.json          第 4 章正文（14801 条）
  ch5/lang_en.json          第 5 章正文（17367 条）
  ch0/                      第 0 章（启动器/章节选择）为硬编码文本，见 merged_ch0.json
  merged_ch*.json           写进 data.win 的硬编码字符串（中文）
  merged_droid.json         game.droid 的硬编码字符串（启动器 FAQ/免责声明/制作名单）
  hardcoded_all.json        启动器通用硬编码字符串
  ru_en.json / uniq_ru_zh.json   移植版自带的俄文残留 → 中文 对照表
glossary/
  items_zh.json             物品译名（依 DELTARUNE 中文 Wiki）
  glossary_zh.json          地名/角色/术语译名
  base_zh.json              基础词表
tools/                      本地化工具链（下述）
```

## 文本格式

`lang_*.json` 是「键 → 文本」映射，键来自游戏反编译出的对象/事件名。文本里含游戏自己的控制码：

| 记号 | 含义 |
| --- | --- |
| `\n`、`&` | 换行 |
| `%`、`/%`、`%%` | 消息终止符（`%%` 为继续） |
| `^n` | 停顿 n 帧 |
| `\E n` `\M n` `\F n` `\C n` `\I n` `\T n` `\S n` `\c` | 表情 / 说话人 / 字体 / 颜色 / 图标等 |
| `~n` | 变量占位（玩家名、数量等） |
| `#` | 换行（仅硬编码字符串用，与 `\n` 等价） |

**修改译文时必须保留控制码的形状与数量**，尤其终止符——它决定对话是否推进，改错会软锁。

## 工具链 tools/

| 脚本 | 作用 |
| --- | --- |
| `tr_ru_zh.py` / `tr_ru_en.py` | 调用 DeepSeek 逐条翻译残留俄文（无上下文、无推理，固定提示词、temperature 0） |
| `gen_need.py` | 从「游戏最终会读到的全部文本」生成图集所需码位表 |
| `audit_coverage.py` | 审计图集是否覆盖文本全部码位（缺字检测） |
| `build_glyphs.py` | 用思源黑体渲染位图图集（字格、步进、基线、控制码全部由脚本量测） |
| `rewrap.py` | 按引擎实际字宽重新排文本换行（引擎上限 = `charline × hspace`） |
| `PatchHardcodedStrings.csx` | 替换 `data.win` / `game.droid` 里 STRG 块的硬编码字符串 |
| `gml_zh_dy.gml` | 逐字符垂直偏移表（供渲染时使用） |

工具依赖：[UndertaleModTool](https://github.com/UnderminersTeam/UndertaleModTool)（读写 `data.win`）、
Python 3 + Pillow、Noto Sans CJK。

## 已知情况

- 第 0 章（启动器）没有独立语言文件，其界面文字是硬编码在 `ch0.win` / `game.droid` 里的，
  已一并汉化（见 `merged_ch0.json`、`merged_droid.json`）。
- 移植版自带俄文的遗留部分（FAQ、免责声明、制作名单、调试提示、俄语格变化系统）已全部替换为中文；
  人名与团队名按惯例保留原文。
- 字体图集的字格尺寸按引擎实际行为量测，非等比缩放；字号表与好人汉化组 `fonts.cfg` 一致
  （`fnt_main` 汉字步进 14 px），因此**无需**修改引擎换行常数，中英换行与原版补丁对齐。

## 感谢

- **好人汉化组** —— DELTARUNE 中文本地化补丁；本项目的译文（经 DeepSeek 改写）与贴图均派生自其成果，
  并沿用其 CC BY-NC-SA 4.0 协议
- **Hopes&Dreams** —— DELTARUNE Android 移植版
- **Toby Fox / Fangamer** —— DELTARUNE 原作
- DELTARUNE 中文 Wiki —— 专名译法参考
