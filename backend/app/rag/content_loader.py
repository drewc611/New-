"""Load runtime content from markdown files with optional YAML frontmatter.

Everything that a non-engineer might reasonably want to change (system
prompt, sample questions, knowledge-base entries, extensions to the
address-standards tables) lives in a ``content/`` or
``data/knowledge_base/`` directory as ``.md`` files. This module gives
the rest of the backend a uniform way to read those files.

The frontmatter parser is intentionally tiny (key: value, one per line)
so we do not need a PyYAML dependency.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class MarkdownDoc:
    path: Path
    meta: dict[str, str]
    body: str

    @property
    def id(self) -> str:
        return self.meta.get("id") or self.path.stem

    @property
    def title(self) -> str:
        return self.meta.get("title") or self.meta.get("name") or self.id

    @property
    def url(self) -> str | None:
        return self.meta.get("url")


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1), text[m.end():]
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip().strip('"').strip("'")
    return meta, body


def read_markdown(path: Path) -> MarkdownDoc:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    return MarkdownDoc(path=path, meta=meta, body=body.strip())


def load_markdown_dir(directory: Path, pattern: str = "**/*.md") -> list[MarkdownDoc]:
    if not directory.exists():
        return []
    return [read_markdown(p) for p in sorted(directory.glob(pattern))]


def load_prompt(directory: Path, name: str, fallback: str) -> str:
    """Return the markdown body of ``{directory}/{name}.md`` or ``fallback``."""
    path = directory / f"{name}.md"
    if not path.exists():
        return fallback
    try:
        return read_markdown(path).body
    except Exception:
        return fallback
