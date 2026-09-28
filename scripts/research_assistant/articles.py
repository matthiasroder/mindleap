"""Retrieve evidence before asking a model to summarize an article."""

from typing import Any

from trafilatura import extract

from .llm import ResearchError
from .logger import log
from .network import download


MAX_ARTICLE_CHARACTERS = 30_000
MIN_ARTICLE_WORDS = 80


def read_article(article: dict[str, Any]) -> dict[str, Any]:
    """Return readable text, or a link-only entry with no inferred article claims."""
    try:
        page = download(article["url"])
        if page.content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
            raise ResearchError(f"Unsupported article format: {page.content_type}")
        if page.content_type == "text/plain":
            text = page.content.decode("utf-8", errors="replace").strip()
        else:
            text = extract(
                page.content, url=page.url, include_comments=False,
                include_tables=False, favor_precision=True,
            ) or ""
        if len(text.split()) < MIN_ARTICLE_WORDS:
            raise ResearchError("Not enough readable article text (possibly a teaser or login page)")
    except (ResearchError, ValueError) as exc:
        log.warning("Keeping %s as a link only: %s", article["url"], exc)
        return {
            **article, "content": "", "content_status": "unavailable",
            "evidence": "Link only — article text unavailable; no article summary was generated.",
        }

    truncated = len(text) > MAX_ARTICLE_CHARACTERS
    return {
        **article, "content": text[:MAX_ARTICLE_CHARACTERS],
        "content_status": "retrieved",
        "evidence": (
            f"Retrieved article text (first {MAX_ARTICLE_CHARACTERS:,} characters)."
            if truncated else "Retrieved article text."
        ),
    }


def read_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [read_article(article) for article in articles]
