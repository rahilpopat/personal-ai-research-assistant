<div align="center">
 
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:00e5c3,50:8b6fd4,100:00e5c3&height=3&section=header" width="100%"/>
 
<br/>
 
<img src="https://capsule-render.vercel.app/api?type=rect&color=0d1117&height=160&text=personal-ai-research-assistant&fontColor=00e5c3&fontSize=28&fontAlignY=45&desc=ANTHROPIC%20CLAUDE%20%C2%B7%20BRAVE%20SEARCH%20%C2%B7%20GITHUB%20API&descAlignY=68&descSize=13&fontFamily=courier" width="100%"/>
 
<br/>
 
[![Python](https://img.shields.io/badge/PYTHON-3.11+-00e5c3?style=flat-square&labelColor=0d1117&color=00e5c3)](https://python.org)
[![Claude](https://img.shields.io/badge/CLAUDE-SONNET%204-8b6fd4?style=flat-square&labelColor=0d1117)](https://anthropic.com)
[![Brave](https://img.shields.io/badge/BRAVE_SEARCH-API-00e5c3?style=flat-square&labelColor=0d1117)](https://brave.com/search/api/)
[![Actions](https://img.shields.io/badge/GITHUB_ACTIONS-AUTOMATED-8b6fd4?style=flat-square&labelColor=0d1117)](https://github.com/features/actions)
[![Cost](https://img.shields.io/badge/DAILY_COST-~$0.13-00e5c3?style=flat-square&labelColor=0d1117)](#cost)
[![License](https://img.shields.io/badge/LICENSE-MIT-8b6fd4?style=flat-square&labelColor=0d1117)](LICENSE)
 
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:00e5c3,50:8b6fd4,100:00e5c3&height=3&section=header" width="100%"/>
 
</div>
 
<br/>
 
## > what_this_is
 
```
Not another newsletter.
A personal agent that reads your GitHub commits and tells you
what you should have built differently.
```
 
Every morning at 07:00 am this pipeline runs automatically and sends you an email like this:
 
```
🔧 smolagents — a minimal Python framework for building AI agents
 
You built this manually: rahilpopat/personal-ai-research-assistant
This could have saved you: 4-6 hours of custom agent scaffolding
With that time: You could have added persistent memory and a feedback loop
 
→ Install: pip install smolagents
```
 
It reads your **actual GitHub commit history**. Every briefing either connects to something you built manually, or is flagged honestly as a forward recommendation. No generic summaries. No filler.
 
<br/>
 
---
 
## > how_it_works
 
```
┌─────────────┐    ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│  1. MONITOR │───▶│  2. SCORE   │───▶│  3. SYNTHESISE   │───▶│  4. DELIVER │
│             │    │             │    │                  │    │             │
│ Brave API   │    │ Claude Haiku│    │  Claude Sonnet   │    │ HTML Email  │
│ GitHub API  │    │ vs profile  │    │  reads commits   │    │ SMTP/SG     │
│ RSS feeds   │    │ + commits   │    │  names your repos│    │ 07:00 UTC   │
└─────────────┘    └─────────────┘    └──────────────────┘    └─────────────┘
  20-50 items         top 8 items          personalised             inbox
```
 
**Stage 1 — Monitor**
Fetches from three source types daily: Brave Search rotating queries, GitHub trending repos (last 7 days, stars > 10), and RSS feeds from Hacker News, Simon Willison, Anthropic Blog, and The Batch. Also fetches your recent public commits as context for the next two stages.
 
**Stage 2 — Score**
Each item scored 0–10 against your `profile.yaml` using Claude Haiku. Extra weight for items that connect to something in your commit history. Only items scoring 7+ pass through.
 
**Stage 3 — Synthesise** ← *the important one*
Claude Sonnet reads your last 40 commits and asks: *"Did this person build something manually that this tool would have done for them?"* Names the repo, estimates hours saved, suggests what to build next. Never fabricates a connection.
 
**Stage 4 — Deliver**
Clean HTML email via GitHub Actions. Also writes `output/DAILY-INTEL.md` — a plain text version future agents can read.
 
<br/>
 
---
 
## > quickstart
 
**1. Fork and clone**
```bash
git clone https://github.com/YOUR_USERNAME/personal-ai-research-assistant
cd personal-ai-research-assistant
pip install -r requirements.txt
cp .env.example .env
```
 
**2. Get your API keys**
 
| Key | Where | Free? |
|-----|-------|-------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Pay per use (~$0.13/day) |
| `BRAVE_API_KEY` | [api.search.brave.com](https://api.search.brave.com) | 2,000 req/month free |
| `GITHUB_TOKEN` | GitHub → Settings → Developer Settings → PAT | Free |
| `SMTP_PASS` | Google Account → Security → App Passwords | Free |
 
**3. Fill in `.env`**
```bash
ANTHROPIC_API_KEY=sk-ant-...
BRAVE_API_KEY=BSA...
GITHUB_TOKEN=github_pat_...
EMAIL_TO=you@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=xxxx-xxxx-xxxx-xxxx   # Gmail App Password, not your account password
```
 
**4. Personalise your profile**
 
Edit `config/profile.yaml` — this is what the agent scores against:
```yaml
user:
  name: Your Name
  github: your-github-handle     # your public commits are read automatically
 
learning_objectives:
  - what you're trying to learn
 
active_projects:
  - what you're currently building
 
exclude:
  - topics you don't care about
```
 
Edit `config/sources.yaml` to add Brave queries, GitHub topics, and RSS feeds for your domain.
 
**5. Test it locally**
```bash
# Full pipeline, no email sent
python run.py --dry-run
 
# Run one stage at a time
python run.py --stage monitor
python run.py --stage scorer
python run.py --stage synthesiser
 
# Send the real email
python run.py
```
 
**6. Automate with GitHub Actions**
 
Add each key from `.env` as a GitHub Actions secret:
```
Repo → Settings → Secrets and variables → Actions → New repository secret
```
Add: `ANTHROPIC_API_KEY` `BRAVE_API_KEY` `GITHUB_TOKEN` `EMAIL_TO` `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASS`
 
The workflow in `.github/workflows/daily-digest.yml` runs at 07:00 UTC every day.
Trigger manually anytime from the Actions tab.
 
<br/>
 
---
 
## > repo_structure
 
```
personal-ai-research-assistant/
├── run.py                      ← entrypoint
├── config/
│   ├── profile.yaml            ← YOUR skills, goals, projects — edit this
│   └── sources.yaml            ← sources to monitor — edit this
├── src/
│   ├── monitor.py              ← Stage 1: fetch items
│   ├── scorer.py               ← Stage 2: score vs profile + commits
│   ├── synthesiser.py          ← Stage 3: write personalised briefings
│   └── digest.py               ← Stage 4: render + send email
├── templates/
│   └── email.html.j2           ← email template
├── output/
│   └── DAILY-INTEL.md          ← plain text digest (other agents read this)
├── docs/
│   └── DECISIONS.md            ← build log
├── .github/
│   └── workflows/
│       └── daily-digest.yml    ← runs at 07:00 UTC daily
├── .env.example
└── requirements.txt
```
 
<br/>
 
---
 
## > cost
 
```
Stage 2 — Scoring ~50 items     claude-haiku-4-5-20251001    ~$0.09/day
Stage 3 — Synthesising 8 items  claude-sonnet-4-20250514     ~$0.04/day
Brave Search                    free tier                     $0.00/day
GitHub API                      free                          $0.00/day
──────────────────────────────────────────────────────────────────────
Total                                                         ~$0.13/day
                                                              ~$4.00/month
```
 
<br/>
 
---
 
## > the_design_principle
 
```
The synthesiser's job is not to summarise articles.
 
It is to answer:
"What did you build manually that this tool would have done for you?"
 
If the answer is something — it names the repo, names the commit,
estimates the hours.
 
If the answer is nothing — it says so. Never fabricates.
 
Generic output means the commit history isn't reaching the prompt.
That's a data problem, not a writing problem.
```
 
<br/>
 
---
 
## > what_comes_next
 
This is Phase 1 — the daily digest. Once validated (2 weeks, open rate > 60%):
 
- 🤖 **Phase 2** — OpenClaw skill for Telegram on-demand access
- ✍️  **Phase 3** — Writer agent that drafts LinkedIn posts from `DAILY-INTEL.md`
- 🗂️  **Phase 4** — Chief of Staff agent for weekly planning briefs
 
Each agent reads from `output/DAILY-INTEL.md`. No API calls between agents. Just files.
 
<br/>
 
---
 
## > built_with
 
[![Anthropic](https://img.shields.io/badge/Anthropic_Claude-CC785C?style=flat-square&labelColor=0d1117&logo=anthropic)](https://anthropic.com)
[![Brave](https://img.shields.io/badge/Brave_Search_API-FB542B?style=flat-square&labelColor=0d1117&logo=brave)](https://api.search.brave.com)
[![PyGitHub](https://img.shields.io/badge/PyGitHub-181717?style=flat-square&labelColor=0d1117&logo=github)](https://pygithub.readthedocs.io)
[![feedparser](https://img.shields.io/badge/feedparser-00e5c3?style=flat-square&labelColor=0d1117)](https://feedparser.readthedocs.io)
[![Jinja2](https://img.shields.io/badge/Jinja2-B41717?style=flat-square&labelColor=0d1117)](https://jinja.palletsprojects.com)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&labelColor=0d1117&logo=github-actions)](https://github.com/features/actions)
 
<br/>
 
---
 
<div align="center">
 
MIT — fork it, personalise it, make it yours.
 
If you build something with this, open an issue or find me at [github.com/rahilpopat](https://github.com/rahilpopat)
 
<br/>
 
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:8b6fd4,50:00e5c3,100:8b6fd4&height=3&section=footer" width="100%"/>
 
</div>
