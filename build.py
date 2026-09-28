#!/usr/bin/env python3
"""Trump vs Reality static site generator.

Reads editions/<YYYY-MM-DD>/edition.json + stories.json,
writes a modern static site into docs/ ready for GitHub Pages.

- / : latest edition (single-column feed, verdict filter)
- /editions/<date>/ : that day's edition
- /archive.html : past editions
- /audio/<date>.mp3 : the day's Trump Spin Check episode (copied in separately)

stories.json entry:
  {id, headline, outlet, article_url, published,
   trending_claim, verdict, rating_explained, sources:[{name,url}],
   trending_context, order}
verdict: accurate | mostly-accurate | mixed | misleading | false | no-claim
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
EDITIONS = os.path.join(ROOT, "editions")
SITE = os.path.join(ROOT, "docs")
BASE_URL = "https://phoenixbyrd.github.io/trump-reality-check"


def esc(s):
    s = "" if s is None else str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def fail(msg):
    print(f"VALIDATION FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


VERDICTS = {
    "accurate":        ("Accurate", "#22c55e"),
    "mostly-accurate": ("Mostly accurate", "#a3e635"),
    "mixed":           ("Mixed", "#fbbf24"),
    "unverifiable":    ("Unverifiable", "#94a3b8"),
    "misleading":      ("Misleading", "#fb923c"),
    "false":           ("False", "#ef4444"),
    "no-claim":        ("Opinion — no checkable claim", "#9ca3af"),
}
VERDICT_ORDER = ["accurate", "mostly-accurate", "mixed", "unverifiable", "misleading", "false", "no-claim"]
SEVERITY = {"false": 0, "misleading": 1, "mixed": 2, "unverifiable": 3,
            "mostly-accurate": 4, "accurate": 5, "no-claim": 6}

STORY_REQUIRED = ["id", "headline", "outlet", "article_url",
                  "trending_claim", "verdict", "rating_explained", "sources"]


def validate_stories(stories, date):
    seen = set()
    for m in stories:
        mid = m.get("id", "?")
        for f in STORY_REQUIRED:
            if not m.get(f):
                fail(f"{date} {mid}: missing/empty required field '{f}'")
        if m["verdict"] not in VERDICTS:
            fail(f"{date} {mid}: bad verdict '{m['verdict']}'")
        if mid in seen:
            fail(f"{date} {mid}: duplicate id")
        seen.add(mid)
        if not re.match(r"https?://", m["article_url"]):
            fail(f"{date} {mid}: article_url is not a URL: {m['article_url']!r}")
        if len(m["rating_explained"]) < 100:
            fail(f"{date} {mid}: rating_explained too short "
                 f"({len(m['rating_explained'])} chars) — explanations must walk through the evidence")
        if not isinstance(m["sources"], list) or len(m["sources"]) < 1:
            fail(f"{date} {mid}: need at least 1 named source")
        for s in m["sources"]:
            if not s.get("name"):
                fail(f"{date} {mid}: source missing name")
        for f in ("trending_claim", "rating_explained", "headline"):
            if "CHECKABLE" in str(m.get(f, "")):
                fail(f"{date} {mid}: raw metadata leaked into '{f}'")


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0d0f14;--card:#161a23;--card2:#1d2230;--line:#262c3d;--txt:#e8ebf2;--mut:#9aa3b8;--acc:#7c5cff}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--txt);line-height:1.6;min-height:100vh}
a{color:#8ea6ff;text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header.site{background:rgba(13,15,20,.85);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);padding:14px 0;position:sticky;top:0;z-index:50;transition:transform .28s ease}
header.site.hide{transform:translateY(-110%)}
header.site .wrap{display:flex;align-items:center;justify-content:space-between}
.brand{font-size:21px;font-weight:800;letter-spacing:.3px;color:#fff}
.brand .m1{background:linear-gradient(135deg,#7c5cff,#00d4ff);-webkit-background-clip:text;background-clip:text;color:transparent}
.brand .m2{color:#ff5c7a}
.tagline{font-size:12px;color:var(--mut);margin-top:1px}
.fbtn{background:var(--card);border:1px solid var(--line);color:var(--mut);border-radius:999px;padding:7px 16px;font-size:13px;cursor:pointer;transition:.15s}
.fbtn:hover{border-color:var(--acc);color:#fff}
.fbtn.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
.fcount{margin-left:auto;font-size:13px;color:var(--mut)}
.verdict{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;border-radius:999px;padding:4px 11px;border:1px solid}
.how{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px;margin:10px auto 40px;max-width:860px;font-size:14px;color:var(--mut)}
.how h2{color:#fff;font-size:18px;margin-bottom:10px}
.how li{margin:6px 0 6px 18px}
footer.site{border-top:1px solid var(--line);padding:26px 0;margin-top:10px;font-size:13px;color:var(--mut)}
.archive-list{list-style:none;padding:24px 0 40px}
.archive-list li{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 22px;margin-bottom:12px}
.archive-list .d{font-size:13px;color:var(--mut)}
.archive-list .kindtag{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--acc);border:1px solid var(--acc);border-radius:999px;padding:2px 10px;margin-left:8px;vertical-align:middle}
.ednav{display:flex;justify-content:space-between;padding:8px 0 30px;font-size:14px;max-width:860px;margin:0 auto}
.dateline{font-size:12px;text-transform:uppercase;letter-spacing:2px;color:var(--mut);text-align:center;margin-top:26px}
.hero{padding:30px 0 6px;text-align:center}
.hero h1{font-size:clamp(28px,4vw,44px);font-weight:800;color:#fff}
.hero h1 .grad{background:linear-gradient(135deg,#7c5cff,#00d4ff 60%,#22c55e);-webkit-background-clip:text;background-clip:text;color:transparent}
/* ---- hamburger drawer menu ---- */
#menuBtn{position:fixed;top:14px;right:14px;z-index:100;width:46px;height:46px;border-radius:12px;background:rgba(20,24,33,.94);border:1px solid var(--line);cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px}
#menuBtn span{display:block;width:20px;height:2px;background:#fff;border-radius:2px;transition:transform .25s ease,opacity .25s ease}
#menuBtn.open span:nth-child(1){transform:translateY(7px) rotate(45deg)}
#menuBtn.open span:nth-child(2){opacity:0}
#menuBtn.open span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
#scrim{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:90;opacity:0;pointer-events:none;transition:opacity .25s ease}
#scrim.show{opacity:1;pointer-events:auto}
#drawer{position:fixed;top:0;right:0;bottom:0;width:min(320px,84vw);background:#10141c;border-left:1px solid var(--line);z-index:95;transform:translateX(105%);transition:transform .3s ease;overflow-y:auto;padding:76px 20px 30px}
#drawer.open{transform:none}
.d-sec{margin-bottom:26px}
.d-h{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:var(--mut);margin-bottom:10px}
.d-sec>a{display:block;color:var(--txt);padding:11px 2px;border-bottom:1px solid var(--line);font-size:15px}
.d-btns{display:flex;flex-wrap:wrap;gap:8px}
.d-foot{font-size:13px;color:var(--mut)}
/* ---- news layout ---- */
.nameplate{text-align:center;padding:34px 0 16px;border-bottom:3px double var(--line);margin-bottom:6px}
.np-kicker{font-size:11px;text-transform:uppercase;letter-spacing:3px;color:var(--acc)}
.np-title{font-family:Georgia,'Times New Roman',serif;font-size:clamp(36px,6vw,60px);font-weight:800;color:#fff;margin:8px 0 6px}
.np-title .vs{color:#ff5c7a;font-style:italic;font-weight:400}
.np-tag{color:var(--mut);font-size:14px;max-width:640px;margin:0 auto}
.np-meta{font-size:12px;color:var(--mut);margin-top:10px}
.scoreboard{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;padding:14px 0 4px}
.sb{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px 14px;font-size:12px;color:var(--mut)}
.sb b{color:#fff;margin-right:6px}
.podplayer{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin:18px auto;max-width:860px;text-align:center}
.pp-kicker{font-size:12px;text-transform:uppercase;letter-spacing:2px;color:var(--acc);margin-bottom:10px}
.podplayer audio{width:100%;max-width:560px}
.pp-note{font-size:12px;color:var(--mut);margin-top:8px}
.leadstory{border-bottom:1px solid var(--line);padding:22px 0 26px;margin:0 auto 8px;max-width:860px}
.leadstory.hidden{display:none}
.leadstory .kicker{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:var(--acc);margin-bottom:8px}
.lead-head{font-family:Georgia,serif;font-size:clamp(26px,4vw,40px);font-weight:800;color:#fff;line-height:1.2}
a.lead-head:hover{color:#8ea6ff;text-decoration:none}
.feed{padding:6px 0 30px;max-width:860px;margin:0 auto}
.brief{padding:16px 0;border-bottom:1px solid var(--line)}
.brief.hidden{display:none}
.b-head{font-family:Georgia,serif;font-size:18px;font-weight:700;color:#fff;line-height:1.35}
a.b-head:hover{color:#8ea6ff;text-decoration:none}
.b-meta{font-size:12px;color:var(--mut);margin:6px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.b-claim{font-size:13.5px;color:var(--mut);font-style:italic;margin:6px 0}
.b-claim b,.b-why b{color:var(--txt);font-style:normal}
.b-why{font-size:13.5px;color:var(--txt);margin:6px 0}
.b-src{font-size:12px;color:var(--mut)}
.b-src a{margin-right:8px}
"""


