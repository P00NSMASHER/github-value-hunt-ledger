# RETALLY Labs 04–14: Nonoverlapping defect repair handoff

**Evidence class: repaired isolated SYNTHETIC toolkits. Neither production code
nor the hosted RecoveryOS application was modified.**

## Coordination and branch ownership

This branch began from main commit `7256bbc2239b5b490e594be681762def43b42c57` and deliberately does NOT edit:
- **PR #279:** cumulative audit register
- **PR #284:** independent financial semantic checker
- **PR #286:** original Unified Laboratory financial controls/state-machine repair
- PRs #263/#264/#271/#272/#273/#275 and their own drafts

The separate conversation is repairing the original Unified/StagingTwin defects. This
branch handles **only** Y-01..Y-04 (Labs 04–10), X-01..X-05 (Labs 11–14), and Z-01
(installer). Do not merge independently before reconciling the other chat's work.

## Delivered reproducible source and patches

The associated ChatGPT download:
`RETALLY_Labs_04_14_Hardened_Synthetic_Toolkits.zip`

- SHA-256: `dc730dece0e9b8bbe92638bae551fc80e9720cf7a43c10ce2e4e8c6b0ee0729d`.
- Each changed tool's full source and regressions is inside the ZIP.
- Human-reviewable patches `PATCH_LABS_04_10.patch` and `PATCH_LABS_11_14.patch`.
- 640 individually SHA-256-controlled files plus the file manifest.
- Original downloadable toolkits are **preserved unmodified**.
- Large legacy seven-million/four-million-case archives are **NOT recertified**; rerun
  them with the corrected engines and independently frozen source census.
- Generated 10,000-source-case pilots and regenerated 1,000-case local UI/replay
  fixtures are included, with separate JSON verification receipts and SQL indexes.

### Findings independently reproduced FAIL before fix and PASS after fix

| Historical ID | Fixed in isolated code | Explicit regression |
|---|---|---|
| Y-01 | Frozen invoice/customer/carrier/source digest compared to independently supplied source row | Rehashed wrong source digest is rejected |
| Y-02 | Lab 5 amount event types tied to source and summary, no free-form cash | Rehashed $1.2M phantom bank reconciliation rejected |
| Y-03 | Credit settlement, receipt, and bank reversal are explicit ordered counter-events | Synthetic reversal has nonzero source-linked cancellation events |
| Y-04 | Cross-lab receipt checks independent source/customer and disallows seven forged agreeing copies | Seven agreeing forged hashes fail source-anchored census |
| X-01 | Independent Lab 11–14 verifier checks money-bearing event amount against summary | Counterfactual event +$100k rehashed and rejected |
| X-02 | Negative/out-of-bounds synthetic latency rejected | -1,000,000 milliseconds rejected |
| X-03 | Vendor/URL/evidence class allowlisted and evidence date/digest pinned | Arbitrary HTTPS vendor URL rejected |
| X-04 | Hypothetical net benefits signed, losses counted and actionable amount separate | Negative costs preserved, including sensitivity report |
| X-05 | Fraud flag checked in both directions against scenario truth | Rehashed fraudulent-flag contradiction rejected |
| Z-01 | Missing/empty archive makes restore fail before output; toolkit-only is explicitly partial | Zero-file/missing ZIP rejects; safe positive restore passes |

### Measured cleaned-source pilot

| Suite | Tests | Original source invoices | Modeled cases | Events |
|---|---:|---:|---:|---:|
| Labs 04–10 | **84/84 PASS** | 10,000 | 70,000 | 509,932 |
| Labs 11–14 | **176/176 PASS** | 10,000 | 40,000 | 195,423 |

Both new pilots compared input rows to the original *fictional* source SHA
`7c670a91a1a411480b35d054b821f483744267b9c07acda9fe974d910888ed81`.
Both rebuilt SQLite indexes successfully. All 640 included files passed a
separate clean-extraction digest and the **260 total** unit tests passed in the
re-extracted toolkits.

Lab 13 signed loss audit on its 10k scenario population found **1,339
negative model outcomes totaling 2,663,480 cents ($26,634.80)** in hypothetical
implementation downside. These represent *fictional modeled losses* not cash lost
or real customer performance. Real verified savings and collections remain zero.

## Critical limitations and merge gate

- The local source anchor proves **fictional internal source equality**, not
  valid buyer consent or external customer ownership.
- Real production vendor pages and their live capabilities were NOT tested.
  A pinned vendor URL/evidence hash is a source-identity control, not an
  independent vendor assertion or commercial reliability claim.
- Model latency, fraud labels, invoice savings, and reversals are synthetic.
- Original **26 offline legacy findings plus 2 narrowly repaired research-gate
  findings** remain tracked in PR #279. This change provides narrow regression
  evidence for ten of the 26 original issues without overwriting that registry.
- Current PR #286 is independently modifying the Unified engine. Coordinate
  review before integrating it with these namespaced toolkits.
- The old full **7,000,000** and **4,000,000** scenario results need full regeneration,
  source-anchored verification, and downstream dashboard refresh before the
  new full-population gate can be marked PASS.
- No merges, scheduled task changes, customer emails, carrier contact, banks,
  purchases, public deployment, or actual recovered revenue occurred.

## New repository-only guard

`freight/lab_repair_04_14_contract.py` and its tests are an additional CI
guard around evidence handoff, ensuring the 10k pilot cannot be conflated with
the full millions. This is **not** a replacement for the downloaded repaired
simulator code or an independent audit of the hosted product.

**Status:** ISOLATED OFFLINE REPAIRS VERIFIED; STAGING/PRODUCTION STILL BLOCKED.
