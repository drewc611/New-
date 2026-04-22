---
id: 508-compliance
name: Section 508 and WCAG 2.1 AA Audit
updated: 2026-04-22
scope: frontend (React SPA), backend response content
---

# Section 508 and WCAG 2.1 AA Audit

Section 508 of the Rehabilitation Act requires federal and federally
funded software to conform to **WCAG 2.1 Level AA**. This document is
the living audit for AMIE. It lists every known deviation, what to fix,
and how to verify the fix.

## How to run an audit

```bash
# 1. Static checks against a running dev server
npm install --no-save @axe-core/cli pa11y
npx axe http://localhost:5173 --tags wcag2a,wcag2aa,wcag21aa
npx pa11y http://localhost:5173 --standard WCAG2AA

# 2. Keyboard-only walk-through
#    Unplug your mouse. Tab through the whole chat flow:
#    sidebar -> new conversation -> composer -> send -> first bubble ->
#    citation link -> delete conversation. Every interactive control
#    must be reachable, have a visible focus ring, and be operable.

# 3. Screen reader smoke test
#    macOS: VoiceOver (Cmd+F5)
#    Windows: NVDA (free), JAWS (commercial)
#    Read through the empty state, send a message, wait for a streaming
#    reply. The reader should announce:
#      - the page heading
#      - each sample prompt as a button
#      - the composer textarea's label
#      - the streaming response once it settles
#      - any error banners

# 4. High contrast and zoom
#    - Browser zoom to 200 percent. No horizontal scroll, nothing cut off.
#    - OS high-contrast mode on. Borders and focus rings still visible.

# 5. Color contrast ratios
#    Use https://webaim.org/resources/contrastchecker/ or the axe
#    devtools extension to measure every foreground / background pair.
```

## Current findings

Severity uses the WCAG convention: **A** is highest-priority for Section
508 conformance, **AA** is required for federal use, **AAA** is nice to
have.

### FE-001  Composer submit button has no accessible name

- **Impact:** Screen-reader users hear "button" with no context.
- **WCAG:** 4.1.2 Name, Role, Value (A)
- **Where:** `frontend/src/components/Composer.tsx:34-40`
- **Fix:** Add `aria-label="Send message"`. When sending, announce the
  state change via the icon swap by pairing it with an `aria-live`
  region that reads "Sending..." then "Done" or an error.

```tsx
<button
  type="submit"
  aria-label={streaming ? "Sending message" : "Send message"}
  aria-disabled={streaming || !value.trim()}
  ...
>
```

### FE-002  Composer textarea relies on placeholder instead of a label

- **Impact:** Placeholders disappear on focus and are not reliably
  announced by all assistive tech.
- **WCAG:** 1.3.1 Info and Relationships (A), 3.3.2 Labels or
  Instructions (A)
- **Where:** `frontend/src/components/Composer.tsx:26-33`
- **Fix:** Either a visible `<label htmlFor="composer">` (visually
  hidden is fine) or `aria-label` on the textarea. Prefer a `<form>`
  element so Enter-to-submit is the platform default.

```tsx
<form onSubmit={handleSubmit} aria-label="Chat input">
  <label htmlFor="composer" className="sr-only">
    Ask AMIE a question
  </label>
  <textarea id="composer" ... />
</form>
```

### FE-003  Delete-conversation button is invisible without hover

- **Impact:** Keyboard-only users cannot tell the button exists; focus
  is not a trigger to reveal it.
- **WCAG:** 2.4.7 Focus Visible (AA), 2.1.1 Keyboard (A)
- **Where:** `frontend/src/components/Sidebar.tsx:67-73`
- **Fix:** Show the button whenever the row receives keyboard focus:

```tsx
<div className="group/row focus-within:bg-ink-50 ...">
  <button
    aria-label={`Delete conversation ${c.title}`}
    className="opacity-0 transition group-hover/row:opacity-100 focus-visible:opacity-100"
  >
```

Also use `focus-visible` so mouse users do not see a stuck focus ring.

### FE-004  Decorative icons are announced as content

- **Impact:** `User`, `Bot`, `MessageCircle`, `MessageSquarePlus`, and
  other lucide icons are announced by screen readers even though the
  neighboring text already conveys the meaning.
- **WCAG:** 1.1.1 Non-text Content (A)
- **Where:** `frontend/src/components/MessageBubble.tsx:22`,
  `frontend/src/components/Sidebar.tsx:38,64,72`,
  `frontend/src/components/CitationList.tsx:9,29`
- **Fix:** Add `aria-hidden="true"` to every lucide icon that is purely
  decorative, or wrap in `<span aria-hidden="true">`.

### FE-005  External citation links have no accessible name

- **Impact:** The link is an icon only. Screen readers read "link".
- **WCAG:** 2.4.4 Link Purpose (A), 4.1.2 (A)
- **Where:** `frontend/src/components/CitationList.tsx:22-30`
- **Fix:** `aria-label="Open {c.title} in a new tab"` on the `<a>`, and
  follow the external-link icon with a visually hidden "opens in new
  tab" span to alert users to the context change.

### FE-006  No skip-to-main-content link

- **Impact:** Keyboard users must tab through the full sidebar on every
  page load.
- **WCAG:** 2.4.1 Bypass Blocks (A)
- **Where:** `frontend/src/App.tsx`, `frontend/index.html`
- **Fix:** Add a visually hidden skip link as the first tab stop:

```tsx
<a href="#main" className="sr-only focus:not-sr-only focus:ring-2 ...">
  Skip to main content
</a>
<main id="main">...</main>
```

### FE-007  Streaming assistant replies are not announced

- **Impact:** A screen-reader user starts typing before the response
  has been announced, because nothing signals "new content arrived".