JS = """
(function(){
const fsrc=document.getElementById('filterSrc');
const dV=document.getElementById('dVerdict');
if(fsrc&&dV){
fsrc.querySelectorAll('.fbtn[data-verdict]').forEach(b=>dV.appendChild(b));
const fc0=document.getElementById('fcount');
if(fc0)document.querySelector('.d-foot').appendChild(fc0);
fsrc.remove();
}
if(dV&&!dV.children.length)dV.closest('.d-sec').style.display='none';
const menuBtn=document.getElementById('menuBtn'),drawer=document.getElementById('drawer'),scrim=document.getElementById('scrim');
function setMenu(open){menuBtn.classList.toggle('open',open);drawer.classList.toggle('open',open);scrim.classList.toggle('show',open);}
menuBtn.onclick=()=>setMenu(!drawer.classList.contains('open'));
scrim.onclick=()=>setMenu(false);
drawer.querySelectorAll('a').forEach(a=>a.onclick=()=>setMenu(false));
document.addEventListener('keydown',e=>{if(e.key==='Escape')setMenu(false);});
})();
const verBtns=[...document.querySelectorAll('.fbtn[data-verdict]')];
let verdict='all';
function apply(){
  let n=0;
  document.querySelectorAll('.brief[data-verdict],.leadstory[data-verdict]').forEach(c=>{
    const show=verdict==='all'||c.dataset.verdict===verdict;
    c.classList.toggle('hidden',!show);
    if(show)n++;
  });
  const fce=document.getElementById('fcount');if(fce)fce.textContent=n+' shown';
}
verBtns.forEach(b=>b.onclick=()=>{verdict=b.dataset.verdict;verBtns.forEach(x=>x.classList.toggle('on',x===b));apply();});
apply();
let lastY=window.scrollY;const hdr=document.querySelector('header.site');
window.addEventListener('scroll',()=>{const y=window.scrollY;
if(y>lastY+4&&y>140){hdr.classList.add('hide');}
else if(y<lastY-4){hdr.classList.remove('hide');}
lastY=y;},{passive:true});
"""

