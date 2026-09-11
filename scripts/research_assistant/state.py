from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .llm import ResearchError


STATE_VERSION = 2
HISTORY_LIMIT = 1000


def _stable_unique(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _url_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ResearchError(f"State field {field!r} must be a list of non-empty strings")
    return _stable_unique(value)


def _normalize_state(raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ResearchError("Research state must be a JSON object")

    last_run = raw.get("last_run")
    if last_run is not None and not isinstance(last_run, str):
        raise ResearchError("State field 'last_run' must be a string or null")

    version = raw.get("version")
    if version is None:
        allowed = {"processed_urls", "last_run"}
        unknown = set(raw) - allowed
        if unknown:
            raise ResearchError(
                f"Unknown legacy research state field(s): {', '.join(sorted(unknown))}"
            )
        if "processed_urls" not in raw:
            raise ResearchError("Legacy research state is missing 'processed_urls'")
        unordered_legacy_urls = _url_list(raw["processed_urls"], "processed_urls")
        return {
            "version": STATE_VERSION,
            "legacy_processed_urls": unordered_legacy_urls,
            "processed_urls": [],
            "last_run": last_run,
        }

    if version != STATE_VERSION:
        raise ResearchError(f"Unsupported research state version: {version!r}")

    allowed = {"version", "legacy_processed_urls", "processed_urls", "last_run"}
    unknown = set(raw) - allowed
    if unknown:
        raise ResearchError(f"Unknown research state field(s): {', '.join(sorted(unknown))}")

    missing = allowed - set(raw)
    if missing:
        raise ResearchError(f"Research state is missing field(s): {', '.join(sorted(missing))}")

    legacy = _url_list(raw["legacy_processed_urls"], "legacy_processed_urls")
    modern = _url_list(raw["processed_urls"], "processed_urls")
    if len(modern) > HISTORY_LIMIT:
        raise ResearchError(
            f"State field 'processed_urls' exceeds the {HISTORY_LIMIT}-URL limit"
        )

    modern_set = set(modern)
    legacy = [url for url in legacy if url not in modern_set]
    if len(modern) == HISTORY_LIMIT:
        legacy = []

    return {
        "version": STATE_VERSION,
        "legacy_processed_urls": legacy,
        "processed_urls": modern,
        "last_run": last_run,
    }


def empty_state() -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "legacy_processed_urls": [],
        "processed_urls": [],
        "last_run": None,
    }


def load_state(state_path: Path) -> dict[str, Any]:
    """Load state; only an absent file means empty history."""
    if not state_path.exists():
        return empty_state()
    try:
        raw = json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchError(f"Could not read research state {state_path}: {exc}") from exc
    return _normalize_state(raw)


def seen_urls(state: Mapping[str, Any]) -> frozenset[str]:
    """Return membership across unknown legacy and ordered modern cohorts."""
    normalized = _normalize_state(state)
    return frozenset(
        normalized["legacy_processed_urls"] + normalized["processed_urls"]
    )


def record_completed(
    state: Mapping[str, Any], completed_urls: Iterable[str], last_run: str
) -> dict[str, Any]:
    """Append known completions and retire legacy history only when safe."""
    normalized = _normalize_state(state)
    legacy = list(normalized["legacy_processed_urls"])
    modern = list(normalized["processed_urls"])

    for url in _stable_unique(completed_urls):
        if not isinstance(url, str) or not url:
            raise ResearchError("Completed URLs must be non-empty strings")
        if url in legacy:
            legacy.remove(url)
        if url in modern:
            modern.remove(url)
        modern.append(url)

    modern = modern[-HISTORY_LIMIT:]
    if len(modern) == HISTORY_LIMIT:
        legacy = []

    return {
        "version": STATE_VERSION,
        "legacy_processed_urls": legacy,
        "processed_urls": modern,
        "last_run": last_run,
    }


def save_state(state_path: Path, state: Mapping[str, Any]) -> None:
    """Validate state, then atomically replace its JSON file."""
    normalized = _normalize_state(state)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(normalized, indent=2) + "\n"
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{state_path.name}.", suffix=".tmp", dir=state_path.parent
    )
    try:
        with os.fdopen(descriptor, "w") as temp_file:
            temp_file.write(payload)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, state_path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
