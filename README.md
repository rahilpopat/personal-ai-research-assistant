# AI Research Assistant

A Python pipeline that runs once daily and sends a personalised email digest connecting new AI tools and research to your actual GitHub commit history.

## Setup

```bash
git clone https://github.com/rahilpopat/personal-ai-research-assistant.git
cd personal-ai-research-assistant
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

## Usage

```bash
# Dry run — prints email HTML to terminal, sends nothing
python run.py --dry-run

# Send for real
python run.py
```

## How It Works

1. **Monitor** — Fetches items from Brave Search, GitHub Trending, and RSS feeds
2. **Score** — Scores each item against your profile and recent GitHub commits using Claude Haiku
3. **Synthesise** — Writes a personalised briefing per item using Claude Sonnet, connecting to your actual work
4. **Digest** — Renders HTML email and sends it

## API Keys Needed

- `ANTHROPIC_API_KEY` — for Claude scoring and synthesis
- `BRAVE_API_KEY` — for web search
- `GITHUB_TOKEN` — for GitHub API access
- SMTP credentials or `SENDGRID_API_KEY` — for email delivery
