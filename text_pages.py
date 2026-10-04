#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文字で読むページ（回ごと）と、言葉の解説ページ・用語集を作る。

  python3 text_pages.py 2026-10-04     # その回の yomu.html と、terms/ 一式を作り直す

AIニュースの用語の部品（ai-news-repo/glossary.py）を借りて使う:
  - 言葉を探して線を引く仕組み（_build_matcher / annotate。各語は1ページに1回だけ）
  - 浮かぶ説明の見た目と動き（TOOLTIP_CSS / TOOLTIP_JS）
      パソコン … 矢印を乗せると短い説明、押すと解説ページ
      スマホ   … 押すと画面の下から説明、「くわしい解説を読む」で解説ページ（押し間違いで移らない）
説明の中身はスマホニュース用の glossary.json（シニア向け）。形は AIニュースの辞書と同じ。
"""
import html
import json
import os
import re
import sys
from datetime import date as _date
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEWS_REPO = Path(os.environ.get("NEWS_REPO") or Path.home() / "Documents/Claude/ai-news-repo")
sys.path.insert(0, str(NEWS_REPO))
import glossary as G   # noqa: E402  AIニュースの用語の部品

GLOSSARY = HERE / "glossary.json"
WEEK = "月火水木金土日"
LIMIT = 60          # 1ページに付ける説明の上限（AIニュースと同じ）


def load_terms() -> dict:
    d = json.loads(GLOSSARY.read_text(encoding="utf-8"))
    return {t["slug"]: t for t in d["terms"] if t.get("status", "published") == "published"}


class Annotator:
    """1ページぶんの注釈。AIニュースの annotate をそのまま使い、データだけ差し替える。"""

    def __init__(self, terms: dict, prefix: str):
        self.terms, self.prefix = terms, prefix
        self.matcher, self.lookup = G._build_matcher(list(terms.values()))
        self.used = set()

    def __call__(self, text: str) -> str:
        return G.annotate(html.escape(text), self.matcher, self.lookup, self.used, LIMIT)

    def assets(self) -> str:
        if not self.used:
            return ""
        data = {s: {"n": self.terms[s]["term"], "r": self.terms[s].get("reading", ""),
                    "s": self.terms[s]["short"], "u": f"{self.prefix}terms/{s}.html"}
                for s in sorted(self.used)}
        return ('<script type="application/json" id="glossary-data">'
                + json.dumps(data, ensure_ascii=False) + "</script>\n" + G.TOOLTIP_JS)


def _date_ja(d: str) -> str:
    y, m, dd = map(int, d.split("-"))
    return f"{m}月{dd}日（{WEEK[_date(y, m, dd).weekday()]}）"


CSS = """
  :root { --bg:#F6F4EE; --card:#fff; --ink:#22251F; --ink2:#55594F; --line:#E2DED2;
          --green:#1E4D3B; --head:#1E4D3B; --orange:#E8792B; --orange-soft:#FCEBDC;
          --accent:#A9481A; --card-bg:#fff; --border:#E2DED2; --text:#22251F; --text-muted:#55594F; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#141915; --card:#1E2420;
          --ink:#ECEDE8; --ink2:#B5B9AE; --line:#333A34; --green:#8CC7A6; --orange-soft:#3A2A1C;
          --accent:#F3A56F; --card-bg:#1E2420; --border:#333A34; --text:#ECEDE8; --text-muted:#B5B9AE; color-scheme:dark; } }
  :root[data-theme="dark"] { --bg:#141915; --card:#1E2420; --ink:#ECEDE8; --ink2:#B5B9AE; --line:#333A34;
          --green:#8CC7A6; --orange-soft:#3A2A1C; --accent:#F3A56F; --card-bg:#1E2420; --border:#333A34;
          --text:#ECEDE8; --text-muted:#B5B9AE; color-scheme:dark; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--ink); font-family:"Zen Kaku Gothic New","Hiragino Sans",sans-serif;
         font-size:19px; line-height:1.9; -webkit-text-size-adjust:100%; }
  header { background:var(--head); color:#fff; padding:20px 16px 18px; text-align:center; }
  header a { color:#fff; text-decoration:none; }
  header .sub { font-size:15px; opacity:.85; }
  header .name { font-size:24px; font-weight:700; line-height:1.3; }
  header .date { margin-top:6px; font-size:16px; }
  main { max-width:680px; margin:0 auto; padding:20px 16px 60px; }
  h1 { font-size:25px; line-height:1.45; text-wrap:balance; }
  .listen { display:flex; align-items:center; justify-content:center; gap:10px; margin-top:16px; padding:15px;
            border-radius:16px; background:var(--orange); color:#fff; font-size:21px; font-weight:700; text-decoration:none; }
  .listen svg { width:26px; height:26px; }
  .hint { margin-top:14px; font-size:16px; color:var(--ink2); background:var(--card); border:1px solid var(--line);
          border-radius:12px; padding:10px 14px; }
  .hint .t { pointer-events:none; }
  h2 { margin:34px 0 8px; font-size:22px; color:var(--green); border-left:6px solid var(--orange); padding-left:10px; text-wrap:balance; }
  article p { margin:12px 0; }
  .t { font-weight:700; }
  .review { background:var(--orange-soft); border-radius:18px; padding:18px 16px; margin-top:34px; }
  .review h2 { margin:0 0 6px; border:0; padding:0; color:var(--ink); }
  .review ol { padding-left:1.4em; font-size:20px; font-weight:700; }
  .review .hw { margin-top:10px; font-size:17px; }
  .src { margin-top:28px; font-size:15px; color:var(--ink2); }
  .src ul { padding-left:1.2em; }
  .src a, .more a { color:var(--green); }
  .more { margin-top:22px; font-size:16px; display:flex; flex-wrap:wrap; gap:8px 18px; }
  .foot { margin-top:28px; text-align:center; font-size:16px; color:var(--ink2); }
  .foot a { color:var(--green); font-weight:700; }
  /* 用語の説明は、シニア向けに AIニュースより文字を大きくする */
  #tip { font-size:17px !important; line-height:1.8 !important; }
  #tip .tip-m { font-size:16px !important; }
  #sheet .tip-n { font-size:21px !important; }
  #sheet .tip-s { font-size:18px !important; color:var(--ink) !important; }
  #sheet .tip-m { font-size:18px !important; padding:14px !important; background:var(--head) !important; }
  /* 解説ページ・用語集 */
  .easy { margin-top:18px; padding:16px; background:var(--card); border:1px solid var(--line); border-left:6px solid var(--orange); border-radius:12px; }
  .lbl { display:block; font-size:14px; font-weight:700; color:var(--ink2); letter-spacing:.06em; }
  .detail { margin-top:22px; }
  .chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
  .chips a { padding:6px 14px; background:var(--card); border:1px solid var(--line); border-radius:999px;
             color:var(--ink); text-decoration:none; font-size:17px; }
  .seen { margin-top:8px; display:flex; flex-direction:column; gap:6px; }
  .seen a { color:var(--green); }
  .cat { margin-top:26px; }
  .list { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:10px; margin-top:8px; }
  .list a { display:block; padding:12px 14px; background:var(--card); border:1px solid var(--line); border-radius:12px;
            text-decoration:none; color:var(--ink); }
  .list .n { font-weight:700; }
  .list .s { font-size:15px; color:var(--ink2); line-height:1.6; }
  :focus-visible { outline:3px solid var(--orange); outline-offset:2px; }
"""

ICON_PLAY = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>'


def _page(title: str, desc: str, header_sub: str, body: str, home: str, tail: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="icon" href="{home}cover.jpg">
<link href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700&display=swap" rel="stylesheet">
<style>{G.TOOLTIP_CSS}{CSS}</style>
</head>
<body>
<header>
  <a href="{home}"><div class="sub">てらこ先生の</div><div class="name">世界一わかりやすい<br>スマホニュース</div></a>
  <div class="date">{header_sub}</div>
</header>
<main>
{body}
  <div class="foot">わからないことは、教室で一緒に確かめましょう。<br>
    <a href="https://lin.ee/9c4pI82">スマホ教室TERACO の公式LINE</a></div>
</main>
{tail}</body>
</html>
"""


def build_yomu(date: str, terms: dict) -> Path:
    ep = HERE / "episodes" / date
    n = json.loads((ep / "notes.json").read_text(encoding="utf-8"))
    ann = Annotator(terms, prefix="../../")
    parts = []
    for line in (ep / "script.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        else:
            m = re.match(r"^\[(?:てらこ先生|ミカ)\]\s*(.+)$", line)
            if m:
                parts.append(f"<p>{ann(m.group(1))}</p>")
    review = "".join(f"<li>{html.escape(r)}</li>" for r in n["review"])
    sources = "".join(f'<li><a href="{html.escape(s["url"])}">{html.escape(s["label"])}</a></li>' for s in n["sources"])
    body = f"""  <h1>{html.escape(n['title'])}</h1>
  <a class="listen" href="./">{ICON_PLAY}<span>音声で聴く</span></a>
  <p class="hint"><span class="t">線が引いてある言葉</span>を押すと、説明が出ます。</p>
  <article>
{chr(10).join(parts)}
  </article>
  <div class="review"><h2>今日のおさらい</h2><ol>{review}</ol>
    <p class="hw"><b>今日やってみること</b>　{html.escape(n['homework'])}</p></div>
  <div class="src"><b>今日の情報のもと</b><ul>{sources}</ul></div>
  <div class="more"><a href="../../terms/">この番組の用語集</a><a href="../../">最新の回へ</a></div>"""
    out = ep / "yomu.html"
    out.write_text(_page(f"{n['title']}｜世界一わかりやすいスマホニュース", n["title"],
                         f"{_date_ja(date)}・第{n['number']}回", body, "../../", ann.assets()), encoding="utf-8")
    return out


def _episodes_mentioning(slug: str) -> list:
    out = []
    for y in sorted((HERE / "episodes").glob("*/yomu.html"), reverse=True):
        if f'data-t="{slug}"' in y.read_text(encoding="utf-8"):
            n = json.loads((y.parent / "notes.json").read_text(encoding="utf-8"))
            out.append((y.parent.name, n))
    return out[:8]


def build_terms(terms: dict):
    d = HERE / "terms"
    d.mkdir(exist_ok=True)
    for slug, t in terms.items():
        ann = Annotator({k: v for k, v in terms.items() if k != slug}, prefix="../")
        name = t["term"] + (f"（{t['reading']}）" if t.get("reading") else "")
        rel = "".join(f'<a href="{r}.html">{html.escape(terms[r]["term"])}</a>' for r in t.get("related", []) if r in terms)
        seen = "".join(f'<a href="../episodes/{dt}/yomu.html">{_date_ja(dt)}　{html.escape(n["title"])}</a>'
                       for dt, n in _episodes_mentioning(slug))
        body = f"""  <h1>{html.escape(name)}</h1>
  <div class="easy"><span class="lbl">ひとことで言うと</span><p>{html.escape(t['short'])}</p></div>
  <div class="detail"><span class="lbl">もう少しくわしく</span><p>{ann(t['detail'])}</p></div>
  {f'<div class="detail"><span class="lbl">いっしょに知りたい言葉</span><div class="chips">{rel}</div></div>' if rel else ''}
  {f'<div class="detail"><span class="lbl">この言葉が出てきた回</span><div class="seen">{seen}</div></div>' if seen else ''}
  <div class="more"><a href="./">用語集へ</a><a href="../">最新の回へ</a></div>"""
        (d / f"{slug}.html").write_text(_page(f"{t['term']}とは｜世界一わかりやすいスマホニュース", t["short"],
                                              "ことばの解説", body, "../", ann.assets()), encoding="utf-8")
    cats = {}
    for t in terms.values():
        cats.setdefault(t.get("category") or "ことば", []).append(t)
    groups = "".join(
        f'<section class="cat"><h2>{html.escape(c)}</h2><div class="list">'
        + "".join(f'<a href="{t["slug"]}.html"><div class="n">{html.escape(t["term"])}</div>'
                  f'<div class="s">{html.escape(t["short"])}</div></a>' for t in sorted(ts, key=lambda x: x.get("reading") or x["term"]))
        + "</div></section>" for c, ts in sorted(cats.items()))
    body = f'  <h1>用語集</h1>\n  <p class="hint">番組に出てきた言葉を、やさしく説明しています。</p>\n{groups}'
    (d / "index.html").write_text(_page("用語集｜世界一わかりやすいスマホニュース", "番組に出てきた言葉の説明",
                                        f"ことば {len(terms)}語", body, "../"), encoding="utf-8")


def build(date: str):
    terms = load_terms()
    p = build_yomu(date, terms)
    build_terms(terms)
    return p


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(build(sys.argv[1]))
