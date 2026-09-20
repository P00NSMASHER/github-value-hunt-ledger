# REJECTED

Cross-lane rejection/deprioritization memory. This file intentionally keeps the repeat-prone, rights-sensitive, safety-sensitive and strategically misleading cases. Detailed lane-local rejected/watch entries remain in `hunters/01.md` through `hunters/47.md` and should be consulted before repeating a search.

## Rules
- Public visibility is not itself a reuse grant. **Standing user assertion (2026-09-19): the user states they hold separate commercial permission/license for every public GitHub repository in this hunt.** Therefore rights-only rejection/demotion reasons are historical provenance, not current search-value blockers for repository-owned code. Actual public licenses remain recorded; third-party datasets, standards, models, trademarks, patents, external APIs/services and safety-sensitive material remain separately governed.
- A repository-level license does not automatically license bundled third-party standards/data/assets.
- If inspection surfaces credentials, private/personal data, controlled/confidential material or unauthorized-access material, stop; do not retain/reproduce/use it.
- “Demoted” means a capability may still be useful as a component/reference but no longer belongs in MASTER.

## Safety / rights quarantine — do not re-open casually

### icdev-ai/icdev GovCon modules
- Reason: an inspected GovCon file carried explicit U.S. DoD CUI / SP-CTI restricted-distribution marking. A root Apache-2.0 license does not nullify controlled-information concerns.
- Disposition: do not preserve, propagate or build from the marked material.
- Revisit trigger: authoritative rights-holder/government evidence establishes the marking is erroneous or unrestricted reuse is authorized.

### Em1lyK/ctrebate_recon
- Reason: inspection surfaced a credential-like/authentication query value in a source URL; inspection stopped. No repository license was established independently.
- Disposition: quarantined; no value was retained or tested.
- Revisit trigger: sanitized revision + explicit reuse rights; restart only from that clean revision.

### Andalusia-Data-Science-Team/QA-for-call-center
- Commit: `fd4c22995809ff78568dad18856fede665fa4ff1`.
- Reason: README advertised a credential-bearing database configuration artifact; no reusable license established and project appeared tied to a clinical contact-center environment.
- Disposition: do not inspect credential-bearing material.
- Revisit trigger: sanitized licensed revision with clearly synthetic/public fixtures.

### ansh-guptaa/LastMileSaathi
- Commit encountered: `ae9e4d2196aedc2b822838a44dd713566318b009`.
- Reason: commit-history inspection surfaced published authentication material. No credential/value was retained, reproduced or used; repository also had no reusable license.
- Revisit trigger: later sanitized/licensed revision only, without historical secret inspection.

### SmartRateCon/smart-ratecon
- Reason: freight RateCon project with GPL/copy-left constraints and a committed environment/config artifact that created unnecessary secret-handling risk during inspection.
- Disposition: do not use the sensitive artifact; do not treat as a permissive freight foundation.
- Revisit trigger: sanitized revision plus a clear product architecture that can comply with GPL and materially beats the MIT A-Jatin RateCon leader.

### VedantVAchole/freight-accessorial-agent
- Commit: `4834…` as cataloged in Hunter 03.
- Reason: no reusable license and source presentation relied on named-counterparty/internal/undocumented operational knowledge rather than a rights-clear public rule source.
- Disposition: clean-room only; do not turn apparently internal carrier knowledge into product authority.
- Revisit trigger: explicit permission/license plus independently authoritative public/customer-owned rule sources.

## Freight / recovery false leads and dominated assets

### Tetrixx-SG/freight-audit-intelligence
- Reason: methodology/use-case/ROI/static research repository rather than a functioning audit engine; no license detected.
- Revisit trigger: executable tested audit software under clear rights.

### freightbill/freightbill
- Reason: static Eleventy article/documentation site despite code-heavy snippets; not a functioning freight-audit product and no license found.
- Revisit trigger: executable tested engine is published under clear rights.

