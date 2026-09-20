# Reusable Components

Cross-lane index maintained by Hunt 15 MASTER Integrator.

Use this file for reusable infrastructure and product building blocks: auth, multi-tenancy, RBAC, audit trails, billing, notifications, job queues, workflow engines, connectors, parsers, ETL, document generation, admin consoles, reporting, import/export, deployment tooling, SDKs, and similar components.

For each entry record:
- Repository
- Canonical URL
- Exact revision / date inspected
- Component capability
- Evidence inspected
- Actual published license / rights metadata
- User-asserted separate commercial authorization posture
- Integration targets
- Build-time compression
- Value score
- Combination opportunities
- Next action

## Elite reusable components — 2026-09-19

### OmarFaig/Assay — calibrated accept/review gate for extracted facts
- Repository: https://github.com/OmarFaig/Assay
- Exact revision: `821303935ef2855908a9a9bd1efd4c33f9cd39d2`.
- Capability: selective-prediction document extraction with field-level constrained-decoding evidence, legal-alternative awareness, arithmetic penalties, calibration, review routing and evaluation.
- Evidence inspected: source/evaluation architecture and calibration/review behavior as recorded in MASTER.
- Published rights: MIT; model weights, datasets and inference runtimes remain separate.
- Standing permission posture: repository-owned code/content commercially authorized under the user's assertion; third-party models/data remain separately governed.
- Integration targets: Freight Recovery, ScopeSignal, CaptureBrief and other money/evidence products where an uncertain extraction must not silently become an assertion.
- Build-time compression: supplies the difficult false-accept/calibration layer instead of another generic OCR/parser.
- Value score: **29/30** — A5 B4 C5 D5 E5 F5.
- Combination: source extraction -> Assay accept/review -> deterministic authority/rule engine -> proof gate.
- Next action: maintain buyer-specific calibration at a fixed false-accept ceiling; unresolved fields remain review/$0 where money-bearing.

### srthck/trustmesh — proof-obligation and next-evidence engine
- Repository: https://github.com/srthck/trustmesh
- Exact revision: `5a93d70b37aafecaf61a5bc0296eaf831e5504ac`.
- Capability: deterministic authority/admissibility/independence/temporal/deadline/contradiction gates, replayable decisions and counterfactual next-best-evidence selection.
- Evidence inspected: source/rule behavior and deterministic proof semantics recorded in MASTER.
- Published rights: MIT; domain policy/scheme content and third-party data remain separate. User also asserted a separate commercial license for this repository.
- Standing permission posture: repository-owned material commercially authorized; no extension to external policy/data.
- Integration targets: Freight Recovery, claims/recovery readiness, ScopeSignal entitlement evidence, compliance/remediation evidence.
- Build-time compression: replaces ad-hoc workflow gates with explicit proof sufficiency and evidence-acquisition semantics.
- Value score: **29/30** — A4 B5 C5 D5 E5 F5.
- Combination: deterministic calculation/claim -> Trustmesh proof obligations -> next-evidence queue -> reviewer/settlement outcome.
- Next action: keep domain policy provenance separate and benchmark whether suggested next evidence actually changes blocked decisions.

### mgilbir/formalis — structured invoice validation gateway
- Repository: https://github.com/mgilbir/formalis
- Exact revision: `2b3895a0c2c54e4f25ccb46e131d215ad4457eb2`.
- Capability: multi-jurisdiction e-invoice validation across EN16931, XRechnung, Factur-X/ZUGFeRD, Peppol/PINT and national CIUS with syntax detection, neutral CII/UBL paths, authority-parity/omission tests and explicit `NotEvaluated`/fatal states.
- Evidence inspected: format/rule coverage and fail-closed semantics recorded in MASTER.
- Published rights: MIT for code; official schemas, Schematrons, code lists and test corpora retain separate rights/provenance.
- Standing permission posture: repository-owned code commercially authorized; standards-derived assets remain separately governed.
- Integration targets: AP audit/recovery, marketplace money assurance, freight structured invoices and regulated invoice gateways.
- Build-time compression: avoids building multiple jurisdiction-specific validation stacks and preserves native structured truth before OCR.
- Value score: **29/30** — A4 B5 C5 D5 E5 F5.
- Combination: structured invoice -> Formalis validation -> contract/rate/entitlement engine -> settlement reconciliation.
- Next action: pin exact rule-pack versions and provenance for each commercial jurisdiction before making compliance claims.

