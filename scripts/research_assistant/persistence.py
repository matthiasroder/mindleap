"""Recoverable publication of a digest and its corresponding URL history."""

from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4, UUID

from filelock import FileLock, Timeout

from .llm import ResearchError
from .logger import log
from .output import write_digest
from .state import load_state, normalize_state, save_state


PENDING_RUN = ".pending-run.json"


@contextmanager
def research_lock(output_dir: Path):
    """Hold one OS-backed lock from state read through publication and recovery."""
    output_dir.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(output_dir / ".research.lock"), timeout=0)
    try:
        lock.acquire()
    except Timeout as exc:
        raise ResearchError("Another research run is active in this vault; retry after it finishes") from exc
    try:
        yield
    finally:
        lock.release()


def _save_pending(path: Path, pending: dict) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(pending, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _validate_pending(pending: object) -> dict:
    try:
        if not isinstance(pending, dict) or pending.get("version") != 1:
            raise ValueError("unsupported journal version")
        required = {"version", "run_id", "date", "generated_at", "articles", "themes", "state_before", "state_after"}
        if set(pending) != required:
            raise ValueError("unexpected journal fields")
        if UUID(pending["run_id"]).hex != pending["run_id"]:
            raise ValueError("invalid run ID")
        if datetime.strptime(pending["date"], "%Y-%m-%d").strftime("%Y-%m-%d") != pending["date"]:
            raise ValueError("invalid digest date")
        datetime.fromisoformat(pending["generated_at"])
        if not isinstance(pending["themes"], str) or not isinstance(pending["articles"], list):
            raise ValueError("invalid digest payload")
        for article in pending["articles"]:
            if not isinstance(article, dict) or any(
                not isinstance(article.get(key), str)
                for key in ("url", "title", "source", "summary", "key_insight", "relevance", "tags", "evidence")
            ):
                raise ValueError("invalid article payload")
        for key in ("state_before", "state_after"):
            if pending[key] is not None:
                pending[key] = normalize_state(pending[key])
        if (pending["state_before"] is None) != (pending["state_after"] is None):
            raise ValueError("incomplete state transition")
    except (ValueError, TypeError, AttributeError, ResearchError) as exc:
        raise ResearchError(f"Invalid pending research run; preserve {PENDING_RUN} for recovery: {exc}") from exc
    return pending


def recover_run(output_dir: Path) -> bool:
    """Finish a journaled run without model calls. Caller must hold research_lock."""
    path = output_dir / PENDING_RUN
    if not path.exists():
        return False
    try:
        pending = _validate_pending(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise ResearchError(f"Could not read pending research run {path}: {exc}") from exc

    state_path = output_dir / "state.json"
    if pending["state_after"] is not None:
        current = load_state(state_path)
        if current not in (pending["state_before"], pending["state_after"]):
            raise ResearchError("History changed outside the pending run; preserve the journal and resolve before retrying")

    if pending["articles"]:
        write_digest(
            output_dir / f"{pending['date']}.md", pending["articles"],
            pending["themes"], pending["date"], run_id=pending["run_id"],
            generated_at=datetime.fromisoformat(pending["generated_at"]),
        )
    if pending["state_after"] is not None:
        save_state(state_path, pending["state_after"])
    path.unlink()
    log.info("Saved research run %s", pending["run_id"])
    return True


def commit_run(output_dir: Path, articles: list[dict], themes: str, *, state_before=None, state_after=None) -> None:
    """Journal first, then publish; caller must hold research_lock."""
    path = output_dir / PENDING_RUN
    if path.exists():
        raise ResearchError("Recover the pending research run before committing another")
    now = datetime.now()
    pending = _validate_pending({
        "version": 1, "run_id": uuid4().hex,
        "date": now.strftime("%Y-%m-%d"), "generated_at": now.isoformat(),
        # Keep article text and private context out of the recovery journal.
        "articles": [
            {key: article.get(key, "") for key in (
                "url", "title", "source", "summary", "key_insight", "relevance", "tags", "evidence"
            )}
            for article in articles
        ],
        "themes": themes, "state_before": state_before, "state_after": state_after,
    })
    _save_pending(path, pending)
    recover_run(output_dir)