### sinchana-g7/RateDrift
- Reason: compelling rate-creep positioning, but inspected repo was frontend/README while described workflow lived externally; no license.
- Revisit trigger: backend workflow, durable historical comparison tests and clear license appear.

### shafeehhecker/HaulSync as invoice-reconciliation engine
- Reason: useful freight workflow/application, but inspection did not substantiate a deterministic contract-vs-invoice reconciliation engine strong enough to displace the active stack.
- Revisit trigger: tested rerating/entitlement/settlement logic is added.

### ClickPostERP as freight-audit core
- Reason: connector/workflow value exists, but it is not the deterministic invoice-reconciliation/rerating core search results could imply.
- Revisit trigger: exact rated-vs-billed math + authority/proof tests become first-class.

### ediflow-lib/core bundled X12 definitions as automatically MIT-cleared standards data
- Commit: `9a631a4104711bf5ac81c96d4b725c8698b4d799`.
- Reason: parser/infrastructure is MIT, but bundled X12 transaction structures/code lists are standards-derived and independent redistribution provenance was not established.
- Disposition: evaluate parser code separately; keep standards-definition corpus outside commercial dependency chain until rights are established.
- Revisit trigger: explicit lawful redistribution/provenance statement for the generated/bundled definitions.

### stowaway freight benchmark as commercial corpus
- Reason: technically useful synthetic freight benchmark, but implementation/license is proprietary/evaluation-only.
- Disposition: do not copy code/data; independently author equivalent acceptance cases.
- Revisit trigger: permissive/commercial license granted.

### BestKylin no-license carrier-specific parser analogs
- Reason: deeper carrier-specific workbooks/parsers surfaced useful failure modes but lacked reusable rights.
- Disposition: requirements only: multi-origin/destination expansion, add-on→base references, included/excluded surcharge text, special-parser precedence, destination-vs-transit semantics and workbook-bound behavior must be independently implemented/tested.
- Revisit trigger: rights change.

## Commercial-rights traps

### Jinotaer/Multi-Tenant-Laundry-Shop-Management-System
- Commit: `cc0f11d322e7e5a80628001cec3255a68914f2fd`.
- Reason: broad multi-tenant app, but README explicitly labels application proprietary/all rights reserved. Laravel being MIT does not license the application.
- Revisit trigger: rights-holder grants open/commercial reuse rights.

### taskfleetai/fieldfleet
- Reason: strong construction/restoration FSM breadth but Elastic License 2.0 prohibits offering FieldFleet itself as a hosted/managed competing service without commercial agreement.
- Revisit trigger: separate commercial license or independently reimplemented requirements only.

### rabbittrix/BSS-OSS-Rust-Ecosystem
- Commit: `7ad417c2590d5a843302f7dbfa163e5e774ed63d`.
- Reason: root licensing adds commercial authorization/donation requirements for TMF crates and proprietary terms for other components despite permissive-looking per-crate metadata.
- Revisit trigger: explicit commercial authorization.

### kundanvarma/genalpha-bss current revisions
- Commit: `8fd5286dd676753bb37324eb395be0df14980356`.
- Reason: BSL 1.1 Additional Use terms exclude a paid competing hosted/embedded product until version-specific change dates.
- Revisit trigger: use a specific revision only after its Apache change date or obtain commercial permission.

### Step Function DNP3 implementation
- Reason: technically strong but license terms prohibit/limit commercial production use for the intended product shape.
- Revisit trigger: separate commercial permission or use only independently authored interoperability requirements.

### rtlabs-com/p-net as a permissive PROFINET core
- Commit: `ca4f37c5d66b5378a8cf9349b9084df0612043da`.
- Reason: technically strong PROFINET Device stack, but the project is GPLv3 with a separate commercial license and explicitly positions commercial products as needing that license. It is not an MIT/Apache drop-in merely because the source is public.
- Disposition: GPL-compatible/reference/test use only unless the intended product has the appropriate commercial grant; keep PROFINET technology/trademark/certification obligations separate.
- Revisit trigger: commercial rights are obtained for the intended architecture, or a maintained permissive implementation with comparable state/test depth appears.