### joschiservice/RosterSpec — schedule verification and minimum-disruption repair kernel
- Repository: https://github.com/joschiservice/RosterSpec
- Exact revision: `f7e701c694bf1facdc4999e1681a3aa11493614d`.
- Capability: deterministic CP-SAT workforce schedule verification/explanation/repair with stable rule codes, hard locks and minimum-disruption replanning backed by goldens/oracles/load tests.
- Evidence inspected: solver/rule/repair/test behavior recorded in MASTER.
- Published rights: Apache-2.0.
- Standing permission posture: repository-owned code commercially authorized under the user's assertion.
- Integration targets: contact-center WFM assurance, field-service proof-to-cash capacity repair and fulfillment workforce acceptance.
- Build-time compression: supplies difficult constraint verification and conservative repair rather than another from-scratch scheduler.
- Value score: **29/30** — A4 B5 C5 D5 E5 F5.
- Combination: demand/coverage evidence -> RosterSpec verify/repair -> human approval -> post-change service/QA measurement.
- Next action: benchmark minimum-disruption repair against incumbent WFM outputs on a closed published-roster period.

### open-eid/SiVa — signature/timestamp trust verifier
- Repository: https://github.com/open-eid/SiVa
- Exact revision: `0c9c5f2490b1a27798b47906bbaa6adb4d26daad`.
- Capability: validation of XAdES/CAdES/PAdES/ASiC/timestamp evidence with chain trust, timestamp imprint, OCSP/CRL status and revocation freshness.
- Evidence inspected: trust/revocation/timestamp validation semantics recorded in MASTER.
- Published rights: EUPL v1.1; DigiDoc4J/DSS, EU trusted lists, certificates and trust-service infrastructure remain separate.
- Standing permission posture: repository-owned code commercially authorized; external trust infrastructure/PKI material remains separately governed.
- Integration targets: Recovery Proof, signed audit evidence, compliance evidence and recovery certificates requiring stronger historical-time/trust validation.
- Build-time compression: materially closes the gap between parsing an RFC 3161 token and evaluating production trust/revocation validity.
- Value score: **25/30** — A3 B4 C5 D4 E5 F4; retained because it is uniquely important to stronger evidence stacks.
- Combination: real restore/application proof -> manifest/hash -> signature/timestamp -> SiVa trust/revocation verification -> buyer/auditor evidence package.
- Next action: define and test a production trust policy, including certificate-chain, OCSP/CRL freshness, retention and external TSA acceptance.

### Benchling-Open-Source/allotropy — analytical-instrument normalization layer
- Repository: https://github.com/Benchling-Open-Source/allotropy
- Exact revision: `ecc574986b74f91eb84cd0ee14756cd8dc5e1b7e`.
- Capability: broad vendor instrument-output parser estate normalizing chromatography/CDS, liquid-handler, plate-reader, cell-analysis, qPCR/dPCR, spectroscopy and related outputs into Allotrope Simple Model structures with dedicated readers/tests.
- Evidence inspected: reader/parser estate and active test/maintenance footprint recorded in MASTER.
- Published rights: MIT for code; Allotrope specifications, vendor formats/fixtures and customer data remain separately governed.
- Standing permission posture: repository-owned code commercially authorized; specifications/vendor/customer assets remain separate.
- Integration targets: Lab Automation v4, governed experiment campaigns, provenance and cross-instrument analytics.
- Build-time compression: removes a large share of heterogeneous vendor export normalization work before orchestration/analysis.
- Value score: **29/30** — A5 B5 C5 D4 E5 F5.
- Combination: instrument export -> Allotropy normalization -> PyTestLab/Galago/PyLabRobot execution/replay -> Flowcept provenance -> HELIOS governed campaign decisions.
- Next action: select one buyer-specific installed-base format mix and prove normalization fidelity against vendor-authorized sample exports.

