"""Stage 3: Write personalised briefings per item using Claude Sonnet."""


def synthesise(scored_items: list, commits: list) -> tuple[list, dict]:
    """Generate briefings for scored items. Returns (synthesised_items, cost_info)."""
    # TODO: Implement in Session 4
    return [], {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


if __name__ == "__main__":
    synthesised, cost = synthesise([], [])
    print(f"Synthesised: {len(synthesised)}, Cost: ${cost['cost_usd']:.4f}")