### gameguild-gg/gameguild marketplace settlement subsystem
- Commit: `0f52022ade885b4489d1d10bda8a3e731be2135e`.
- Reason: unusually strong settlement/refund/entitlement lineage, but no repository license despite “open source” wording.
- Disposition: clean-room property-test/reference material only.
- Revisit trigger: valid license/permission.

### DataBricks retail promotion schema outside Databricks use
- Reason: detailed promotion semantic model exists, but license restricts use to connection with/use of Databricks Services.
- Revisit trigger: target product is explicitly Databricks-native and agreement-compatible.

## Stale deterministic authority — do not use as current legal/eligibility truth

### bedrocka-ventures/bedrocka-tools-calc — SBA size-standard path
- Commit: `7723112b433f6ca9351bddaf0c37248e673356db`.
- Rights: MIT, but rights cleanliness does not make outdated decision logic safe.
- Reason: inspected federal-contracting receipts logic uses a three-year average and user-supplied thresholds. Current 13 CFR §121.104 generally uses the most recent five completed fiscal years for firms in business five or more years, subject to exceptions, and affiliate receipts matter. A deterministic stale eligibility result is worse than an explicit unresolved state.
- Disposition: do not use its result path as current SBA authority. Rebuild from versioned official SBA/eCFR sources with effective dates, exception handling, affiliation inputs and fail-closed source-integrity checks.
- Revisit trigger: repository updates to the current official rule set and adds version/effective-date/provenance plus regression tests against official examples.

## Demoted / surpassed

### Fajendagba/Construction-Change-Order-Engine
- Commit: `60f5ab99bfb97647039e6cec280c246a10f8a856`.
- Reason: no license; rights-clean Massing/OpenTakeoff/BIMChange stack now materially surpasses it.
- Revisit trigger: permissive rights + implementation/tests that beat current ScopeSignal stack.

### quanshuyang/cad-diff-agent
- Commit: `386200f2fe04566fa794e44e3ebb7231fc18352e`.
- Reason: MIT and useful baseline, but Massing PDF + CaD-Track now cover ScopeSignal registration/correspondence more deeply.
- Revisit trigger: independently validated correspondence/move-vs-change capability materially exceeds current pair.

### D-ivy/renewables_indexes
- Commit: `fe31ab507987a38cc9c042cd745d89546b6f25c0`.
- Reason: valuable site-screening methodology/data but no license and incomplete visible reproducibility.
- Revisit trigger: clear code/data rights and reproducible build or licensed successor.

### robawtic/heijunka as workforce-assurance core
- Commit: `14559d42a08f011467261383cc533fb447529c7b`.
- Reason: fallback objective can prefer zero assignments unless coverage is forced; RosterSpec is stronger on verification/repair semantics.
- Revisit trigger: corrected objective/coverage semantics with regression tests.

### khayaklap/inventory-rl
- Commit: `38ad9dffc7caaa8b9fbdc0a5a376d8cf7fb49e07`.
- Reason: no license, single-SKU scope and own results show simpler baselines can beat the more complex RL path; commercially dominated by deterministic/decision-focused alternatives.
- Revisit trigger: licensed multi-SKU/capacity result with robust out-of-sample economic advantage.

### TNRIS/weather-alerts-parser
- Commit: `c692ebbbabd40b912e3c8375fc2490385ae2df8b`.
- Reason: rights-friendly but Python-2-era/API assumptions are obsolete versus current NWS/CAP/GeoJSON tooling.
- Revisit trigger: legacy-format archaeology only.

### edgego/device-console
- Commit: `106d1668d34ec33bf20763eaebed7f05b69ecf57`.
- Reason: Apache-2.0 but inspected tree was mainly deployment manifests rather than a distinct device control-plane implementation; dominated by Edgehog/Kura.
- Revisit trigger: executable application/control-plane source appears.

### thin-edge/opc-ua-demo-server
- Commit: `4e9bd6819fb31ceaa9ba37a98ee506e033fa79ba`.
- Reason: permissive but shallow relative to existing independent OPC UA peers; no meaningful conformance/fault-test advantage.
- Revisit trigger: substantial conformance/reconnect/failure test layer added.

