MARKER: <!-- INTEGRATOR-R11-POSTCHECKPOINT-2026-09-20T0056-0400 -->

=== APPEND COMBINATIONS.md ===
## Integrator overlay — post-checkpoint hunter deltas (2026-09-20)

### Freight Recovery v14.1 — anti-circular acceptance + public tariff acquisition
- Add `WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c` as an **independently authored golden-oracle methodology** beneath the existing blind acceptance protocol. Its strongest contribution is not another rerater: hand-derived literal truth is kept separate from the production pricing path, so action-bucket correctness and exact-dollar correctness can be measured without circular fixture generation.
- Add `Akash-kolladikkel/Emirates-Line-Tariff-Scraper-AI@5a2a48ea0f4b3d985076082ab4a43f7c9d214644` only as an authority-acquisition blueprint for carrier-published detention/demurrage schedules. Preserve source URL, retrieval timestamp, raw-artifact hash, carrier/port/equipment/direction, effective/expiry dates and reviewed source locations before normalization. Carrier files/site terms remain separately governed.
- Add `edrisibra/counterpart@edf3d930ea4b35b7e4623b1123af1399310382d7` as the pre-booking quote-usability negative corpus: fuel, accessorial completeness, class/weight, equipment/lane, transit basis and quote-validity defects must be rejected before a tender can become the immutable booked-rate snapshot.
- Hard invariant: WRBriska's inspected unknown-accessorial behavior is **not** adopted. Missing or incomplete contractual basis remains REVIEW / `$0 asserted recovery`; a published carrier schedule is comparator evidence unless the customer's controlling contract incorporates it.
- Validation: freeze one synthetic corpus where truth literals are hand-derived outside the runtime; score clean/finding/review action, exact cents and false-recovery dollars separately. Then test one rights-clean carrier tariff acquisition path through raw artifact hash -> reviewed facts -> authority applicability -> rerating. The commercial P0 remains a real customer blind population through actual settlement.

### Risk-Priced Infrastructure Inspection — conditional new cluster
- Components: `JestradaG/StochasticInspectionRouting@2e7ab15b429b5138bd9ec5bb6494278c0b5da279` for endogenous-failure-aware stochastic route/inspection selection + `ErToBar2/ORBIT@25903ddbdca245131ce37ca7fd057eff64faa4d7` for bridge/UAS mission planning where a selected asset requires GNSS-degraded or under-deck inspection + existing condition/anomaly evidence and TrustMesh-style proof obligations.
- Buyer/problem: utilities, DOT/bridge owners, industrial asset fleets and inspection contractors must decide **which assets to inspect first and how to execute the inspection**, while travel/crew cost competes with failure risk and field feasibility.
- First paid wedge: read-only/shadow **Inspection Policy Benchmark** on one network or bridge portfolio. Compare the customer's current policy against highest-risk-first, nearest-route and the stochastic policy; no field action changes until the benchmark wins on expected failure + deployment cost without increasing missed-critical-asset risk.
- Evidence boundary: the pinned Jestrada snapshot contains real decomposition/column-generation code but also hard-coded research stopping/debug limits and no surfaced conventional test suite. ORBIT's field-use claims and bridge/geospatial assets require independent repeatability/rights validation. This cluster is therefore **validation-stage, not MASTER**.
- Promotion gate: independently reproduce a small Jestrada benchmark with an open solver and show material advantage over simple baselines; only then run ORBIT on a synthetic/public bridge model and measure mission-planning time, coverage, reflight burden and operator acceptance.

### Recovery Proof v9.1 — semantic bad-backup rejection + host/credential independence
- Add `vncwr/backwyn@57f4b8afc3d9ce14f2a35febc802536cfa816839` as the hosted-Postgres negative-control challenger: real scratch restore, corrupted-artifact rejection, failing verification-query rejection, stale/no-fresh-proof alerting, unverified-restore guards and RLS partial-backup checks.
- Add `heyvaldemar/restore-drill@16082f0ab26ee3986b24fbfef97d229faf6a05b0` as a compact falsification corpus for truncated archives, empty-but-valid dumps and `last-run` versus `last-ok` state semantics; absorb those cases rather than maintaining another platform.
- Add `danieltamas/fortified@c677ef30f750e1cc0b761dd9eed3bab2b40d18f4` for a distinct total-host-loss/escrowed-recovery-identity drill. It proves a different-machine/credential-boundary failure mode but must be paired with application/data truth before a full-recovery claim.
- Keep `OmarRao/r3vp@404f7f7aaed5b9fbc39506622175d87e628b3054` as the Veeam/vCenter MSP orchestration shell only after an authorized lab removes the recovered-object placeholder fallback and wires a real application/data invariant. `databasus/databasus@6b3f3df008851b91299e100a474681cfe50b0179` remains broad backup operations/UI/storage plumbing, not verifier authority.
- New acceptance rule: positive restore proof is insufficient. A verifier must also reject at least one **wrong-but-restorable** state whose row/table counts look plausible but a known-value/content hash or business invariant is wrong.

