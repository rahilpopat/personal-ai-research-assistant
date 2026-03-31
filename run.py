#!/usr/bin/env python3
"""AI Research Assistant — daily digest pipeline orchestrator."""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Logging setup ---
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="AI Research Assistant — daily digest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.getenv("DRY_RUN", "false").lower() == "true",
        help="Print email HTML to stdout instead of sending",
    )
    return parser.parse_args()


def run(dry_run: bool = True) -> None:
    """Run the full pipeline: monitor → score → synthesise → digest."""
    start = datetime.now()
    logger.info("=== AI Research Assistant — pipeline start ===")
    logger.info("Mode: %s", "DRY RUN" if dry_run else "LIVE")

    # Stage 1: Monitor — fetch items from all sources
    logger.info("Stage 1: Monitor — fetching items...")
    items: list = []
    starred: list = []
    commits: list = []
    logger.info("  Found %d items, %d starred repos, %d commits (stubbed)", len(items), len(starred), len(commits))

    # Stage 2: Score — rank items against profile + commits
    logger.info("Stage 2: Scorer — scoring items...")
    scored: list = []
    logger.info("  %d items passed scoring threshold (stubbed)", len(scored))

    # Stage 3: Synthesise — write personalised briefings
    logger.info("Stage 3: Synthesiser — generating briefings...")
    synthesised: list = []
    logger.info("  %d briefings generated (stubbed)", len(synthesised))

    # Stage 4: Digest — render and deliver
    logger.info("Stage 4: Digest — rendering email...")
    if dry_run:
        logger.info("  [DRY RUN] Email would be sent here. No items to render yet.")
    else:
        logger.info("  [LIVE] Email would be sent here. No items to render yet.")

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("=== Pipeline complete in %.1fs ===", elapsed)


if __name__ == "__main__":
    args = parse_args()
    run(dry_run=args.dry_run)
