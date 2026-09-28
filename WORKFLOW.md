# Trump vs Reality — daily runbook (4:30 AM ET)

Run every day at 4:30 AM America/New_York. Today's date = the edition date.

Site: https://phoenixbyrd.github.io/trump-reality-check/
Repo: https://github.com/phoenixbyrd/trump-reality-check (local: ~/workspace/trump-reality-check)
Companion podcast: Trump Spin Check (cron `trump-spin-check-daily`, 6:30 AM ET).

## House rules (never break these)

- **Honest verdicts, both directions.** A biased outlet can still report facts accurately — when the claim holds up, it gets `accurate`, full stop. The mission is "what's factual and what isn't", not debunking everything. Never downgrade accurate reporting, never manufacture wrongdoing.
- **Facts only.** Check each story's central claim against NAMED, published sources (e.g. AP, Reuters, agencies, court filings, official transcripts). Never infer motive or intent. Never attribute feelings or opinions that weren't explicitly stated.
- **Attribute and admit.** State what's disputed or unknown. If a claim can't be verified either way, say so — don't guess.
- **Verify the EVENT, not just that it was said.** "X claims Y happened," repeated by outlets, verifies only that X made the claim — it does not verify Y. Label a claim `accurate` only when the underlying event is confirmed by direct evidence: primary documents, official records/data, direct video/audio, on-the-ground wire reporting (AP/Reuters), or authoritative datasets. A claim echoed across outlets that cite each other, a lone anonymous "sources say," or a viral social-media assertion is NOT event verification. When the event itself can't be verified, the verdict is `mixed` at best — state exactly what is and isn't verified in `rating_explained`. Never upgrade "someone said it" into "it's true." (Symmetrically: absence of confirmation alone doesn't make a claim `false` — `false` needs contradicting evidence.)
- **Explain every rating.** `rating_explained` must walk through the evidence step by step: what the story asserts, what the named sources actually say (with key numbers/dates), and the explicit reasoning from evidence to verdict. A verdict without a visible evidence trail is a failed card.
- **Opinions are opinions.** Pure opinion/analysis pieces with no checkable factual claim get verdict `no-claim` ("Opinion — no checkable claim"), never a fake verdict.
- **Never fabricate.** Every `article_url` must be a real page that was opened and confirmed to match the headline. Never invent headlines, links, claims, ratings, sources, or trending context.
- **Focus:** claims ABOUT President Trump — actions attributed to him, quotes attributed to him. Mostly from outlets critical of him, but the check is the claim, not the outlet.

## Verdicts

`accurate` · `mostly-accurate` · `mixed` · `misleading` · `false` · `no-claim`

## Pipeline

### 1. Source stories (target: up to 100; quality bar governs)

Spawn research subagents in parallel across topic clusters (foreign policy/national security, DOJ/FBI/executive power, economy/domestic policy, politics/media/culture). Sources: Ground News trending, Memeorandum, Google News top stories, most-read pages at HuffPost / Daily Kos / MSNBC / MeidasTouch / Crooks and Liars / Raw Story / Common Dreams / Mother Jones / Media Matters, r/politics rising/hot. Search "Trump" filtered to the last 2 days.

Each story must clear ALL of these:
1. Genuinely trending in the last ~48h (most-read, most-shared, leading an aggregator — record the evidence in `trending_context`).
2. Newsworthy and about Trump (action attributed, quote attributed).
3. Has a central checkable factual claim.

**Never pad with filler to hit 100** — publish only what clears the bar and report the honest count in `edition.json` `description`.

**Selection target: roughly 50/50.** About half the edition should be claims that hold up (`accurate`/`mostly-accurate` — what to believe) and about half should be claims that don't (`misleading`/`false` — what not to believe), with a healthy share of the latter being *demonstrably false* claims where `rating_explained` shows exactly why they're false. This is a selection priority, not a verdict quota: actively hunt for strong examples of both kinds — true stories that deserve belief AND false stories that deserve debunking. Never force or soften a verdict to hit the ratio; if a day's checkable claims skew one way, publish what the evidence supports and report the actual split honestly.

Each story needs: exact `headline`, `outlet` name, `article_url` (opened and verified), `published` date, `trending_claim` (the central assertion as it circulates, 1–2 sentences), `trending_context` (1 sentence on why it's trending).

### 2. Fact-check

Split the story list across fact-check subagents (e.g. 15–20 each). Each returns, per story:
- `trending_claim` (confirm or sharpen what the story actually asserts)
- `verdict`
- `rating_explained` (3–6 sentences / 400+ characters: what the story asserts → what the named sources actually say with key numbers/dates → why this verdict follows)
- `sources` (2+ NAMED sources with real URLs that were opened — wire services, agencies, primary documents; the original article itself doesn't count as a fact-check source)

Cross-check the established fact-checkers: before finalizing a verdict, check whether Snopes, PolitiFact, FactCheck.org, Reuters Fact Check, or AP Fact Check have already rated the same claim. If they have, cite the relevant one as a corroborating source — but still verify against primary sources yourself; a fact-checker's verdict is a lead, not the evidence. If fact-checkers disagree with each other or with the primary sources, say so in `rating_explained` and let the verdict reflect the disagreement.

### 3. Assemble edition

Write `editions/<YYYY-MM-DD>/stories.json` — array of:
```json
{"id": "T01", "headline": "...", "outlet": "HuffPost",
 "article_url": "https://...", "published": "2026-09-27",
 "trending_claim": "...", "verdict": "mixed",
 "rating_explained": "...", "sources": [{"name": "Associated Press", "url": "https://..."}],
 "trending_context": "Most-read on HuffPost; 6k shares in 24h.", "order": 1}
```
IDs: `T01`… sequential, `order` sequential.

Write `editions/<YYYY-MM-DD>/edition.json`:
```json
{"kind": "stories", "title": "September 28, 2026", "date_label": "Monday, September 28, 2026",
 "description": "37 trending claims about President Trump, each checked against named sources."}
```

### 4. Validate

`python3 build.py` validates every story (required fields, verdict values, URL shape, explanation length, no metadata leakage) and **fails loudly** — a failed build means the edition is not publishable; fix the data, don't weaken the checks.

Link-check every `article_url`:
```
python3 - <<'EOF'
import json, urllib.request
d = "<YYYY-MM-DD>"
for m in json.load(open(f"editions/{d}/stories.json")):
    req = urllib.request.Request(m["article_url"], headers={"User-Agent": "Mozilla/5.0"})
    try:
        r = urllib.request.urlopen(req, timeout=20)
        print(r.status, m["id"], m["article_url"][:80])
    except Exception as e:
        print("ERROR", m["id"], m["article_url"][:80], str(e)[:100])
EOF
```

### 5. Publish

`git add -A && git commit -m "Edition <YYYY-MM-DD>: <N> Trump claims checked" && git push origin main`
Curl-verify: `curl -s https://phoenixbyrd.github.io/trump-reality-check/ | grep -c '<article class="brief"'` should equal the story count (allow ~2 min for Pages).

### 6. Podcast handoff

The 6:30 AM `trump-spin-check-daily` cron reads `editions/<today>/stories.json`, generates the Trump Spin Check episode, uploads it to Drive, and copies the MP3 to `docs/audio/<YYYY-MM-DD>.mp3` + commits + pushes (this wires up the edition page's player). The site job does NOT generate audio.

## Mobile UX notes

- Header hides on scroll down, returns on scroll up.
- Hamburger (top-right, always visible) opens the drawer: nav links + verdict filter + story count.
- Podcast player sits under the nameplate on every edition page.