### Continuous Compliance Evidence Service v3 — narrow M365 wedge + portable offline bundle gate
- Add `amyanger/comply-core@2d7334cedea7c79cc0a7e9eea8364f9d1083f736` as the immediate Microsoft 365 / ISO 27001 evidence-service wedge: Graph collection, explicit `MANUAL_REQUIRED` states, evidence/gap reporting and stored evidence hash-chain verification.
- Add `DNYoussef/guardspine-spec@4b21006daa82af52647c5b6e4288d995ccbaf401` as a portable offline evidence-bundle interoperability/falsification contract, especially its malformed-vector rejection and sanitization attestation. Compare directly with epack/OpenWright rather than creating a second incompatible evidence format.
- `compliance-framework/agent@bd0ed53bbba77ff24ebb0e5523cc7be866b6de68` remains a candidate customer-side plugin/policy runtime only if collector crash, timeout and OPA/policy errors are provably non-pass.
- Buyer / first paid wedge: Microsoft 365-heavy SMB/SaaS/professional-services companies and MSPs; fixed-price **M365 ISO Evidence Refresh** followed by recurring evidence collection, manual-control queue and portable signed/offline-verifiable evidence packs.
- Validation: in an authorized sandbox inject revoked/expired Graph authorization, missing permissions, empty audit windows, modified stored evidence and malformed portable bundles. Missing/error/invalid evidence must never become a passing control.

=== APPEND COMPONENTS.md ===
## Post-checkpoint reusable components — acceptance, recovery and scheduling

### WRBriska/InvoiceAudit — independent freight golden-oracle pattern
- Revision: `bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c`.
- Score: **27/30**.
- Rights: no root public license was visible; under the standing user assertion, repository-owned code is treated as separately commercially authorized. External standards/customer data remain separate.
- Capability: production freight pricing/audit plus a deliberately separate golden evaluator using hand-derived literal expected dollars and action buckets, reducing circular self-test risk.
- Integration: blind Freight Audit Acceptance Test; report action accuracy, exact-dollar accuracy and false-recovery dollars separately.
- Caveat / next action: do not adopt its unknown-accessorial-as-zero behavior. Convert missing contractual basis to REVIEW/$0 and independently rederive the frozen benchmark truth.

### vncwr/backwyn — hosted-Postgres negative-control recovery verifier
- Revision: `57f4b8afc3d9ce14f2a35febc802536cfa816839`.
- Score: **27/30**.
- Rights: MIT; PostgreSQL/Supabase/Neon/object-storage services and customer data remain separately governed.
- Capability: least-privilege encrypted off-provider backup plus real scratch restore; test corpus rejects corruption, failing verification queries, stale proof, unverified restore and RLS partial-backup conditions.
- Integration: Recovery Proof adversarial matrix.
- Next action: add a wrong-but-restorable known-value/content-hash fixture; row parity/queryability alone cannot prove semantic correctness.

### DNYoussef/guardspine-spec — portable evidence interop/falsification contract
- Revision: `4b21006daa82af52647c5b6e4288d995ccbaf401`.
- Score: **24/30**.
- Rights: Apache-2.0 repository material; external standards/integrations/customer evidence remain separate.
- Capability: canonical JSON evidence bundle with item hashes, ordered chain/root, optional signatures, offline verification, malformed vectors and redaction/sanitization attestation.
- Integration: portability gate after recovery/compliance evidence producers and before auditor/customer delivery.
- Next action: differential-test one synthetic signed recovery proof against epack/OpenWright and mutate content/order/chain/root/signature/sanitization count one at a time.