<!-- INTEGRATOR-R12-2026-09-19T2231-0400 -->
### cmdrvl/canon — reviewed versioned identity compiler
- Repository: https://github.com/cmdrvl/canon
- Exact revision: `45e9702ba7f3874c073134c1a6fb74500232b6a1`.
- Capability: messy identity evidence -> scored/reviewed decisions -> promoted versioned registry -> exact deterministic runtime replay. Runtime is pinned to a registry version, provider materialization/calibration is separated from registry mutation, and unresolved/refusal/partial states plus rule/confidence provenance remain explicit.
- Evidence inspected: identity architecture/evaluation docs, registry/promotion/replay contracts, structural-linkage artifacts, benchmark/test/CI surface recorded in hunter 18.
- Published rights: MIT for repository-owned code; provider/reference datasets and customer identities remain separately governed.
- Standing permission posture: repository-owned code/content commercially authorized; no extension to external registries/data.
- Integration targets: CaptureBrief entity/parent identity, freight carrier/vendor mastering, AP/vendor mastering, CRM/MDM reconciliation.
- Build-time compression: approximately 4–8+ months of registry/versioning, review/promotion, evidence artifacts, calibration workflow and exact replay control-plane work.
- Value score: **29/30** — A4 B5 C5 D5 E5 F5.
- Combination: probabilistic candidate generation -> Canon review/promotion -> pinned production registry -> downstream exact identity joins.
- Next action: synthetic vendor/company corpus through candidate generation -> review -> promotion -> replay; runtime output must change only after a new reviewed version is promoted.

### ChelseaKR/constituent-reconciler — consent-aware review and audited writeback
- Repository: https://github.com/ChelseaKR/constituent-reconciler
- Exact revision: `dbc09d25baec026027e65a0f8d21930509e2dd8e`.
- Capability: offline-first CSV/PDF/image/text/email intake, source-spanned extraction, deterministic normalization, probabilistic matching, human review, controlled CRM writeback and append-only provenance; policy packs can restrict cloud egress, write targets and merged consent.
- Evidence inspected: README/tree, connectors, tests, benchmark/claims-audit/security/data-flow tooling and negative-control work recorded in hunter 18.
- Published rights: Apache-2.0 for repository-owned code; CRM APIs, timestamp services, benchmark/source datasets and real identities remain separate.
- Standing permission posture: repository-owned code/content commercially authorized; customer identity/consent data remains separately authorized and protected.
- Integration targets: Canon-reviewed registry workflows, nonprofit/CRM reconciliation, regulated customer/vendor mastering and safe correction/writeback.
- Build-time compression: roughly 3–6+ months of multi-format intake, evidence, review, target writeback, policy and audit plumbing.
- Value score: **29/30** — A5 B4 C5 D5 E5 F5.
- Combination: candidate engine/Canon registry -> policy-aware review -> controlled writeback -> append-only receipt -> correction/split replay.
- Next action: benchmark consent conflict, ambiguous match, partial extraction, rollback and write-target semantics on fully synthetic multi-CRM data.

### oscal-compass/compliance-to-policy-go — policy-as-code to OSCAL assessment bridge
- Repository: https://github.com/oscal-compass/compliance-to-policy-go
- Exact revision: `45bfc1a8947e8b56b7e11391e13f8c1f2136cfaa`.
- Capability: maps heterogeneous policy-engine results through plugin contracts into OSCAL observations/findings while preserving resource identity, evidence, waived subjects and explicit non-pass states.
- Evidence inspected: v2 plugin architecture and `framework/actions/report.go` Assessment Results construction recorded in hunter 14.
- Published rights: Apache-2.0; OSCAL/NIST materials, Kyverno/OCM and proprietary policy engines/services remain separately governed.
- Standing permission posture: repository-owned code/content commercially authorized.
- Integration targets: Continuous Compliance Evidence Ops, Recovery Proof evidence packaging and governed remediation/re-proof.
- Build-time compression: approximately 3–6 months of OSCAL assessment semantics, plugin contracts, control mapping and result aggregation.
- Value score: **27/30** — A4 B4 C5 D4 E5 F5.
- Combination: production collectors -> policy engine -> C2P OSCAL findings -> epack/OpenWright -> CAGE remediation -> fresh re-test.
- Next action: synthetic three-control pass/fail/error/waive/missing-result fixture plus one authorized sandbox policy engine; incomplete collection may never become a pass.

