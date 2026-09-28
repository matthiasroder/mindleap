"""
Fetch and parse RSS feeds.
"""

from pathlib import Path
from typing import Any
import html
import re

import feedparser
import yaml

from .llm import ResearchError
from .network import download


DEFAULT_MAX_ARTICLES = 50


def load_feed_config(config_path: Path) -> list[dict[str, Any]]:
    """Load feed configuration from YAML file."""
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ResearchError(f"Could not read feed config {config_path}: {exc}") from exc
    if not isinstance(config, dict) or not isinstance(config.get("feeds"), list):
        raise ResearchError("Feed config must contain a 'feeds' list")
    feeds = config["feeds"]
    for feed in feeds:
        if not isinstance(feed, dict) or any(
            not isinstance(feed.get(key), str) or not feed[key].strip()
            for key in ("name", "url")
        ):
            raise ResearchError("Each feed needs a non-empty name and URL")
        limit = feed.get("max_articles", DEFAULT_MAX_ARTICLES)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ResearchError(f"Feed {feed['name']!r}: max_articles must be a positive integer")
    return feeds


def fetch_feed(feed_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse a single RSS feed."""
    name = feed_config["name"]
    url = feed_config["url"]

    try:
        response = download(url)
        parsed = feedparser.parse(
            response.content, response_headers={
                "content-location": response.url, "content-type": response.content_type,
            }
        )

        if parsed.bozo and not parsed.entries:
            raise ResearchError(f"Failed to parse feed {name}: {parsed.bozo_exception}")
        if not parsed.version:
            raise ResearchError(f"Response from {name} is not an RSS or Atom feed")

        articles = []
        for entry in parsed.entries[:feed_config.get("max_articles", DEFAULT_MAX_ARTICLES)]:
            # Extract content or summary
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")
            elif hasattr(entry, "summary"):
                content = entry.summary
            elif hasattr(entry, "description"):
                content = entry.description

            # Clean HTML (basic)
            content = html.unescape(re.sub(r"<[^>]+>", "", content))
            content = content.strip()

            articles.append({
                "source": name,
                "title": entry.get("title", "Untitled"),
                "url": entry.get("link", ""),
                "content": content[:2000],  # Limit content length
                "published": entry.get("published", ""),
            })

        print(f"  {name}: {len(articles)} articles")
        return articles

    except (ResearchError, ValueError, TypeError) as exc:
        raise ResearchError(f"Feed {name!r} failed: {exc}") from exc


def fetch_all_feeds(config_path: Path) -> list[dict[str, Any]]:
    """Fetch all configured RSS feeds."""
    feeds = load_feed_config(config_path)
    all_articles = []

    for feed in feeds:
        articles = fetch_feed(feed)
        all_articles.extend(articles)

    return all_articles
