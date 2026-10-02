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
SOLO_PAUSE = 0.7   # 一人語りの段落の間（秒）

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


def _reuse(work: Path, old_lines, new_lines):
    """台本を直したとき、文が同じ台詞の声は作り直さずに使い回す（ElevenLabs の利用枠を守る）。

    声の作業ファイルは「何番目の台詞か」で名前が付く（t_0003.wav など）ので、
    文を1つ足すと後ろが全部ずれて、別の台詞の声が流れてしまう。
    前回の台本と照らし合わせ、同じ文の声を新しい番号へ付け替え、変わった台詞の分は消す。
    """
    if not work.exists():
        return
    old_at = {}
    for i, line in enumerate(old_lines):
        old_at.setdefault(line, []).append(i)
    kinds = (("てらこ先生", "t_{:04d}.wav"), ("ミカ", "m_{:04d}.mp3"))
    staged = []
    for i, line in enumerate(new_lines):
        name = dict(kinds)[line[0]]
        src_i = old_at.get(line, [None]).pop(0) if old_at.get(line) else None
        if src_i is not None and (work / name.format(src_i)).exists():
            tmp = work / ("keep_" + name.format(i))
            (work / name.format(src_i)).rename(tmp)
            staged.append((tmp, work / name.format(i)))
    for f in list(work.glob("t_*.wav")) + list(work.glob("m_*.mp3")):
        f.unlink()                                   # 使わない（中身が変わった）台詞の声は捨てる
    for tmp, dst in staged:
        tmp.rename(dst)
    print(f"声の使い回し: {len(staged)} 件／作り直し: {len(new_lines) - len(staged)} 件")


# ─── 音声 ─────────────────────────────────────────────────
def cmd_voice(date: str) -> int:
    ep = HERE / "episodes" / date
    if cmd_check(date):
        print("検査に通らないので音声は作りません")
        return 1
    voice_script = ep / "work" / "script.voice.txt"
    voice_script.parent.mkdir(parents=True, exist_ok=True)
    new_lines = [(s, to_voice(t)) for s, t in _lines((ep / "script.txt").read_text(encoding="utf-8"))]
    if voice_script.exists():
        _reuse(ep / "work" / "podcast" / ".work" / "script.voice",
               _lines(voice_script.read_text(encoding="utf-8")), new_lines)
    voice_script.write_text("\n\n".join(f"[{s}] {t}" for s, t in new_lines) + "\n", encoding="utf-8")
    sys.path.insert(0, str(NEWS_REPO))
    import podcast_teraco_voice as pv          # Teraco Voice とミカの結合（AIニュースと共用）
    pv.HERE = ep / "work"                      # 台詞ごとの作業ファイルをこの回のフォルダに置く
    # 一人語り（2026-10-02 から）は段落の間を長めにとる。シニアが聞いた内容を飲み込む間。
    # 作り済みの声はそのまま使い回すので、ここを変えても利用枠は使わない。
    lines = _lines((ep / "script.txt").read_text(encoding="utf-8"))
    if all(s == "てらこ先生" for s, _ in lines):
        pv.SIL_SAME = SOLO_PAUSE
        for f in (ep / "work" / "podcast" / ".work" / "script.voice").glob("sil_*.wav"):
            f.unlink()
    # 1本の中で声を混ぜない。ElevenLabs で作った回の続きを、0円の声で作ることはしない。
    engine_file = ep / "work" / "engine.txt"
    engine = "elevenlabs" if pv._eleven() else "free"
    if engine == "elevenlabs":                       # 残りが足りないと共用部品が途中で0円の声に切り替えるので先に見る
        need = sum(len(pv._tidy_for_teraco(t)) for s, t in new_lines if s == "てらこ先生")
        u = pv._eleven()[0].eleven_usage()
        if not u.get("ok") or u.get("limit", 0) - u.get("used", 0) - need < pv.ELEVEN_RESERVE:
            engine = "free"
    before = engine_file.read_text().strip() if engine_file.exists() else engine
    work = ep / "work" / "podcast" / ".work" / "script.voice"
    if before != engine and any(work.glob("t_*.wav")):
        if engine == "free":
            print("！ この回は ElevenLabs（本人の声）で作り始めましたが、いまは ElevenLabs が使えません。"
                  "声が混ざるので止めます。ElevenLabs の設定（声のID・鍵）を確かめてから作り直してください。"
                  "全部を0円の声で作り直すなら work/ を消してから TERACO_VOICE_ENGINE=free で実行。")
            return 1
        for f in work.glob("t_*.wav"):              # 0円の声で作った回を本人の声へ上げるときは全部作り直す
            f.unlink()
    engine_file.write_text(engine + "\n")
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
