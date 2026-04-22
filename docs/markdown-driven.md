# Markdown Driven Configuration

This codebase is structured so that everything a non-engineer might
reasonably want to change lives in a `.md` file rather than in Python or
TypeScript source. The runtime loads those files at boot, with safe
fallbacks when a file is missing so the app always runs.

## What is already markdown driven

| Concern | File | Loader |
|---|---|---|
| System prompt (AMIE persona, response rules) | `backend/content/prompts/system.md` | `app.rag.prompts._load_system_prompt` |
| Knowledge base documents | `backend/data/knowledge_base/*.md` and `*.json` | `app.rag.indexer.build_from_knowledge_base` |
| Street suffix overrides | `backend/content/standards/suffix-overrides.md` | `app.tools.address_overrides.apply_overrides` |
| Secondary unit designator overrides | `backend/content/standards/secondary-overrides.md` | `app.tools.address_overrides.apply_overrides` |
| Chat empty-state samples | `frontend/public/samples.json` | `ChatView` (client-side fetch) |
| Operator docs | `docs/*.md` | read by humans |

## Conventions

### Frontmatter

Every markdown file that is read at runtime starts with a simple
frontmatter block. Only `key: value` pairs are supported, one per line,
so no YAML parser is required:

```
---
id: system
name: AMIE system prompt
updated: 2026-04-22
---

# Body starts here.
```

`id` and `title` are surfaced to the UI as citation identifiers when the
file is a knowledge-base doc. `url` is optional.

### Override tables

Tables in `content/standards/*.md` follow this shape:

```
| variant | standard |
|---------|----------|
| APMT    | APT      |
| FLR     | FL       |
```

The loader is forgiving about whitespace and ignores header separator
rows. Unknown columns are skipped. Rows whose standard value is already
present in the baked-in table are no-ops; entries that introduce a new
variant are added.

### Fallbacks

Every loader has a hardcoded default so a deployment without the
content directory still works. Failures are logged, never raised.

## How to change behavior without touching code

| Task | Edit this file |
|---|---|
| Change AMIE's tone, add response rules | `backend/content/prompts/system.md` |
| Add a new Publication 28 policy snippet to retrieval | add a `.md` file under `backend/data/knowledge_base/` |
| Teach the parser a new suffix variant | add a row to `backend/content/standards/suffix-overrides.md` |
| Teach the parser a new secondary unit variant | add a row to `backend/content/standards/secondary-overrides.md` |
| Swap the chat landing-page sample prompts | `frontend/public/samples.json` |
| Rebuild the index after any KB edit | `bash scripts/build-index.sh` (inside the backend container) |

## Directory layout

```
backend/
  content/
    prompts/
      system.md                 <- system prompt body
    standards/
      suffix-overrides.md       <- extends STREET_SUFFIXES
      secondary-overrides.md    <- extends SECONDARY_DESIGNATORS
  data/
    knowledge_base/
      seed.json                 <- original seed content
      *.md                      <- drop-in markdown KB docs (optional)
frontend/
  public/
    samples.json                <- chat empty-state prompts
docs/
  markdown-driven.md            <- this file
  config.md                     <- every environment variable explained
  address-verification.md       <- parser, suggestions, analytics
  windows-quickstart.md         <- Ollama Desktop local build
```

## Roadmap

Two more items could move to markdown once the surface stabilizes:

1. **Tool catalog** - today `address_verify` is the only tool. If the
   project grows to multiple tools, their names, descriptions, and
   invocation rules can live in `backend/content/tools/*.md` and be
   merged into the system prompt at boot.
2. **Sample analytics queries** - when the analytics dashboard is built
   out, saved queries can be stored as `content/analytics/*.md`.
