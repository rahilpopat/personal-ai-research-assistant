"""Stage 4: Render HTML email and send digest."""


def deliver(synthesised_items: list, dry_run: bool = True) -> None:
    """Render and deliver the digest email."""
    # TODO: Implement in Session 5
    if dry_run:
        print("[DRY RUN] No items to render yet.")
    else:
        print("[LIVE] No items to render yet.")


if __name__ == "__main__":
    deliver([], dry_run=True)
