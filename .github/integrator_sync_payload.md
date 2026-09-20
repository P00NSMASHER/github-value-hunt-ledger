MARKER: <!-- INTEGRATOR-R11-LATE-2026-09-20T0037-0400 -->

=== SUBSTITUTE MASTER.md ===
- Commit: `8d46d765...` (exact inspected revision recorded in hunter 15; preserve the full SHA from that catalog when referenced in downstream artifacts).
--- NEW ---
- Commit: `8d46d7651e0d948397b37ce73ea63a7898ee4935`.

=== APPEND MASTER.md ===
## Late-run promotion — generalized accounting truth

### Superheld/summae — deterministic accounting/close oracle
- Commit: `9c5292af99bab9716723b82fd221a56f91ab4581`.
- Rights: MIT for repository-owned code plus the user's standing separate commercial permission. Jurisdiction packs, statutory/tax authority and external accounting/regulatory data remain independently governed and must be current before jurisdiction-specific conclusions.
- Score: **29/30 — A5 B5 C5 D5 E5 F4**.
- Capability: embeddable append-only double-entry accounting engine with deterministic posting policies, invoicing/AP/AR, trial balance, balance sheet/P&L/cash flow, FX, hard period close, inventory costing, fixed assets, bank reconciliation, close checklist and versioned jurisdiction-policy packs. Parallel PHP/Node implementations target a shared language-neutral conformance suite with canonical JSON, decimal money, injected clock/IDs and journal-derived reporting.
- Buyer/problem: controllers, finance-engineering teams, audit/recovery firms and vertical SaaS vendors need an independent way to prove operational money events reconcile into a correct GL and closed period instead of trusting stored balances or one application.
- Monetization / first paid wedge: **Monthly Close / Ledger Integrity Diagnostic** — ingest an authorized frozen GL/subledger period, independently recompute balances and close controls, flag unexplained posting differences/period-lock/FX/inventory/asset anomalies and return a traceable exception pack.
- Why it beats alternatives: the rare asset is a jurisdiction-neutral deterministic accounting truth layer plus cross-language conformance, making it useful across AP, billing, commission, utility, telecom and other recovery products rather than one vertical only.
- Integrity boundary: repository permission does not make bundled/current jurisdiction policy authoritative. Hard-dollar findings require source transaction authority and later accounting/payment disposition.

### Late-run restraint
- `recurso-dev/recurso@b071318ff9b349e83daa92e6a5e0c5873664421e` also scored **29/30** and is indexed as the operational billing-event/immutable-ledger component beneath Summae rather than promoted as a second overlapping MASTER accounting leader.
- `OPCFoundation/UA-.NETStandard@37b552254e8da434514c87d8185c1595c03c4063` scored **29/30** and is indexed as the strongest current .NET OPC UA migration/conformance component, but remains outside MASTER until the proposed cross-stack migration regression proves buyer-facing defect catch/value.
- `malon64/floe@9a0bbf1f2f4647f5b9304a2ebcff3e79182a1beb` scored **28/30** and is retained as shared trusted-ingress infrastructure rather than a standalone portfolio leader.

=== APPEND COMBINATIONS.md ===
## Late-run cross-vertical combination — Money-State Integrity v1
- Components: operational billing/usage/invoice/payment events from `recurso-dev/recurso@b071318ff9b349e83daa92e6a5e0c5873664421e` -> independent deterministic accounting/close recomputation in `Superheld/summae@9c5292af99bab9716723b82fd221a56f91ab4581` -> structured-invoice/identity evidence where relevant -> provider/bank/payment/GL settlement evidence. OpenPartner, AP Leakage, telecom, utility and other vertical engines can feed this generic accounting boundary rather than inventing their own ledger truth.
- Buyer/problem: finance teams often know an operational system billed or paid something but cannot cheaply prove that the event became the correct, balanced, non-duplicated journal/period-close state.
- First paid wedge: one authorized frozen month, replay `usage/order/receipt/refund/payment -> invoice/credit -> journal -> close`, deliberately inject duplicate/missing/unbalanced/locked-period failures and compare the independent result to the customer GL/subledger.
- Commercial shape: fixed-price Close & Ledger Integrity Diagnostic -> recurring month-end assurance -> vertical recovery engagements on validated exceptions.
- Hard invariant: operational event presence, invoice issuance, journal posting, period close and cash settlement are distinct facts. Demo tax/nexus/rate content is never treated as statutory authority without a current controlling source.

