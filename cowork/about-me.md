# About this team

> Edit this file with your team's specifics. Keep it short — under 2,000 words. Long about-me files burn tokens on every session.

## Who works on this

- USPS Address Management product team and authorized contractors.

## How we like to work

- Spec first, code second.
- Imperative, terse commit messages with a scope prefix (`backend:`, `frontend:`, `deploy:`, `docs:`).
- PRs link the spec in `cowork/outputs/` when one exists.
- Ask before guessing architecture.

## What breaks if the agent doesn't know this

- The LLM layer is provider-agnostic — `ollama | anthropic | mock`. Don't add a hard vendor dependency.
- Redis Stack covers vectors (RediSearch), conversations (RedisJSON), and cache. Don't introduce a second store.
- 508 accessibility is a hard requirement for any UI work.
- `python-jose[cryptography]` is the JWT library. Don't swap to PyJWT.
- Tests must run with `LLM_PROVIDER=mock` and `fakeredis` — no network calls.
