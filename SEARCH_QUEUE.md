# SEARCH_QUEUE

Integrator-owned search and validation direction. Updated 2026-09-20. **Experiment bottlenecks, independent falsification, source authority and outcome evidence outrank repository count.** This file is current direction, not history; older run-specific overrides remain in Git history and hunter catalogs.

## Operating rules for all 14 workstreams
- Deduplicate by **repository + exact revision + capability**.
- Repository-owned public code may use the user's standing separate-commercial-permission assumption for prioritization; record actual published rights and keep datasets, standards, patents, trademarks, APIs/services, customer records and other third-party material separately governed.
- Verify beyond README using source, tests, schemas/migrations, fixtures, deployments/config and history. Distinguish IMPLEMENTED / TESTED / CLAIMED / EXPERIMENTAL / UNVERIFIED.
- Never inspect, retain, reproduce, test or exploit credentials, authentication material, private/personal/confidential data, accidental secrets, leaked trade secrets, unauthorized-access material or vulnerabilities intended for unauthorized access.
- Reuse benchmark-supported skills when applicable, but do not leak benchmark gold. Before important NO_FIND conclusions, run one recall-rescue pass using repository family/old name/author-org adjacency, oracle/test-fixture vocabulary and near-match lineage without lowering the verification bar.
- PASS/VERIFIED must survive missing, stale, ambiguous, malformed, partial and selection-fallback states. Source exceptions may not become empty-success.
- Any decision claim must trace **dispatch -> executable implementation -> meaningful side effect -> semantic test**.
- Any money/trust claim must identify source authority and prevent rejected/unknown evidence from re-entering totals, billing, recovery, health or proof summaries.
- Effective-dated rules must pin authority, event/effective time, supersession and load-bearing thresholds/exceptions.
- No padding. A no-new-find run is acceptable.

## 1. Freight Recovery — P0 / EXP-001
**Current state:** internal settlement semantics are now substantially exercised. Hunter 03's planted 210/812/820 corpus passed exact/unique allocation, reviewed partial/split edges, duplicate events, full reversal, ambiguous partial reversal, wrong currency, pre-authority timing and 2,000 deterministic fuzz ledgers. This is technical evidence only; EXP-001 remains **BLOCKED_EXTERNAL**.

**Do next:**
- freeze internal engineering except persistence/concurrency/security defects exposed by the planted corpus;
- search only when a real authorized buyer population exposes a named missing authority, correction/rebill, source-format or settlement edge;
- preserve the chain: controlling authority -> independently computed expected charge -> unique economic claim -> buyer adjudication -> issued adjustment -> independent settlement event -> one-use allocation edge -> later counter-event/reversal -> realized recovery.

**Stop:** generic freight audit/reconciliation/TMS/OCR/rating/EDI discovery. A discrepancy, dispute, issued credit or provider status remains **$0 realized** until independently allocated settlement exists.

## 2. AP Leakage Assurance — P0 / EXP-002
**New evidence:** ERPNext's current Purchase Receipt billing service supplies high-value regression fixtures for partial receipts, mixed PO-level/direct receipt billing and rejected quantities. Cross-ERP evidence also falsifies a universal `has_receipt` rule: receipt authority is policy- and line-type-dependent.

**Do next:** build an ERP-neutral `ReceiptAuthorityPolicy` over `{ERP/system, PO line type, buyer configuration, supplier override, verification mode}` and allow authority artifacts such as `GoodsReceipt`, `ServiceEntrySheet`, or explicit `DirectInvoiceAllowed`. Run it with CAP-019 source observation receipts (`PRESENT / VERIFIED_EMPTY / UNAVAILABLE`), Nomenklatura negative/reversible identity decisions, Canon pinned replay and bitemporal corrections.

Port at least these adversarial fixtures: one PO line across multiple partial receipts; residual amount+quantity after mixed direct and PO-level billing; rejected-quantity billing denominator; service-entry-sheet required vs legitimately not required; source outage/partial ingestion; corrected receipt after original decision.

**Stop:** matcher/OCR/RPA/anomaly hunting and any universal missing-GR conclusion. ERP status is a semantic oracle/challenger, not independent truth.

## 3. Partner / Commission Payout Assurance — P0/P1 / EXP-003
**New evidence:** `Modern-Treasury/modern-treasury-python@406f354a...` supplies the strongest current bank-observation bridge: Payment Order -> bank/reference metadata including ACH trace/original trace -> bank-derived Transaction/Transaction Line Item -> later Return/Reversal. `szapata85/ACHInterbank@395a359...` supplies a useful fail-closed correlation policy: exact unique return linkage may mutate state, while duplicate candidates become `Ambiguous` and zero candidates become `NotFound` with no money-state mutation. Hosted treasury/bank services and bank-feed coverage remain external; the Modern Treasury server-side auto-reconciliation algorithm is not public and a trace value alone is not proof of unique settlement identity.

