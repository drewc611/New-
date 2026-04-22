#!/usr/bin/env bash
# Generate an AMIE executive status report.
#
# Usage:
#   bash scripts/exec-report.sh > reports/$(date +%Y-%m-%d)-exec.md
#
# Environment variables:
#   SINCE       days of history to include (default 14)
#   API_BASE    backend base URL for analytics (default http://localhost:8000)
#   SKIP_TESTS  set to 1 to skip pytest (use when pytest is unavailable)
#
# The script never fails the whole report if a single section cannot be
# produced; missing pieces are replaced with the string "n/a".

set -u

SINCE_DAYS="${SINCE:-14}"
API_BASE="${API_BASE:-http://localhost:8000}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TODAY="$(date +%Y-%m-%d)"
START_DATE="$(date -d "-${SINCE_DAYS} days" +%Y-%m-%d 2>/dev/null \
  || date -v-"${SINCE_DAYS}"d +%Y-%m-%d)"
VERSION="$(git describe --tags --always 2>/dev/null || echo unknown)"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

# ---------- Commit summary ----------------------------------------------------
git_log_since() {
  git log --since="$START_DATE" --pretty=format:'- %h %s' -- "$@" 2>/dev/null \
    | head -n 25
}

BACKEND_COMMITS="$(git_log_since backend/ || echo '- n/a')"
FRONTEND_COMMITS="$(git_log_since frontend/ || echo '- n/a')"
INFRA_COMMITS="$(git_log_since deploy/ scripts/ docker-compose.yml docker-compose.windows.yml || echo '- n/a')"
DOCS_COMMITS="$(git_log_since docs/ README.md CHANGELOG.md || echo '- n/a')"

# ---------- Test suite --------------------------------------------------------
TESTS_TOTAL="n/a"
TESTS_PASSED="n/a"
TESTS_FAILED="n/a"
if [[ "${SKIP_TESTS:-0}" != "1" ]] && command -v python >/dev/null 2>&1; then
  if [[ -d backend ]]; then
    pushd backend >/dev/null
    TEST_OUT="$(python -m pytest -q 2>&1 || true)"
    popd >/dev/null
    TESTS_PASSED="$(echo "$TEST_OUT" | grep -oE '[0-9]+ passed' | head -1 | awk '{print $1}')"
    TESTS_FAILED="$(echo "$TEST_OUT" | grep -oE '[0-9]+ failed' | head -1 | awk '{print $1}')"
    TESTS_PASSED="${TESTS_PASSED:-0}"
    TESTS_FAILED="${TESTS_FAILED:-0}"
    TESTS_TOTAL="$(( TESTS_PASSED + TESTS_FAILED ))"
  fi
fi

# ---------- Address analytics -------------------------------------------------
ADDR_TOTAL="n/a"
ADDR_VERIFIED_RATE="n/a"
ADDR_AVG_CONFIDENCE="n/a"
ADDR_TOP_DPV="n/a"
ADDR_TOP_WARNINGS="n/a"
if command -v curl >/dev/null 2>&1 \
   && ANALYTICS_JSON="$(curl -fsS --max-time 3 "$API_BASE/api/tools/address/analytics" 2>/dev/null)"; then
  if command -v jq >/dev/null 2>&1; then
    ADDR_TOTAL="$(echo "$ANALYTICS_JSON" | jq -r '.total // "n/a"')"
    ADDR_VERIFIED_RATE="$(echo "$ANALYTICS_JSON" | jq -r '.verified_rate // "n/a"')"
    ADDR_AVG_CONFIDENCE="$(echo "$ANALYTICS_JSON" | jq -r '.average_confidence // "n/a"')"
    ADDR_TOP_DPV="$(echo "$ANALYTICS_JSON" | jq -r '.by_dpv_code | to_entries | map("\(.key):\(.value)") | join(", ")')"
    ADDR_TOP_WARNINGS="$(echo "$ANALYTICS_JSON" | jq -r '.top_warnings[:5] | map("\(.warning):\(.count)") | join(", ")')"
  fi
fi

# ---------- Tech debt counts --------------------------------------------------
count_debt_rows() {
  local severity="$1"
  # Count "Current inventory" rows whose first column is the severity.
  awk -v sev="| $severity " '
    /^## Current inventory/ {in_inv=1; next}
    /^## Resolved/ {in_inv=0}
    in_inv && index($0, sev) == 1 {count++}
    END {print count+0}
  ' docs/tech-debt.md 2>/dev/null || echo 0
}

count_debt_closed() {
  local severity="$1"
  awk -v sev="| $severity " -v start="| $START_DATE" '
    /^## Resolved/ {in_res=1; next}
    /^## / && in_res {in_res=0}
    in_res && index($0, sev) > 0 && index($0, start) == 1 {count++}
    END {print count+0}
  ' docs/tech-debt.md 2>/dev/null || echo 0
}

