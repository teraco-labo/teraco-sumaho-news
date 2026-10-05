#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ポッドキャストの配信ファイル（feed.xml）と回の一覧（episodes.json）を作る。

  python3 make_feed.py

episodes/<日付>/ に notes.json と audio.mp3 がそろっている回を、新しい順にすべて載せる。
Spotify などはこの feed.xml を読みに来て、新しい回を番組に並べる。
各回の説明文には「文字で読めるページ」のURLを入れる（注釈つきの記事版）。
"""
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def _x(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _hms(sec):
    sec = int(sec)
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


def _duration(mp3: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(mp3)], capture_output=True, text=True).stdout
    return float(out.strip() or 0)


def main():
    base = CFG["base_url"].rstrip("/")
    eps = []
    for d in sorted((HERE / "episodes").iterdir(), reverse=True):
        notes, mp3 = d / "notes.json", d / "audio.mp3"
        if not (notes.exists() and mp3.exists()):
            continue
        n = json.loads(notes.read_text(encoding="utf-8"))
        page = f"{base}/episodes/{d.name}/"
        desc = ("今日のテーマ：" + n["lesson"] + "。きっかけのニュース：" + "／".join(n["news"]) + "。")
        eps.append({"date": d.name, "number": n["number"], "title": f"第{n['number']}回 {n['title']}",
                    "description": desc, "page": page, "url": f"{base}/episodes/{d.name}/audio.mp3",
                    "size": mp3.stat().st_size, "duration": round(_duration(mp3))})
    (HERE / "episodes.json").write_text(json.dumps(eps, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    items = ""
    for e in eps:
        text = f"{e['description']} 文字で読む（むずかしい言葉の説明つき）→ {e['page']} ／ 公式LINE → {CFG['line_url']}"
        pub = datetime.strptime(e["date"], "%Y-%m-%d").replace(hour=6, tzinfo=JST)   # 自動配信は朝6時
        items += f"""
  <item>
    <title>{_x(e['title'])}</title>
    <itunes:title>{_x(e['title'])}</itunes:title>
    <link>{e['page']}</link>
    <description>{_x(text)}</description>
    <itunes:summary>{_x(text)}</itunes:summary>
    <enclosure url="{e['url']}" length="{e['size']}" type="audio/mpeg"/>
    <guid isPermaLink="false">{e['url']}</guid>
    <pubDate>{pub.strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate>
    <itunes:author>{_x(CFG['author'])}</itunes:author>
    <itunes:episode>{e['number']}</itunes:episode>
    <itunes:episodeType>full</itunes:episodeType>
    <itunes:duration>{_hms(e['duration'])}</itunes:duration>
    <itunes:explicit>false</itunes:explicit>
  </item>"""
    cat1, cat2 = CFG["category"]
    # カバーの中身から作った印。中身が変わったときだけURLが変わり、Spotify が取り直す（2026-10-04）
    import hashlib
    v = hashlib.md5((HERE / "cover.jpg").read_bytes()).hexdigest()[:8]
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{_x(CFG['show_title'])}</title>
  <itunes:title>{_x(CFG['show_title'])}</itunes:title>
  <link>{base}/</link>
  <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
  <language>ja</language>
  <description>{_x(CFG['description'])}</description>
  <itunes:summary>{_x(CFG['description'])}</itunes:summary>
  <itunes:author>{_x(CFG['author'])}</itunes:author>
  <itunes:owner>
    <itunes:name>{_x(CFG['author'])}</itunes:name>
    <itunes:email>{CFG['owner_email']}</itunes:email>
  </itunes:owner>
  <image><url>{base}/cover.jpg?v={v}</url><title>{_x(CFG['show_title'])}</title><link>{base}/</link></image>
  <itunes:image href="{base}/cover.jpg?v={v}"/>
  <itunes:explicit>false</itunes:explicit>
  <itunes:type>episodic</itunes:type>
  <itunes:category text="{cat1}"><itunes:category text="{cat2}"/></itunes:category>
  <lastBuildDate>{datetime.now(JST).strftime('%a, %d %b %Y %H:%M:%S %z')}</lastBuildDate>{items}
</channel>
</rss>
"""
    (HERE / "feed.xml").write_text(feed, encoding="utf-8")
    print(f"feed.xml を更新（{len(eps)}本）")


if __name__ == "__main__":
    main()
