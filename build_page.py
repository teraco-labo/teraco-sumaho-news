#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""押すだけ再生のページ（記事版つき）を作る。

  python3 build_page.py 2026-10-02

入力: episodes/<日付>/script.txt（台本）・notes.json（題名・注釈・情報のもと）・audio.mp3
出力: episodes/<日付>/index.html（その回のページ）と、いちばん上の index.html（最新回＝LINEのボタンの行き先）

台詞ごとの開始時刻は、音声を作ったときの作業ファイル（concat.txt）から計算する。
これで「いま話しているせりふに色がつく」「せりふを押すとそこから聴ける」ができる。
"""
import html
import json
import re
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEEK = "月火水木金土日"


def _timings(ep: Path) -> dict:
    """台詞番号 → 開始秒。音声の作業ファイルが無ければ空（色づけ無しで表示）。"""
    lst = ep / "work" / "podcast" / ".work" / "script.voice" / "concat.txt"
    if not lst.exists():
        return {}
    t, out = 0.0, {}
    for line in lst.read_text().splitlines():
        p = Path(line.strip()[6:-1])
        m = re.match(r"p_(\d+)\.wav$", p.name)
        if m:
            out[int(m.group(1))] = round(t, 2)
        with wave.open(str(p)) as w:
            t += w.getnframes() / w.getframerate()
    return out


def _annotate(text: str, terms: dict, used: set):
    """台詞の中で、まだ説明していない言葉に印を付ける。長い言葉を優先し、重ならないようにする。"""
    spans = []
    for term in sorted(terms, key=len, reverse=True):
        if term in used:
            continue
        i = text.find(term)
        if i < 0 or any(a < i + len(term) and i < b for a, b, _ in spans):
            continue
        spans.append((i, i + len(term), term))
        used.add(term)
    spans.sort()
    out, pos = "", 0
    for a, b, term in spans:
        out += html.escape(text[pos:a]) + f'<b class="term">{html.escape(term)}</b>'
        pos = b
    out += html.escape(text[pos:])
    notes = "".join(f'<div class="note"><span class="note-k">ことば</span><b>{html.escape(t)}</b>　{html.escape(terms[t])}</div>'
                    for _, _, t in spans)
    return out, notes


def build(date: str) -> Path:
    ep = HERE / "episodes" / date
    meta = json.loads((ep / "notes.json").read_text(encoding="utf-8"))
    times = _timings(ep)
    y, m, d = map(int, date.split("-"))
    import datetime as _dt
    wd = WEEK[_dt.date(y, m, d).weekday()]
    date_ja = f"{m}月{d}日（{wd}）"

    body, used, idx = [], set(), 0
    for line in (ep / "script.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            if body:
                body.append("</section>")
            body.append(f'<section class="part"><h3>{html.escape(line[3:])}</h3>')
            continue
        mm = re.match(r"^\[(てらこ先生|ミカ)\]\s*(.+)$", line)
        if not mm:
            continue
        spk, text = mm.groups()
        cls = "t" if spk == "てらこ先生" else "m"
        txt, notes = _annotate(text, meta["terms"], used)
        start = times.get(idx)
        attr = f' data-t="{start}"' if start is not None else ""
        body.append(f'<div class="line {cls}"{attr}><div class="who">{spk}</div><p>{txt}</p>{notes}</div>')
        idx += 1
    body.append("</section>")

    review = "".join(f"<li>{html.escape(r)}</li>" for r in meta["review"])
    sources = "".join(f'<li><a href="{html.escape(s["url"])}">{html.escape(s["label"])}</a></li>' for s in meta["sources"])
    news = "".join(f"<li>{html.escape(n)}</li>" for n in meta["news"])
    audio_rel = "audio.mp3"
    page = TEMPLATE.format(
        title=html.escape(meta["title"]), date_ja=date_ja, num=meta["number"],
        news=news, lesson=html.escape(meta["lesson"]), review=review,
        homework=html.escape(meta["homework"]), sources=sources,
        body="\n".join(body), audio="{AUDIO}")
    (ep / "index.html").write_text(page.replace("{AUDIO}", audio_rel), encoding="utf-8")
    # いちばん上の index.html ＝ 最新回（LINE のボタンはここを開く）
    top = page.replace("{AUDIO}", f"episodes/{date}/{audio_rel}").replace('href="../../cover.jpg"', 'href="cover.jpg"')
    (HERE / "index.html").write_text(top, encoding="utf-8")
    return ep / "index.html"


TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>世界一わかりやすいスマホニュース</title>
<meta name="description" content="{title}">
<link rel="icon" href="../../cover.jpg">
<link href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700&display=swap" rel="stylesheet">
<style>
  :root {{ --bg:#F6F4EE; --card:#fff; --ink:#22251F; --ink2:#55594F; --line:#E2DED2;
          --green:#1E4D3B; --green2:#163A2C; --orange:#E8792B; --orange-soft:#FCEBDC;
          --teach:#E6F0EA; --mika:#FFF3E8; --now:#FFE7A8; --note:#fff; --head:#1E4D3B; }}
  @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141915; --card:#1E2420; --ink:#ECEDE8;
          --ink2:#B5B9AE; --line:#333A34; --green:#8CC7A6; --orange-soft:#3A2A1C; --teach:#1F3229; --mika:#3A2A1C;
          --now:#5C4A12; --note:#141915; color-scheme:dark; }} }}
  :root[data-theme="dark"] {{ --bg:#141915; --card:#1E2420; --ink:#ECEDE8; --ink2:#B5B9AE; --line:#333A34;
          --green:#8CC7A6; --orange-soft:#3A2A1C; --teach:#1F3229; --mika:#3A2A1C; --now:#5C4A12; --note:#141915;
          color-scheme:dark; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--ink); font-family:"Zen Kaku Gothic New","Hiragino Sans",sans-serif;
         font-size:19px; line-height:1.75; -webkit-text-size-adjust:100%; }}
  header {{ background:var(--head); color:#fff; padding:22px 16px 20px; text-align:center; }}
  header .sub {{ font-size:15px; opacity:.85; }}
  header h1 {{ font-size:27px; font-weight:700; line-height:1.3; }}
  header .date {{ margin-top:8px; font-size:17px; }}
  main {{ max-width:640px; margin:0 auto; padding:0 16px 60px; }}
  .player {{ background:var(--card); border:2px solid var(--line); border-radius:20px; padding:18px 16px;
            margin-top:-2px; position:sticky; top:env(safe-area-inset-top, 0px); z-index:5; box-shadow:0 4px 14px rgba(0,0,0,.06); }}
  .ttl {{ font-size:18px; font-weight:700; line-height:1.45; }}
  .btn {{ display:flex; align-items:center; justify-content:center; gap:12px; width:100%; margin-top:12px;
         padding:18px; border:none; border-radius:16px; background:var(--orange); color:#fff;
         font-size:24px; font-weight:700; font-family:inherit; cursor:pointer; }}
  .btn svg {{ width:30px; height:30px; }}
  .row {{ display:flex; align-items:center; gap:10px; margin-top:12px; }}
  .back {{ flex:none; border:2px solid var(--line); background:var(--card); border-radius:12px; padding:8px 12px;
          font-size:16px; font-weight:700; font-family:inherit; color:var(--ink); cursor:pointer; }}
  input[type=range] {{ flex:1; min-width:0; accent-color:var(--orange); height:28px; }}
  .time {{ font-size:15px; color:var(--ink2); text-align:right; margin-top:2px; }}
  .speed {{ margin-top:12px; }}
  .player.mini .ttl, .player.mini .speed, .player.mini .time {{ display:none; }}
  .player.mini .btn {{ margin-top:0; padding:12px; font-size:20px; }}
  .speed-k {{ display:flex; justify-content:space-between; font-size:13px; color:var(--ink2); padding:0 2px; }}
  .speed-row {{ display:grid; grid-template-columns:repeat(5,1fr); gap:6px; margin-top:2px; }}
  .sp {{ border:2px solid var(--line); background:var(--card); color:var(--ink); border-radius:10px;
        padding:8px 0; font-size:16px; font-weight:700; font-family:inherit; cursor:pointer; }}
  .sp.on {{ background:var(--head); border-color:var(--head); color:#fff; }}
  .sp:focus-visible, .btn:focus-visible, .back:focus-visible {{ outline:3px solid var(--orange); outline-offset:2px; }}
  .menu {{ background:var(--card); border:2px solid var(--line); border-radius:18px; padding:16px; margin-top:16px; }}
  .menu h2 {{ font-size:17px; color:var(--green); }}
  .menu ul {{ padding-left:1.2em; }}
  .menu .k {{ display:inline-block; font-size:14px; font-weight:700; color:#fff; background:var(--head);
             border-radius:6px; padding:0 8px; margin-top:8px; }}
  .part h3 {{ margin:30px 0 10px; font-size:21px; color:var(--green); border-left:6px solid var(--orange); padding-left:10px; }}
  .line {{ border-radius:14px; padding:10px 14px; margin:8px 0; cursor:pointer; transition:background .2s; }}
  .line.t {{ background:var(--teach); margin-right:28px; }}
  .line.m {{ background:var(--mika); margin-left:28px; }}
  .line.now {{ background:var(--now); }}
  .who {{ font-size:13px; font-weight:700; color:var(--ink2); }}
  .term {{ text-decoration:underline; text-decoration-color:var(--orange); text-decoration-thickness:3px; text-underline-offset:4px; }}
  .note {{ margin-top:6px; background:var(--note); border-radius:10px; padding:6px 10px; font-size:16px; line-height:1.6; color:var(--ink2); }}
  .note b {{ color:var(--ink); }}
  .note-k {{ font-size:12px; font-weight:700; color:#fff; background:var(--orange); border-radius:5px; padding:1px 6px; margin-right:6px; }}
  .review {{ background:var(--orange-soft); border-radius:18px; padding:18px 16px; margin-top:28px; }}
  .review h2 {{ font-size:20px; }}
  .review ol {{ padding-left:1.4em; font-size:20px; font-weight:700; }}
  .review .hw {{ margin-top:12px; font-size:17px; }}
  .src {{ margin-top:28px; font-size:15px; color:var(--ink2); }}
  .src ul {{ padding-left:1.2em; }}
  .src a {{ color:var(--green); }}
  .foot {{ margin-top:28px; text-align:center; font-size:16px; color:var(--ink2); }}
  .foot a {{ color:var(--green); font-weight:700; }}
</style>
</head>
<body>
<header>
  <div class="sub">てらこ先生の</div>
  <h1>世界一わかりやすい<br>スマホニュース</h1>
  <div class="date">{date_ja}・第{num}回</div>
</header>
<main>
  <div class="player">
    <div class="ttl">{title}</div>
    <button class="btn" id="play"></button>
    <div class="row">
      <button class="back" id="back">10秒もどる</button>
      <input type="range" id="seek" min="0" max="1000" value="0" aria-label="再生位置">
    </div>
    <div class="time" id="time">0:00</div>
    <div class="speed">
      <div class="speed-k"><span>ゆっくり</span><span>聴く速さ</span><span>はやく</span></div>
      <div class="speed-row" id="speed">
        <button class="sp" data-r="0.8">0.8倍</button>
        <button class="sp" data-r="0.9">0.9倍</button>
        <button class="sp" data-r="1">ふつう</button>
        <button class="sp" data-r="1.2">1.2倍</button>
        <button class="sp" data-r="1.4">1.4倍</button>
      </div>
    </div>
  </div>

  <div class="menu">
    <h2>今日の内容</h2>
    <span class="k">ニュース</span>
    <ul>{news}</ul>
    <span class="k">レッスン</span>
    <ul><li>{lesson}</li></ul>
  </div>

{body}

  <div class="review">
    <h2>今日のおさらい</h2>
    <ol>{review}</ol>
    <p class="hw"><b>宿題</b>　{homework}</p>
  </div>

  <div class="src">
    <b>今日の情報のもと</b>
    <ul>{sources}</ul>
  </div>

  <div class="foot">
    わからないことは、教室で一緒に確かめましょう。<br>
    <a href="https://lin.ee/9c4pI82">スマホ教室TERACO の公式LINE</a>
  </div>
</main>
<audio id="audio" src="{audio}" preload="metadata"></audio>
<script>
const a = document.getElementById('audio'), play = document.getElementById('play'),
      seek = document.getElementById('seek'), time = document.getElementById('time');
const PLAY  = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>聴く</span>';
const PAUSE = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg><span>止める</span>';
const lines = [...document.querySelectorAll('.line[data-t]')];
function fmt(s) {{ s = Math.floor(s || 0); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }}
function ui() {{ play.innerHTML = a.paused ? PLAY : PAUSE; }}
ui();
play.onclick = () => {{ a.paused ? a.play() : a.pause(); }};
a.onplay = a.onpause = ui;
document.getElementById('back').onclick = () => {{ a.currentTime = Math.max(0, a.currentTime - 10); }};
seek.oninput = () => {{ if (a.duration) a.currentTime = a.duration * seek.value / 1000; }};
const player = document.querySelector('.player');
const menu = document.querySelector('.menu');
function fold() {{ player.classList.toggle('mini', menu.getBoundingClientRect().bottom < 0); }}
addEventListener('scroll', fold, {{ passive: true }}); fold();
let rate = 1;
try {{ rate = parseFloat(localStorage.getItem('rate')) || 1; }} catch (e) {{}}
const sps = [...document.querySelectorAll('.sp')];
function setRate(r) {{
  rate = r; a.playbackRate = r; a.preservesPitch = true;
  sps.forEach(b => b.classList.toggle('on', +b.dataset.r === r));
  try {{ localStorage.setItem('rate', r); }} catch (e) {{}}
}}
sps.forEach(b => b.onclick = () => setRate(+b.dataset.r));
setRate(sps.some(b => +b.dataset.r === rate) ? rate : 1);
a.addEventListener('loadedmetadata', () => {{ a.playbackRate = rate; }});
a.addEventListener('play', () => {{ a.playbackRate = rate; }});
let now = null;
a.ontimeupdate = () => {{
  if (a.duration) seek.value = a.currentTime / a.duration * 1000;
  time.textContent = fmt(a.currentTime) + ' / ' + fmt(a.duration);
  let cur = null;
  for (const l of lines) {{ if (+l.dataset.t <= a.currentTime + 0.1) cur = l; else break; }}
  if (cur !== now) {{
    if (now) now.classList.remove('now');
    now = cur;
    if (now) {{
      now.classList.add('now');
      const r = now.getBoundingClientRect(), top = document.querySelector('.player').offsetHeight;
      if (r.top < top || r.bottom > innerHeight) scrollTo({{ top: scrollY + r.top - top - 16, behavior: 'smooth' }});
    }}
  }}
}};
a.onloadedmetadata = () => {{ time.textContent = '0:00 / ' + fmt(a.duration); }};
lines.forEach(l => l.onclick = () => {{ a.currentTime = +l.dataset.t; a.play(); }});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(build(sys.argv[1]))
