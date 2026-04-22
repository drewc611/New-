---
id: executive-report
name: Executive Status Report Template
updated: 2026-04-22
cadence: weekly or on request
audience: program leadership, USPS sponsor, security auditor
---

# Executive Status Report

This is the template and the generator instructions for AMIE's
executive status reports. Run the generator whenever a briefing is due,
then fill in the narrative sections and send.

## How to generate a report

A companion script wires together git history, test results, address
analytics, and the 508 / tech-debt inventories.

```bash
# From the repo root
bash scripts/exec-report.sh > reports/$(date +%Y-%m-%d)-exec.md
```

The generator:

1. Pulls the last 14 days of `git log` and groups commits by area.
2. Runs `pytest -q` and records pass / fail counts.
3. Calls `GET /api/tools/address/analytics` on the local backend if it
   is running and drops the rollup into the metrics section.
4. Counts open rows in `docs/tech-debt.md` by severity.
5. Counts open rows in `docs/508-compliance.md` by WCAG severity.
6. Writes the filled-in report to stdout.

The narrative sections (Executive Summary, Risks, Upcoming Work) are
left with `TODO` placeholders; the human owner fills them in before
sending.

## Report template

Copy the block below when you need to write a report by hand. The
generator emits the same structure so formatting stays consistent.

```markdown
# AMIE Executive Status  {REPORT_DATE}

**Reporting period:** {START_DATE} to {END_DATE}
**Prepared by:** {NAME, ROLE}
**Release:** {VERSION or branch}
**Environment:** {dev | staging | prod}

## 1. Executive Summary

Three bullets. No more. What shipped, what is at risk, what is next.

- TODO what shipped
- TODO what is at risk
- TODO what is next

## 2. Program Health

| Indicator | Status | Trend |
|---|---|---|
| Delivery vs plan | Green | flat |
| Quality (test pass rate) | {PASS_RATE} | up/down |
| Security posture | {SEC_STATUS} | up/down |
| 508 conformance | {WCAG_STATUS} | up/down |
| Tech debt balance | {DEBT_STATUS} | up/down |

Legend: **Green** on plan, **Yellow** recoverable risk, **Red**
escalation required.

## 3. What Shipped This Period

Grouped by area, bullet form, one line each. Link commit hashes.

### Backend
- TODO {commit} short description

### Frontend
- TODO {commit} short description

### Infrastructure and ops
- TODO {commit} short description

### Documentation and policy
- TODO {commit} short description

## 4. Metrics

### 4.1 Test suite

- Total tests: {TESTS_TOTAL}
- Passing: {TESTS_PASSED}
- Failing or skipped: {TESTS_FAILED}
- Coverage (backend): {COV_BACKEND}
- Coverage (frontend): {COV_FRONTEND}

### 4.2 Address verification analytics

Pulled from `GET /api/tools/address/analytics`.

- Total verifications: {ADDR_TOTAL}
- Verified rate: {ADDR_VERIFIED_RATE}
- Average confidence: {ADDR_AVG_CONFIDENCE}
- Top DPV codes: {ADDR_TOP_DPV}
- Top warnings: {ADDR_TOP_WARNINGS}
- Suggestions offered / accepted: {ADDR_SUG_OFFERED} / {ADDR_SUG_ACCEPTED}

### 4.3 Tech debt

From `docs/tech-debt.md`.

| Severity | Open | Closed this period |
|---|---|---|
| Critical | {DEBT_CRIT_OPEN} | {DEBT_CRIT_CLOSED} |
| High | {DEBT_HIGH_OPEN} | {DEBT_HIGH_CLOSED} |
| Medium | {DEBT_MED_OPEN} | {DEBT_MED_CLOSED} |
| Low | {DEBT_LOW_OPEN} | {DEBT_LOW_CLOSED} |

### 4.4 Section 508 conformance

From `docs/508-compliance.md`.

| WCAG Severity | Open | Closed this period |
|---|---|---|
| A | {WCAG_A_OPEN} | {WCAG_A_CLOSED} |
| AA | {WCAG_AA_OPEN} | {WCAG_AA_CLOSED} |
| AAA / preference | {WCAG_AAA_OPEN} | {WCAG_AAA_CLOSED} |

## 5. Risks and Mitigations

List the top three risks, each with owner, mitigation, and target date.

| Risk | Likelihood | Impact | Mitigation | Owner | Target |
|---|---|---|---|---|---|
| TODO | Low / Med / High | Low / Med / High | TODO | TODO | YYYY-MM-DD |

## 6. Upcoming Work

Next sprint, by workstream. Keep it to commitments, not a wish list.

- **Backend:** TODO
- **Frontend:** TODO
- **Infra:** TODO
- **Security / 508:** TODO

## 7. Asks of Leadership

What decisions or resources are needed? None is a valid answer.

- TODO decision needed by {DATE}

## 8. Appendix

- Full commit list: `git log --since={START_DATE}`
- Release notes: `CHANGELOG.md`
- Open pull requests: `gh pr list`
- Incident log: `docs/incidents/` (if any this period)
```

## Cadence

| Audience | Frequency | Owner |
|---|---|---|
| Engineering lead to program manager | Weekly, Fridays | Engineering lead |
| Program manager to USPS sponsor | Biweekly | Program manager |
| Security auditor snapshot | Monthly or on request | Security lead |
| All-hands summary | Quarterly | Program manager |

## Editorial rules

- Keep the executive summary to three bullets.
- Facts first, narrative second.
- Every metric must cite its source (API, file, script).
- Colors are earned. A green status requires trend data to back it up.
- Never include PII in examples or metrics. The analytics endpoint
  already strips input addresses from the rollup; if a recent-events
  list is attached for triage it goes in a separate appendix marked
  **Sensitive**.

## See also

- `scripts/exec-report.sh` the generator script.
- `docs/tech-debt.md` source of truth for the debt metrics.
- `docs/508-compliance.md` source of truth for the 508 metrics.
- `docs/address-verification.md` describes the analytics endpoint.
