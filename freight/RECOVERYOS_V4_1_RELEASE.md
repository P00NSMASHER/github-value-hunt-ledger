# RecoveryOS 4.1 | Exact-cent correction and overflow safety

**Status:** Published October 31, 2026 to [Freight RecoveryOS](https://freight-recoveryos.floot.app). Supersedes the operational metadata for 4.0; preserves the [4.0 historical release record](RECOVERYOS_V4_0_RELEASE.md).

- Floot source version: `1793500547437` (project `c719b60c-9b3b-4193-a543-0be9d3ceaef2`).
- Independently reported Floot production publish: job `5a9bf623-ebe4-42a9-a912-345f480bceed`, **succeeded**.
- Reversible code checkpoint: `e01ddee5-c110-408a-9c99-fe3d63edbbdd`.
- Verification: **17 Jasmine spec files passed**, full TypeScript typecheck **clean**.

## Customer-risk correction

The human review field for invoice totals previously called `Math.round(Number(amount) * 100)`, which could silently round sub-cent inputs and lose precision. RecoveryOS 4.1 now parses decimal tokens into exact integer cents with `BigInt`, limits entries to 2 decimal places and safe integer-cent range, rejects scientific notation/malformed entries, and formats stored cents as a canonical decimal string. When a new extraction version becomes available for the same source document, the visible correction fields refresh from that extraction rather than silently retaining an outdated draft.

The extraction assessment also **blocks** aggregate line-item sums beyond exact integer precision. It does not mislabel overflow as an ordinary line-total difference or approve a new finding. Regression tests include 5,000 exact-cent roundtrips, malformed and malicious inputs, upper bounds, stale-review state and an overflowing source line-item case.

## Nonclaims and preserved boundaries

This release does **not** prove a freight overcharge, authorize carrier contacts, process payouts, admit new customers, verify any provider-supplied settlement against a bank, or relax source/contract/independent reviewer checks. There were **no** new payment endpoints, credentials, database migrations, or customer data in the change. Production customer-recovery acceptance remains `HOLD`.

Floot reported three pre-existing endpoint integration warnings, including an intentionally disabled Microsoft login and external integration endpoints; they are not part of this release and must not be wired into UI merely to suppress warnings.
