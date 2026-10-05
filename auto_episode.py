#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""世界一わかりやすいスマホニュース：1回分を自動で作る（火曜・金曜の朝、Mac の定時実行から呼ぶ）。

  python auto_episode.py build   [日付]   # 04:00 ニュース集め→台本→事実確認→検査→声→ページ（公開はしない）
  python auto_episode.py publish [日付]   # 06:00 GitHub に送って公開し、藤崎さんの LINE に知らせる（自動配信は朝6時に統一）

台本と事実確認は Claude Code をサブスク枠で呼ぶ（claude -p）。APIキーは子プロセスに渡さない
＝従量課金にならない。有料APIへの切り替えも付けない（失敗したらその回は休み）。
渡す道具は読むだけのもの（WebFetch・WebSearch・Read）に限る。

声は make_episode.py（ElevenLabs の本人の声を優先・足りなければ0円の Teraco Voice）。
失敗したら公開せず、LINE で「今回は作れませんでした」と知らせる。
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
KNOWLEDGE = Path.home() / ".openclaw/workspace/terako-sensei/knowledge"
STUDIO = Path.home() / ".openclaw/workspace/terako-sensei"
FEEDS = ["https://k-tai.watch.impress.co.jp/data/rss/1.0/ktw/feed.rdf",
         "https://rss.itmedia.co.jp/rss/2.0/mobile.xml"]
LOG = HERE / "logs" / "auto.log"
WEEK = "月火水木金土日"


def log(msg: str):
    LOG.parent.mkdir(exist_ok=True)
    line = f"{datetime.now(JST):%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def notify(text: str):
    """藤崎さん1人の LINE に送る（Teraco Studio の部品を共用・無料枠）。失敗しても止めない。"""
    try:
        sys.path.insert(0, str(STUDIO))
        import app
        app.notify_line(text)
    except Exception as e:
        log(f"LINE に送れませんでした: {e}")


# ─── 1. ニュース集め ─────────────────────────────────────────
def gather(days: int = 4) -> list:
    """専門サイトの更新情報から、ここ数日の見出しを集める（見つけるだけ。裏取りは台本の段で公式に当たる）。"""
    since = datetime.now(JST) - timedelta(days=days)
    out = []
    for url in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            text = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            log(f"ニュースの取得に失敗（続行）: {url} {e}")
            continue
        for it in re.findall(r"<item[ >].*?</item>", text, re.S):
            t = re.search(r"<title>(.*?)</title>", it, re.S)
            l = re.search(r"<link>(.*?)</link>", it, re.S)
            d = re.search(r"<(?:dc:date|pubDate)>(.*?)</", it, re.S)
            if not (t and l and d):
                continue
            ds = d.group(1).strip()
            try:
                dt = datetime.fromisoformat(ds) if "T" in ds else datetime.strptime(ds, "%a, %d %b %Y %H:%M:%S %z")
            except ValueError:
                continue
            if dt < since:
                continue
            title = re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1)).strip()
            out.append({"date": dt.strftime("%Y-%m-%d"), "title": title, "url": l.group(1).strip()})
    log(f"ニュース候補 {len(out)} 件")
    return out[:120]


# ─── Claude（サブスク枠） ─────────────────────────────────────
def claude(prompt: str, system: str, tools=("WebFetch", "WebSearch"), timeout=1800) -> str:
    cli = next((c for c in (str(Path.home() / ".npm-global/bin/claude"), "/opt/homebrew/bin/claude")
                if Path(c).exists()), None)
    if not cli:
        raise RuntimeError("claude コマンドが見つかりません")
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + str(Path.home() / ".npm-global/bin")
    safe = [t for t in tools if t in ("WebFetch", "WebSearch", "Read")]
    cmd = [cli, "-p", prompt, "--system-prompt", system,
           "--tools", *safe, "--allowedTools", *safe,
           "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--disable-slash-commands", "--no-chrome", "--no-session-persistence",
           "--setting-sources", "", "--output-format", "json"]
    pr = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, cwd=str(KNOWLEDGE))
    outer = json.loads(pr.stdout)
    if outer.get("is_error"):
        raise RuntimeError("Claude が途中で止まりました: " + str(outer.get("result", ""))[:300])
    return str(outer.get("result", ""))


def _json(text: str) -> dict:
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


