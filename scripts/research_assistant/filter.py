"""
Batch relevance filtering using Claude Haiku.
"""

import json
from typing import Any

from .llm import DEFAULT_MODELS, ResearchError, complete_text
from .logger import log


def filter_articles(
    articles: list[dict[str, Any]],
    context: str,
    *,
    model: str = DEFAULT_MODELS.filter,
) -> list[dict[str, Any]]:
    """
    Filter articles for relevance using Claude Haiku.

    Processes in batches of 20, returns articles scoring 4 or 5.
    """
    relevant = []
    batch_size = 20
    total = len(articles)

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        # Log each URL being filtered
        for j, article in enumerate(batch):
            log.info(f"Filtering {i + j + 1}/{total}: {article['url']}")
        batch_relevant = filter_batch(batch, context, model=model)
        relevant.extend(batch_relevant)

    return relevant


def filter_batch(
    articles: list[dict[str, Any]],
    context: str,
    *,
    model: str = DEFAULT_MODELS.filter,
) -> list[dict[str, Any]]:
    """Filter a single batch of articles."""

    # Format articles for the prompt
    article_list = []
    for idx, article in enumerate(articles):
        preview = article["content"][:200] if article["content"] else ""
        article_list.append(
            f'{idx}. "{article["title"]}" by {article["source"]}\n   {preview}...'
        )

    articles_text = "\n\n".join(article_list)

    prompt = f"""You are a research assistant filtering articles for relevance.

CONTEXT ABOUT THE USER:
{context}

ARTICLES TO EVALUATE:
{articles_text}

Rate each article's relevance from 1-5:
1 = Not relevant
2 = Slightly relevant
3 = Moderately relevant
4 = Highly relevant
5 = Essential reading

Return ONLY a JSON object mapping article index to score, like:
{{"0": 3, "1": 5, "2": 1, ...}}

Be selective. Most articles should score 1-3. Only score 4-5 if truly relevant to the user's current work and interests."""

    response_text = complete_text(
        stage="filter", model=model, prompt=prompt, max_tokens=500
    )
    scores = _parse_scores(response_text, len(articles), model)

    return [
        {**article, "relevance_score": scores[index]}
        for index, article in enumerate(articles)
        if scores[index] >= 4
    ]


def _parse_scores(text: str, article_count: int, model: str) -> list[int]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result

    try:
        scores = json.loads(text, object_pairs_hook=unique_object)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ResearchError(
            f"filter model {model!r} returned malformed scores: {exc}"
        ) from exc

    expected = {str(index) for index in range(article_count)}
    if not isinstance(scores, dict) or set(scores) != expected:
        raise ResearchError(
            f"filter model {model!r} returned incomplete scores; "
            f"expected indices {sorted(expected)}, got {sorted(map(str, scores)) if isinstance(scores, dict) else type(scores).__name__}"
        )

    ordered = []
    for index in range(article_count):
        score = scores[str(index)]
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
            raise ResearchError(
                f"filter model {model!r} returned invalid score for index {index}: {score!r}"
            )
        ordered.append(score)
    return ordered
