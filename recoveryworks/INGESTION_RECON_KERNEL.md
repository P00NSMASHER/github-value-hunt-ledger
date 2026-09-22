# Recon shared matching-kernel ingestion contract

This document records the first normalized third-party capability ingestion for
RecoveryWorks. It captures a verified external implementation and the boundary
for adapting it into the common Recovery OS. It does not vendor code into this
repository, send claims, contact counterparties, authorize recovery actions, or
change existing RecoveryWorks production behavior.

## Source identity

- Repository: `dylanpulver/recon`
- Canonical URL: `https://github.com/dylanpulver/recon`
- Default branch: `main`
- Pinned commit: `e6b787213bb023568c99c432ea4733e1f2456a5e`
- Commit date: 2026-09-04
- Observed license: MIT
- Package: `recon@1.0.0`
- Runtime: Node.js >= 20
- Runtime dependencies: none declared; TypeScript and Node types are development dependencies
- Intended role in RecoveryWorks: shared deterministic transaction-reconciliation kernel
- Commercial evaluation assumption: user states they hold commercial rights; observed MIT license independently permits reuse subject to its terms

The pinned commit is the provenance anchor for all implementation statements
below. Future ingestion refreshes must record a new commit and re-run the same
verification checks rather than silently treating `main` as immutable.

## What is actually implemented

The source implements a deterministic five-tier matching ladder in
`src/engine.ts`. Higher-confidence matches consume rows before lower tiers, so
an exact match cannot later be stolen by a fuzzy or tolerance match.

### Tier 1 — exact

Requires:

- same currency
- identical minor-unit amount
- identical calendar date
- a nonblank reference on both sides
- byte-identical reference after surrounding whitespace is trimmed

Blank references are deliberately not treated as identity evidence.

### Tier 2 — normalized-reference match

Requires:

- same currency
- identical amount
- normalized references that reduce to the same canonical value
- dates within a configurable window

The match receipt preserves the raw references, normalized value, and
normalization steps that fired. The implementation therefore exposes the
reason a fuzzy reference matched rather than returning only a score.

### Tier 3 — amount/date-window match

Requires:

- same currency
- identical amount
- dates within the configured window

No reference is required. Candidate ambiguity is resolved deterministically by
closest date and then settlement ID.

### Tier 4 — amount-tolerance match

Requires:

- same currency
- dates inside the configured window
- amount delta inside the configured basis-point tolerance or absolute minor-unit floor

Receipts preserve:

- signed amount delta
- allowed delta
- consumed basis points
- date delta

Candidate selection prefers the smallest amount delta, then closest date, then
stable ID ordering.

### Tier 5 — many-to-one batch match

Implements a bounded subset-sum search so multiple internal rows can reconcile
to one settlement row.

Controls include:

- maximum group size
- maximum candidate count
- maximum search-node budget
- date window
- optional basis-point tolerance on the batch total

The implementation only uses positive rows as batch components. Refunds and
other non-positive values are intentionally excluded from many-to-one grouping.
This prevents a positive sale plus negative refund from manufacturing a batch
sum that the source does not explicitly support.

## Determinism and money handling

`src/engine.ts` canonicalizes row processing order by date, amount, then unique
ID before matching. The stated and tested invariant is that the same input sets
produce byte-identical output even when the input arrays arrive in different
orders.

`src/money.ts` converts amounts to integer minor units rather than performing
reconciliation in floating point. Malformed numbers, unsupported precision, and
ambiguous money representations fail rather than being silently rounded into a
match.

Currencies never cross-match. The kernel does not perform foreign-exchange
conversion.

## Explainability receipts

Every accepted match carries a receipt. Depending on tier, it records:

- rule/tier name
- fields compared
- date delta
- amount delta
- tolerance consumed
- normalized raw/reference evidence
- human-readable evidence notes

The kernel's design commitment is effectively: **no receipt, no match**.

RecoveryWorks should preserve this property when adapting the engine. A branch
adapter may enrich a receipt with source hashes, row locators, rule IDs, contract
or tariff provenance, but it must not discard the matching receipt.

## Residual classification

Unmatched rows are not collapsed into one generic bucket.

The engine emits:

- `missing-in-settlement`
- `missing-in-internal`
- `amount-mismatch`

An amount mismatch can retain the candidate row ID, signed amount delta, and
shared normalized reference. This is directly useful to recovery branches
because it distinguishes "money never appeared" from "related money appeared at
a different amount."

## Verified implementation evidence

Key source files at the pinned commit:

