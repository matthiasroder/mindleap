from __future__ import annotations

import os
import re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import anthropic
import openai
import yaml


Stage = Literal["context", "filter", "analysis", "synthesis"]
Provider = Literal["anthropic", "openai", "openai-compatible"]


@dataclass(frozen=True)
class ModelChoice:
    provider: Provider
    model: str
    base_url: str | None = None

    def __str__(self) -> str:
        return f"model {self.model!r} (provider {self.provider})"


@dataclass(frozen=True)
class Models:
    context: ModelChoice = ModelChoice("anthropic", "claude-haiku-4-5-20251001")
    filter: ModelChoice = ModelChoice("anthropic", "claude-haiku-4-5-20251001")
    analysis: ModelChoice = ModelChoice("anthropic", "claude-sonnet-5")
    synthesis: ModelChoice = ModelChoice("anthropic", "claude-sonnet-5")


DEFAULT_MODELS = Models()
_MODEL_FIELDS = {field.name for field in fields(Models)}
_MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
_PROVIDERS = {"anthropic", "openai", "openai-compatible"}


class ResearchError(RuntimeError):
    """A research stage failed and must not be treated as completed."""


class ModelConfigError(ResearchError):
    """The committed research model configuration is invalid."""


def _provider(value: object, setting: str) -> Provider:
    if not isinstance(value, str) or value not in _PROVIDERS:
        raise ModelConfigError(
            f"{setting} must be one of: {', '.join(sorted(_PROVIDERS))}"
        )
    return value


def _base_url(value: object, setting: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelConfigError(f"{setting} must be a non-empty HTTP(S) URL")
    url = value.strip()
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ModelConfigError(f"{setting} is not a valid HTTP(S) URL: {exc}") from exc
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or port == 0 or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ModelConfigError(
            f"{setting} must be an HTTP(S) URL without credentials, query, or fragment"
        )
    return url


def _model_id(value: object, setting: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelConfigError(f"{setting} must be a non-empty string")
    value = value.strip()
    if not _MODEL_ID.fullmatch(value):
        raise ModelConfigError(
            f"{setting} is not a valid API-style model identifier: {value!r}"
        )
    return value


def load_models(path: Path) -> Models:
    """Load provider and per-stage model choices from the committed YAML config."""
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

    unknown_root = set(raw) - {"provider", "base_url", "models"}
    if unknown_root:
        raise ModelConfigError(
            f"Unknown setting(s) in {path}: {', '.join(sorted(map(str, unknown_root)))}"
        )

    provider = _provider(raw.get("provider", "anthropic"), "provider")
    base_url = _base_url(raw["base_url"], "base_url") if "base_url" in raw else None
    if base_url and provider != "openai-compatible":
        raise ModelConfigError("base_url requires provider: openai-compatible")
    if provider == "openai-compatible" and not base_url:
        raise ModelConfigError("provider: openai-compatible requires base_url")

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
    if provider != "anthropic" and set(overrides) != _MODEL_FIELDS:
        missing = sorted(_MODEL_FIELDS - set(overrides))
        raise ModelConfigError(
            f"provider: {provider} requires explicit models for every stage; "
            f"missing: {', '.join(missing)}"
        )

    values = {field.name: getattr(DEFAULT_MODELS, field.name) for field in fields(Models)}
    for stage, value in overrides.items():
        setting = f"models.{stage}"
        stage_provider = provider
        stage_base_url = base_url
        if isinstance(value, dict):
            unknown = set(value) - {"provider", "model", "base_url"}
            if unknown:
                raise ModelConfigError(
                    f"Unknown setting(s) in {setting}: "
                    f"{', '.join(sorted(map(str, unknown)))}"
                )
            if "provider" in value:
                stage_provider = _provider(value["provider"], f"{setting}.provider")
            stage_base_url = (
                _base_url(value["base_url"], f"{setting}.base_url")
                if "base_url" in value else (base_url if stage_provider == provider else None)
            )
            value = value.get("model")
            setting = f"{setting}.model"
        model = _model_id(value, setting)
        if stage_provider == "openai-compatible" and not stage_base_url:
            raise ModelConfigError(
                f"models.{stage} uses openai-compatible and requires base_url"
            )
        if stage_provider != "openai-compatible" and stage_base_url:
            raise ModelConfigError(
                f"models.{stage}.base_url requires openai-compatible provider"
            )
        values[stage] = ModelChoice(stage_provider, model, stage_base_url)

    return Models(**values)


def required_api_keys(models: Models) -> set[str]:
    """Return the environment variable names needed by the selected providers."""
    providers = {getattr(models, stage).provider for stage in _MODEL_FIELDS}
    names = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openai-compatible": "LLM_API_KEY",
    }
    return {names[provider] for provider in providers}


def complete_text(*, stage: Stage, model: ModelChoice | str, prompt: str, max_tokens: int) -> str:
    """Return complete non-empty text from the selected provider, without fallback."""
    choice = model if isinstance(model, ModelChoice) else ModelChoice("anthropic", model)
    if choice.provider == "openai-compatible" and not choice.base_url:
        raise ResearchError(
            f"{stage} {choice} failed: set models.{stage}.base_url in "
            "config/research.yaml; no fallback was attempted."
        )
    key_name = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openai-compatible": "LLM_API_KEY",
    }[choice.provider]
    api_key = os.environ.get(key_name)
    if not api_key:
        raise ResearchError(
            f"{stage} {choice} failed: set {key_name}; no fallback was attempted."
        )

    try:
        if choice.provider == "anthropic":
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=choice.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            finish = getattr(response, "stop_reason", None)
            text = "".join(
                block.text for block in getattr(response, "content", ())
                if getattr(block, "type", None) == "text"
                and isinstance(getattr(block, "text", None), str)
            ).strip()
            complete = finish in {"end_turn", "stop_sequence"}
            truncated = finish == "max_tokens"
        else:
            kwargs = {"api_key": api_key}
            kwargs["base_url"] = (
                "https://api.openai.com/v1"
                if choice.provider == "openai" else choice.base_url
            )
            client = openai.OpenAI(**kwargs)
            token_arg = (
                "max_completion_tokens" if choice.provider == "openai" else "max_tokens"
            )
            response = client.chat.completions.create(
                model=choice.model,
                messages=[{"role": "user", "content": prompt}],
                **{token_arg: max_tokens},
            )
            choices = getattr(response, "choices", ())
            selected = choices[0] if choices else None
            finish = getattr(selected, "finish_reason", None)
            content = getattr(getattr(selected, "message", None), "content", None)
            text = content.strip() if isinstance(content, str) else ""
            complete = finish == "stop"
            truncated = finish == "length"
    except Exception as exc:
        raise ResearchError(
            f"{stage} {choice} failed: {exc}. "
            f"Change models.{stage} in config/research.yaml; no fallback was attempted."
        ) from exc

    if not complete:
        detail = "response was truncated" if truncated else f"response ended with reason {finish!r}"
        raise ResearchError(
            f"{stage} {choice} failed: {detail}. "
            f"Change models.{stage} in config/research.yaml; no fallback was attempted."
        )
    if not text:
        raise ResearchError(
            f"{stage} {choice} failed: response contained no text. "
            f"Change models.{stage} in config/research.yaml; no fallback was attempted."
        )
    return text