## Misleading README / incomplete implementation

### qa-audit-portal current revision
- Reason: MIT rights are clean but current repository is early Next.js/Prisma setup with merge-conflict/Sprint-1 remnants, not a functioning contact-center QA product.
- Revisit trigger: real scorecards, calibration/adjudication and analytics implemented/tested.

### pengyulong/InvoiceAuditAgent
- Reason: README itself marks core audit, AI, tests and deployment incomplete; no license detected.
- Revisit trigger: substantive functioning backend plus clear license.

### RestoreVerify/restoreverify
- Commit inspected: `ba9e…` as cataloged in Hunter 15.
- Reason: polished recovery-verification surface but critical functions are placeholders: inspected health logic always returns healthy, backup validation always succeeds and benchmark/verification paths do not provide the adversarial restore truth the product description implies.
- Disposition: do not use it as recovery proof or as evidence that a backup restored correctly.
- Revisit trigger: real restore execution + failing negative fixtures + application/content invariants are implemented and independently reproducible.

### VeeamHub/veeam-vscan-security as reusable implementation
- Commit: `ded6d26d26065a76cbd22234af7c6ff0536bf63b`.
- Reason: public repository contains useful docs/examples/assets, not the full product source/test suite implied by product description; MIT applies only to what is actually published.
- Revisit trigger: real source adapter/test suite published permissively.

### retail-ecommerce/promoengine-biz-suite
- Commit: `d1c13a2acac51d3090ed420cebc34d7fb4a03be2`.
- Reason: stale, sprawling Java framework; no self-contained tested promotion engine or reusable license validated.
- Revisit trigger: newer licensed branch with isolated promotion execution module/tests.

## Rights/engineering ambiguity — do not let a useful domain idea become an authority claim

### nrivasdatafy/api_nodal_capacity
- Commit inspected: `fe98…` as cataloged in Hunter 11.
- Reason: repository presentation described a useful nodal-capacity API and referenced MIT, but no root license grant was established at the inspected revision. Public visibility/README wording is not sufficient reuse authority.
- Disposition: inspect/clean-room only; do not ship source or market its calculations as an engineering oracle.
- Revisit trigger: explicit repository license plus reproducible electrical validation against known feeder cases.

### grid-gent
- Reason: the inspected “MIT License” artifact was only a tiny/nonstandard placeholder rather than a valid grant, and the electrical model was too simplified to establish AC power-flow/hosting-capacity truth.
- Disposition: reject as both a rights and engineering-authority foundation.
- Revisit trigger: valid license + independent power-flow validation + substantive test corpus.

## Policy
Do not add a weak repository to this file merely because it was rejected once. Lane-local low-value misses belong in their hunter catalog. Add here when a find is likely to be rediscovered, has a misleading surface, contains a rights/safety trap, or was formerly important enough that future hunters need to know why it is no longer preferred.

<!-- INTEGRATOR-R11-2026-09-19T2028-0400 -->
## Integrator rejection / quarantine additions — 2026-09-19 20:28 ET

### notaryproject/tspclient-go as the Recovery Proof trust authority
- Commit: `6c337f1e30f2cbdcd73d01ab54d7a49e6a34da31`.
- Reason: real RFC 3161 client and chain verification, but inspected CMS verification explicitly does not perform revocation checking. SiVa materially surpasses it for the current PKIX/OCSP/CRL/freshness gap.
- Revisit trigger: substantive revocation/trust-policy support or a new failure mode SiVa does not cover.

### pasrom/profinet-rs as an independent PROFINET controller oracle
- Commit: `5732f5a7f438c13efa41774921a021ea83671ee5`.
- Reason: strong Rust implementation, but it explicitly derives wire layouts/structures/test vectors from `f0rw4rd/profinet-py`; agreement between the two is not independent conformance evidence.
- Disposition: usable operational peer under the standing permission posture, but not counted as an independent falsifier.
- Revisit trigger: an independently originated controller lineage or independently derived protocol vectors.