## Late-run industrial refinement — OPC UA .NET migration acceptance
- `OPCFoundation/UA-.NETStandard@37b552254e8da434514c87d8185c1595c03c4063` supplies an official current .NET migration analyzer plus hard-earned stateful subscription-transfer/republish/reconnect behavior.
- Combine mechanical 1.5.378→2.0 migration with independent S2OPC/open62541/node-opcua endpoints and the existing Pre-FAT evidence harness. The paid deliverable is a customer-source migration diff plus secure-channel/session/subscription/PubSub regression report, not a claim of OPC Foundation certification.
- Promotion gate: one frozen sample app with planted API/session/subscription/certificate failures, measured manual-fix time and defects caught before rollout.

=== APPEND COMPONENTS.md ===
## Late-run reusable components — financial integrity and migration

### recurso-dev/recurso — immutable billing-event/ledger boundary
- Revision: `b071318ff9b349e83daa92e6a5e0c5873664421e`.
- Score: **29/30**.
- Rights: Apache-2.0 repository code; tax/nexus data, payment processors and legal authority are separate.
- Capability: subscriptions, usage/meter/tiered pricing, invoicing, credits, payments/dunning/tax plus immutable double-entry journal; inspected invariant tests cover balanced journals, tenant/project isolation, idempotent posting and duplicate prevention.
- Integration: operational billing source under Summae's independent GL/close oracle; useful across telecom/utility/SaaS/revenue-assurance products.
- Next action: synthetic usage→invoice→payment→journal benchmark with duplicate/missing/unbalanced failures and a provider-neutral export schema.

### OPCFoundation/UA-.NETStandard — official .NET OPC UA migration/regression substrate
- Revision: `37b552254e8da434514c87d8185c1595c03c4063`.
- Score: **29/30**.
- Rights: OPC Foundation MIT License 1.00 for repository code. OPC specifications, CTT/certification tooling/marks, separately licensed NodeSets/companion assets and customer code remain separate.
- Capability: full .NET OPC UA client/server/PubSub/GDS/complex-type implementation with explicit 1.x→2.0 migration analyzer (26 rules/fixes) and current regression knowledge around transferred-subscription notification recovery, republish, sequence wrap, reconnect/session behavior.
- Integration: Industrial Virtual Commissioning / Pre-FAT migration lane; falsify upgraded apps against independent S2OPC/open62541/node-opcua endpoints.
- Next action: fixed migration corpus including subscription transfer/republish, session reactivation, secure-channel renewal, certificate/auth changes and PubSub.

### malon64/floe — trusted ingress/quarantine contract engine
- Revision: `9a0bbf1f2f4647f5b9304a2ebcff3e79182a1beb`.
- Score: **28/30**.
- Rights: MIT; external storage/services and customer/source data remain separate.
- Capability: Rust/Polars multi-format trusted-layer ingestion with declarative header/schema/row/type/null/PK checks, accepted/rejected quarantine, manifests/JSON reports, PII masking and OpenLineage identities/replay.
- Integration: place after extraction and before freight/AP/CaptureBrief/ScopeSignal money or evidence decisions so schema/key defects cannot silently enter the authoritative pipeline.
- Next action: adversarial multi-format benchmark with broken headers/types/nulls/duplicate keys and replayed cloud identities.

=== APPEND OPPORTUNITIES.md ===
## Late-run challenger — Money-State Integrity / Close Assurance
- Core: Recurso operational billing-event ledger + Summae independent deterministic accounting/close oracle.
- Buyer: controllers, subscription/usage-billing finance engineering, audit/recovery firms and vertical SaaS operators.
- First paid wedge: one-month read-only close diagnostic; replay authorized usage/order/invoice/credit/payment/journal state and identify source-linked missing, duplicated, unbalanced or period-lock violations.
- Revenue path: fixed diagnostic -> recurring month-end assurance -> vertical recovery/controls work on validated exceptions.
- Why it matters: this can become the accounting truth boundary underneath AP, commission, telecom, utility and marketplace assurance instead of building a separate ledger interpretation in every vertical.
- Promotion discipline: Recurso remains COMPONENTS; Summae is the single promoted generalized accounting leader. Tax/jurisdiction packs require independent current-authority validation.

=== APPEND SEARCH_QUEUE.md ===
## Late-run refinements from concurrent hunter commits
- **Finance/accounting:** do not hunt more generic ledgers. Differential-test Recurso operational-event posting against Summae close truth on the same synthetic month, then route any novel tax/accounting authority gaps into the sparse tax/accounting catalog. Search only for missing bank/provider settlement evidence, authoritative current policy packs or hard failure cases the pair cannot represent.
- **Industrial migration:** `UA-.NETStandard` closes much of the generic .NET OPC UA migration-tool gap. Hunters should now seek customer-like migration fixtures, independent endpoint incompatibilities, NodeSet/companion-model drift and secure session/subscription failure evidence — not another OPC UA client/server implementation.
- **Trusted data ingress:** Floe is the current contract/quarantine reference. Search further only when a source format or replay/lineage failure materially blocks a top money/evidence stack; generic ETL/data-contract tools are deprioritized.
