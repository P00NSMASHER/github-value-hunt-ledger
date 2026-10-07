# Freight Recovery Customer Lifecycle Laboratory V2 — synthetic evidence handoff

**Status: offline fictional simulation only.** This file records reproducible local test artifacts packaged in this conversation; the multi-gigabyte 1M-case data is intentionally *not* committed into this public GitHub repository.

## Exact V2 offline test scope
- Baseline simulated source: 10,000 fictional profiles, 1,000,000 independently replayed lifecycle histories, 35,036,764 hash-linked events and 7,327,572 fictional communications.
- Read-only next-action policy: 1,000,000 decisions, zero internally defined policy violations.
- Staffing and customer service operations analysis: 1,000,000 histories, explicit minutes-per-event assumptions (NOT measured employee work).
- Isolated financial chaos: 100,000 permitted operations + 100,000 deliberately unsafe operations rejected. The mutations are *synthetic controls*, not 100k observed hacking attempts.
- Sealed grouped customer/source-account holdout: 125,057 fictional cases across TRAIN 85,034, DEVELOPMENT 15,919, TEST 24,104, with zero identity-overlap for profile IDs, freight source IDs or connected identity components. This is NOT real freight invoice truth.
- Sequential retention projection: 50,000 episodes across 10,000 profiles. The original selected independent episodes overlapped in 39,876 time windows; the new projection sequences them without overlap and requires renewed permission when fictional consent is revoked.
- Read-only SQLite index: 1,000,000 case summaries, integrity `ok`, exact synthetic ID search; local-only replay server. Separate 8-section operations dashboard alongside preserved original 12-section journey viewer.
- Local regression suite: **82/82 PASS** with full data/index installed; **81 PASS and 1 appropriately SKIPPED** in toolkit-only mode without 2+GB corpus.
- Full-corpus acceptance gate: **15/15 PASS_SYNTHETIC_LAB_ONLY** after extraction and bytewise SHA-256 of **800/800** original gzip files across 200 shards.
- Clean extracted ZIP installation verified independently: tests, local HTTP search/replay and Chromium dashboard interactions all passed.
- Archive delivery: one ~13.6MB runnable toolkit, an optional ~100MB read-only SQLite search index, and ten ~228MB parts containing the original 1M synthetic case histories. Exact hashes in companion download manifest.

## Critical unresolved integration gaps
- Baseline `FCUST-*` synthetic relationship IDs and `CUSTOMER-*` synthetic freight source-account IDs are distinct namespaces; **zero original independently attested source-owner binding receipts**. 974,500 cases show different numeric suffixes. Numerical matches are not proof of real ownership. The new Python domain guard requires an **explicit fictional test binding**; this must never be interpreted as legally valid customer consent.
- No verified real customer correspondence, CRM, contract signature, carrier recovery portal, production hosted Floot API end-to-end, payment rail, client credit reconciliation, independent freight accuracy, or real recovery payments.
- Simulated revenue, fee collection, staffing, satisfaction, marketing conversion and retention are modeling assumptions, **not business performance or market evidence**.
- Hash chaining is integrity/reproducibility within this synthetic corpus, not independent trusted timestamps, cryptographic signer authority or real SOC/security certification.

## GitHub product-domain scope in this draft PR
`freight/customer_lifecycle_product_probe.py` invokes the *actual* existing `freight.payment_orchestration` Python engine on fictional proof hashes and fake provider events. `freight/customer_scope_recovery_guard.py` adds fictional tenant-account scope verification, immutable checksum, effective dates and revocation checks. Twenty-five synthetic domain regression checks pass and are governed by an exact-SHA-pinned, read-only pull-request CI workflow. **Neither module is deployed**, merged or an actual bank/consumer-data integration.

## Release policy
Retain draft PR status until a human owner reviews. Never publish, merge, send customer emails, contact carriers, initiate funds transfers, import private data into public GitHub, or claim production success from this synthetic suite. The ten-part archive is delivered outside Git and should be revalidated using its provided full-source manifest and hashes.

See the downloadable toolkit documentation:
`docs/CUSTOMER_LAB_UPGRADE_V2.md`, `docs/CUSTOMER_FAILURE_TRIAGE_V2.md`, `docs/RELEASE_HANDOFF_V2.md`.