PAGE_TOP = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Trump vs Reality</title>
<meta name="description" content="Daily fact-check of trending claims about President Trump. What's claimed vs. what's true, checked against named sources.">
<style>""" + CSS + """</style></head>
<body>
"""

HEADER = """<header class="site"><div class="wrap">
<div><a class="brand" href="{base}/"><span class="m1">TRUMP</span> <span class="m2">VS</span> <span class="m1">REALITY</span></a><div class="tagline">Checking claims about President Trump against named sources.</div></div>
</div></header>
<button id="menuBtn" aria-label="Open menu"><span></span><span></span><span></span></button>
<div id="scrim"></div>
<aside id="drawer" aria-label="Site menu">
<div class="d-sec"><div class="d-h">Menu</div>
<a href="{base}/">Today's edition</a>
<a href="{base}/archive.html">Archive</a>
<a href="#how">How we rate</a>
</div>
<div class="d-sec"><div class="d-h">Verdict</div><div class="d-btns" id="dVerdict"></div></div>
<div class="d-foot"></div>
</aside>"""

FOOTER = """<footer class="site"><div class="wrap">
<strong style="color:#fff">Trump vs Reality</strong> — every day we pull the most-trending claims about President Trump — actions attributed to him, quotes attributed to him — link the originals, and check the central claims against named sources.<br>
<span style="font-size:12px">Articles belong to their publishers and are linked for reference. Corrections: reply in the Muse app.</span>
</div></footer>
<script>""" + JS + """</script>
</body></html>"""

HOW = """<div class="how" id="how"><h2>How we rate</h2>
<ul>
<li><strong style="color:#fff">What this site is.</strong> Every day we collect the most-trending claims about President Trump — actions attributed to him, quotes attributed to him — largely from outlets critical of him, and check each claim against named, published sources.</li>
<li><strong style="color:#fff">What we check.</strong> The central factual claim — and we check whether it is actually true, not merely whether someone said it. "X says Y happened" proves only that X said it. A claim earns "Accurate" only when the underlying event is confirmed by direct evidence: primary documents, official records, direct video or audio, on-the-ground wire reporting. When the core assertion can neither be confirmed nor denied, it gets "Unverifiable" — never a guess. "Why this rating" walks through the evidence step by step, with the key numbers, dates, and quotes. Pure opinion pieces with no checkable factual claim get "Opinion — no checkable claim" instead of a fake verdict.</li>
<li><strong style="color:#fff">Honest verdicts, both directions.</strong> A biased outlet can still report facts accurately — when the claim holds up, it gets "Accurate", full stop. The mission is what's factual and what isn't, not debunking everything. We don't infer motives, and when sources disagree or something is unknown, we say so.</li>
<li><strong style="color:#fff">Read the original.</strong> Every story links the original article so you can check our work.</li>
</ul></div>"""


def verdict_chip(v):
    label, color = VERDICTS.get(v, VERDICTS["no-claim"])
    return (f'<span class="verdict" style="color:{color};border-color:{color}55;'
            f'background:{color}14">&#9679; {esc(label)}</span>')


def brief_sources(m):
    return " ".join(
        f'<a href="{esc(s.get("url", "#"))}" target="_blank" rel="noopener">{esc(s.get("name", "source"))}</a>'
        for s in m.get("sources", []))


def brief_html(m):
    vlabel = VERDICTS.get(m.get("verdict"), VERDICTS["no-claim"])[0]
    srcs = brief_sources(m)
    pub = f" &middot; {esc(m['published'])}" if m.get("published") else ""
    claim = m.get("trending_claim") or "No checkable factual claim — opinion or analysis."
    return f"""<article class="brief" data-verdict="{m['verdict']}">
