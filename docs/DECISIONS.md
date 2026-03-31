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

**Next session:** Session 2 — implement `src/monitor.py` (Brave, GitHub, RSS fetching)
