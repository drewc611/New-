---
id: tech-debt
name: Tech Debt Audit Playbook
updated: 2026-04-22
owner: engineering
---

# Tech Debt Audit Playbook

This is both a living inventory of known tech debt in the AMIE codebase
and a playbook for finding more. It is meant to be edited in place.
Every item carries enough context that someone new to the repo can pick
it up, triage it, and either fix it or push it onto a backlog.

## How to use this file

1. Run the **discovery commands** below. Each one lists debt of a
   specific flavor: dependency drift, dead code, missing tests, slow
   endpoints, etc.
2. For every real finding, add a row to the **Inventory** table or update
   an existing row.
3. Triage with the **Severity x Effort** rubric. Anything High severity
   should be tracked on the current sprint board.
4. Once fixed, move the row to **Resolved** with the commit hash.

Never delete a resolved entry. History is how we audit that debt is
going down over time.

## Severity x Effort rubric

| Severity | Meaning |
|---|---|
| Critical | Security, data loss, or compliance risk. Fix now. |
| High | Blocks a near-term feature or causes user-visible failure. Fix this sprint. |
| Medium | Slows development or degrades quality but ships anyway. Fix within a quarter. |
| Low | Nice-to-have cleanup. Fix opportunistically. |

| Effort | Meaning |
|---|---|
| S | One afternoon |
| M | One to three days |
| L | More than a week, or needs a design doc |

## Discovery commands

Run these from the repo root. They are read-only and safe.

### Python (backend)

```bash
# Dead code, unused imports, complexity
ruff check backend/app --select E,F,W,B,C90,UP,SIM,RUF

# Type coverage (if mypy is installed)
mypy backend/app --ignore-missing-imports --follow-imports=silent

# Dependency drift
pip list --outdated --format=columns

# Dependency CVEs
pip install pip-audit && pip-audit -r backend/requirements.txt

# Test coverage
cd backend && pytest --cov=app --cov-report=term-missing

# Slowest tests (find flaky or bloated tests)
cd backend && pytest --durations=20

# Dead code (vulture)
pip install vulture && vulture backend/app --min-confidence 80

# Cyclomatic complexity per file
pip install radon && radon cc backend/app -nb -a

# Secrets check (never commit .env)
git ls-files | xargs grep -lE '(API_KEY|SECRET|PASSWORD|TOKEN)\s*=\s*[A-Za-z0-9]+' || true
```

### TypeScript (frontend)

```bash
# Type errors
cd frontend && npm run typecheck

# Unused exports
cd frontend && npx ts-prune --project tsconfig.json

# Bundle size regressions (requires a prod build)
cd frontend && npm run build && ls -lh dist/assets

# Dependency drift
cd frontend && npm outdated

# Dependency CVEs
cd frontend && npm audit --omit=dev

# Lint (if eslint is configured later)
cd frontend && npx eslint "src/**/*.{ts,tsx}" --max-warnings=0
```

### Repo hygiene

```bash
# TODO and FIXME markers
git grep -nE 'TODO|FIXME|XXX|HACK'

# Files over 500 lines (candidates for splitting)
find backend/app frontend/src -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) -exec wc -l {} \; | sort -rn | awk '$1 > 500 {print}'

# Commits tagged WIP or squash candidates
git log --grep='WIP\|wip\|squash' --oneline

# Branches older than 30 days (pre-push cleanup)
git for-each-ref --sort=-committerdate refs/heads --format='%(committerdate:short) %(refname:short)'
```

## Current inventory