### duke5am/pg-restore-drill — PITR negative-control acceptance fixture
- Repository: https://github.com/duke5am/pg-restore-drill
- Exact revision: `e914caddd14ab1604d85ccb7919d4da071a6766c`.
- Capability: PostgreSQL base-backup/WAL PITR drill with known pre/post-target data, exact-state checksums, measured RPO/RTO and a deliberate negative-control mode that only succeeds when the verifier detects the wrong recovery target.
- Evidence inspected: repository tree/README, substantial restore/report scripts and negative-control/archive-gap semantics recorded in hunter 15.
- Published rights: MIT; PostgreSQL/storage/runtime providers remain separate.
- Standing permission posture: repository-owned code commercially authorized.
- Integration targets: Recovery Proof test-the-test methodology; challenger to pg_hardstorage/BackupDrill rather than a parallel generic product.
- Build-time compression: roughly 2–4 months of PITR choreography, exact-state verification and negative-control design.
- Value score: **28/30** — A5 B4 C5 D4 E5 F5.
- Combination: Postgres restore engine -> positive fixture + mandatory negative control -> signed proof SLA -> trust validation.
- Next action: compare identical WAL-gap/wrong-target/checksum-corruption fixtures against the current PostgreSQL engines and retain the strongest execution path plus the negative-control methodology.

<!-- INTEGRATOR-R11-2026-09-20T0025-0400 -->
## Additional reusable components — 2026-09-20

### sandyliu3056/UPS-reconciliation — parcel correction/rebill specialist oracle
- Revision: `d1e11940b262debc3c3216aba6467f39722c3000`.
- Score: **28/30**.
- Capability: reconstructs UPS-style original/corrected billing chronology and contractual reprice logic including corrected weight/zone/returns/multipiece/LPS cases; useful for proving incremental base-charge shortages after corrections.
- Integration: Freight Recovery v14 specialist comparator, not a second TMS/rating plane. Same-family `ups-reprice-web` is deduped as supporting evidence.
- Rights: actual public provenance recorded in hunter 36; user's separate permission applies to repository-owned code. Carrier tariff/contracts/customer data remain separate.
- Next action: independently author correction/rebill fixtures and compare oracle output against the main freight calculation plane.

### clay-good/vaulytica — construction contract/flow-down rule component
- Revision: `ffb88ed27354f8a3b17269d327ec29bd1d1fae98`.
- Score: **28/30**.
- Capability: deterministic construction contract-analysis/playbook rules around prime/subcontract scope, incorporation/flow-down, payment/retainage, change orders, lien waivers, bonds, insurance/indemnity and related evidence.
- Integration: ScopeSignal v5 authority extraction/review before commercial-state calculations.
- Rights: MIT repository code; source legal forms/standards/current law remain independently governed and require authoritative current-source review.
- Next action: held-out contract set with exact source spans and deliberate conflicting/absent clauses; unresolved authority stays unresolved.

### abdu2030/Resolve_api — deterministic resolver challenger for identity mastering
- Revision: `de593e6...` (full exact SHA preserved in hunter 18).
- Score: **28/30**.
- Capability: evidence-oriented record/identity resolution that complements Canon's reviewed/versioned registry boundary.
- Integration: candidate generation/normalization -> Resolve/other challenger -> Canon human review/promotion -> pinned production registry.
- Next action: synthetic vendor/customer corpus with ambiguous aliases, mergers/splits and negative matches; compare false-merge/false-split frontier.

### attestwire/en16931 — independent structured-invoice rule oracle
- Revision: `09d08...` (full exact SHA preserved in hunter 16).
- Score: **29/30**.
- Capability: strong independent EN16931 structured-invoice validation source/oracle.
- Integration: use as a peer challenge to Formalis rather than replacing it; disagreements in money/compliance fields route to rule-pack/source review.
- Rights: repository-owned material under public/standing permission; official schemas/Schematrons/code lists remain separately governed.
- Next action: parity corpus across identical UBL/CII fixtures and exact rule-pack versions.

### adamleap02/PermitBuild — canonical permit/version/source-QA plane
- Revision: `ff795137e0c66e62a87e62956fa351926886255d`.
- Score: **29/30**.
- Capability: Socrata/ArcGIS/CKAN/Accela-style connectors, canonical permit/property schema, idempotent upserts, immutable versions + field-level diffs and demonstrated semantic source-field QA such as fee-vs-valuation and professional-role/date mapping corrections.
- Integration: PermitPlate source-of-event/version layer before parcel/buildability/economic enrichment.
- Safety: reported `.playwright-signup-evidence/` browser-profile-like artifacts were not opened or used; see EXPOSURES_INDEX.
- Next action: three-jurisdiction held-out completeness/semantic-mapping benchmark.