### AbhishekLGowda05/SAGE — ordered-relaxation / feasible-first scheduling reference
- Revision: `49aee96f0a15e12e7b14b1c97989600f7ab0a146`.
- Score under standing commercial-permission posture: **28/30 — A4 B4 C5 D5 E5 F5**. Actual public metadata shows no root public license; that is provenance, not a value penalty under the user's separate-permission assertion.
- Capability: two-phase scheduling solver with pre-solve capacity analysis, deterministic input hash, hard-core versus relaxable/soft constraint classification, ordered automatic relaxation, warm-start optimization and explicit Phase-1 fallback when optimization fails; tests cover deterministic hashing, free periods, relaxation ordering and end-to-end feasibility.
- Integration: pair with RosterSpec's verification/minimum-disruption repair on a common workforce/field-service fixture.
- Promotion gate: prove that the relaxation contract transfers beyond school timetabling and that every relaxed rule is minimally sufficient, human-readable and approval-ready. The committed `frontend/.env` remains uninspected and safety-indexed separately.

=== APPEND OPPORTUNITIES.md ===
## Post-checkpoint validation-stage opportunities

### Risk-Priced Infrastructure Inspection
- Core: stochastic inspection selection/routing -> field/UAS mission plan -> inspection evidence -> defect/work-order outcome.
- Buyer: utility/bridge/DOT/industrial reliability owners and inspection contractors.
- First paid wedge: shadow one asset portfolio and compare existing policy with highest-risk-first, nearest-route and stochastic policy on expected failure + deployment cost before changing operations.
- Revenue path: fixed benchmark -> recurring inspection-priority refresh -> field mission planning/evidence service where authorized.
- Status: promising P1, below the direct-money freight/AP/commission priorities until open-solver reproduction and field-plan repeatability prove advantage.

### M365 ISO Evidence Refresh
- Core: ComplyCore Microsoft Graph evidence collection/evaluation -> manual-control queue -> GuardSpine/epack-style portable evidence package -> existing policy/remediation/re-proof stack.
- Buyer: Microsoft 365-heavy SMB/SaaS/professional-services firms, ISO consultants and MSPs.
- First paid wedge: fixed-price baseline evidence/gap refresh, followed by monthly recurring evidence collection and auditor export.
- Revenue path: setup + recurring managed evidence operations.
- Status: fast service-first challenger; promotion depends on authorized-sandbox failure injection proving missing permissions/expired auth/empty windows/integrity breaks remain non-pass.

=== APPEND REJECTED.md ===
## Post-checkpoint safety/provenance quarantine

### muhdwaseem/Logisticsrate — third-party contract-derived tariff material
- Revision: `6250dc36137f66d65e4d18314d36ca3b86b66913`.
- Disposition: **safety/provenance quarantine**, not a technical-license rejection.
- Safe evidence: repository contains functioning logistics rating code, but public commit history describes a signed real freight agreement being transcribed into tariff data.
- Boundary: the standing permission for repository-owned public code does **not** extend to a third party's confidential/commercial contract terms. The signed agreement, tariff-seed values and contract-derived commercial numbers were not opened, copied, tested or retained.
- Revisit trigger: only a sanitized revision/fork that cleanly separates generic code from contract-derived values and uses independently generated synthetic/publicly authorized tariff fixtures.

=== APPEND EXPOSURES_INDEX.md ===
### muhdwaseem/Logisticsrate
- Repository: `muhdwaseem/Logisticsrate`.
- Canonical URL: https://github.com/muhdwaseem/Logisticsrate
- File/path: signed-agreement / tariff-seed material referenced by public commit history; exact sensitive artifact contents and contract-derived values were deliberately not opened or retained.
- Exact revision: `6250dc36137f66d65e4d18314d36ca3b86b66913`.
- Date observed: 2026-09-20.
- High-level exposure type: potentially confidential third-party commercial contract/tariff material transcribed into a public repository.
- Apparent status: **not inspected or validated** beyond non-sensitive commit/tree metadata.
- Non-sensitive context: safe architecture evidence was insufficient to justify touching contract-derived material, and repository-code permission does not extend to third-party confidential terms.
- Remediation note: quarantine contract-derived assets; use only a sanitized code revision with independently generated synthetic/publicly authorized tariff fixtures. No commercial rate or contract value is stored here.
