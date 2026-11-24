"""Load JSON schemas into a referencing registry and validate documents."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .core import load_json

BASE = "https://dsys.local/schemas/"

STREAM_SCHEMA = {
    "arxiv": "arxiv.schema.json",
    "research_updates": "research_updates.schema.json",
    "world": "world.schema.json",
    "discovery": "discovery.schema.json",
    "youtube_shorts": "youtube_shorts.schema.json",
    "language": "language.schema.json",
    "reading": "reading.schema.json",
    "weekly": "weekly.schema.json",
    "monthly": "monthly.schema.json",
    "quarterly": "quarterly.schema.json",
    "feedback": "feedback.schema.json",
    "ideas": "ideas.schema.json",
    "recommendation": "recommendation.schema.json",
}


@lru_cache(maxsize=8)
def _registry(schema_dir: str) -> Registry:
    resources = []
    for f in sorted(Path(schema_dir).glob("*.schema.json")):
        doc = load_json(f)
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=32)
def validator(schema_dir: str, name: str) -> Draft202012Validator:
    reg = _registry(schema_dir)
    schema = reg.contents(BASE + STREAM_SCHEMA[name])
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=reg, format_checker=FormatChecker())


def schema_errors(schema_dir: Path, name: str, doc) -> list[str]:
    v = validator(str(schema_dir), name)
    out = []
    for e in sorted(v.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path))):
        loc = "/".join(str(p) for p in e.absolute_path) or "<root>"
        out.append(f"{loc}: {e.message}")
    return out
