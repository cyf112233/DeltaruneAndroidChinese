#!/usr/bin/env python3
"""tr_ru_en.py -- 把 data.win 里残留的俄文逐条译成英文（无上下文、无推理）。

只用一次 API 调用/条，提示词固定、不喂上下文、不要求解释，保证输出就是译文本身。
控制码必须原样保留（^n \\X{кап} {пол} ~n[...] % & # 等）。
"""
import json, os, re, sys, time, urllib.request

KEY = os.environ["DS_KEY"]
URL = "https://api.deepseek.com/chat/completions"
W = "/media/cyf112233/data/deltarune/work"
import sys as _sys
_TAG = _sys.argv[1] if len(_sys.argv) > 1 else "uniq_ru"
SRC = f"{W}/zh/cyr/{_TAG}.json"
OUT = f"{W}/zh/cyr/{_TAG}_en.json"

PROMPT = ("Translate the following Russian game string to English. "
          "Output ONLY the translation, no quotes, no explanation. "
          "Keep every control code and placeholder exactly as-is, including "
          "backslash codes like \\E0 \\V1 \\M0, ^ followed by digits, "
          "{{кап}}, {{пол}}[...], ~1[...], the characters % & # (a # is a line "
          "break, keep them all in the same places) and any \\n. "
          "Keep personal names in Latin script.\n\n")


def call(text):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": PROMPT + text}],
        "temperature": 0, "max_tokens": 400,
    }).encode()
    req = urllib.request.Request(URL, body, {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + KEY,
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"].strip()


def main():
    src = json.load(open(SRC, encoding="utf-8"))
    done = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    todo = [s for s in src if s not in done]
    print(f"共 {len(src)} 条，已完成 {len(done)}，待译 {len(todo)}")
    for i, s in enumerate(todo, 1):
        for attempt in range(3):
            try:
                done[s] = call(s)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  失败 {s[:30]!r}: {e}")
                    done[s] = s
                time.sleep(2)
        if i % 25 == 0:
            json.dump(done, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"  {i}/{len(todo)}")
    json.dump(done, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {OUT}  {len(done)} 条")


if __name__ == "__main__":
    main()
