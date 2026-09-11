from datetime import date
from pathlib import Path
import re

from .llm import DEFAULT_MODELS, complete_text


_DATED_DRAFT = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\D|$)")


def _draft_sort_key(path: Path) -> tuple[int, int, str]:
    match = _DATED_DRAFT.match(path.name)
    if match:
        try:
            draft_date = date.fromisoformat(match.group(1))
            return (1, draft_date.toordinal(), path.name)
        except ValueError:
            pass
    return (0, 0, path.name)


def build_context(
    drafts_dir: Path,
    ideas_path: Path,
    user_path: Path | None = None,
    *,
    model: str = DEFAULT_MODELS.context,
) -> str:
    """
    Build context from full contents of drafts, IDEAS.md, and USER.md.

    Returns an AI-generated summary of current focus based on complete file contents.
    """
    context_parts = []

    if user_path and user_path.exists():
        user_content = user_path.read_text().strip()
        context_parts.append(f"USER BACKGROUND:\n{user_content}")

    if ideas_path.exists():
        ideas_content = ideas_path.read_text().strip()
        context_parts.append(f"IDEAS AND INTERESTS:\n{ideas_content}")

    if drafts_dir.exists():
        draft_contents = []
        draft_files = sorted(drafts_dir.glob("*.md"), key=_draft_sort_key, reverse=True)
        for draft_file in draft_files[:5]:
            try:
                content = draft_file.read_text().strip()
                draft_contents.append(f"--- {draft_file.name} ---\n{content}")
            except Exception:
                continue

        if draft_contents:
            context_parts.append("CURRENT DRAFTS:\n" + "\n\n".join(draft_contents))

    raw_context = "\n\n".join(context_parts)

    return summarize_with_ai(raw_context, model=model)


def summarize_with_ai(raw_context: str, *, model: str = DEFAULT_MODELS.context) -> str:
    """Summarize the raw context into a user interest profile."""
    prompt = f"""You are summarizing a user's current interests and focus areas based on their notes.

INPUT:
{raw_context}

Write a single paragraph (3-5 sentences) starting with "The user is interested in..."

Focus on:
- Specific topics and themes they're exploring
- Any projects or drafts they're actively working on
- Recurring ideas or questions

Be concrete and specific, not generic. Reference actual titles and concepts from the input."""

    return complete_text(stage="context", model=model, prompt=prompt, max_tokens=300)
