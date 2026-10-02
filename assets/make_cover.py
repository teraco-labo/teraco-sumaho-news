#!/usr/bin/env python3
"""番組の表紙（3000×3000）。AIニュースの表紙と同じ配置で、色だけ緑＋オレンジに変えた兄弟版。
キャラは ~/ai-office/advisors/lecture/character/bust/center-plain-point-wide.png（メガネなし）を
白背景だけ抜いた terako_cutout.png。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = Path(__file__).resolve().parent
S = 3000
bg = Image.new('RGB', (S, S)); d = ImageDraw.Draw(bg)
top, bot = (12, 38, 30), (20, 52, 42)
for y in range(S):
    t = y / S; d.line([(0, y), (S, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
glow = Image.new('L', (S, S), 0); ImageDraw.Draw(glow).ellipse((450, 1250, 2550, 3350), fill=150)
bg = Image.composite(Image.new('RGB', (S, S), (40, 105, 80)), bg, glow.filter(ImageFilter.GaussianBlur(260)))
d = ImageDraw.Draw(bg)
f1 = ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc', 230)
f2 = ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc', 350)
def ctext(y, txt, f, fill):
    d.text(((S - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=fill)
ctext(430, '世界一わかりやすい', f1, (214, 230, 222))
ctext(800, 'スマホニュース', f2, (255, 255, 255))
d.rounded_rectangle(((S - 300) / 2, 1270, (S + 300) / 2, 1300), radius=15, fill=(251, 146, 60))
ch = Image.open(HERE / 'terako_cutout.png'); r = 1640 / ch.height
ch = ch.resize((int(ch.width * r), 1640), Image.LANCZOS)
bg.paste(ch, ((S - ch.width) // 2, S - ch.height), ch)
bg.save(HERE.parent / 'cover.jpg', quality=88)