### adrianstanca1/cortexx current revision
- Commit: `87679c82a6bb5cf3619d63ee32786f8260f3ef6b`.
- Reason: recursive tree inspection surfaced a committed environment-vault artifact. It was not opened and no values were collected or retained.
- Disposition: safety quarantine at this revision.
- Revisit trigger: clearly sanitized later revision and a concrete unmet construction-domain gap.

### boomlocal/Dumpster-Rental-Management-System-2320 current revision
- Commit: `ca9ec596d559c10c64fcdd3706f125f1985f9af7`.
- Reason: current tree contains a committed environment file. It was not opened; no credential/auth material was collected.
- Disposition: safety quarantine.
- Revisit trigger: sanitized later revision only.

### ClintonK399/Fuel-Delivery-Management-System current revision
- Commit: `ced5ce2faecd5ceea4cc7fa94d7275b1cce35a3d`.
- Reason: tree contains a database-configuration artifact that could contain connection/auth material; inspection stopped before opening it, and safe evidence did not establish enough domain depth to justify further risk.
- Disposition: safety quarantine/deprioritized.
- Revisit trigger: clearly sanitized later revision plus a specific fuel-delivery gap.

<!-- INTEGRATOR-R12-2026-09-19T2231-0400 -->
## Integrator deprioritization additions — 2026-09-19 22:31 ET

### pypi-ahmad/OpenAI-X-RapidOCR-Agentic-Document_extraction as another portfolio OCR leader
- Commit: `eeae35…` as cataloged by the inspecting hunter.
- Reason: useful evidence-heavy OCR/layout extraction, but the portfolio already has Assay's calibrated accept/review semantics plus domain-specific RateCon/structured-invoice extraction. Another generic document extractor does not change a buyer, authority chain or first paid wedge.
- Disposition: component/watch only; stop generic OCR discovery.
- Revisit trigger: independently demonstrates materially lower false-accept at the same review rate on a money-bearing benchmark, or uniquely solves a document class the current stack cannot parse.

### generic EIA diesel/index adapters as contractual fuel-surcharge authority
- Representative repository: `naren514/Fuel-surcharge-Updater@18bad10b45b3e45a832ab549f9bf512c2e3b41fe`.
- Reason: pulling an authoritative public diesel index is useful input plumbing, but the index value alone does not establish the customer/carrier's controlling FSC formula, base index, trigger band, rounding, publication lag or effective-date convention.
- Disposition: source adapter only; never promote its calculated factor to contractual authority without the controlling agreement/addendum/tariff.
- Revisit trigger: a repository binds source index + exact customer/carrier contractual formula/version/effective dates and proves that lineage with tests.

<!-- INTEGRATOR-R11-2026-09-20T0025-0400 -->
## Integrator additions — 2026-09-20

### Emmanuel-tech-hub/freight-invoice-auditor — production-blocked fail-open recovery logic
- Revision: `1987a776` (full inspected SHA preserved in hunter 36).
- Reason: missing contracted accessorial authority can resolve to `$0 expected`, making a positive billed charge appear as an overcharge; rows marked `needs_review` can still flow into totals. In a recovery product this is a false-dollar failure, not a cosmetic defect.
- Disposition: retain only as a negative regression fixture. Do not use its output for asserted/recovered money.
- Revisit trigger: missing/ambiguous authority routes to REVIEW/$0, review rows are excluded from money totals, and tests prove the fail-closed behavior on planted missing-rate/accessorial cases.

### mccabetrow/capsight — permit/property connector surpassed on source truth
- Revision: `1f0afdaa90e8c7e5ef0c3310fdbc8ce6a5ecdb6`.
- Reason: inspected municipal source layer included placeholder/example dataset configuration and lacked the stronger retained controls for portal-count completeness, explicit source-health/refusal semantics and immutable permit-version history.
- Disposition: deprioritized; PermitBuild + Urban Signal + source-health/completeness components are stronger.
- Revisit trigger: real source coverage plus independently verified completeness, versioning/diff and `fresh/stale/not_covered/error` semantics.

