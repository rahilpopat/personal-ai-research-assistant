"""Stage 3: Write personalised briefings per item using Claude Sonnet."""

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

MODEL = "claude-sonnet-4-20250514"

# Sonnet pricing per million tokens
SONNET_INPUT_COST = 3.00 / 1_000_000
SONNET_OUTPUT_COST = 15.00 / 1_000_000


def _load_profile() -> dict[str, Any]:
    """Load profile.yaml."""
    with open(CONFIG_DIR / "profile.yaml") as f:
        return yaml.safe_load(f)


def _format_commits(commits: list[dict], limit: int = 40) -> str:
    """Format commits as [date] repo — message lines."""
    lines = []
    for c in commits[:limit]:
        date = c.get("date", "")[:10]
        repo = c.get("repo", "")
        message = c.get("message", "")
        lines.append(f"[{date}] {repo} — {message}")
    return "\n".join(lines)


SYSTEM_PROMPT = """You are a personal AI research assistant for Rahil Popat.
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
}"""


def _build_user_message(
    item: dict,
    commits_text: str,
    profile: dict,
) -> str:
    """Build the user message with commits, profile context, and item details."""
    active_projects = "\n".join(f"- {p}" for p in profile.get("active_projects", []))
    learning_goals = "\n".join(f"- {g}" for g in profile.get("learning_objectives", []))

    return f"""Here are Rahil's recent GitHub commits:

{commits_text}

Active projects:
{active_projects}

Learning goals:
{learning_goals}

---

Score this item for Rahil's personalised digest:

Title: {item['title']}
URL: {item['url']}
Summary: {item['summary']}
Score reason: {item.get('reason', 'N/A')}"""


def synthesise_item(
    client: anthropic.Anthropic,
    item: dict,
    commits_text: str,
    profile: dict,
) -> tuple[dict, int, int]:
    """Synthesise a single item. Returns (briefing_dict, input_tokens, output_tokens)."""
    user_msg = _build_user_message(item, commits_text, profile)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=400,
            temperature=0,
            messages=[{"role": "user", "content": user_msg}],
            system=SYSTEM_PROMPT,
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

        briefing = json.loads(text)
        return briefing, input_tokens, output_tokens

    except json.JSONDecodeError:
        logger.error("  Failed to parse JSON for '%s': %s", item['title'][:50], text[:200])
        return {
            "headline": item["title"],
            "built_connection": None,
            "time_saved": None,
            "what_next": None,
            "action": item["url"],
            "action_label": "Read",
            "forward_only": True,
        }, 0, 0
    except anthropic.APIError as e:
        logger.error("  Sonnet API error for '%s': %s", item['title'][:50], e)
        return {
            "headline": item["title"],
            "built_connection": None,
            "time_saved": None,
            "what_next": None,
            "action": item["url"],
            "action_label": "Read",
            "forward_only": True,
        }, 0, 0


def synthesise(
    scored_items: list[dict],
    commits: list[dict],
) -> tuple[list[dict], dict]:
    """Generate briefings for scored items. Returns (synthesised_items, cost_info)."""
    profile = _load_profile()
    commits_text = _format_commits(commits, limit=40)

    client = anthropic.Anthropic()
    total_input = 0
    total_output = 0

    synthesised: list[dict] = []
    for i, item in enumerate(scored_items):
        briefing, inp, out = synthesise_item(client, item, commits_text, profile)
        total_input += inp
        total_output += out

        # Merge item data with briefing
        result = {**item, **briefing}
        synthesised.append(result)

        logger.info("  [%d/%d] %s — %s",
                     i + 1, len(scored_items),
                     "connected" if not briefing.get("forward_only") else "forward",
                     briefing.get("headline", "")[:60])

    # Cost calculation
    cost_usd = (total_input * SONNET_INPUT_COST) + (total_output * SONNET_OUTPUT_COST)
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
            f"\n[SYNTHESISER] {datetime.now().isoformat()} — "
            f"input: {total_input}, output: {total_output}, "
            f"cost: ${cost_usd:.4f}\n"
        )

    logger.info("  Cost: %d input + %d output tokens = $%.4f", total_input, total_output, cost_usd)

    return synthesised, cost_info


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from src.monitor import fetch_all
    from src.scorer import score_items

    logger.info("Fetching items from monitor...")
    items, starred, commits = fetch_all()

    logger.info("Scoring items...")
    scored, score_cost = score_items(items, commits, starred)

    logger.info("Synthesising %d scored items...", len(scored))
    synthesised, synth_cost = synthesise(scored, commits)

    print(f"\n{'='*60}")
    print(f"SYNTHESISED ITEMS ({len(synthesised)})")
    print(f"{'='*60}")

    connected_count = 0
    for item in synthesised:
        icon = "forward" if item.get("forward_only") else "connected"
        if not item.get("forward_only"):
            connected_count += 1

        print(f"\n{'connected' if icon == 'connected' else 'forward'} — {item.get('headline', 'N/A')}")
        print(f"  Built: {item.get('built_connection', 'N/A')}")
        print(f"  Saved: {item.get('time_saved', 'N/A')}")
        print(f"  Next:  {item.get('what_next', 'N/A')}")
        print(f"  -> [{item.get('action_label', 'Read')}] {item.get('action', 'N/A')}")

    print(f"\n{'='*60}")
    print(f"Connected: {connected_count}/{len(synthesised)} items reference a specific repo")
    print(f"Score cost: ${score_cost['cost_usd']:.4f} | Synth cost: ${synth_cost['cost_usd']:.4f}")
    print(f"Total cost: ${score_cost['cost_usd'] + synth_cost['cost_usd']:.4f}")