**Do next:** stop architecture hunting and execute the provider-neutral finality corpus. Model bank-observation outcome explicitly as `EXACT_UNIQUE / AMBIGUOUS / NOT_FOUND / UNAVAILABLE`; only `EXACT_UNIQUE` inside a verified source-observation window may become a settlement candidate, and later Return/Reversal must be able to revoke it. Plant duplicate trace, substring-reference collision, equal-total/swapped-identity, unparseable amount, stale cursor, bank-posted-then-returned and duplicate-semantic-return cases. Use CAP-019-style source-health evidence so stale/unavailable feeds cannot masquerade as `no return` or `no transaction`.

Provider `sent/paid/succeeded` remains distinct from bank/network finality. Unknown provider results remain claimed/pending and must not auto-release for retry. A later return/reversal invalidates prior finality without deleting history.

**Search only:** a concrete provider/reference -> bank-observation mapping or completeness/freshness gap exposed by the corpus.

**Stop:** commission calculators, payout wrappers, generic bank-statement parsers and reconciliation libraries. An `EXACT_REFERENCE` label, substring/fuzzy reference match, amount equality, first-match policy or last-seen cursor is not settlement proof.

## 4. ScopeSignal / Construction Change Leakage — P0/P1 / EXP-005
**New evidence:** `mradul010/construction_management@ce345579...` is a strong authority-to-bill component: submitted work-order/PO context is server-reloaded, measured quantity/rate is bounded against authoritative lines, Approved SC Bill gates Purchase Invoice creation, and retention/payment consistency is checked. It does **not** prove independent field-measurement approval or bank finality. ERPNext also supplies a live false-finality case where a bank transaction can be Reconciled while the Payment Entry remains uncleared.

**Do next:** construct a cross-implementation corpus comparing Nirman's approved-measurement path with `construction_management` server-side contract/quantity bounds. Plant wrong work-order ownership, over-measurement, draft/rejected measurement, wrong billing period, concurrent quantity claim, retention error, payment-entry/bank-reconciliation divergence and later reversal.

**Search only:** signed/approved field-measurement authority, unbypassable certification-to-bill linkage, prime/sub flow-down/amendment authority, and independent cleared-cash/reversal evidence.

**Stop:** generic IPC/pay-app UI, RA-bill CRUD, quantity/takeoff/diff or internal `PAID/Reconciled` labels.

## 5. Recovery Proof — P0/P1 / EXP-004
**New evidence:** `gitdr-io/gitdr@c9d15a2...` shows that successful restoration and durable proof filing are separate assurance states; a restore may succeed while proof persistence fails, and overall assurance must remain non-green. Current recovery catalogs also reinforce verifier-self-test/mutation and wrong-state controls.

**Do next:** add `proof_sink_unavailable_after_successful_restore` to the common adversarial matrix. Run PostgreSQL plus a non-Postgres/object workload through wrong-but-restorable content, missing history, stale proof, corrupt object, service-up/data-wrong, trust/revocation failure and a deliberately damaged verifier assertion/helper.

**Stop:** broad backup/restore tooling. Search only if the matrix reveals a missing negative control or workload invariant.

## 6. CaptureBrief / Government acquisition intelligence — P0/P1 / EXP-006
**New evidence:** official SAM/Data Services lineage can support notice/version history but is not attachment-complete. `chrisfulcher/orrery@89ae2218...` implements the missing public attachment-manifest/currentness plane using the SAM web-interface resource manifest, preserving access/deleted/export-controlled/file-existence metadata and failing closed on unknown manifest shape. The remaining gap is historical manifest-state completeness when attachments disappear or mutate.

**Do next:** for the frozen 10-solicitation corpus, maintain separate planes:
1. official notice/version/action history;
2. attachment manifest state;
3. immutable downloaded artifact hashes where public access is authorized;
4. FAR/supplement/deviation authority;
5. entity/award lineage.

Require append-only manifest snapshots or an equivalent deterministic history rule so disappearance/deletion cannot be mistaken for absence. Benchmark latest-row conclusions against full packet/history and source-degraded intervals.

**Search only:** successor/deviation authority, historical attachment-state losslessness, source-currentness/freshness or exact packet gaps exposed by the corpus. Stop generic SAM/FAR wrappers and procurement dashboards.

## 7. Installed-Base Lab / Sequencing Operations — P1 / EXP-007
Sequencing remains the primary profile: Clarity workflow state -> run identity -> independently validated sample sheet -> InterOp operational metrics -> provenance/replay using synthetic/dummy or explicitly authorized non-PHI data.

New LADS and CETONI findings support the broader category of standards facades over real installed devices, but both remain WATCH because production hardening, hardware-in-loop regression and safe command ownership are not proven.

**Do next:** complete the Clarity synthetic handoff. For device-standardization searches, require a named installed family plus real vendor/native actuation, behavioral/HITL regression, fault/recovery semantics and explicit arbitration/single-actuation authority. Do not count a standards facade alone as safe production control.