<a class="b-head" href="{esc(m['article_url'])}" target="_blank" rel="noopener">{esc(m['headline'])}</a>
<div class="b-meta"><span>{esc(m['outlet'])}{pub}</span>{verdict_chip(m['verdict'])}<a href="{esc(m['article_url'])}" target="_blank" rel="noopener">Read the original &rarr;</a></div>
<p class="b-claim"><b>The claim:</b> {esc(claim)}</p>
<p class="b-why"><b>Why {esc(vlabel.lower())}:</b> {esc(m.get('rating_explained', ''))}</p>
<div class="b-src"><strong>Sources:</strong> {srcs if srcs else "&mdash;"}</div>
</article>"""


def lead_html(m):
    vlabel = VERDICTS.get(m.get("verdict"), VERDICTS["no-claim"])[0]
    srcs = brief_sources(m)
    pub = f" &middot; {esc(m['published'])}" if m.get("published") else ""
    return f"""<section class="leadstory" data-verdict="{m['verdict']}">
<div class="kicker">Top reality check</div>
<a class="lead-head" href="{esc(m['article_url'])}" target="_blank" rel="noopener">{esc(m['headline'])}</a>
<div class="b-meta"><span>{esc(m['outlet'])}{pub}</span>{verdict_chip(m['verdict'])}<a href="{esc(m['article_url'])}" target="_blank" rel="noopener">Read the original &rarr;</a></div>
<p class="b-claim"><b>The claim:</b> {esc(m.get('trending_claim') or 'No checkable factual claim — opinion or analysis.')}</p>
<p class="b-why"><b>Why {esc(vlabel.lower())}:</b> {esc(m.get('rating_explained', ''))}</p>
<div class="b-src"><strong>Sources:</strong> {srcs if srcs else "&mdash;"}</div>
</section>"""


def pick_lead(items):
    # most severe verdict leads; ties broken by order
    return sorted(items, key=lambda m: (SEVERITY.get(m.get("verdict", "no-claim"), 5),
                                        m.get("order", 0)))[0]


def edition_page(date, edition, items, prev_date, next_date):
    sev = lambda m: (SEVERITY.get(m.get("verdict", "no-claim"), 5), m.get("order", 0))
    ordered = sorted(items, key=sev)
    lead = pick_lead(items)
    rest = [m for m in ordered if m["id"] != lead["id"]]
    counts = {v: 0 for v in VERDICTS}
    for m in items:
        counts[m.get("verdict", "no-claim")] = counts.get(m.get("verdict", "no-claim"), 0) + 1
    sb = ('<div class="scoreboard"><span class="sb"><b>' + str(len(items)) + '</b>claims checked</span>' +
          "".join(f'<span class="sb"><b style="color:{VERDICTS[v][1]}">{counts[v]}</b>{VERDICTS[v][0]}</span>'
                  for v in VERDICT_ORDER if counts[v]) + '</div>')
    ver_btns = "".join(f'<button class="fbtn" data-verdict="{v}">{VERDICTS[v][0]}</button>'
                       for v in VERDICT_ORDER)
    nav = []
    if prev_date:
        nav.append(f'<a href="{BASE_URL}/editions/{prev_date}/">&larr; {prev_date}</a>')
    else:
        nav.append('<span></span>')
    if next_date:
        nav.append(f'<a href="{BASE_URL}/editions/{next_date}/">{next_date} &rarr;</a>')
    else:
        nav.append(f'<a href="{BASE_URL}/archive.html">Archive &rarr;</a>')
    feed_html = "\n".join(brief_html(m) for m in rest)
    return (PAGE_TOP.replace("{title}", edition["title"]) + HEADER.replace("{base}", BASE_URL) + f"""
