# AI Research Assistant — CLAUDE.md

Read this file fully before writing any code.
Check `docs/DECISIONS.md` at the start of every session to see where we left off.

---

## What We Are Building

A Python pipeline that runs once daily and sends a personalised email digest.

The output format for every item is:

> "Hey Rahil — there's a new GitHub repo that lets you do X. You actually built this
> manually when you worked on Y. If you'd used this tool it could have saved you Z time,
> and with that time you could have built W. Here's the link and here's how to get started."

This is not a generic newsletter. Every item must either:
- Connect to something in Rahil's actual GitHub commit history, OR
- Be flagged explicitly as a forward recommendation (not a retroactive match)

If an item could have been written for anyone, it should not be in the digest.

---

## Working Practices

1. **Always work in the project folder**
   ```bash
   cd ~/ai-research-assistant
   claude
   ```

2. **Let Claude Code run and fix things itself**
   Say: "run this and fix any errors" — never paste errors back manually.

3. **Commit after every session**
   Say: "commit everything with a descriptive message"
   Never end a session without committing.

4. **Start every session by reading context**
   Say: "read CLAUDE.md and docs/DECISIONS.md and tell me where we left off"

5. **Update DECISIONS.md at end of every session**
   Say: "update docs/DECISIONS.md with what we built today"

6. **One thing at a time**
   One module per session. Build it. Test it. Commit. Move on.

7. **Always dry-run first**
   ```bash
   python run.py --dry-run
   ```
   Prints email HTML to terminal. Never send a real email until dry-run looks right.

8. **Test each stage standalone before wiring together**
   Every `src/*.py` module must run on its own and print real output.

---

## Repo Structure

```
ai-research-assistant/
├── CLAUDE.md                    ← this file
├── run.py                       ← entrypoint: python run.py --dry-run
├── config/
│   ├── profile.yaml             ← Rahil's goals, skills, active projects
│   └── sources.yaml             ← sources to monitor
├── src/
│   ├── __init__.py
│   ├── monitor.py               ← Stage 1: fetch from Brave, GitHub, RSS
│   ├── scorer.py                ← Stage 2: score vs profile + commits
│   ├── synthesiser.py           ← Stage 3: write personalised brief per item
│   └── digest.py                ← Stage 4: render HTML email + send
├── templates/
│   └── email.html.j2            ← Jinja2 email template
├── docs/
│   └── DECISIONS.md             ← session log — read at start, update at end
├── tests/
│   ├── test_monitor.py
│   └── test_scorer.py
├── logs/                        ← daily run logs (git-ignored)
├── .env.example
├── .env                         ← never commit this
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Session Plan

Complete in order. Do not move to the next session until the verify step passes.

---

### Session 1 — Scaffold + Config

**Goal:** Repo structure exists, config files populated, run.py runs cleanly.

**Build:**
1. Create all folders and empty `__init__.py` files
2. Write `config/profile.yaml` — copy exactly from Config section below
3. Write `config/sources.yaml` — copy exactly from Config section below
4. Write `run.py` — orchestrator shell, stages stubbed, logs start/end time
5. Write `requirements.txt` — copy from Dependencies section below
6. Write `.env.example` — copy from Environment Variables section below
7. Write `.gitignore` — ignore `.env`, `logs/`, `__pycache__/`, `.DS_Store`
8. Write `docs/DECISIONS.md` — session log template
9. Write `README.md` — setup: clone, pip install, cp .env, python run.py --dry-run

**Verify:**
```bash
pip install -r requirements.txt
python run.py --dry-run
```
Must complete without errors and print a run summary.

---

### Session 2 — monitor.py

**Goal:** Fetch 20–50 real deduplicated items from all three source types.

**Brave Search:**
- Endpoint: `https://api.search.brave.com/res/v1/web/search`
- Header: `X-Subscription-Token: {BRAVE_API_KEY}`
- Params: `q={query}&count=5&freshness=pd`
- Run each query in `sources.yaml brave_queries`

**GitHub Trending:**
- PyGitHub search: `created:>={7_days_ago} topic:{topic} stars:>10`
- For each topic in `sources.yaml github_topics`
- Also fetch last 10 starred repos for `rahilpopat` as `starred_signal`

**Recent Commits — MOST IMPORTANT:**
- GitHub Events API: `GET /users/rahilpopat/events/public?per_page=100`
- Filter `PushEvent` only
- Extract per commit: `repo`, `message` (first line, max 120 chars), `date`
- Store as `recent_commits` — passed to scorer + synthesiser
- If commits = 0 after fetch, something is broken. Fix before moving on.

**RSS Feeds:**
- feedparser for each feed in `sources.yaml rss_feeds`
- Strip HTML from summaries with BeautifulSoup

