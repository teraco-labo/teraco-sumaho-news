# -*- coding: utf-8 -*-
"""「この番組を毎回聴く」ボタンと、押すと下から出る案内（聴くページ・文字で読むページで共用）。

藤崎さん（2026-10-05）「生徒さんが聴いていいなと思ったら、毎回聴くボタンがあった方がいい」。
入口は LINE（いちばん簡単。生徒さんはすでに LINE からこのページに来ている）と Spotify の2つ。
「ホーム画面に追加」は、LINE の中のブラウザでは使えないので入れていない。
JS に { } を含むので、str.format のテンプレートには format の後で差し込むこと。
"""
import json
from pathlib import Path

CFG = json.loads((Path(__file__).resolve().parent / "config.json").read_text(encoding="utf-8"))

CSS = """
  .follow { display:flex; align-items:center; justify-content:center; gap:10px; width:100%; margin-top:30px;
            padding:16px; border:none; border-radius:16px; background:var(--head); color:#fff;
            font-size:21px; font-weight:700; font-family:inherit; cursor:pointer; }
  .follow svg { width:26px; height:26px; }
  #fveil { position:fixed; inset:0; z-index:80; background:rgba(0,0,0,.4); display:none; }
  #fsheet { position:fixed; left:0; right:0; bottom:0; z-index:81; max-width:680px; margin:0 auto;
            background:var(--card); color:var(--ink); border-radius:18px 18px 0 0; padding:22px 18px 28px;
            box-shadow:0 -8px 30px rgba(0,0,0,.25); display:none; max-height:88vh; overflow:auto; }
  #fveil.on, #fsheet.on { display:block; }
  #fsheet h3 { font-size:22px; margin-bottom:6px; }
  #fsheet .way { margin-top:16px; padding:14px; border:1px solid var(--line); border-radius:14px; }
  #fsheet .way b { display:block; font-size:19px; }
  #fsheet .way p { font-size:17px; color:var(--ink2); margin-top:4px; line-height:1.7; }
  #fsheet .go { display:block; margin-top:10px; padding:13px; border-radius:12px; text-align:center;
                font-size:19px; font-weight:700; text-decoration:none; color:#fff; }
  #fsheet .go.line { background:#06C755; }
  #fsheet .go.spotify { background:#1DB954; }
  #fsheet .close { display:block; width:100%; margin-top:16px; padding:12px; border:1px solid var(--line);
                   border-radius:12px; background:transparent; color:var(--ink); font-size:18px; font-family:inherit; cursor:pointer; }
"""

ICON = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>'


def html() -> str:
    return f"""
  <button class="follow" id="follow" type="button">{ICON}<span>この番組を毎回聴く</span></button>
  <div id="fveil"></div>
  <div id="fsheet" role="dialog" aria-modal="true" aria-labelledby="fsheet-h">
    <h3 id="fsheet-h">毎回聴くには</h3>
    <div class="way"><b>LINE から</b>
      <p>スマホ教室TERACO のトーク画面で、下のメニューの「ラジオを聴く」を押すと、いつでも最新の回が開きます。毎週火曜と金曜に新しい回が出ます。</p>
      <a class="go line" href="{CFG['line_url']}">LINE を開く</a></div>
    <div class="way"><b>Spotify で</b>
      <p>Spotify を使っている人は、フォローしておくと、新しい回がすぐ見つかります。</p>
      <a class="go spotify" href="{CFG['spotify_url']}">Spotify でフォローする</a></div>
    <button class="close" id="fclose" type="button">閉じる</button>
  </div>
<script>
(function(){{
  var s = document.getElementById('fsheet'), v = document.getElementById('fveil');
  function open(){{ s.classList.add('on'); v.classList.add('on'); }}
  function close(){{ s.classList.remove('on'); v.classList.remove('on'); }}
  document.getElementById('follow').addEventListener('click', open);
  document.getElementById('fclose').addEventListener('click', close);
  v.addEventListener('click', close);
  document.addEventListener('keydown', function(e){{ if (e.key === 'Escape') close(); }});
}})();
</script>
"""