<div class="wrap">
<div class="nameplate">
<div class="np-kicker">Daily Trump fact-check</div>
<div class="np-title">Trump <span class="vs">vs.</span> Reality</div>
<div class="np-tag">Claims about President Trump — checked against named sources. What's claimed vs. what's true.</div>
<div class="np-meta">{esc(edition['date_label'])} &middot; Daily edition</div>
</div>
<div class="podplayer"><div class="pp-kicker">&#127911; Listen to today's episode</div><audio controls preload="none" src="{BASE_URL}/audio/{date}.mp3"></audio><div class="pp-note">Trump Spin Check &mdash; all of today's stories read aloud (~20 min). New episode daily at 6:30 AM ET.</div></div>
{sb}
<div id="filterSrc" hidden>
<button class="fbtn on" data-verdict="all">Any verdict</button>
{ver_btns}
<span class="fcount" id="fcount"></span>
</div>
{lead_html(lead)}
<div class="feed">
{feed_html}
</div>
{HOW}
<div class="ednav">{nav[0]}{nav[1]}</div>
</div>
{FOOTER}""")


def archive_label(edition):
    n = edition.get("story_n", 0)
    return (f"{n} claims about President Trump checked",
            '<span class="kindtag">stories</span>')


def archive_page(items):
    lis = ""
    for d, ed in items:
        desc, tag = archive_label(ed)
        lis += f"""<li><a href="{BASE_URL}/editions/{d}/"><strong style="color:#fff">{esc(ed['title'])}</strong></a>{tag}
<div class="d">{esc(ed['date_label'])} &middot; {desc}</div></li>"""
    return (PAGE_TOP.replace("{title}", "Archive") + HEADER.replace("{base}", BASE_URL) + f"""
<div class="wrap">
<div class="dateline">Archive</div>
<div class="hero"><h1>Past <span class="grad">editions.</span></h1></div>
<ul class="archive-list">{lis}</ul>
</div>
{FOOTER}""")


def load_edition(d):
    edir = os.path.join(EDITIONS, d)
    with open(os.path.join(edir, "edition.json")) as f:
        edition = json.load(f)
    sp = os.path.join(edir, "stories.json")
    if not os.path.exists(sp):
        fail(f"{d}: stories.json not found")
    with open(sp) as f:
        items = json.load(f)
    validate_stories(items, d)
    edition["story_n"] = len(items)
    return edition, items


def main():
    dates = sorted([d for d in os.listdir(EDITIONS)
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", d)
                    and os.path.isdir(os.path.join(EDITIONS, d))
                    and os.path.exists(os.path.join(EDITIONS, d, "edition.json"))],
                   reverse=True)
    if not dates:
        print("no editions", file=sys.stderr)
        sys.exit(1)
    os.makedirs(SITE, exist_ok=True)
    os.makedirs(os.path.join(SITE, "audio"), exist_ok=True)

    editions = {}
    for d in dates:
        edition, items = load_edition(d)
        editions[d] = (edition, items)

    for i, d in enumerate(dates):
        edition, items = editions[d]
        prev_d = dates[i + 1] if i + 1 < len(dates) else None
        next_d = dates[i - 1] if i - 1 >= 0 else None
        out_dir = os.path.join(SITE, "editions", d)
        os.makedirs(out_dir, exist_ok=True)
        html = edition_page(d, edition, items, prev_d, next_d)
        with open(os.path.join(out_dir, "index.html"), "w") as f:
            f.write(html)
        if i == 0:  # latest edition is also the homepage
            with open(os.path.join(SITE, "index.html"), "w") as f:
                f.write(html)

    with open(os.path.join(SITE, "archive.html"), "w") as f:
        f.write(archive_page([(d, editions[d][0]) for d in dates]))
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    total = sum(len(v[1]) for v in editions.values())
    print(f"built {len(dates)} edition(s): {', '.join(dates)} ({total} stories)")


if __name__ == "__main__":
    main()
