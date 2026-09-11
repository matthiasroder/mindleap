"""
Deep analysis of relevant articles using Claude Sonnet.
"""

from typing import Any

from .llm import DEFAULT_MODELS, ResearchError, complete_text
from .logger import log


def analyze_articles(
    articles: list[dict[str, Any]],
    context: str,
    *,
    model: str = DEFAULT_MODELS.analysis,
) -> list[dict[str, Any]]:
    """
    Perform deep analysis on each relevant article using Claude Sonnet.
    """
    analyzed = []
    total = len(articles)
    for i, article in enumerate(articles):
        log.info(f"Analyzing {i + 1}/{total}: {article['url']}")
        analysis = analyze_single(article, context, model=model)
        analyzed.append({**article, **analysis})

    return analyzed


def analyze_single(
    article: dict[str, Any],
    context: str,
    *,
    model: str = DEFAULT_MODELS.analysis,
) -> dict[str, str]:
    """Analyze a single article."""

    prompt = f"""You are a research assistant providing deep analysis of an article.

CONTEXT ABOUT THE USER:
{context}

ARTICLE TO ANALYZE:
Title: {article['title']}
Source: {article['source']}
URL: {article['url']}

Content:
{article['content']}

Provide analysis in this exact format:

SUMMARY: [2-3 sentence summary of the article]

KEY_INSIGHT: [The most important or contrarian idea from this article]

RELEVANCE: [Why this matters to the user's current work - be specific about connections to their drafts or ideas]

TAGS: [3-5 relevant tags, comma-separated, like: ai, productivity, local-first]

Be concise and specific. Focus on what makes this article valuable for the user."""

    response_text = complete_text(
        stage="analysis", model=model, prompt=prompt, max_tokens=500
    )
    return _parse_analysis(response_text, model)


def _parse_analysis(text: str, model: str) -> dict[str, str]:
    labels = {
        "SUMMARY:": "summary",
        "KEY_INSIGHT:": "key_insight",
        "RELEVANCE:": "relevance",
        "TAGS:": "tags",
    }
    analysis: dict[str, str] = {}
    current_field: str | None = None
    current_content: list[str] = []

    def finish_field() -> None:
        if current_field is None:
            return
        content = " ".join(current_content).strip()
        if not content:
            raise ResearchError(
                f"analysis model {model!r} returned an empty {current_field} field"
            )
        analysis[current_field] = content

    for raw_line in text.splitlines():
        line = raw_line.strip()
        matched = next((label for label in labels if line.startswith(label)), None)
        if matched:
            finish_field()
            field = labels[matched]
            if field in analysis:
                raise ResearchError(
                    f"analysis model {model!r} returned duplicate {field} fields"
                )
            current_field = field
            current_content = [line[len(matched):].strip()]
        elif line:
            if current_field is None:
                raise ResearchError(
                    f"analysis model {model!r} returned text before the required fields"
                )
            current_content.append(line)

    finish_field()
    missing = set(labels.values()) - set(analysis)
    if missing:
        raise ResearchError(
            f"analysis model {model!r} omitted required field(s): {', '.join(sorted(missing))}"
        )
    return analysis