## 8. Insurance Subrogation Recovery — P1 / EXP-011
Search only authoritative versioned jurisdiction/policy rules, policy-language precedence, limitations/fault effective periods and closed-claim settlement evidence. Unknown/missing/conflicting/superseded rule or unresolved policy wording = **REVIEW / $0 asserted recovery**.

**Stop:** generic claims AI, demand-letter tools or illustrative statutes presented as current authority.

## 9. Money-State Integrity / Payments — P1 / EXP-010
Internal contract/rating/invoice/allocation/reconciliation machinery is deep enough. Search only independent contract/amendment authority and external PSP/bank settlement/readback that can contradict the operational system, including returns/reversals/chargebacks and final amount/currency/trace.

Run the canonical synthetic month before adding another payment core. Keep action/decision score, evaluator and buyer economic outcome separate under Evaluation-Target Independence.

## 10. Revenue Decision Assurance / Pricing-Yield — P1/P2
Search only held-out replay adapters, real capacity/censoring/no-show/cancellation state, incumbent decision logs and realized revenue/load outcomes. Every claimed optimizer/abstention/information-acquisition mode must reach a changed operational action and semantic test.

**Stop:** recommendation-only analytics and model-valued ROI without independent buyer outcomes.

## 11. Industrial Virtual Commissioning / Protocol Acceptance — P1 / EXP-008
Execute the frozen Dreamine.Gem <-> `bparzella/secsgem` dialogue/error differential corpus and the duplicate-EC atomicity probe before searching more SECS/GEM implementations. Classify each disagreement as profile ambiguity, implementation defect or unresolved standards/vendor-authority question.

Search a third engine only to adjudicate a concrete disagreement. For PLC/OPC-UA, hunt only a customer-configuration/import or migration/reconnect/fault gap that changes pre-FAT acceptance. Same-family agreement is not independent proof and implementation agreement is not formal conformance.

## 12. Permit / Public-Data Intelligence — P1 / EXP-009
Apply source topology + immutable version/diff history + explicit run truth. CAP-019 observation receipts are mandatory for absence claims. Search only jurisdiction/semantic/identity/version gaps that change a buyer decision.

**Stop:** mutable upsert scrapers, connector-count projects and lead maps without completeness/freshness/run evidence.

## 13. Grid / Infrastructure Risk & Inspection — P1/P2 / EXP-012
**Current evidence boundary:** USECPO v2 is the rights-clear historical benchmark, but exact v2 artifact schema/event keys still require direct artifact inspection. Michigan MPSC is a strong independent historical regulator challenger but commercially rights-constrained; NYC 311 is a rights-clean construct-validity negative control, not utility outage truth; California OES is public-domain prospective outage-map evidence but has no history.

**Do next:** use a two-plane design: (a) whole-event/chronology-preserving historical evaluation on USECPO with explicit evaluator ancestry, and (b) independent challenge using rights-permitted regulator/utility evidence plus prospective public-domain feeds after predictions are frozen. Never credit multiple EAGLE-I descendants as independent validation.

**Stop:** more outage datasets/models until exact USECPO v2 schema is frozen or a genuinely independent, commercially reusable historical outage oracle is found.

## 14. Sparse-lane repair + wildcard analogs — P2
Only pursue adjacent domains reproducing the strongest portfolio DNA: **authoritative source/version -> deterministic expected state -> observed actual state -> governed review/action -> independent realized outcome -> counter-event/reversal**.

Prefer old product names, protocol/standard signatures, dependency/fork/commit archaeology, obscure internal-tool-style repositories and paper->code->production lineage over broad category keywords. After five weak measured runs from a query family, record the negative evidence and rotate strategy; do not retire strategies from anecdotes alone.

## Global stop list
Do not spend capacity on generic OCR, CRUD, dashboards, RAG, fuzzy matching, commodity auth/RBAC, job queues, generic protocol clients, generic scheduling/routing/optimization demos, backup-status tools, generic TMS/CMMS/FSM/LIMS/AP OCR or speculative AI agents unless a candidate adds a **rare domain invariant, authoritative source, difficult installed-base integration, independently falsifiable algorithm, governed transition, or realized-money/evidence loop** that materially beats the current portfolio.

## Current highest-value execution order
1. EXP-001 external authorized freight population; internal settlement corpus is no longer the bottleneck.
2. EXP-002 AP source-health + ReceiptAuthorityPolicy + partial-receipt/identity/bitemporal corpus.
3. EXP-006 CaptureBrief notice-history + attachment-manifest completeness on 10 solicitations.
4. EXP-005 ScopeSignal measurement/contract authority -> bill -> independent cash/reversal corpus.
5. EXP-004 Recovery Proof including proof-sink and broken-verifier controls.
6. EXP-003 commission provider->bank/payroll finality and later-return matrix.
7. EXP-008 industrial differential corpus.
8. EXP-007 sequencing handoff.
9. EXP-012 outage evaluator-ancestry/independence benchmark.

**Portfolio rule:** repository discovery resumes only when one of these experiments exposes a concrete missing capability, authority source, comparator or outcome edge.