**Output format:**
```python
{
    "title": str,
    "url": str,
    "summary": str,    # max 400 chars, HTML stripped
    "source": str,     # "brave" | "github" | feed name
    "published": str,
    "stars": int,
}
```

**Verify:**
```bash
python -m src.monitor
```
Prints 20–50 items AND shows commit count. Commits must be > 0.

---

### Session 3 — scorer.py

**Goal:** Score each item 0–10 against profile + commit history. Return top 5–8.

**Pre-filter (free):** Drop items matching `profile.yaml exclude` list, title < 10 chars, no summary.

**Claude Haiku scoring:**
- Model: `claude-haiku-4-5-20251001`, max_tokens: 100
- Return JSON: `{"score": 7, "reason": "one sentence"}`
- System prompt includes: full profile + last 30 commits + scoring guide
- 10 = connects to recent commit/project. 0–3 = not relevant.

**Starred signal boost:** topics from starred repos → +1 to matching items (cap 10)

**Selection:** score >= SCORE_THRESHOLD (default 7), top MAX_ITEMS (default 8)

**Cost logging:** input tokens + output tokens + estimated USD → `logs/YYYY-MM-DD.log`

**Verify:**
```bash
python -m src.scorer
```
Returns 5–8 items. Read the `reason` field.
If reasons are generic ("relevant to AI interests") — commit history is not
reaching the prompt. Fix this. Do not move to Session 4 until reasons
reference something specific from the profile or commits.

---

### Session 4 — synthesiser.py

**Goal:** Each item gets a briefing that names something Rahil actually built.

**One Claude Sonnet call per item:**
- Model: `claude-sonnet-4-20250514`, max_tokens: 400, temperature: 0

**System prompt:**
```
You are a personal AI research assistant for Rahil Popat.
You have his GitHub commit history.

Your job: does this new tool connect to something Rahil built manually?

If YES — write:
1. What the tool does (one sentence)
2. Which specific repo/commit this replaces (name it exactly)
3. How much time it could have saved (be specific)
4. What he could build with that saved time
5. How to start RIGHT NOW (one command or URL — not "read the docs")

If NO genuine match — write a forward recommendation.
Never fabricate a connection.

Return ONLY valid JSON:
{
  "headline": "one sentence — what this does and why it matters to Rahil",
  "built_connection": "specific repo/commit or null",
  "time_saved": "specific estimate or null",
  "what_next": "what he could build now or null",
  "action": "exact command or URL",
  "action_label": "Clone / Install / Try / Read",
  "forward_only": true or false
}
```

**User message must include:**
- Last 40 commits as `[date] repo — message`
- Active projects from profile
- Learning goals from profile
- Item title, URL, summary, score reason

**Verify:**
```bash
python -m src.synthesiser
```
Print 3 items. Read them out loud.
Item 1 must name a specific repo or commit message.
If generic — commit data is not in the prompt. Fix before Session 5.

---

### Session 5 — digest.py + email template + wire everything

**Goal:** Full pipeline runs end to end. Real email arrives in inbox.

**email.html.j2:**
- Inline CSS only (Gmail strips `<style>` blocks)
- Max width 600px
- Per item: score badge, headline, commit connection block (if not forward_only), action CTA button
- Commit connection block:
  ```
  You built this manually: {built_connection}
  This could have saved you: {time_saved}
  With that time: {what_next}
  ```
- Footer: "AI Research Assistant · github.com/rahilpopat"

**digest.py:**
- Render Jinja2 template
- Send via smtplib (SMTP) or SendGrid if `SENDGRID_API_KEY` set
- `--dry-run`: print HTML to stdout, send nothing
- Write `output/DAILY-INTEL.md` — plain text for future agents

**run.py — wire all 4 stages:**
```python
items, starred, commits = monitor.fetch_all()
scored, score_cost      = scorer.score_items(items, commits, starred)
synthesised, synth_cost = synthesiser.synthesise(scored, commits)
digest.deliver(synthesised, dry_run=dry_run)
```

Each stage in try/except. Log failures. If scorer returns 0 → send quiet day email.

**Verify:**
```bash
python run.py --dry-run   # read HTML output — does item 1 name a real repo?
python run.py             # send for real — check inbox
```
Open the email. Read item 1. That's the acceptance test.

---

### Session 6 — GitHub Actions + hardening

**Goal:** Pipeline runs automatically every morning.

