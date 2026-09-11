"""Render and atomically append research runs to a daily digest."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import tempfile
from typing import Any


def _render_run(
    articles: list[dict[str, Any]], themes: str, generated_at: datetime
) -> str:
    lines = [
        f"## Run at {generated_at.strftime('%H:%M')}",
        "",
        "### Themes",
        "",
        themes,
        "",
        "### Articles",
        "",
    ]

    for article in articles:
        title = article.get("title", "Untitled")
        source = article.get("source", "Unknown")
        url = article.get("url", "")
        summary = article.get("summary", "No summary available.")
        key_insight = article.get("key_insight", "")
        relevance = article.get("relevance", "")
        tags = article.get("tags", "")

        lines.extend([
            f"#### {source}: [{title}]({url})",
            "",
            f"**Summary:** {summary}",
            "",
        ])
        if key_insight:
            lines.extend([f"**Key insight:** {key_insight}", ""])
        if relevance:
            lines.extend([f"**Relevance:** {relevance}", ""])
        if tags:
            tag_list = [f"#{tag.strip()}" for tag in tags.split(",") if tag.strip()]
            lines.extend([f"**Tags:** {' '.join(tag_list)}", ""])

    return "\n".join(lines).rstrip() + "\n"


def write_digest(
    output_path: Path,
    articles: list[dict[str, Any]],
    themes: str,
    date: str,
) -> None:
    """Append one complete run while preserving every existing digest byte."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now()
    run = _render_run(articles, themes, generated_at).encode("utf-8")

    if output_path.exists():
        previous = output_path.read_bytes()
        separator = b"" if not previous or previous.endswith(b"\n\n") else (
            b"\n" if previous.endswith(b"\n") else b"\n\n"
        )
        payload = previous + separator + run
    else:
        try:
            formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y")
        except ValueError:
            formatted_date = date
        payload = f"# Research Digest: {formatted_date}\n\n".encode("utf-8") + run

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as temp_file:
            temp_file.write(payload)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, output_path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
