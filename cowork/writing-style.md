# Writing style

Anti-AI-slop rules for prose, docs, commit messages, and PR descriptions.

## Do

- Lead with the point. One sentence per idea.
- Concrete nouns and verbs. Specific examples over abstractions.
- Active voice. "We do X because Y" beats "X is done because of Y."
- Short paragraphs. Two sentences is fine.
- Cite paths and line numbers when referencing code.

## Don't

- "Comprehensive," "robust," "seamless," "leverage," "delve," "furthermore," "in conclusion."
- Marketing throat-clearing — "In today's fast-paced world…"
- Bullet lists where prose would be clearer.
- Headings on a 200-word doc.
- Closing summaries that restate what's already on screen.
- Em-dashes used as filler.
- Emojis unless a human asks for them.

## Commit messages

`<scope>: <imperative summary under 72 chars>`

Body, if needed, explains the WHY in 1–3 short paragraphs. Reference paths as `backend/app/foo.py:42`.

## PR descriptions

```
## Summary
<2–4 sentences>

## Why
<1–2 sentences — the user-facing or technical reason>

## Test plan
- [ ] <observable check>
```