### davidlarrimore/curatore-v2 — acquisition-forecast version/history plane
- Exact revision: recorded in hunter 42 (`d4e42ac...`).
- Score: **29/30**.
- Capability: multi-source planned-buy/acquisition-forecast normalization with rich fields, SHA-256 content/history, first-seen/last-updated/field diffs and source-run success/failed/partial states.
- Integration: CaptureBrief pre-solicitation signal; forecast must later be linked to actual SAM notice/award evidence rather than treated as procurement fact.
- Next action: frozen forecast→SAM outcome benchmark and source coverage/failure accounting.

### Gaskony-Ignition/module-plc-emulator — L5K-derived virtual PLC
- Revision: `518f56b55566d7e20f19ce64003cdae45a08edc8`.
- Score: **29/30**.
- Capability: imports customer-authorized Rockwell L5K exports and creates an OPC-UA simulated controller with real tag hierarchy/types/UDT/AOI/arrays/module I/O and configurable behaviors; intended NodeIds can challenge HMI/SCADA bindings before hardware FAT.
- Rights: Apache-2.0 repository code; Rockwell/Allen-Bradley/Studio 5000/Ignition trademarks, proprietary formats/specifications and third-party test assets remain separate.
- Next action: synthetic L5K→OPC-UA→Ignition browse/read/write/type-drift regression.

### BroadbandForum USP acceptance/model family
- `BroadbandForum/usp-test@5d53f5280b2a90ea0040887e62828c7b7369a240` — **29/30**, standards-body TP-469-style acceptance procedures/pass metrics for message/path/access-control/MTP and stateful firmware/certificate/event behavior.
- `BroadbandForum/usp-data-models@a6c869d4c6e80a3d940c4dc4fbeb9b5c859d233d` — **25/30**, structured model/version/object/parameter/command/event source.
- `BroadbandForum/cwmp-xml-tools@ea856e227734001695e61135f38071afd67be90d` — **23/30**, archived migration/mapping/conversion tooling.
- Integration: CWMP/USP model diff -> selected acceptance cases -> independent controller/agent matrix -> readiness evidence.
- Rights: repository permission does not imply BBF certification, trademark, patent/IPR or wholesale standards redistribution rights.
- Next action: automate 10–20 highest-value cases while keeping outputs framed as readiness unless official certification rights are verified.

### thermofisherlsms/meth-modifications — official vendor method schema/version component
- Exact revision: recorded in hunter 20 (`b30bbe1...`).
- Score: **28/30**.
- Capability: Thermo method XML/XSD/versioned modification surface useful for authoritative instrument-method interchange and regression.
- Integration: Lab Automation v5 vendor-control plane beside SLIMS and normalized outputs.
- Rights: MIT repository code; Thermo runtime/services/trademarks/vendor ecosystem remain separately governed.
- Next action: dummy/authorized method round-trip with version mismatch and unsupported-field negative cases.

<!-- INTEGRATOR-R11-LATE2-2026-09-20T0042-0400 -->
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
- Capability: full .NET OPC UA client/server/PubSub/GDS/complex-type implementation with a 1.x→2.0 migration analyzer (26 rules/fixes) and current regression knowledge around transferred-subscription notification recovery, republish, sequence wrap and reconnect/session behavior.
- Integration: Industrial Virtual Commissioning / Pre-FAT migration lane; falsify upgraded apps against independent S2OPC/open62541/node-opcua endpoints.
- Next action: fixed migration corpus including subscription transfer/republish, session reactivation, secure-channel renewal, certificate/auth changes and PubSub.

### malon64/floe — trusted ingress/quarantine contract engine
- Revision: `9a0bbf1f2f4647f5b9304a2ebcff3e79182a1beb`.
- Score: **28/30**.
- Rights: MIT; external storage/services and customer/source data remain separate.
- Capability: Rust/Polars multi-format trusted-layer ingestion with declarative header/schema/row/type/null/PK checks, accepted/rejected quarantine, manifests/JSON reports, PII masking and OpenLineage identities/replay.
- Integration: place after extraction and before freight/AP/CaptureBrief/ScopeSignal money or evidence decisions so schema/key defects cannot silently enter the authoritative pipeline.
- Next action: adversarial multi-format benchmark with broken headers/types/nulls/duplicate keys and replayed cloud identities.
