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