- **WCAG:** 4.1.3 Status Messages (AA)
- **Where:** `frontend/src/components/ChatView.tsx:28-52`
- **Fix:** Wrap the message list in `role="log" aria-live="polite"` so
  additions are announced without stealing focus. Only announce the
  final settled text, not every token.

### FE-008  Focus ring missing on most buttons

- **Impact:** Keyboard users cannot tell what is focused.
- **WCAG:** 2.4.7 Focus Visible (AA)
- **Where:** Nearly every `<button>` in `Sidebar.tsx`, `ChatView.tsx`,
  `CitationList.tsx`. Only the composer textarea uses `focus:ring-2`.
- **Fix:** Add a project-wide base button class in `index.css`:

```css
@layer components {
  .focus-ring {
    @apply focus-visible:outline-none focus-visible:ring-2
           focus-visible:ring-usps-blue/50 focus-visible:ring-offset-1;
  }
}
```

Apply `focus-ring` to every interactive element.

### FE-009  Respect `prefers-reduced-motion`

- **Impact:** Spinners, token fade-ins, and hover transitions can
  trigger vestibular disorders.
- **WCAG:** 2.3.3 Animation from Interactions (AAA, federal preference)
- **Where:** `animate-spin` in `Composer.tsx:39`, `typing-cursor` in
  `MessageBubble.tsx`, all `transition-*` classes.
- **Fix:** In Tailwind:

```js
// tailwind.config.js
plugins: [require('tailwindcss/plugin')(({ addVariant }) => {
  addVariant('reduced-motion', '@media (prefers-reduced-motion: reduce)');
})]
```

Then: `className="animate-spin reduced-motion:animate-none"`.

### FE-010  Color contrast near the AA floor for body text

- **Impact:** `text-ink-500` (#64748b) on `bg-ink-50` (#f8fafc) measures
  about 4.4:1, which fails normal-text AA (4.5:1).
- **WCAG:** 1.4.3 Contrast Minimum (AA)
- **Where:** `frontend/src/components/Sidebar.tsx:28`, `ChatView.tsx`
  empty-state subtitle, `Composer.tsx:42`
- **Fix:** Swap muted body text from `ink-500` to `ink-700` (#334155)
  which clears 9:1 on `ink-50`. Keep `ink-500` for decorative labels
  only.

### FE-011  Error messages disappear without being announced

- **Impact:** The red error box in `ChatView.tsx` shows once but is not
  a live region.
- **WCAG:** 4.1.3 Status Messages (AA)
- **Where:** `frontend/src/components/ChatView.tsx:54-58`
- **Fix:** `role="alert"` announces assertively. Provide a dismiss
  button so the message does not linger.

### FE-012  Keyboard trap risk in future modal work

- **Impact:** None today, but the existing code has no focus-trap
  utility and when modals land (delete confirmation, settings) they
  will ship without one.
- **WCAG:** 2.1.2 No Keyboard Trap (A)
- **Fix:** Add `focus-trap-react` or use `<dialog>` with the native
  `showModal()` API when a modal is introduced.

### BE-001  Backend error responses leak stack traces in dev

- **Impact:** Not strictly 508, but accessible error messages must be
  plain language. Stack traces in the UI alert banner fail 3.3.3 Error
  Suggestion (AA).
- **Where:** `frontend/src/lib/api.ts:19-22` displays the raw response
  body.
- **Fix:** In dev show a link "View details" that expands on demand; in
  prod strip stack trace content server-side before serialization.

### CO-001  Content authoring: Markdown replies must pass plain-language checks

- **Impact:** Long dense paragraphs are hard for screen readers and for
  users with cognitive disabilities.
- **WCAG:** 3.1.5 Reading Level (AAA, federal preference for plain
  language per Plain Writing Act).
- **Where:** System prompt in `backend/content/prompts/system.md`.
- **Fix:** The prompt already says "be concise." Add: "prefer short
  sentences; explain acronyms on first use; target a Flesch reading
  ease >= 50."

## Severity roll-up

| Count | Severity |
|---|---|
| 4 | A (blockers for Section 508) |
| 6 | AA (required for federal use) |
| 2 | AAA / federal preference |

## Remediation checklist

Copy this into a pull request description when fixing a batch:

```
## Section 508 remediation

- [ ] FE-001  Composer submit aria-label
- [ ] FE-002  Composer textarea label
- [ ] FE-003  Delete button focus-visible
- [ ] FE-004  Decorative icons aria-hidden
- [ ] FE-005  Citation link aria-label
- [ ] FE-006  Skip to main content
- [ ] FE-007  Live region for streaming replies
- [ ] FE-008  Focus-visible on all buttons
- [ ] FE-009  prefers-reduced-motion
- [ ] FE-010  Contrast on muted body text
- [ ] FE-011  Error banner role=alert
- [ ] BE-001  Redact error bodies
- [ ] CO-001  Plain language in system prompt

### Verification

- [ ] axe and pa11y both return zero violations at `--tags wcag2aa`
- [ ] Keyboard-only walkthrough complete
- [ ] NVDA or VoiceOver walkthrough complete
- [ ] Contrast report attached
```

## Getting to green

We treat the current state as **provisional 508 conformance with known
deviations**. Each sprint we close at least two items from the **A** or
**AA** list. A full VPAT (Voluntary Product Accessibility Template)
cannot be signed until every A and AA row above is resolved.

## See also

- `docs/tech-debt.md` for overlapping frontend debt.
- `docs/executive-report.md` for how 508 counts feed the status roll-up.
- USPS Accessibility Statement policy (internal): Handbook EL-307.
- GSA Section 508 program: https://www.section508.gov
