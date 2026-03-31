"""Stage 2: Score items against profile and commit history."""


def score_items(items: list, commits: list, starred: list) -> tuple[list, dict]:
    """Score and filter items. Returns (scored_items, cost_info)."""
    # TODO: Implement in Session 3
    return [], {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


if __name__ == "__main__":
    scored, cost = score_items([], [], [])
    print(f"Scored: {len(scored)}, Cost: ${cost['cost_usd']:.4f}")
