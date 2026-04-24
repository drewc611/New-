---
description: "Clarify scope before acting — ask me questions instead of guessing"
model: claude-sonnet-4.6
agent: ask
---

# /ask-me-questions

For the task I'm about to give, do not start coding. First, ask me a short numbered list of clarifying questions.

## Rules

- Maximum 5 questions. Prefer 2–3.
- Each question should be answerable with a short reply — options are better than open-ended.
- Cover: scope boundary, acceptance criteria, constraints I haven't mentioned, and any architectural choice you'd otherwise guess.
- Wait for my answers before proposing an approach or writing code.

This mirrors the Cowork workflow rule: "AskUserQuestion = always on."
