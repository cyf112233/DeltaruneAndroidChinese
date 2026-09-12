#!/usr/bin/env python3
"""tr_ru_zh.py -- 把残留俄文逐条译成中文（无上下文、无推理）。

提示词固定、不喂上下文、不要求解释，保证输出就是译文本身。
控制码一律原样保留：# 是换行标记、\\X 是字体/表情码、^n 是停顿。
人名、团队名、商标保留原文。
用法: tr_ru_zh.py <清单名>   （读 zh/cyr/<名>.json，写 zh/cyr/<名>_zh.json）
"""
import json, os, sys, time, urllib.request

KEY = os.environ["DS_KEY"]
URL = "https://api.deepseek.com/chat/completions"
W = "/media/cyf112233/data/deltarune/work"
TAG = sys.argv[1] if len(sys.argv) > 1 else "uniq_ru"
SRC = f"{W}/zh/cyr/{TAG}.json"
OUT = f"{W}/zh/cyr/{TAG}_zh.json"

PROMPT = ("Translate the following Russian game string into Simplified Chinese. "
          "Output ONLY the translation, no quotes, no explanation. "
          "Keep every control code exactly as-is, including the # characters "
          "(each # is a line break and must stay in the same place), "
          "backslash codes like \\E0 \\V1 \\M0, ^ followed by digits, "
          "{{кап}}, {{пол}}[...], ~1[...] and every \\n. "
          "Keep personal names, team names and trademarks (Cozy Inn, Deltarune, "
          "DualSense, Fangamer, Toby Fox, Hopes&Dreams, NXRune, DocumentsProvider) "
          "in their original Latin spelling.\n\n")


def call(text):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": PROMPT + text}],
        "temperature": 0, "max_tokens": 600,
    }).encode()
    req = urllib.request.Request(URL, body, {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + KEY,
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def main():
    src = json.load(open(SRC, encoding="utf-8"))
    done = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    todo = [s for s in src if s not in done]
    print(f"{SRC}: 共 {len(src)}，已完成 {len(done)}，待译 {len(todo)}")
    for i, s in enumerate(todo, 1):
        for attempt in range(3):
            try:
                done[s] = call(s); break
            except Exception as e:
                if attempt == 2:
                    print(f"  失败 {s[:30]!r}: {e}"); done[s] = s
                time.sleep(2)
        if i % 20 == 0:
            json.dump(done, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"  {i}/{len(todo)}")
    json.dump(done, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {OUT}  {len(done)} 条")


if __name__ == "__main__":
    main()
