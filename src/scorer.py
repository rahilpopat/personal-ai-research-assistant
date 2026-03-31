"""Stage 2: Score items against profile and commit history."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic
import yaml
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"
LOG_DIR = Path(__file__).parent.parent / "logs"

MODEL = "claude-haiku-4-5-20251001"
SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", "7"))
MAX_ITEMS = int(os.getenv("MAX_ITEMS", "8"))

# Haiku pricing per million tokens
HAIKU_INPUT_COST = 0.80 / 1_000_000
HAIKU_OUTPUT_COST = 4.00 / 1_000_000


def _load_profile() -> dict[str, Any]:
    """Load profile.yaml."""
    with open(CONFIG_DIR / "profile.yaml") as f:
        return yaml.safe_load(f)


def _load_profile_text() -> str:
    """Load profile.yaml as raw text for the prompt."""
    with open(CONFIG_DIR / "profile.yaml") as f:
        return f.read()


def _format_commits(commits: list[dict], limit: int = 30) -> str:
    """Format commits as [date] repo — message lines."""
    lines = []
    for c in commits[:limit]:
        date = c.get("date", "")[:10]
        repo = c.get("repo", "")
        message = c.get("message", "")
        lines.append(f"[{date}] {repo} — {message}")
    return "\n".join(lines)


def pre_filter(items: list[dict], profile: dict) -> list[dict]:
    """Drop items matching exclude list, short titles, or missing summaries."""
    exclude = [term.lower() for term in profile.get("exclude", [])]
    filtered = []
    dropped = 0

    for item in items:
        title = item.get("title", "")
        summary = item.get("summary", "")

        # Drop: title too short
        if len(title) < 10:
            dropped += 1
            continue

        # Drop: no summary
        if not summary.strip():
            dropped += 1
            continue

        # Drop: matches exclude list
        text_lower = f"{title} {summary}".lower()
        if any(term in text_lower for term in exclude):
            dropped += 1
            continue

        filtered.append(item)

    logger.info("  Pre-filter: %d items kept, %d dropped", len(filtered), dropped)
    return filtered


def _build_system_prompt(profile_text: str, commits_text: str) -> str:
    """Build the scoring system prompt with profile and commit history."""
    return f"""You are a relevance scorer for a personalised AI research digest for Rahil Popat.

Here is Rahil's full profile:

{profile_text}

Here are Rahil's recent GitHub commits:

{commits_text}

SCORING GUIDE:
- 10: Directly connects to a recent commit or active project (name the specific repo or commit)
- 8-9: Strongly relevant to current learning objectives or active projects
- 6-7: Relevant to stated interests but no direct project connection
- 4-5: Tangentially related to AI/tech interests
- 0-3: Not relevant or matches exclude list

IMPORTANT: Your reason MUST reference something specific — a repo name, a commit message, a project name, or a learning objective from the profile. Never write generic reasons like "relevant to AI interests". Be specific about WHY this matters to Rahil.

Return ONLY valid JSON: {{"score": <0-10>, "reason": "<one specific sentence>"}}"""


def score_single_item(
    client: anthropic.Anthropic,
    item: dict,
    system_prompt: str,
) -> tuple[dict, int, int]:
    """Score a single item with Claude Haiku. Returns (result, input_tokens, output_tokens)."""
    user_msg = f"""Score this item for Rahil's digest:

Title: {item['title']}
URL: {item['url']}
Source: {item['source']}
Summary: {item['summary']}
Stars: {item.get('stars', 0)}"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": user_msg}],
            system=system_prompt,
        )
        text = response.content[0].text.strip()
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        # Parse JSON response
        result = json.loads(text)
        score = int(result.get("score", 0))
        reason = result.get("reason", "")

        return {"score": score, "reason": reason}, input_tokens, output_tokens

    except json.JSONDecodeError:
        logger.error("  Failed to parse JSON from Haiku for '%s': %s", item['title'][:50], text)
        return {"score": 0, "reason": "parse error"}, 0, 0
    except anthropic.APIError as e:
        logger.error("  Haiku API error for '%s': %s", item['title'][:50], e)
        return {"score": 0, "reason": "api error"}, 0, 0


def apply_starred_boost(
    scored_items: list[dict],
    starred: list[dict],
) -> list[dict]:
    """Boost scores for items matching topics from starred repos."""
    starred_topics: set[str] = set()
    for repo in starred:
        for topic in repo.get("topics", []):
            starred_topics.add(topic.lower())

    if not starred_topics:
        return scored_items

    for item in scored_items:
        text_lower = f"{item['title']} {item['summary']}".lower()
        if any(topic in text_lower for topic in starred_topics):
            old_score = item["score"]
            item["score"] = min(10, item["score"] + 1)
            if item["score"] != old_score:
                item["reason"] += " (+1 starred boost)"

    return scored_items


def score_items(
    items: list[dict],
    commits: list[dict],
    starred: list[dict],
) -> tuple[list[dict], dict]:
    """Score and filter items. Returns (scored_items, cost_info)."""
    profile = _load_profile()
    profile_text = _load_profile_text()
    commits_text = _format_commits(commits, limit=30)

    # Pre-filter
    filtered = pre_filter(items, profile)

    # Build system prompt
    system_prompt = _build_system_prompt(profile_text, commits_text)

    # Score each item with Haiku
    client = anthropic.Anthropic()
    total_input = 0
    total_output = 0

    scored: list[dict] = []
    for i, item in enumerate(filtered):
        result, inp, out = score_single_item(client, item, system_prompt)
        total_input += inp
        total_output += out

        scored_item = {**item, "score": result["score"], "reason": result["reason"]}
        scored.append(scored_item)

        if (i + 1) % 10 == 0:
            logger.info("  Scored %d/%d items...", i + 1, len(filtered))

    logger.info("  Scored all %d items", len(scored))

    # Apply starred signal boost
    scored = apply_starred_boost(scored, starred)

    # Select top items above threshold
    above_threshold = [item for item in scored if item["score"] >= SCORE_THRESHOLD]
    above_threshold.sort(key=lambda x: x["score"], reverse=True)
    selected = above_threshold[:MAX_ITEMS]

    logger.info("  %d items >= threshold %d, selected top %d", len(above_threshold), SCORE_THRESHOLD, len(selected))

    # Cost calculation
    cost_usd = (total_input * HAIKU_INPUT_COST) + (total_output * HAIKU_OUTPUT_COST)
    cost_info = {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cost_usd": cost_usd,
    }

    # Log cost
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a") as f:
        f.write(
            f"\n[SCORER] {datetime.now().isoformat()} — "
            f"input: {total_input}, output: {total_output}, "
            f"cost: ${cost_usd:.4f}\n"
        )

    logger.info("  Cost: %d input + %d output tokens = $%.4f", total_input, total_output, cost_usd)

    return selected, cost_info


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from src.monitor import fetch_all

    logger.info("Fetching items from monitor...")
    items, starred, commits = fetch_all()

    logger.info("Scoring %d items against %d commits...", len(items), len(commits))
    scored, cost = score_items(items, commits, starred)

    print(f"\n{'='*60}")
    print(f"SCORED ITEMS ({len(scored)} selected)")
    print(f"{'='*60}")
    for item in scored:
        print(f"  [{item['score']}/10] {item['title'][:80]}")
        print(f"          Reason: {item['reason']}")
        print()

    print(f"Cost: {cost['input_tokens']} input + {cost['output_tokens']} output = ${cost['cost_usd']:.4f}")