| Severity | Effort | Area | Summary | Evidence | Owner | Opened |
|---|---|---|---|---|---|---|
| Medium | S | backend/app/api/chat.py | `get_orchestrator` returns a new `ChatOrchestrator` per request; LLM and conversation-store singletons are captured per call instead of shared | `backend/app/api/chat.py:17` | | 2026-04-22 |
| Medium | M | backend/app/rag/indexer.py | `RedisVectorIndex` reaches into `self._client` directly from the retriever helpers. Encapsulate info/count lookups behind methods. | `backend/app/rag/retriever.py:36-43` | | 2026-04-22 |
| Medium | S | backend/app/rag/chunking.py | Chunk overlap is char-based. When a chunk ends mid-sentence the semantic boundary is lost. Consider sentence-aware splitting. | `backend/app/rag/chunking.py:36-39` | | 2026-04-22 |
| Medium | M | backend/app/tools/address_parser.py | City detection is positional only. A one-word city on the last line with no comma delimiter fails. | `backend/app/tools/address_parser.py` (city extraction) | | 2026-04-22 |
| Medium | S | backend/requirements.txt | `python-jose==3.3.0` is pinned; the project has stalled upstream. Evaluate `authlib` or `PyJWT` for JWKS parsing. | `backend/requirements.txt` | | 2026-04-22 |
| Medium | S | backend/app/services/address_analytics.py | Rollups use individual counter keys scanned with `SCAN`. At 50k+ warning categories the summary endpoint gets slow. Move to a Redis hash per category. | `backend/app/services/address_analytics.py:93-112` | | 2026-04-22 |
| Low | S | frontend/src/components/Composer.tsx | Submit button and textarea lack `aria-label`; cross-reference `docs/508-compliance.md`. | `frontend/src/components/Composer.tsx:34-40` | | 2026-04-22 |
| Low | S | frontend/src/lib/api.ts | `fetch` errors include the raw response body. Any upstream that echoes user input (PII) can leak into the UI error toast. Redact before display. | `frontend/src/lib/api.ts:19-22` | | 2026-04-22 |
| Low | S | backend/app/core/security.py | JWKS cache has no jitter. Under a key-rotation event the whole fleet refreshes at the same time. | `backend/app/core/security.py:30-41` | | 2026-04-22 |
| Low | S | backend/tests | No contract tests between backend and frontend. Pydantic schemas change independently of the TypeScript `types/` file. | `frontend/src/types/index.ts` | | 2026-04-22 |
| Low | S | docs | `docs/local-dev.md` still implies `LLM_PROVIDER=mock` as the default path; the default is now `ollama`. Update. | `docs/local-dev.md:13` | | 2026-04-22 |

## Resolved (recent)

| Closed | Severity | Area | Summary | Commit |
|---|---|---|---|---|
| 2026-04-22 | Critical | backend/app/rag/retriever.py | File was a placeholder that crashed import. Rebuilt with `bootstrap_if_needed` and `retrieve`. | 84fc4fb |
| 2026-04-22 | Critical | backend/app/core/security.py | `get_current_user` did not actually verify JWTs when auth was enabled. Replaced with JWKS-backed verification. | 84fc4fb |
| 2026-04-22 | Critical | backend/app/tools/address_usps.py | XML request was built via f-string with no escaping and parsed with `xml.etree`. Fixed XML injection and XXE. | 84fc4fb |
| 2026-04-22 | High | backend/app/main.py | No request body limit. Added `BodySizeLimitMiddleware` at 256 KiB. | 84fc4fb |
| 2026-04-22 | High | backend/app/models/schemas.py | `datetime.utcnow()` usage was deprecated in Python 3.12. Replaced with `datetime.now(timezone.utc)`. | 84fc4fb |
| 2026-04-22 | Medium | backend/app/rag/indexer.py | `redis.commands.search.indexDefinition` import path breaks on redis-py 5.1+. Added snake_case fallback. | 84fc4fb |

## Adding new debt

Copy this template into the inventory table:

```
| Severity | Effort | Area | Summary | Evidence | Owner | Opened |
|---|---|---|---|---|---|---|
| Medium | M | <path or module> | <1-sentence what and why> | <file:line or command output> | <github handle> | YYYY-MM-DD |
```

## Debt budget

We hold an explicit budget for debt work:

- 10 percent of every sprint is reserved for items from this file.
- Any **Critical** or **High** item blocks the release it is found in.
- Any item open longer than two quarters must be either resolved or
  downgraded with a written rationale added to the `Summary` column.

## See also

- `docs/security.md` for the security threat model.
- `docs/508-compliance.md` for accessibility findings that overlap with
  frontend tech debt.
- `docs/executive-report.md` for how tech-debt counts feed the monthly
  status roll-up.