RULES = """\
# 番組
「世界一わかりやすいスマホニュース」。スマホ教室TERACO（宮崎県西都市）のてらこ先生が、
教室の生徒さん（シニア・初心者が中心）に向けて話す、耳で聞く番組。てらこ先生の一人語り。5〜6分（台本1,800〜2,100字）。

# 台本の型（この順番）
1. 冒頭：「みなさん、おはようございます。世界一わかりやすいスマホニュース、てらこ先生です。」
   続けて「今日お伝えするのは、〇〇のお話です」。**「これ1つ」「3つ」など数で絞らない**。
2. 共感：ニュースを入口にしてよい。**ニュースを使うときは必ず次の3つを守る**
   - 冒頭で流れを先に言う（「その前に、まずは今日のニュースから。〇〇が公式に発表したお知らせです」）
   - 出どころと日付を言う（「〇〇が〇月〇日に、公式に発表しました」）
   - 本題に入る前に区切る（「ここまでが、〇〇からのお知らせでした」）
   - **「本物のニュース」「本当のニュース」とは言わない**（番組のほかのニュースが本物でないように聞こえる。
     2026-10-06 藤崎さん）。見出しは「今日のニュース」
3. 手順3つ（「ひとつめ」「ふたつめ」「みっつめ」）
4. 「ここが大切」
5. 今日やってみること
6. 締め：「この番組は、毎週火曜日と金曜日の朝にお届けしています。」
   「フォローしていただくと、スマホの理解がぐっと深まりますよ。」
   「世界一わかりやすいスマホニュース、てらこ先生でした。また〇曜日の朝に、お会いしましょう。」

# 書き方
- 1文は40字まで。ゆっくり、やさしく、敬体。落ち着いた口調（「！」は使わない）
- 人を指す「方」は使わない（音声が「ほう」と読む）→「人」「みなさん」
- 「今日は〇月〇日」「きのう」など、公開日がずれると通じない言い方は使わない
- 英字の名前（LINE、iPhone など）は正式な表記で書いてよい。ただし readings に読み方を必ず入れる
- 数字は算用数字（2,970円）でよい（音声側で読み替える）
- 教室での具体的なエピソードを作り話で足さない。分からないことは書かない
- 詐欺や偽物がテーマの回は、本物と偽物の区別があいまいになる言い方をしない（偽物と比べる必要があるときだけ「本物の〇〇」を使ってよい）

# 言葉の説明（terms）
- AIニュースと同じく「分からないかもしれない言葉にはすべて説明を付ける」。目安は20〜30語
- 用語集にすでにある言葉（下の一覧）は terms に書かなくてよい（自動で説明が付く）
- **重点はカタカナ語・英語・英字の名前**（サービス名・プラン名・アプリ名・IT用語）。聞き手のシニアは漢字には強いが、
  横文字に不安がある（2026-10-04 藤崎さん）。カタカナ・英字の言葉は、身近そうなもの（スマホ・メール等）も含めて多めに付ける
- 漢字の言葉（公式・高額・明細など）には基本的に付けない
- 見出しの言葉は台本に出てくる表記と一字一句同じにする（ページで、その言葉の初めて出たところに説明が付く）
- 説明は事実だけ。分からないことは書かない

# 事実
- ニュースの数字・日付・条件は、**必ず公式発表（各社のニュースリリース・お知らせ、総務省など）を WebFetch で開いて確かめる**。
  専門サイトの記事は見つけるためだけに使う。公式で確かめられない細部は書かない
- 操作手順は機種やバージョンで変わるので、画面の細かいボタン名に頼らない言い方にする
"""

FORMAT = """\
# 返す形（JSON だけ。前後に説明を書かない）
{
 "title": "回の題名（30字前後）",
 "news": ["きっかけのニュースを1行で（無ければ空の配列）"],
 "lesson": "今日のテーマ",
 "script": "台本。見出し行は『## 見出し』、話す行は『[てらこ先生] 本文』。段落ごとに空行",
 "review": ["おさらい1", "おさらい2", "おさらい3"],
 "homework": "今日やってみること（1行）",
 "terms": {"台本に出てくる言葉（台本の表記そのまま）": {"slug": "英小文字とハイフンの名前（例 docomo-shop）", "reading": "読み（ひらがな/カタカナ・不要なら空）", "category": "スマホの基本／安全／携帯会社／インターネット／アプリ／ことば のどれか", "short": "触れると出るやさしい説明（1〜2文・敬体）", "detail": "解説ページの『もう少しくわしく』（2〜3文・敬体・事実だけ）"}},
 "sources": [{"label": "出どころ（会社名・日付・何の発表か）", "url": "公式のURL"}],
 "fact_check": ["確かめた事実と、確かめた先"],
 "readings": {"英字や読み間違えやすい言葉": "カタカナの読み"}
}
"""


def past_topics() -> list:
    out = []
    for n in sorted((HERE / "episodes").glob("*/notes.json")):
        try:
            j = json.loads(n.read_text(encoding="utf-8"))
            out.append(f"{j['date']} {j['title']}")
        except Exception:
            pass
    return out


