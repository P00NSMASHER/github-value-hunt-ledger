# RETALLY Phase 4 — Mission 39 cross-lab synthetic integrity

**October 13, 2026 · INTERNAL RESEARCH ONLY · DRAFT stacked on M38 PR #432.** Does not merge, deploy, add a lab, schedule tasks, contact customers, import private files or move money.

## Substantive new capability

Previous Phase 4 code executed 14 existing modules and stored a local SHA receipt. Its bounded experiment verifier rejected missing proof and obvious tampering, but still trusted broad statuses beginning with EXECUTED and generic negative-probe labels. A misleading JSON receipt could be rehashed after changing a lab status, expected negative proof, fictional settlement amount or a claimed real customer approval. A matching SHA does **not** mean a trusted source produced the fields.

M39 introduces a **separate closed-contract proof checker spanning all fourteen existing labs** before experimental evidence can enter the experiment ledger or the Control Center's accepted view.

The checker validates each element in the original 14-lab receipt, including:

- Exactly labs 1–14, in order, with titles, supported statuses, expected synthetic scope and complete executed and failed status sets. Budget-skipped work remains incomplete—not a 14/14 pass.
- Every successful lab's **specific expected negative-probe identifier**, not merely a nonempty or plausible-sounding string. All five inherited Phase 3 proofs are bound to their original domain-step labels and hash-shaped evidence.
- Structured proof fields and fail-closed assertions for synthetic reviewer fixtures (Lab 3), fictional security/procurement certifications (Labs 6 and 9), human-reviewed tariffs (Lab 10), synthetic payment labels (Lab 12), zero real customer margins (Lab 13), and Lab 14's **M35–M38 source/claim/human approval firebreak**. A rehashed invented endorsement is rejected.
- Recomputes the **entire three-customer fictional pilot** from its original Phase 3 Python fixture; enforces zero real customer fees/cash/authorities and local receipt, so inventing fictional recovery figures then rehashing both reports cannot pass.
- Recomputes the original timing-normalized execution receipt; runtime durations remain informational and cannot change the stable evidence hash. No original input or test signer is treated as real bank, buyer or carrier proof.

**This is stronger local consistency assurance, not cryptographic independence of the original execution, external provider authentication, an objective correctness proof or a production certification.** A coordinated malicious source-code modification and its tests could still fabricate compliant outputs. Live safety, real bank authority and customer signoffs are separate prerequisites.

## Integration, tests, output

- freight/lab_cross_lab_assurance_m39.py: strict lab receipt and synthetic pilot validator; always labels local confidence as synthetic-only. Returns 14-lab proof table and a local receipt.
- freight/test_lab_cross_lab_assurance_m39.py: mutation tests for each of the 14 negative-probe identifiers, removed proofs, fake execution statuses, lab reordering/duplication, false financial/customer authority, report tampering after recomputing a valid local SHA, budget shortfalls, timing variability, HTML escaping, and before-write CLI rejection.
- freight/lab_phase4_experiments.py: requires the M39 original receipt assurance **before** writing findings to the existing experiment ledger; the earlier checks remain.
- freight/lab_phase4_control_center.py: checks the original raw 14-lab record **before** augmenting it with marketing or economic research, and emits an M39 read-only panel, cross_lab_assurance.json and cross_lab_assurance.html.
- .github/workflows/retally-cross-lab-integrity-m39.yml: PR/manual-only test, full 14-lab replay, bounded research regressions and a separate-process negative proof. Artifact receipts retained for 14 days. No cron or deployment.

### Local reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_cross_lab_assurance_m39.py freight/test_lab_phase4_experiments.py
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m39
    # Inspect /tmp/retally-m39/cross_lab_assurance.html

M39's CLI also accepts a separate **raw** execute_all_labs JSON input via --receipt and writes its own internal HTML/JSON. This is distinct from enriched phase4_control.json, which contains additional report families. Every input is validated before any output directory is created. The integrity report never includes customer/carrier data.

## Open first-customer conditions

**26 historical research findings remain open**, independent of the local pass count. The three accepted cases are fictional and no real customer has been authenticated by these labs. None of P11's **18 independently unmet external human pilot controls** are satisfied by passing M39. Hosted production, real invoice chain, authority, monetary settlement, legal/privacy review, registration and external source-publication claims remain separate from this code.

**No merge, production deployment, scheduled task, customer outreach, cash movement, or external audit recovery claims.**
