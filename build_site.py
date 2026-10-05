#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""スマホニュースのサイトを、シリーズ共用のエンジン（ai-news-repo/series/engine.py）で作り直す。

  python3 build_site.py      # 全部（各回のページ・トップ・これまでの回・用語集・サイトの地図）

1回につき1枚のページ（episodes/<日付>/index.html）で、聴く・読むの両方ができる。
旧「文字で読む」ページ（yomu.html）は、新しいページの「文字で読む」へ自動で移すだけのページにする。
番組ごとの見た目・言葉は ai-news-repo/series/shows/sumaho-news.json。
"""
import json
import os
import re
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEWS_REPO = Path(os.environ.get("NEWS_REPO") or Path.home() / "Documents/Claude/ai-news-repo")
sys.path.insert(0, str(NEWS_REPO))
from series import engine as E   # noqa: E402

SHOW = E.load_show("sumaho-news")


def times_from_work(ep: Path) -> list:
    """音声を作ったときの作業ファイル（concat.txt）から、台詞ごとの開始秒を計算する。"""
    lst = ep / "work" / "podcast" / ".work" / "script.voice" / "concat.txt"
    if not lst.exists():
        return []
    t, starts = 0.0, {}
    for line in lst.read_text().splitlines():
        p = Path(line.strip()[6:-1])
        m = re.match(r"p_(\d+)\.wav$", p.name)
        if m:
            starts[int(m.group(1))] = round(t, 2)
        with wave.open(str(p)) as w:
            t += w.getnframes() / w.getframerate()
    n = max(starts) + 1 if starts else 0
    return [starts.get(i) for i in range(n)]


def load_times(ep: Path) -> list:
    """台詞ごとの開始秒。times.json があればそれ、無ければ作業ファイルから計算して times.json に残す。"""
    f = ep / "times.json"
    if f.exists():
        return json.loads(f.read_text())
    ts = times_from_work(ep)
    if ts:
        f.write_text(json.dumps(ts) + "\n")
    return ts


def episode_data(ep: Path, prefix: str, audio: str) -> dict:
    n = json.loads((ep / "notes.json").read_text(encoding="utf-8"))
    times = load_times(ep)
    items, k = [], 0
    for line in (ep / "script.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            items.append({"h": line[3:]})
            continue
        m = re.match(r"^\[(てらこ先生|ミカ|イロハ)\]\s*(.+)$", line)
        if m:
            items.append({"who": m.group(1), "text": m.group(2), "t": times[k] if k < len(times) else None})
            k += 1
    return {"date": ep.name, "number": n["number"], "title": n["title"], "audio": audio,
            "cover": f"{prefix}{SHOW['cover']}", "items": items, "news": n.get("news", []), "lesson": n.get("lesson", ""),
            "review": n.get("review", []), "homework": n.get("homework", ""), "sources": n.get("sources", []),
            "desc": "今日のテーマ：" + n.get("lesson", n["title"])}


def build_all() -> list:
    terms = E.load_terms(HERE / "glossary.json")
    eps = sorted([d for d in (HERE / "episodes").iterdir() if (d / "notes.json").exists() and (d / "audio.mp3").exists()],
                 reverse=True)
    written = []
    meta = []
    for ep in eps:
        page = E.episode_html(SHOW, episode_data(ep, "../../", "audio.mp3"), terms, prefix="../../")
        (ep / "index.html").write_text(page, encoding="utf-8")
        (ep / "yomu.html").write_text(E.redirect_html("./#yomu"), encoding="utf-8")   # 旧「文字で読む」ページ
        n = json.loads((ep / "notes.json").read_text(encoding="utf-8"))
        meta.append({"date": ep.name, "number": n["number"], "title": n["title"]})
        written.append(ep / "index.html")
    if eps:   # トップ＝最新の回（同じページを、トップの位置から開けるように作る）
        latest = eps[0]
        top = E.episode_html(SHOW, episode_data(latest, "", f"episodes/{latest.name}/audio.mp3"), terms, prefix="")
        top = top.replace('href="#yomu"', 'href="#yomu"')
        (HERE / "index.html").write_text(top, encoding="utf-8")
    (HERE / "archive.html").write_text(E.archive_html(SHOW, meta), encoding="utf-8")
    tdir = HERE / "terms"
    tdir.mkdir(exist_ok=True)
    titles = {m["date"]: m["title"] for m in meta}
    keep = set()
    for slug, t in terms.items():
        (tdir / f"{slug}.html").write_text(E.term_html(SHOW, t, terms, titles, HERE), encoding="utf-8")
        keep.add(f"{slug}.html")
    (tdir / "index.html").write_text(E.terms_index_html(SHOW, terms), encoding="utf-8")
    for f in tdir.glob("*.html"):          # 辞書で下書きに戻した言葉のページは消す（作り直せる）
        if f.name != "index.html" and f.name not in keep:
            f.unlink()
    paths = [""] + ["archive.html", "terms/"] + [f"episodes/{m['date']}/" for m in meta] + [f"terms/{s}.html" for s in terms]
    (HERE / "sitemap.xml").write_text(E.sitemap_xml(SHOW, paths), encoding="utf-8")
    (HERE / "robots.txt").write_text(E.robots_txt(SHOW), encoding="utf-8")
    subprocess.run([sys.executable, str(HERE / "make_feed.py")], check=True)
    return written


if __name__ == "__main__":
    for p in build_all():
        print(p)
