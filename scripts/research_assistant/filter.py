"""
Batch relevance filtering using Claude Haiku.
"""

import json
import os
from typing import Any

import anthropic

from .logger import log


def filter_articles(articles: list[dict[str, Any]], context: str) -> list[dict[str, Any]]:
    """
    Filter articles for relevance using Claude Haiku.

    Processes in batches of 20, returns articles scoring 4 or 5.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    relevant = []
    batch_size = 20
    total = len(articles)

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        # Log each URL being filtered
        for j, article in enumerate(batch):
            log.info(f"Filtering {i + j + 1}/{total}: {article['url']}")
        batch_relevant = filter_batch(client, batch, context)
        relevant.extend(batch_relevant)

    return relevant


def filter_batch(
    client: anthropic.Anthropic,
    articles: list[dict[str, Any]],
    context: str
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

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        response_text = response.content[0].text.strip()

        # Extract JSON from response
        if "{" in response_text:
            json_start = response_text.index("{")
            json_end = response_text.rindex("}") + 1
            json_str = response_text[json_start:json_end]
            scores = json.loads(json_str)
        else:
            log.warning("Could not parse filter response")
            return []

        # Keep articles with score >= 4
        relevant = []
        for idx_str, score in scores.items():
            idx = int(idx_str)
            if score >= 4 and idx < len(articles):
                articles[idx]["relevance_score"] = score
                relevant.append(articles[idx])

        return relevant

    except Exception as e:
        log.error(f"Error in batch filter: {e}")
        return []
