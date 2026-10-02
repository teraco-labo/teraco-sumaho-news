#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""世界一わかりやすいスマホニュース：1回分の台本を検査し、音声にする。

  python make_episode.py check 2026-10-02   # 台本の機械検査（40字・「方」・英字残り・繰り返し）
  python make_episode.py voice 2026-10-02   # てらこ先生＝Teraco Voice、ミカ＝edge-tts で音声に

台本 episodes/<日付>/script.txt は**記事版のページにもそのまま載せる**ので、
数字は「2,970円」、名前は「ドコモ MAX」のように読みやすく書く。
声に渡すときだけ、読み替え（漢数字・カタカナ）をかける。

声の部品は AIニュース（~/Documents/Claude/ai-news-repo/podcast_teraco_voice.py）を呼び出して使う。
音量差（てらこ先生をミカより1dB下）も向こうの設定をそのまま使う。
実行は AIニュースの venv（edge-tts 入り）で:
  ~/Documents/Claude/ai-news-repo/venv/bin/python make_episode.py voice 2026-10-02
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEWS_REPO = Path.home() / "Documents/Claude/ai-news-repo"
READINGS = HERE / "readings.json"

# ─── 読み替え ─────────────────────────────────────────────
_DIG = "〇一二三四五六七八九"


def _kanji_num(n: int) -> str:
    """整数を漢数字に（一万未満を4桁ずつ）。十・百・千の前の「一」は付けない。"""
    if n == 0:
        return "ゼロ"
    out = ""
    for unit_big, val in (("億", 10**8), ("万", 10**4), ("", 1)):
        chunk = (n // val) % 10000
        if not chunk:
            continue
        s = ""
        for unit, v in (("千", 1000), ("百", 100), ("十", 10), ("", 1)):
            d = (chunk // v) % 10
            if d:
                s += ("" if (d == 1 and unit) else _DIG[d]) + unit
        out += s + unit_big
    return out


def to_voice(text: str) -> str:
    """記事用の書き方を、声に渡す書き方へ。辞書 → 数字の順。"""
    d = json.loads(READINGS.read_text(encoding="utf-8"))
    for k in sorted((k for k in d if not k.startswith("_")), key=len, reverse=True):
        text = text.replace(k, d[k])
    text = re.sub(r"\d[\d,]*", lambda m: _kanji_num(int(m.group().replace(",", ""))), text)
    return text


# ─── 検査 ─────────────────────────────────────────────────
def _lines(script: str):
    return [(m.group(1), m.group(2).strip()) for m in
            (re.match(r"^\[(てらこ先生|ミカ)\]\s*(.+)$", l.strip()) for l in script.splitlines()) if m]


def cmd_check(date: str) -> int:
    script = (HERE / "episodes" / date / "script.txt").read_text(encoding="utf-8")
    lines = _lines(script)
    problems = []
    seen = set()
    for i, (spk, text) in enumerate(lines, 1):
        for s in re.findall(r"[^。！？]+[。！？]?", text):
            if len(s) > 40:
                problems.append(f"{i}行目 40字超（{len(s)}字）: {s}")
        if re.search(r"(この|その|あの|どの|若い|年配の|ご高齢の|お)方[がはにをもの]", text):
            problems.append(f"{i}行目 人を指す「方」: {text}")
        if text in seen:
            problems.append(f"{i}行目 同じ台詞の繰り返し: {text}")
        seen.add(text)
        v = to_voice(text)
        if re.search(r"[A-Za-z]", v):
            problems.append(f"{i}行目 英字が読み替えられていない: {v}")
        if re.search(r"[㐀-鿿]{1}[们这个说吗呢]|[们这个说吗呢]", text):
            problems.append(f"{i}行目 中国語の混入の疑い: {text}")
    chars = sum(len(t) for _, t in lines)
    est = chars * 0.157 / 60 + len(lines) * 0.45 / 60
    print(f"台詞 {len(lines)} 件・{chars} 字・推定 {est:.1f} 分")
    for p in problems:
        print("  ！", p)
    print("合格" if not problems else f"要修正 {len(problems)} 件")
    return 1 if problems else 0


# ─── 音声 ─────────────────────────────────────────────────
def cmd_voice(date: str) -> int:
    ep = HERE / "episodes" / date
    if cmd_check(date):
        print("検査に通らないので音声は作りません")
        return 1
    voice_script = ep / "work" / "script.voice.txt"
    voice_script.parent.mkdir(parents=True, exist_ok=True)
    voice_script.write_text("\n\n".join(f"[{s}] {to_voice(t)}" for s, t in
                                        _lines((ep / "script.txt").read_text(encoding="utf-8"))) + "\n",
                            encoding="utf-8")
    sys.path.insert(0, str(NEWS_REPO))
    import podcast_teraco_voice as pv          # Teraco Voice とミカの結合（AIニュースと共用）
    pv.HERE = ep / "work"                      # 台詞ごとの作業ファイルをこの回のフォルダに置く
    with open(ep / "work" / "voice.log", "a", encoding="utf-8") as log:
        pv.build(voice_script, ep / "audio.mp3", log)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", str(ep / "audio.mp3")],
                               capture_output=True, text=True).stdout.strip() or 0)
    print(f"できました {ep / 'audio.mp3'}  {dur / 60:.1f}分")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("check", "voice"):
        sys.exit(__doc__)
    sys.exit({"check": cmd_check, "voice": cmd_voice}[sys.argv[1]](sys.argv[2]))