def write(date: str, news: list) -> dict:
    wd = WEEK[datetime.strptime(date, "%Y-%m-%d").weekday()]
    nxt = "金" if wd == "火" else "火"
    kfiles = "、".join(p.name for p in sorted(KNOWLEDGE.glob("*.md")))
    prompt = f"""{RULES}
# 今回
- 公開日：{date}（{wd}曜日）。締めは「また{nxt}曜日の朝に、お会いしましょう。」
- これまでの回（同じテーマは避ける）：{json.dumps(past_topics(), ensure_ascii=False)}
- ここ数日のニュース候補（専門サイトの見出し）：
{json.dumps(news, ensure_ascii=False, indent=0)}
- 教室のナレッジ（実際の教室の記録。今いるフォルダにある。Read で読める）：{kfiles}
- 用語集にすでにある言葉（terms に書かなくてよい）：{"、".join(t["term"] for t in json.loads((HERE / "glossary.json").read_text(encoding="utf-8"))["terms"])}

# やること
1. 候補の中から、シニアの生徒さんに役立つ「スマホの使い方・安全・お得」につながるニュースを1つ選ぶ。
   携帯会社（ドコモ・au・ソフトバンク・楽天モバイル）、LINE、詐欺対策、身近な家電やサービスを優先。
   ちょうどいいニュースが無ければ、ニュース無しの「学びの回」にしてよい
2. 選んだニュースの公式発表を WebFetch で開いて、数字・日付・条件を確かめる
3. ニュースを入口に、使い方を1テーマ教える台本を書く（教室のナレッジから、生徒さんがよくつまずく点を拾ってよい）
{FORMAT}"""
    system = "あなたはスマホ教室の講師てらこ先生の台本作家です。事実は公式で確かめ、確かめられないことは書きません。返事は指定の JSON だけです。"
    log("台本を書いています（Claude・サブスク枠）")
    return _json(claude(prompt, system, tools=("WebFetch", "WebSearch", "Read")))


def factcheck(ep: dict) -> dict:
    prompt = f"""次の台本の「事実」を、公式の出どころで確かめ直してください。
- 数字・日付・条件・会社名・サービス名を1つずつ、sources の公式URL（足りなければ公式サイトを WebFetch / WebSearch）で照合する
- 確かめられない・食い違う部分は、台本から削るか、公式どおりに直す（言い回しや構成は変えない。型と書き方の決まりは守る）
- 専門サイトの記事だけを根拠にしない

{RULES}

# 台本と付属情報
{json.dumps(ep, ensure_ascii=False)}

# 返す形（JSON だけ）
{{"ok": true か false（直しが必要だったか）, "changes": ["直した点"], "episode": {{上と同じ形の、直した後の全体}}}}"""
    system = "あなたは放送前の事実確認の担当です。公式の一次情報だけを根拠にします。返事は指定の JSON だけです。"
    log("事実確認をしています（別の Claude・サブスク枠）")
    j = _json(claude(prompt, system))
    for c in j.get("changes", []):
        log(f"  事実確認で直した: {c}")
    return j.get("episode") or ep


def run_check(date: str) -> tuple:
    py = sys.executable
    r = subprocess.run([py, str(HERE / "make_episode.py"), "check", date], capture_output=True, text=True)
    return r.returncode == 0, r.stdout


def fix(ep: dict, problems: str) -> dict:
    prompt = f"""次の台本は機械検査に通りませんでした。指摘された行だけを直してください（意味と事実は変えない）。
英字が読み替えられていないという指摘は、readings にその言葉の読み方を足せば直ります。
# 検査の結果
{problems}
{RULES}
# 台本と付属情報
{json.dumps(ep, ensure_ascii=False)}
# 返す形：上と同じ形の JSON だけ"""
    return _json(claude(prompt, "返事は指定の JSON だけです。", tools=()))


