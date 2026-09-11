"""Claude model configuration and the shared text-completion boundary."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Literal

import anthropic
import yaml


Stage = Literal["context", "filter", "analysis", "synthesis"]


@dataclass(frozen=True)
class Models:
    context: str = "claude-haiku-4-5-20251001"
    filter: str = "claude-haiku-4-5-20251001"
    analysis: str = "claude-sonnet-5"
    synthesis: str = "claude-sonnet-5"


DEFAULT_MODELS = Models()
_MODEL_FIELDS = {field.name for field in fields(Models)}
_MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class ResearchError(RuntimeError):
    """A research stage failed and must not be treated as completed."""


class ModelConfigError(ResearchError):
    """The committed research model configuration is invalid."""


def load_models(path: Path) -> Models:
    """Load optional per-stage overrides from the committed YAML config."""
    if not path.exists():
        return DEFAULT_MODELS

    try:
        raw = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ModelConfigError(f"Could not read model config {path}: {exc}") from exc

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ModelConfigError(f"Model config {path} must be a mapping")

    unknown_root = set(raw) - {"models"}
    if unknown_root:
        raise ModelConfigError(
            f"Unknown setting(s) in {path}: {', '.join(sorted(map(str, unknown_root)))}"
        )

    overrides = raw.get("models", {})
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, dict):
        raise ModelConfigError(f"The 'models' setting in {path} must be a mapping")

    unknown_models = set(overrides) - _MODEL_FIELDS
    if unknown_models:
        raise ModelConfigError(
            f"Unknown model stage(s) in {path}: "
            f"{', '.join(sorted(map(str, unknown_models)))}"
        )

    values = {field.name: getattr(DEFAULT_MODELS, field.name) for field in fields(Models)}
    for stage, value in overrides.items():
        if not isinstance(value, str) or not value.strip():
            raise ModelConfigError(f"models.{stage} in {path} must be a non-empty string")
        value = value.strip()
        if not _MODEL_ID.fullmatch(value):
            raise ModelConfigError(
                f"models.{stage} in {path} is not a valid API-style model identifier: {value!r}"
            )
        values[stage] = value

    return Models(**values)


def complete_text(*, stage: Stage, model: str, prompt: str, max_tokens: int) -> str:
    """Return complete non-empty Claude text, or raise without model fallback."""
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise ResearchError(
            f"{stage} model {model!r} failed: {exc}. "
            f"Change models.{stage} in config/research.yaml; no fallback was attempted."
        ) from exc

    stop_reason = getattr(response, "stop_reason", None)
    if stop_reason not in {"end_turn", "stop_sequence"}:
        detail = "response was truncated" if stop_reason == "max_tokens" else (
            f"response ended with stop reason {stop_reason!r}"
        )
        raise ResearchError(
            f"{stage} model {model!r} failed: {detail}. "
            f"Change models.{stage} in config/research.yaml; no fallback was attempted."
        )

    text_parts = []
    for block in getattr(response, "content", ()):
        if getattr(block, "type", None) == "text":
            text = getattr(block, "text", None)
            if isinstance(text, str):
                text_parts.append(text)

    text = "".join(text_parts).strip()
    if not text:
        raise ResearchError(
            f"{stage} model {model!r} failed: response contained no text. "
            f"Change models.{stage} in config/research.yaml; no fallback was attempted."
        )
    return text
