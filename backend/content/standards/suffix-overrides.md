---
id: suffix-overrides
name: USPS street suffix overrides
source: Publication 28 Appendix C1
updated: 2026-04-22
---

# Street Suffix Overrides

Each row is a variant spelling that should be collapsed to the standard
USPS abbreviation at parse time. The parser ships with the full table
baked in. This file only needs entries for corrections or local
additions that have not yet been merged upstream.

| variant      | standard |
|--------------|----------|
| PRKWY        | PKWY     |
| XRD          | XRD      |
| XING         | XING     |

If a variant and standard already exist in the baked-in table, the
override here is a no-op.
