#!/usr/bin/env python3
"""
Research Assistant - Main Entry Point

Fetches RSS feeds, filters for relevance, analyzes with Claude,
and writes a personalized digest.
"""

import argparse
from datetime import datetime
from pathlib import Path

from .feeds import fetch_all_feeds
from .context import build_context
from .state import load_state, save_state
from .filter import filter_articles
from .analyze import analyze_articles
from .synthesize import synthesize_themes
from .output import write_digest
from .logger import log


def main(reprocess: bool = False):
    """Run the research assistant pipeline."""
    log.info("Starting research assistant")

    # Paths
    repo_root = Path(__file__).parent.parent.parent
    config_path = repo_root / "config" / "feeds.yaml"
    state_path = repo_root / "feeds" / "state.json"
    output_dir = repo_root / "feeds"
    drafts_dir = repo_root / "drafts"
    ideas_path = repo_root / "IDEAS.md"
    user_path = repo_root / "USER.md"

    # Load state
    state = load_state(state_path)
    processed_urls = set(state.get("processed_urls", []))

    # Fetch feeds
    articles = fetch_all_feeds(config_path)

    # Filter out already processed (unless reprocessing)
    if reprocess:
        new_articles = articles
    else:
        new_articles = [a for a in articles if a["url"] not in processed_urls]

    if not new_articles:
        log.info("Complete: No new articles to process")
        return

    # Build context from drafts and ideas
    context = build_context(drafts_dir, ideas_path, user_path)

    # Filter for relevance (Haiku)
    relevant_articles = filter_articles(new_articles, context)

    if not relevant_articles:
        if not reprocess:
            # Still mark all as processed
            state["processed_urls"] = list(processed_urls | {a["url"] for a in new_articles})
            state["last_run"] = datetime.now().isoformat()
            save_state(state_path, state)
        log.info("Complete: No relevant articles found")
        return

    # Deep analysis (Sonnet)
    analyzed_articles = analyze_articles(relevant_articles, context)

    # Synthesize themes
    themes = synthesize_themes(analyzed_articles)

    # Write digest
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = output_dir / f"{today}.md"
    write_digest(output_path, analyzed_articles, themes, today)

    # Update state (skip if reprocessing)
    if not reprocess:
        all_processed = processed_urls | {a["url"] for a in new_articles}
        state["processed_urls"] = list(all_processed)
        state["last_run"] = datetime.now().isoformat()
        save_state(state_path, state)

    log.info(f"Complete: {len(analyzed_articles)} articles in digest")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research Assistant - Fetch and analyze RSS feeds")
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Reprocess all articles (ignore state, don't update state)"
    )
    args = parser.parse_args()
    main(reprocess=args.reprocess)
