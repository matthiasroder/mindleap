from typing import Any

from .llm import DEFAULT_MODELS, complete_text


def synthesize_themes(
    articles: list[dict[str, Any]],
    *,
    model: str = DEFAULT_MODELS.synthesis,
) -> str:
    if not articles:
        return "No articles to synthesize."

    article_summaries = []
    for article in articles:
        summary = article.get("summary", article["title"])
        source = article["source"]
        article_summaries.append(f"- {source}: {summary}")

    articles_text = "\n".join(article_summaries)

    prompt = f"""You are a research assistant identifying patterns across today's articles.

TODAY'S RELEVANT ARTICLES:
{articles_text}

Identify 2-4 themes or patterns you notice:
- What topics are multiple authors discussing?
- Are there contrasting viewpoints on the same issue?
- What trends or shifts do you notice?

Be concise. Write 2-4 bullet points, each 1-2 sentences.
Format as a simple bulleted list starting with "- "."""

    return complete_text(
        stage="synthesis", model=model, prompt=prompt, max_tokens=300
    )
