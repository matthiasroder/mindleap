#!/usr/bin/env python3

import argparse
from datetime import datetime
from pathlib import Path

from .feeds import fetch_all_feeds
from .context import build_context
from .state import load_state, record_completed, save_state, seen_urls
from .filter import filter_articles
from .analyze import analyze_articles
from .synthesize import synthesize_themes
from .output import write_digest
from .logger import log
from .llm import ResearchError, load_models


def _unique_articles(articles):
    seen = set()
    unique = []
    for article in articles:
        url = article.get("url")
        if not isinstance(url, str) or not url.strip():
            log.warning(
                "Skipping linkless article: %s",
                article.get("title", "Untitled"),
            )
            continue
        if url not in seen:
            seen.add(url)
            unique.append(article)
    return unique


def main(reprocess: bool = False):
    log.info("Starting research assistant")

    repo_root = Path(__file__).parent.parent.parent
    feed_config_path = repo_root / "config" / "feeds.yaml"
    model_config_path = repo_root / "config" / "research.yaml"
    state_path = repo_root / "feeds" / "state.json"
    output_dir = repo_root / "feeds"
    drafts_dir = repo_root / "drafts"
    ideas_path = repo_root / "IDEAS.md"
    user_path = repo_root / "USER.md"

    state = load_state(state_path)
    processed_urls = seen_urls(state)
    models = load_models(model_config_path)

    articles = _unique_articles(fetch_all_feeds(feed_config_path))

    if reprocess:
        new_articles = articles
    else:
        new_articles = [a for a in articles if a["url"] not in processed_urls]

    if not new_articles:
        log.info("Complete: No new articles to process")
        return

    context = build_context(
        drafts_dir, ideas_path, user_path, model=models.context
    )

    relevant_articles = filter_articles(
        new_articles, context, model=models.filter
    )

    if not relevant_articles:
        if not reprocess:
            state = record_completed(
                state,
                (article["url"] for article in new_articles),
                datetime.now().isoformat(),
            )
            save_state(state_path, state)
        log.info("Complete: No relevant articles found")
        return

    analyzed_articles = analyze_articles(
        relevant_articles, context, model=models.analysis
    )

    themes = synthesize_themes(analyzed_articles, model=models.synthesis)

    today = datetime.now().strftime("%Y-%m-%d")
    output_path = output_dir / f"{today}.md"
    write_digest(output_path, analyzed_articles, themes, today)

    if not reprocess:
        state = record_completed(
            state,
            (article["url"] for article in new_articles),
            datetime.now().isoformat(),
        )
        save_state(state_path, state)

    log.info(f"Complete: {len(analyzed_articles)} articles in digest")


def cli() -> int:
    """Parse CLI arguments and turn expected research failures into exit status 1."""
    parser = argparse.ArgumentParser(description="Research Assistant - Fetch and analyze RSS feeds")
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Reprocess all articles (ignore state, don't update state)"
    )
    args = parser.parse_args()
    try:
        main(reprocess=args.reprocess)
    except ResearchError as exc:
        log.error(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