### GSA/GSA-Acquisition-NMCARS — currentness not established
- Revision: `09d5b2d7040065fead99e15aacabb1d782b450d5`.
- Reason: repository maintenance recency did not establish that sampled substantive NMCARS content was current; inspected lineage pointed to older 2022-era content.
- Disposition: do not use for live rule applicability until independently reconciled with the current authoritative Navy/Marine Corps source.
- Revisit trigger: newer substantive publication or authoritative cross-check proves effective/current content.

### GSA/GSA-Acquisition-DAFFARS — historical/archived authority only
- Revision: `645e3050d4e40d600bdd68a8b7fd112a6bf3171b`.
- Reason: inspected repository is archived and directs users to a newer Department of the Air Force contracting publication location.
- Disposition: historical provenance only; never silently use the archived snapshot as current authority.
- Revisit trigger: none for current authority; follow the successor official source instead.

### Rejection lesson reinforced
Clear repository use permission does not cure **stale authority, fail-open money logic, weak source coverage or misleading completeness**. Technical/commercial scoring must continue to penalize those defects independently of license category.

<!-- INTEGRATOR-R11-POSTCHECKPOINT-2026-09-20T0056-0400 -->
## Post-checkpoint safety/provenance quarantine

### muhdwaseem/Logisticsrate — third-party contract-derived tariff material
- Revision: `6250dc36137f66d65e4d18314d36ca3b86b66913`.
- Disposition: **safety/provenance quarantine**, not a technical-license rejection.
- Safe evidence: repository contains functioning logistics rating code, but public commit history describes a signed real freight agreement being transcribed into tariff data.
- Boundary: the standing permission for repository-owned public code does **not** extend to a third party's confidential/commercial contract terms. The signed agreement, tariff-seed values and contract-derived commercial numbers were not opened, copied, tested or retained.
- Revisit trigger: only a sanitized revision/fork that cleanly separates generic code from contract-derived values and uses independently generated synthetic/publicly authorized tariff fixtures.

<!-- INTEGRATOR-R11-DECISION-ACTION-2026-09-20T0112-0400 -->
## Decision-engine dominated patterns — 2026-09-20
- `AbedSalekin/revenue-decision-engine@4a545f96255c758b6886a86306c490156579ac7c` — reject/deprioritize. Broad app scaffolding and AI recommendation text do not provide deterministic/causal decision logic, auditable objective math or evidence that recommendations improve revenue. Revisit only with tested economic models, reason codes and controlled outcome evidence.
- `AkramZaabi/Operational-Resaerch-Inspection-Routing-Optimizer@c5e847b3e02abd1f79f869f167c4e4f9511cd6b7` and `maudefish/operator-task-optimization@ede0acf65addd6d79d8425a4317724b3dc535911` — generic routing/assignment formulations are dominated by Jestrada/SAGE/RosterSpec/MIP++ and the established inspection/scheduling stack. Revisit only if they add unique domain authority, stronger route semantics, conventional tests and an incumbent-quality benchmark.
- `anara-analytics/decision-intelligence-inventory-optimization-olist@e18efdf867bde9e3296f9665b16d7a8d74f23232` and `nathaniel-gordon/stockmind@68435497715497cb309eb40ce4b0228eb86c1129` — standard forecast/reorder/BI logic is dominated by `inventory_tools`, Calibre-style temporal correctness and `deepbullwhip`. Revisit only for materially richer constraints, live operational state or decision-cost validation.
- `tadiwamark/pdM_Genset_Analytics@e7c79ddb7f022661d58047ce3f9d7372e6482c8b` — anomaly-to-LLM recommendation prototype without deterministic action economics or surfaced conventional tests. External model/API and bundled data/model rights remain separate. The inspected README showed only a placeholder environment-variable example; no credential or sensitive value was collected, retained or tested. Revisit only with validated maintenance-action economics and auditable deterministic decision logic.
