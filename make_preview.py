#!/usr/bin/env python3
"""試聴用ページ（アーティファクト）を作る。本番ページに音声を埋め込み、上に「見本」の帯を付ける。
  python3 make_preview.py 2026-10-02 出力.html
アーティファクトは外部の音声ファイルを読めないので、mp3 をページの中に埋め込む（16MBまで）。"""
import base64, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
date, out = sys.argv[1], Path(sys.argv[2])
ep = HERE / "episodes" / date
page = (ep / "index.html").read_text(encoding="utf-8")
mp3 = base64.b64encode((ep / "audio.mp3").read_bytes()).decode()
page = page.replace('src="audio.mp3"', f'src="data:audio/mpeg;base64,{mp3}"')
page = page.replace('href="yomu.html"', f'href="https://teraco-labo.github.io/teraco-sumaho-news/episodes/{date}/yomu.html"')  # 試聴ページからは公開中の文字で読むページへ
page = re.sub(r'<!DOCTYPE html>\s*<html lang="ja">\s*<head>\s*', "", page)
page = re.sub(r'<meta charset[^>]*>\s*<meta name="viewport"[^>]*>\s*', "", page)
page = re.sub(r'<link rel="icon"[^>]*>\s*', "", page)
page = page.replace("</head>\n<body>", "").replace("</body>\n</html>", "")
band = ('<div style="background:var(--orange);color:#fff;text-align:center;font-size:15px;font-weight:700;'
        'padding:8px 16px">試聴用の見本です（まだ公開していません）</div>\n')
page = page.replace("<header>", band + "<header>", 1)
out.write_text(page, encoding="utf-8")
print(out, f"{len(page)/1e6:.1f}MB")
