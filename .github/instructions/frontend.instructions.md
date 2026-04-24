---
applyTo: "frontend/**"
description: "React + TypeScript frontend conventions"
---

# Frontend (React 18 + TypeScript + Vite + Tailwind)

## Style

- Function components with hooks. No class components.
- TypeScript strict mode — no `any` unless unavoidable and commented.
- Tailwind utility classes inline. No CSS modules, no styled-components.
- Co-locate component, styles (if any), and tests in the same folder.

## Structure

- `frontend/src/components/` — reusable UI.
- `frontend/src/pages/` or route-level views.
- `frontend/src/api/` — typed fetch wrappers for the FastAPI backend.
- `frontend/src/hooks/` — custom hooks.

## Data fetching

- Hit the backend via the typed clients in `frontend/src/api/`. Don't scatter `fetch` calls.
- SSE for chat streaming. Handle reconnect and cleanup on unmount.

## Accessibility (508)

- Semantic HTML. Label every interactive element.
- Keyboard navigable. Visible focus indicators.
- Color contrast WCAG AA minimum. See `docs/508-compliance.md`.

## Do not commit

- Compiled JS (`frontend/src/**/*.js`) — gitignored.
- `package-lock.json` — gitignored per repo policy.
