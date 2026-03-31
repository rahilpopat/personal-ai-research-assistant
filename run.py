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
    """Run the full pipeline: monitor -> score -> synthesise -> digest."""
    start = datetime.now()
    logger.info("=== AI Research Assistant — pipeline start ===")
    logger.info("Mode: %s", "DRY RUN" if dry_run else "LIVE")

    from src import digest, monitor, scorer, synthesiser

    # Stage 1: Monitor
    logger.info("Stage 1: Monitor — fetching items...")
    try:
        items, starred, commits = monitor.fetch_all()
        logger.info("  Found %d items, %d starred repos, %d commits", len(items), len(starred), len(commits))
    except Exception as e:
        logger.error("Stage 1 FAILED: %s", e)
        items, starred, commits = [], [], []

    # Stage 2: Score
    logger.info("Stage 2: Scorer — scoring items...")
    try:
        scored, score_cost = scorer.score_items(items, commits, starred)
        logger.info("  %d items passed scoring (cost: $%.4f)", len(scored), score_cost["cost_usd"])
    except Exception as e:
        logger.error("Stage 2 FAILED: %s", e)
        scored, score_cost = [], {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    # Stage 3: Synthesise
    if scored:
        logger.info("Stage 3: Synthesiser — generating briefings...")
        try:
            synthesised, synth_cost = synthesiser.synthesise(scored, commits)
            logger.info("  %d briefings generated (cost: $%.4f)", len(synthesised), synth_cost["cost_usd"])
        except Exception as e:
            logger.error("Stage 3 FAILED: %s", e)
            synthesised, synth_cost = [], {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    else:
        logger.info("Stage 3: Skipped — no scored items (quiet day)")
        synthesised, synth_cost = [], {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    # Stage 4: Digest
    logger.info("Stage 4: Digest — rendering and delivering...")
    try:
        digest.deliver(synthesised, dry_run=dry_run)
    except Exception as e:
        logger.error("Stage 4 FAILED: %s", e)

    # Summary
    total_cost = score_cost["cost_usd"] + synth_cost["cost_usd"]
    elapsed = (datetime.now() - start).total_seconds()
    logger.info("=== Pipeline complete in %.1fs | Total cost: $%.4f ===", elapsed, total_cost)


if __name__ == "__main__":
    args = parse_args()
    run(dry_run=args.dry_run)