DEBT_CRIT_OPEN="$(count_debt_rows Critical)"
DEBT_HIGH_OPEN="$(count_debt_rows High)"
DEBT_MED_OPEN="$(count_debt_rows Medium)"
DEBT_LOW_OPEN="$(count_debt_rows Low)"
DEBT_CRIT_CLOSED="$(count_debt_closed Critical)"
DEBT_HIGH_CLOSED="$(count_debt_closed High)"
DEBT_MED_CLOSED="$(count_debt_closed Medium)"
DEBT_LOW_CLOSED="$(count_debt_closed Low)"

# ---------- 508 counts --------------------------------------------------------
count_508_open() {
  # Each finding block ends with "**WCAG:** ... (A)" or (AA) or (AAA)
  local tag="$1"
  grep -oE "\\*\\*WCAG:\\*\\*[^(]*\\($tag\\)" docs/508-compliance.md \
    2>/dev/null | wc -l | awk '{print $1}'
}

WCAG_A_OPEN="$(count_508_open A)"
WCAG_AA_OPEN="$(count_508_open AA)"
WCAG_AAA_OPEN="$(count_508_open AAA)"
# Closed counts come from Resolved sections if you maintain them; default 0.
WCAG_A_CLOSED=0
WCAG_AA_CLOSED=0
WCAG_AAA_CLOSED=0

# ---------- Roll-up statuses --------------------------------------------------
if [[ "$TESTS_FAILED" != "n/a" && "$TESTS_FAILED" -gt 0 ]]; then
  PASS_RATE_STATUS="Yellow"
else
  PASS_RATE_STATUS="Green"
fi

if [[ "$DEBT_CRIT_OPEN" -gt 0 ]]; then
  SEC_STATUS="Red"
elif [[ "$DEBT_HIGH_OPEN" -gt 0 ]]; then
  SEC_STATUS="Yellow"
else
  SEC_STATUS="Green"
fi

if [[ "$WCAG_A_OPEN" -gt 0 ]]; then
  WCAG_STATUS="Red"
elif [[ "$WCAG_AA_OPEN" -gt 0 ]]; then
  WCAG_STATUS="Yellow"
else
  WCAG_STATUS="Green"
fi

DEBT_STATUS="Green"
if (( DEBT_CRIT_OPEN + DEBT_HIGH_OPEN > 0 )); then DEBT_STATUS="Yellow"; fi
if (( DEBT_CRIT_OPEN > 0 )); then DEBT_STATUS="Red"; fi

# ---------- Emit the report ---------------------------------------------------
cat <<EOF
# AMIE Executive Status  $TODAY

**Reporting period:** $START_DATE to $TODAY
**Prepared by:** TODO name, role
**Release:** $VERSION on $BRANCH
**Environment:** dev

## 1. Executive Summary

- TODO what shipped
- TODO what is at risk
- TODO what is next

## 2. Program Health

| Indicator | Status | Trend |
|---|---|---|
| Delivery vs plan | TODO | TODO |
| Quality (test pass rate) | $PASS_RATE_STATUS ($TESTS_PASSED / $TESTS_TOTAL) | TODO |
| Security posture | $SEC_STATUS | TODO |
| 508 conformance | $WCAG_STATUS | TODO |
| Tech debt balance | $DEBT_STATUS | TODO |

## 3. What Shipped This Period

### Backend
$BACKEND_COMMITS

### Frontend
$FRONTEND_COMMITS

### Infrastructure and ops
$INFRA_COMMITS

### Documentation and policy
$DOCS_COMMITS

## 4. Metrics

### 4.1 Test suite
- Total: $TESTS_TOTAL
- Passing: $TESTS_PASSED
- Failing: $TESTS_FAILED

### 4.2 Address verification analytics
- Total verifications: $ADDR_TOTAL
- Verified rate: $ADDR_VERIFIED_RATE
- Average confidence: $ADDR_AVG_CONFIDENCE
- DPV breakdown: $ADDR_TOP_DPV
- Top warnings: $ADDR_TOP_WARNINGS

### 4.3 Tech debt

| Severity | Open | Closed this period |
|---|---|---|
| Critical | $DEBT_CRIT_OPEN | $DEBT_CRIT_CLOSED |
| High | $DEBT_HIGH_OPEN | $DEBT_HIGH_CLOSED |
| Medium | $DEBT_MED_OPEN | $DEBT_MED_CLOSED |
| Low | $DEBT_LOW_OPEN | $DEBT_LOW_CLOSED |

### 4.4 Section 508 conformance

| WCAG Severity | Open | Closed this period |
|---|---|---|
| A | $WCAG_A_OPEN | $WCAG_A_CLOSED |
| AA | $WCAG_AA_OPEN | $WCAG_AA_CLOSED |
| AAA / preference | $WCAG_AAA_OPEN | $WCAG_AAA_CLOSED |

## 5. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation | Owner | Target |
|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO |

## 6. Upcoming Work

- **Backend:** TODO
- **Frontend:** TODO
- **Infra:** TODO
- **Security / 508:** TODO

## 7. Asks of Leadership

- TODO

## 8. Appendix

Generated by \`scripts/exec-report.sh\` at $(date -u +"%Y-%m-%dT%H:%M:%SZ").
EOF
