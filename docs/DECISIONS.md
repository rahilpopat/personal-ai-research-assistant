# Decisions Log

## Session 1 — Scaffold + Config (2026-03-31)

**What we built:**
- Project scaffold: all folders, config files, stubbed modules
- `config/profile.yaml` — Rahil's goals, skills, active projects
- `config/sources.yaml` — Brave queries, GitHub topics, RSS feeds
- `run.py` — orchestrator shell with stubbed stages, --dry-run support
- `requirements.txt`, `.env.example`, `.gitignore`, `README.md`

**Decisions made:**
- Python logging to both stdout and `logs/YYYY-MM-DD.log`
- Each stage stubbed to return empty lists; wired in Session 5
- `--dry-run` flag controls email sending (default: uses DRY_RUN env var)

---

## Session 2 — Monitor (2026-03-31)

**What we built:**
- `src/monitor.py` — four fetchers: Brave Search, GitHub Trending, Recent Commits, RSS
- Brave: 45 results from 9 queries, freshness=pd
- GitHub: PyGitHub search by topic (stars>10, created last 7 days), 28 repos from 10 topics
- Commits: Events API with fallback to repo commits API (Events API returns empty payloads for this account)
- RSS: feedparser + BeautifulSoup HTML stripping, 20 items from 5 feeds
- Deduplication by URL, 89 total items

**Decisions made:**
- Events API `commits` array comes back empty — added fallback to `/repos/{repo}/commits` API
- PyGitHub `PaginatedList` can't be sliced — iterate with counter instead
- Updated `Github()` constructor to use `auth=Auth.Token(token)` (old positional arg deprecated)

---

## Session 3 — Scorer (2026-03-31)

**What we built:**
- `src/scorer.py` — pre-filter + Claude Haiku scoring + starred boost + selection
- Pre-filter drops exclude-list matches, short titles, empty summaries (3 dropped)
- Haiku system prompt includes full profile.yaml text + last 30 commits
- Scoring guide: 10 = connects to recent commit, 0-3 = not relevant
- Starred signal boost: +1 for items matching starred repo topics (cap 10)
- Selection: score >= 7, top 8 items sorted descending
- Cost logging to `logs/YYYY-MM-DD.log`

**Decisions made:**
- Haiku returns JSON wrapped in markdown code fences — added stripping before `json.loads`
- All 8 selected items scored 9/10 with specific reasons referencing repos and learning objectives
- Scoring cost: ~$0.09 per run (well under $1/day target)

---

## Session 4 — Synthesiser (2026-03-31)

**What we built:**
- `src/synthesiser.py` — one Claude Sonnet call per scored item
- System prompt instructs: find commit connection, name repo, estimate time saved, suggest next build
- User message includes last 40 commits, active projects, learning goals, item details + score reason
- Returns structured JSON: headline, built_connection, time_saved, what_next, action, forward_only
- 8/8 items connected to real repos (personal-ai-research-assistant, bmad-project)

**Decisions made:**
- Sonnet also wraps JSON in code fences — reused same stripping logic
- Synthesis cost: ~$0.04 per run
- Total pipeline cost: ~$0.13 per run

---

## Session 5 — Digest + Email + Full Pipeline (2026-03-31)

**What we built:**
- `templates/email.html.j2` — inline CSS, 600px max width, score badges (green 9-10, teal 7-8), commit connection blocks, CTA buttons, footer
- `src/digest.py` — Jinja2 rendering, SMTP sending, SendGrid fallback, dry-run mode, DAILY-INTEL.md output
- `run.py` — wired all 4 stages with try/except, quiet day handling, total cost logging

**Decisions made:**
- SMTP with Gmail App Password for email delivery
- SendGrid as optional fallback (checked via SENDGRID_API_KEY env var)
- Quiet day: if scorer returns 0 items, send a "quiet day" email instead of crashing
- `output/DAILY-INTEL.md` written as plain text for future agents

**Verify result:**
- `python run.py --dry-run` — full pipeline completes, HTML renders with 8 connected items
- `python run.py` — real email delivered to inbox via SMTP
- Pipeline: ~209s, $0.14 total cost
- All 8 items name specific repos from commit history

**Next session:** Session 6 — GitHub Actions workflow + hardening
