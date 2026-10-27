# Freight engine cleanup — October 26, 2026

Base: `ebbc7a27de9c879aae538ff662614fcd91c6cc3b`.

## Removed stale code and closed discovery gaps

Both existing release and commercial workflows now discover the complete Freight pytest suite, including standalone functions and nested site tests. The old unittest-only release command and manually enumerated commercial test list omitted coverage. The Priority 1 subprocess bridge is removed because its underlying suite now runs directly. Unused imports and assignments were removed; meaningful idempotency calls and rehearsal assertions remain. Pinned Ruff checks reject F401/F811/F821/F841 in the release lane.

## Reproduced stale Pennine replay expectation

Initial cleanup CI run 40438243510 passed the 85 four-release regression tests and replayed the 110 original freight invoices, then failed the Pennine fingerprint assertion. Neither scoped reconciliation nor the public census implementation had been changed by cleanup.

The earlier Priority 0 repair (`f176081d2902b28e0e8307b3c94333b81064b004`) introduced schema 2 and `all_original_inputs_sha256` in the reconciliation result. The census verifier still expected the schema-1 fingerprint.

A fresh read of all five original publisher files passed their existing byte SHA-256 checks. The replay preserved 314 disclosed rows, 273 unique invoices, 217 declaration groups, 7,423,667,742 source minor units, zero unmatched invoices, zero independently verified bank settlements, zero realized recovery and unknown freight accuracy.

Instrumenting only the result-hash boundary established the exact differential:

- Current schema-2 hash: `5e05a98f6c91a5dee5dcb9eb305e55438c694534d8f83cd83e2f372b36947eab`.
- The identical result body with only `schema=1` and `all_original_inputs_sha256` removed reproduces the old expected hash exactly: `c599d67a0887fa84aacb4bc91af28d3b72dfbadf6a552bb64ee76947d45ff213`.

The expected fingerprint is updated to schema 2; original source pins and financial totals are unchanged. A regression explicitly rejects the retired schema-1 fingerprint. This is an accounting interoperability replay, not customer recovery evidence.

## Verification and limits

Initial cleanup: 2,023 Python tests passed (baseline 2,024; redundant wrapper removed), 24 JavaScript tests, 18 production contract tests, compilation, rights consistency and unused-code checks passed. The fingerprint correction adds one parameterized negative case. Hosted checks on the final candidate remain the release authority.

This bounded cleanup does not establish absence of all dead code or undiscovered defects, real freight-error accuracy, independent bank evidence or customer launch authorization. Historical research and evidence are retained rather than removed solely because of age.
