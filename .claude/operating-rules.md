# Operating rules / guardrails

Applies to every Claude Code session in this repo.

## Folder protocol
- **Read-only**: `/backend`, `/frontend/src`, `/deploy`, `/docs`, `/scripts`,
  `/.claude` — edit only when the task explicitly targets them.
- **Write-only scratch**: `/.claude/outputs/` — throwaway artifacts, preview
  HTML, one-off scripts. Gitignored.
- **Never commit**: build outputs (`dist/`, `*.tsbuildinfo`,
  `frontend/src/**/*.js`), `node_modules/`, lockfiles we don't track, `.env`,
  screenshots from `/tmp`.

## File naming
Scratch artifacts in `.claude/outputs/` use `<topic>_<kind>_v<n>.<ext>`, e.g.
`chat_redesign_preview_v1.html`.

## Before editing
1. Read the relevant file(s) first — no "I'll guess the API" edits.
2. If the request is ambiguous, ask one crisp clarifying question rather than
   picking a direction silently.
3. For features bigger than a one-liner, write a 6-line `spec.yaml` next to
   the code (template at repo root).

## Before shipping
1. Type-check passes (`cd frontend && npx tsc -b`).
2. Build passes (`cd frontend && npm run build`).
3. Git status is clean or only contains intentional additions.
4. Commit message leads with the *why*.
5. Push to the feature branch (never `main`).

## Never-do list
- Don't use `--no-verify`, `--amend` on pushed commits, or force-push to
  `main`.
- Don't add backwards-compat shims, stub feature flags, or "might be useful"
  helpers.
- Don't rename existing public tokens (`AMIE → AES` renames only happen
  deliberately, never as drive-by).
- Don't generate backend TTS — use the browser `SpeechSynthesis` API.

## The one rule
**Never send a PR without a spec.** A 6-line YAML counts. If you can't write
one, you don't understand the change well enough to ship it.
