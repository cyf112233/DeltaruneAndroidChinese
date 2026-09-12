# DELTARUNE 中文本地化（Android 移植版）· 派生文本

本仓库是 **DELTARUNE Android 移植版**（`org.hndteam.deltarune`，8.5.0-CI，ch0–ch5）简体中文化的
**文本数据**。仅供查阅与二次利用，**不含**工具链、字体图集、贴图资源。

## 来源声明（先看这个）

**本仓库的译文是[好人汉化组](https://github.com/gm3dr/DeltaruneChinese) DELTARUNE 中文本地化补丁的派生作品。**

| 内容 | 来源与方式 |
| --- | --- |
| `text/ch*/lang_en.json`（正文） | 以**好人汉化组的译文**为底，用 DeepSeek API 逐条做无上下文、无推理的同义改写（逐条完全一致率约 12.6%，≥12 字长句仅 0.85%）。**是派生作品，不是独立翻译** |
| `text/merged_*.json`（写进 data 文件的硬编码中文） | 同上，含启动器 FAQ / 免责声明 / 制作名单 |
| `text/ru_en.json`、`uniq_ru_zh.json` | 移植版自带俄文残留 → 中文对照（移植版特有部分） |

译名体系（人物名保留英文原文、物品/菜单/地名依 DELTARUNE 中文 Wiki 与好人汉化组的既定译法）同样沿用其成果。

> 游戏内制作名单（`text/merged_droid.json`）已写入署名：
> `中文文本：#好人汉化组 DELTARUNE 中文本地化补丁#（CC BY-NC-SA 4.0，已获协议授权使用）`

## 协议 License

**[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans)**，与好人汉化组补丁同协议。

- **署名 BY**：任何形式的分发/修改，都必须保留**好人汉化组**与本移植版适配者的署名，并注明是派生作品。
- **非商业 NC**：不得用于商业用途。
- **相同方式共享 SA**：修改后须以相同协议发布。

**本项目未使用好人汉化组的任何音频资源**；字体由管线从 Noto Sans CJK（思源黑体）自行渲染；
游戏资源（`ch0..ch5.win`、`game.droid`）与构建工具链不在本仓库。

## 目录

```
text/
  ch1…ch5/lang_en.json          各章正文（键 → 文本）
  ch2/lang_ja.json              第 2 章实际读取的语言槽位（移植版 ch2 读 lang_ja）
  merged_ch0.json               第 0 章（启动器）硬编码文本
  merged_ch1/ch3/ch4/ch5.json   写进对应 data.win 的硬编码文本
  merged_droid.json             game.droid 的硬编码文本（FAQ/免责声明/制作名单）
  hardcoded_all.json            启动器通用硬编码字符串
  ru_en.json / uniq_ru_zh.json  俄文残留 → 中文对照
```

## 文本里的控制码（改动时必须原样保留）

| 记号 | 含义 |
| --- | --- |
| `\n`、`&` | 换行（引擎里两者**完全等价**） |
| `%`、`/%`、`%%` | 消息终止符（`/%` 等按键，`%%` 继续） |
| `^n` | 停顿 n 帧 |
| `\E n` `\M n` `\F n` `\C n` `\I n` `\T n` `\S n` `\cX` | 表情 / 说话人 / 字体 / 颜色 / 图标等 |
| `~n` | 变量占位（玩家名、数量等） |
| `#` | 换行（仅硬编码字符串用，与 `\n` 等价） |

**终止符的形状与数量绝不能改错**——它决定对话是否推进，改错会软锁。

本仓库的文本已按引擎换行规则重排过：一行上限 `charline(33) × hspace(8) = 264px`，
接在换行后面的行还要给引擎自动补的 `* ` 留 16px；重排后单行超 264px 的只剩个位数。
