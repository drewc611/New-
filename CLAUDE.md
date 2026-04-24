# CLAUDE.md

Project playbook for Claude Code sessions. Keep this file short.

## Read before every task
- `.claude/about-me.md` — product identity, who breaks what.
- `.claude/style.md` — writing + code style rules.
- `.claude/operating-rules.md` — folder protocol + guardrails.
- `spec.template.yaml` — the 6-line spec scaffold for any non-trivial change.

## Project
USPS Address Enterprise Service (AES) Help Assistant.
- Frontend: React 18 + TypeScript + Vite + Tailwind + Zustand + lucide-react.
- Backend: FastAPI + Anthropic SDK + Redis RAG + sentence-transformers.
- TTS: browser `SpeechSynthesis` API (no backend TTS service).
- USPS brand tokens live in `frontend/tailwind.config.js` (`usps-blue #004b87`, `usps-red #da291c`).

## Working style

### Spec first, code second
Before non-trivial work, write / update a `spec.yaml` next to the change.
Template in `spec.template.yaml`. Blocks: `goal`, `decisions`, `steps`, `done`.
Goal is one sentence. Decisions record the *why*, not the *what*.

### Avoid vibe coding
No speculative abstractions. No "might be useful later" helpers. Three similar
lines beat a premature abstraction. Delete unused code rather than keep it
around "just in case".

### Document the why, not the what
Comments explain hidden constraints, subtle invariants, workarounds — never
restate code. PR descriptions hold the narrative; code stays clean.

## Token discipline (session hygiene)

1. **Convert files before uploading** — paste text / markdown, not PDFs or
   screenshots of text.
2. **Plan in chat, build in code** — decide the approach in conversation, then
   make one focused edit pass.
3. **Ask questions** when requirements are ambiguous. Don't guess, don't
   silently invent API shapes.
4. **Batch related tasks** into one message rather than ping-ponging 3 prompts.
5. **Edit the original message** instead of "no I meant…" follow-ups.
6. **Restart, don't follow up** when a thread has drifted — each follow-up
   re-reads the whole history.
7. **New topic = new chat.** Don't pile unrelated work into one session.
8. **Don't dump the whole folder.** Attach only the files needed for the
   current task.
9. **Keep this file short** (< ~2000 tokens). Every session re-reads it.
10. **Turn off features you don't need** (web search, extra MCP servers) on
    tasks that don't use them.
11. **Summarize every 15-20 messages**, then start fresh with the summary.
12. **Pick the right model.** Haiku/Sonnet for spell-checks and grunt work,
    Opus for architecture and hard debugging.
13. **Reuse prompt structure.** Stable scaffolding, swap only the variable part.
14. **Stop using Claude for things it can't do** — no image generation, no
    real-time search. Route those elsewhere.

## Commands
- Frontend dev: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`
- Frontend type-check only: `cd frontend && npx tsc -b`
- Backend: see `backend/README` / `docker-compose.yml`

## Branching
Feature branches follow `claude/<kebab-description>-<suffix>`. Commit messages
lead with the *why*, body explains the *what* only when non-obvious. Never
force-push `main`. Never `--no-verify`.
