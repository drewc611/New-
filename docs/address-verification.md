# Address Verification

AMIE's address tool parses, standardizes, scores, and when needed
suggests corrections for free-form US addresses. It follows USPS
Publication 28 and is designed to handle the full range of addressing
formats the AMS can issue.

## Supported formats

| Format | Example |
|---|---|
| Street address | `1600 Pennsylvania Ave NW, Washington, DC 20500` |
| With secondary unit | `500 Market St Ste 2200, San Francisco, CA 94105` |
| Secondary without number | `221 Baker St Bsmt, Chicago, IL 60614` |
| PO Box | `PO Box 12345, Anchorage, AK 99501-0001` |
| Rural Route | `RR 2 Box 152, Ames, IA 50014` |
| Highway Contract | `HC 68 Box 23A, Eagle, AK 99738` |
| General Delivery | `General Delivery, Juneau, AK 99801` |
| Military APO/FPO/DPO | `PSC 1234 Box 5678, APO AE 09369` |
| Puerto Rico urbanization | `URB Las Gladiolas, 150 Calle A, San Juan, PR 00926` |
| Firm (company) line | `Acme Widgets Inc, 100 Industrial Pkwy, Suite 400, Buffalo, NY 14201` |

Each of those is covered by `backend/tests/test_address_parser.py`.

## Pipeline

```
raw input
   |
   v
noise cancellation        <-- app.tools.address_noise
   | (strips filler, quotes, emoji, phone, email, URL, ATTN, c/o,
   |  trailing country, trailing "thanks/please", etc.)
   v
Publication 28 parser     <-- app.tools.address_parser
   | (primary number, pre/post directional, street name, suffix,
   |  secondary designator, firm, urbanization, last line)
   v
verifier                  <-- app.tools.address_mock or address_usps
   | (dpv, confidence, verified flag)
   v
(optional) suggester      <-- app.tools.address_suggester
   | (fuzzy match unknown suffix / directional / designator / state,
   |  stitch corrected candidate, score each)
   v
analytics sink            <-- app.services.address_analytics
   | (bounded Redis stream + rollup counters)
   v
response
```

## Confidence scoring

| DPV | Meaning | Confidence |
|---|---|---|
| `Y` | Primary and secondary both valid | 0.95 |
| `S` | Primary valid, secondary not confirmed | 0.55 - 0.70 |
| `D` | Primary valid, secondary required but missing | 0.70 |
| `N` | Address not valid | 0.20 |

When the mock verifier is used, the score reflects parse completeness;
when `usps_api` is configured, the score comes from the live DPV code
returned by USPS Web Tools.

## Suggestions

If the verifier produces low confidence, the suggester:

1. Reruns noise cancellation.
2. Fuzzy matches unknown tokens against the Publication 28 tables:
   suffixes, directionals, secondary designators, and states. The
   matcher uses `difflib.SequenceMatcher` (Ratcliff-Obershelp) and
   requires a score above category-specific cutoffs so near-misses do
   not overfit.
3. Rebuilds the address with the corrections applied, reparses, and
   returns the top N candidates ranked by confidence.

Each suggestion includes a `reasons` array ("removed noise: filler",
"corrected suffix 'STRET' -> 'ST'") so the chat UI can show the user
why a correction was offered.

## Analytics

`/api/tools/address/analytics` returns rollups:

```
{
  "total": 142,
  "verified": 118,
  "verified_rate": 0.831,
  "average_confidence": 0.78,
  "by_dpv_code": {"Y": 103, "S": 15, "D": 7, "N": 17},
  "by_address_type": {"street": 121, "po_box": 14, "rural_route": 4, "military": 3},
  "top_warnings": [
    {"warning": "secondary_missing_number", "count": 9},
    {"warning": "missing_zip", "count": 6}
  ],
  "recent": [ AddressAnalyticsEvent, ... ]
}
```

Each verification attempt goes into a bounded Redis stream
(`amie:addr:events`, capped at 50k entries) and increments hash
counters. The analytics path never raises; if Redis is unreachable the
verifier still returns its result and the event is silently dropped.

## Extending the parser

Add a suffix variant that USPS recognizes but the baked-in table did
not include:

1. Edit `backend/content/standards/suffix-overrides.md` and add a row.
2. Restart the backend (`apply_overrides()` runs during lifespan startup).

The same mechanism exists for secondary designators. See
`docs/markdown-driven.md` for details.

## API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/tools/address/verify` | POST | Verify an address, return components + suggestions |
| `/api/tools/address/suggest` | POST | Return only suggestions (no analytics row) |
| `/api/tools/address/analytics` | GET | Rollup of verification outcomes |