| File | Verified role |
|---|---|
| `src/engine.ts` | deterministic five-tier ladder, residuals, summaries |
| `src/money.ts` | strict money parsing into minor units |
| `src/normalize.ts` | reference normalization |
| `src/subset-sum.ts` | bounded deterministic many-to-one search |
| `src/dates.ts` | strict date handling |
| `src/types.ts` | transaction/config/result/receipt domain model |
| `src/report.ts` | output/report formatting |
| `src/cli.ts` | executable command-line surface |

Test evidence:

| File | Verified coverage |
|---|---|
| `test/tiers.test.ts` | exact semantics for all five tiers, ladder order, currency isolation, residuals, guardrails |
| `test/property.test.ts` | deterministic seeded scenarios, partition/conservation-style properties, receipts, corruption buckets, shuffle invariance, residual fixpoint behavior |
| `test/units.test.ts` | money/date/normalization unit behavior |
| `test/cli.test.ts` | CLI behavior |
| `test/gen.ts` | generated scenario corpus |
| `test/harness.ts` | test harness utilities |

`package.json` defines `npm test` as a TypeScript build followed by Node's
test runner over the compiled test suite.

## RecoveryWorks capability mapping

This is a **shared primitive**, not a standalone recovery branch.

Primary primitive:

`normalized source rows -> deterministic matching -> receipts -> residuals`

Likely first consumers:

1. APRecovery
   - invoice/payment matching
   - vendor credits
   - duplicate-payment evidence
   - batch-payment allocation

2. FreightRecovery
   - invoice/settlement joins
   - carrier credit tracking
   - payment/remittance exceptions

3. Merchant/Processor Recovery
   - processor transaction -> settlement -> payout -> bank deposit
   - fee and net-settlement exception queues

4. SaaS / Cloud / SLA Recovery
   - vendor credit note -> expected credit -> received credit

5. Amazon/FBA Recovery
   - reimbursement candidates -> reimbursements actually received

6. BenefitsRecovery
   - expected carrier credit -> later invoice credit
   - payroll/enrollment/invoice linkage after domain-specific eligibility checks

7. Utility / Telecom / Lease / Rebate branches
   - expected credit or adjustment -> settlement evidence

## Integration boundary

RecoveryWorks should not copy the matching result directly into a validated
recovery finding.

The safe boundary is:

```text
branch adapter
  -> normalized transaction rows
  -> reconciliation kernel
  -> match receipts / residuals
  -> branch-specific entitlement and eligibility rules
  -> source/rule verification
  -> finding review
  -> claim/credit workflow
  -> recovered-cash confirmation
```

A reconciliation match proves that two monetary records correspond under the
configured rule. It does **not** prove:

- contractual entitlement
- statutory entitlement
- tariff applicability
- claim eligibility
- causation
- recoverability
- that a counterparty owes money

Those remain branch-specific RecoveryWorks responsibilities.

## Fail-closed requirements for adaptation

The RecoveryWorks adapter should preserve or strengthen these source
guardrails:

- unique IDs per side
- mandatory currency
- strict date parsing
- strict amount parsing
- no cross-currency matches
- bounded fuzzy/tolerance windows
- explicit many-to-one resource limits
- receipts on every match
- unmatched rows retained as evidence, not discarded

Additional RecoveryWorks requirements:

- preserve source SHA-256 and row/object locator for every normalized transaction
- retain original raw value alongside normalized value
- record the exact reconciliation config used
- record the pinned kernel version/commit
- distinguish imported algorithm evidence from verified customer source evidence
- never promote a tolerance/fuzzy match to entitlement without branch evidence
- never treat an amount mismatch as a recoverable amount until entitlement is independently computed

## Known limitations

The verified implementation does not provide:

- one-to-many matching
- general many-to-many matching
- FX conversion
- probabilistic/ML entity matching
- contract or tariff interpretation
- entitlement calculation
- deadline logic
- claim submission
- settlement collection
- recovered-cash verification

Many-to-one is intentionally bounded and only considers positive internal rows.
These constraints are desirable defaults for hostile-examination-grade recovery
because they make unsupported aggregation harder, but branches may need
additional explicitly verified match types later.

## Engineering leverage

Estimated engineering saved: **4-8 weeks** for a trustworthy common matching
kernel, potentially more when counting property-test design and receipt
semantics.

Opportunity score as a reusable Recovery OS primitive: **9.7 / 10**.

The commercial value is leverage across many recovery branches rather than a
standalone buyer-facing product.

## Next ingestion step

Do not broaden this file into branch logic.

The next small implementation step should be a native
`recoveryworks/reconciliation_kernel.py` compatibility layer or equivalent
internal interface that reproduces these invariants in RecoveryWorks' Python
runtime while preserving this pinned source as provenance. That adapter should
be tested against a compact cross-language fixture set before any existing
branch is switched to it.
