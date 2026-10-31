# Freight Recovery 16.0 | Release requirements and evidence boundaries

**Candidate engineering version:** 16.0.0, October 31, 2026.

## Version authority

- Core historical canonical release: v15.14, documented in `freight/RELEASE_MANIFEST.md`.
- Version 16.0.0 introduces a **public browser-only original-record evidence preflight**; it does not change contracts, rate authority, settlement accounting, recovery rights, or provider actions.
- Website visual/marketing system retains its independent `free-audit-contingency-v5` release marker.
- RecoveryOS is a separate authenticated application. Its v4.0 proof dashboard is not the same as Freight Recovery v16.

## 16.0.0 shipping acceptance

1. All six buyer-marked source families are represented: original carrier invoice, effective signed rate, original shipment facts, paid/credit evidence, prior incumbent state, and stable invoice/shipment identity.
2. The preflight produces only `REVIEW` / `MISSING` / `HOLD` / `READY TO REQUEST PRIVATE HUMAN REVIEW`. It does not claim a verified overcharge, guarantee recovery, compute fee-eligible cash, contact a carrier, or authorize action.
3. Client JavaScript does not fetch, send, store, submit, track or ingest any freight or customer records. It supports explicit copy and manual-copy fallback; no automatically sent inquiry or charge.
4. Test all 4^6=4,096 source-state permutations, unsupported inputs, and publication allowlist. Run Freight contracts + full protected GitHub release-gate, RecoveryOS Public Sites acceptance, and no-secret Cloudflare build.
5. Only merge via the existing protected `main` PR process after green exact-head CI; independently verify published Cloudflare source revision and successful live read-only HTTP checks. Do not rely on green CI as proof of commercial success.
6. Preserve old signed v15.14 provenance and R1-R4 October 19 research records as immutable historical evidence.

## Separate customer-production HOLD (not automatically waived by software version)

- No verified population of real positive AND real negative overcharges with applicable buyer-signed tariff and shipment-specific facts.
- No independently verified original customer bank-cleared paid/recovered funds, adjudicated carrier action, or measured earned fee.
- No approval to move confidential customer records into the public website or unverified parser runtime.
- Commercial rights, private-data-custody, live tenant access, independent backup/restore and buyer-specific scope remain individual gates.
- Actual customer audit/claim initiation, sending, money movement and billing require explicit authority, not a version number.

**Release interpretation:** 16.0.0 may be a shipped **public research-preflight feature** once its actual CI, protected merge and exact-host deployment pass. The broader private, automated commercial recovery engine remains `CUSTOMER_PRODUCTION_HOLD` until the above proof exists.
