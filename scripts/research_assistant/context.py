"""
Build context from repository content.
"""

import os
from pathlib import Path

import anthropic


def build_context(drafts_dir: Path, ideas_path: Path, user_path: Path = None) -> str:
    """
    Build context from full contents of drafts, IDEAS.md, and USER.md.

    Returns an AI-generated summary of current focus based on complete file contents.
    """
    context_parts = []

    # Read USER.md (user bio/background) - full content
    if user_path and user_path.exists():
        user_content = user_path.read_text().strip()
        context_parts.append(f"USER BACKGROUND:\n{user_content}")

    # Read IDEAS.md - full content
    if ideas_path.exists():
        ideas_content = ideas_path.read_text().strip()
        context_parts.append(f"IDEAS AND INTERESTS:\n{ideas_content}")

    # Read current drafts - full content
    if drafts_dir.exists():
        draft_contents = []
        for draft_file in sorted(drafts_dir.glob("*.md"))[:5]:  # Limit to 5 most recent
            try:
                content = draft_file.read_text().strip()
                draft_contents.append(f"--- {draft_file.name} ---\n{content}")
            except Exception:
                continue

        if draft_contents:
            context_parts.append("CURRENT DRAFTS:\n" + "\n\n".join(draft_contents))

    raw_context = "\n\n".join(context_parts)

    # Use AI to create a succinct summary
    return summarize_with_ai(raw_context)


def summarize_with_ai(raw_context: str) -> str:
    """Use Haiku to summarize the raw context into a user interest profile."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    prompt = f"""You are summarizing a user's current interests and focus areas based on their notes.

INPUT:
{raw_context}

Write a single paragraph (3-5 sentences) starting with "The user is interested in..."

Focus on:
- Specific topics and themes they're exploring
- Any projects or drafts they're actively working on
- Recurring ideas or questions

Be concrete and specific, not generic. Reference actual titles and concepts from the input."""

    response = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()