def save(date: str, ep: dict):
    d = HERE / "episodes" / date
    d.mkdir(parents=True, exist_ok=True)
    (d / "script.txt").write_text(ep["script"].strip() + "\n", encoding="utf-8")
    nums = [json.loads(p.read_text(encoding="utf-8")).get("number", 0)
            for p in (HERE / "episodes").glob("*/notes.json") if p.parent.name != date]
    notes = {k: ep.get(k) for k in ("title", "news", "lesson", "review", "homework", "sources", "fact_check")}
    notes["terms"] = {k: (v.get("short") if isinstance(v, dict) else v) for k, v in (ep.get("terms") or {}).items()}
    _merge_glossary(ep.get("terms") or {})
    notes.update({"number": max(nums or [0]) + 1, "date": date, "format": "一人語り・自動作成"})
    (d / "notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if ep.get("readings"):
        rp = HERE / "readings.json"
        r = json.loads(rp.read_text(encoding="utf-8"))
        for k, v in ep["readings"].items():
            # 辞書は文章全体を置き換えるので、日本語の言葉を足すと別の場所を壊す
            # （試運転で「付け→づけ」が入り、「気を付けて」が「気をづけて」になるところだった）。
            # Claude に足させるのは英字を含む言葉の読みだけ。既存の読みは上書きしない。
            if re.search(r"[A-Za-z]", k):
                r.setdefault(k, v)
        rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _merge_glossary(terms: dict):
    """新しい言葉を用語辞書（glossary.json）に足す。すでにある言葉・名前は上書きしない（人が直した説明を守る）。"""
    gp = HERE / "glossary.json"
    g = json.loads(gp.read_text(encoding="utf-8"))
    have_terms = {t["term"] for t in g["terms"]} | {a for t in g["terms"] for a in t.get("aliases", [])}
    have_slugs = {t["slug"] for t in g["terms"]}
    for word, v in terms.items():
        if not isinstance(v, dict) or word in have_terms or not v.get("short"):
            continue
        slug = re.sub(r"[^a-z0-9-]", "", (v.get("slug") or "").lower()) or f"term-{len(have_slugs) + 1}"
        while slug in have_slugs:
            slug += "-2"
        g["terms"].append({"slug": slug, "term": word, "reading": v.get("reading", ""), "aliases": [],
                           "category": v.get("category") or "ことば", "short": v["short"],
                           "detail": v.get("detail") or v["short"], "related": [], "status": "published"})
        have_slugs.add(slug); have_terms.add(word)
    gp.write_text(json.dumps(g, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ─── 本体 ───────────────────────────────────────────────────
def build(date: str) -> int:
    d = HERE / "episodes" / date
    if (d / "audio.mp3").exists():
        log(f"{date} はもう作ってあります")
        return 0
    try:
        ep = factcheck(write(date, gather()))
        save(date, ep)
        ok, out = run_check(date)
        if not ok:
            log("機械検査に通らないので直します\n" + out)
            ep = fix(ep, out)
            save(date, ep)
            ok, out = run_check(date)
            if not ok:
                raise RuntimeError("台本が機械検査に通りません\n" + out)
        r = subprocess.run([sys.executable, str(HERE / "make_episode.py"), "voice", date],
                           capture_output=True, text=True)
        log(r.stdout[-1500:])
        if r.returncode != 0 or not (d / "audio.mp3").exists():
            raise RuntimeError("声を作れませんでした\n" + (r.stdout + r.stderr)[-800:])
        subprocess.run([sys.executable, str(HERE / "build_site.py")], check=True)   # 共用エンジンで全ページと feed を作り直す
        title = json.loads((d / "notes.json").read_text(encoding="utf-8"))["title"]
        log(f"{date} を作りました：{title}（公開は6時）")
        if datetime.now(JST).hour >= 6:   # Mac が寝ていて作るのが遅れた日は、作り終えたらすぐ公開する
            return publish(date)
        return 0
    except Exception as e:
        log(f"失敗: {e}")
        notify(f"【スマホニュース】{date} の回は作れませんでした。今回はお休みにします。\n理由: {str(e)[:300]}")
        return 1


def publish(date: str) -> int:
    d = HERE / "episodes" / date
    if not (d / "audio.mp3").exists():
        log(f"{date} の音声が無いので公開しません")
        return 1
    git = ["git", "-C", str(HERE)]
    subprocess.run(git + ["add", "episodes", "terms", "glossary.json", "index.html", "archive.html", "sitemap.xml", "robots.txt",
                         "feed.xml", "episodes.json", "readings.json"], check=True)
    if subprocess.run(git + ["diff", "--cached", "--quiet"]).returncode == 0:
        log(f"{date} は公開済み")
        return 0
    n = json.loads((d / "notes.json").read_text(encoding="utf-8"))
    subprocess.run(git + ["commit", "-q", "-m", f"第{n['number']}回 {n['title']}（自動作成）"], check=True)
    r = subprocess.run(git + ["push", "-q", "origin", "main"], capture_output=True, text=True)
    if r.returncode != 0:
        notify(f"【スマホニュース】{date} の回を公開できませんでした（GitHub への送信に失敗）。")
        log("push 失敗: " + r.stderr[-500:])
        return 1
    base = json.loads((HERE / "config.json").read_text(encoding="utf-8"))["base_url"]
    notify(f"【スマホニュース】第{n['number']}回を公開しました。\n「{n['title']}」\n{base}/episodes/{date}/")
    log(f"{date} を公開しました")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("build", "publish"):
        sys.exit(__doc__)
    day = sys.argv[2] if len(sys.argv) > 2 else datetime.now(JST).strftime("%Y-%m-%d")
    sys.exit({"build": build, "publish": publish}[sys.argv[1]](day))