**.github/workflows/daily-digest.yml:**
```yaml
name: Daily AI Research Digest
on:
  schedule:
    - cron: '0 7 * * *'
  workflow_dispatch:
jobs:
  run-digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run digest
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          BRAVE_API_KEY: ${{ secrets.BRAVE_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          EMAIL_TO: ${{ secrets.EMAIL_TO }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
        run: python run.py
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: digest-log-${{ github.run_id }}
          path: logs/
```

**Verify:** Push → Actions → Run workflow manually → green → email arrives.

---

## Config Files

### config/profile.yaml
```yaml
user:
  name: Rahil Popat
  github: rahilpopat
  role: AI Product Manager transitioning to AI Builder

current_skills:
  - Python (intermediate)
  - Claude API and Anthropic SDK
  - Prompt engineering
  - Product strategy

learning_objectives:
  - Claude Code — building real projects end to end
  - Agentic system design — multi-agent, memory, tool use, MCP servers
  - Shipping Python projects to GitHub
  - LLM evaluation patterns and frameworks
  - Building in public

active_projects:
  - AI Research Assistant (this project)
  - AXIS — personal AI research chat tool with GitHub skill-gap loop
  - one-person-ai-company — agent system template repo
  - FBA wholesale automation (Mountain View Global Ltd)

interests:
  - AI product strategy
  - LLM benchmarks and capability evaluations
  - MCP servers and tool ecosystems
  - Open source AI tooling
  - Claude Code workflows
  - Agentic AI patterns — planning, memory, reflection, tool use

exclude:
  - healthcare AI
  - medical imaging
  - drug discovery
  - image generation
  - diffusion models
  - stable diffusion
  - AI hardware specs
  - gaming AI
  - robotics
  - autonomous vehicles
```

### config/sources.yaml
```yaml
brave_queries:
  - "Claude API new features 2025"
  - "LLM agent framework open source"
  - "MCP model context protocol server"
  - "agentic AI Python tools"
  - "Claude Code tips workflows"
  - "LLM evaluation framework"
  - "Anthropic announcement"
  - "multi-agent systems tutorial"
  - "AI developer tools launch"

github_topics:
  - llm-agents
  - mcp-server
  - claude-api
  - anthropic
  - langchain
  - langgraph
  - openai-agents
  - ai-assistant
  - prompt-engineering
  - llm-tools

rss_feeds:
  - url: "https://hnrss.org/frontpage?q=LLM+AI+agent+Claude"
    name: "Hacker News AI"
  - url: "https://simonwillison.net/atom/everything/"
    name: "Simon Willison"
  - url: "https://www.anthropic.com/news/rss.xml"
    name: "Anthropic Blog"
  - url: "https://www.deeplearning.ai/the-batch/feed/"
    name: "The Batch"
  - url: "https://buttondown.com/ainews/rss"
    name: "AI News"
```

---

## Environment Variables (.env.example)

```bash
ANTHROPIC_API_KEY=sk-ant-...
BRAVE_API_KEY=BSA...
GITHUB_TOKEN=github_pat_...
EMAIL_TO=your@email.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your-app-password   # Gmail App Password — not your account password
                               # Get it: Google Account → Security → App Passwords
SENDGRID_API_KEY=              # optional alternative to SMTP
SCORE_THRESHOLD=7
MAX_ITEMS=8
TARGET_COST_DAILY=1.00
DRY_RUN=false
```

---

## Dependencies (requirements.txt)

```
anthropic>=0.40.0
requests>=2.31.0
PyGithub>=2.1.1
feedparser>=6.0.11
jinja2>=3.1.4
pyyaml>=6.0.1
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
sendgrid>=6.11.0
```

---

## Coding Standards

- Type hints on all function signatures
- Docstrings on all public functions
- No bare `except` — catch specific exceptions, always log them
- Secrets via environment variables + python-dotenv, never hardcoded
- Log to stdout AND `logs/YYYY-MM-DD.log` via Python `logging` module
- Every `src/*.py` runnable standalone with `if __name__ == "__main__"`
- `python run.py --dry-run` always works without sending email

---

## The One Rule That Matters

The synthesiser's job is NOT to summarise articles.

It is to answer: **"What did Rahil build manually that this tool would have done for him?"**

If the answer is something — name the repo, name the commit, estimate the hours.
If the answer is nothing — say so. Frame it as a forward recommendation.

Generic output = commit history is not reaching the prompt.
Fix the data flow, not the wording.

---

## Phase 2 Gate

Do not build anything else until these pass for 2 consecutive weeks:

- [ ] Email open rate > 60%
- [ ] ≥ 2 items/week lead to a concrete action
- [ ] < 3 items/digest rated "not relevant"
- [ ] API cost < $1.00/day
- [ ] GitHub Actions > 90% success rate

When these pass: add OpenClaw Telegram interface, then Writer agent, then Chief of Staff.
