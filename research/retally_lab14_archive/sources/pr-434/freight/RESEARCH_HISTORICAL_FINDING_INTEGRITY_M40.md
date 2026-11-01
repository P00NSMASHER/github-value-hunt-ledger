# RETALLY Research Lab 14 — M40 historical experiment-ledger integrity

**October 13, 2026 · draft internal research only · stacked on M39 PR #433.** No merge, production deployment, cron, customer/carrier contact, private invoice import or money actions.

## The actual vulnerability fixed

The existing SQLite append-only experiment ledger validated local SHA chain continuity, but its read path trusted a persisted, writer-supplied verdict and did not check the serialized experiment against the SQL identity columns, original boolean fields or contiguous sequence numbers. With enough control to rewrite a local SQLite receipt and its SHA, an actor could relabel an inconclusive test a demonstrated repair without its own claimed evidence even satisfying the ledger's verdict rules. The existing experiment ledger is not independently authenticated, so **even correctly derived local repair verdicts must not automatically close historical RecoveryOS defects**.

Mission 40 strengthens **two actual executable boundaries**, while preserving the existing experiment-writing API and the original 14-lab test runner:

1. **ExperimentLedger:** Every read *and every subsequent append* now validates the complete strict stored Experiment schema, recomputes the verdict from typed boolean evidence declarations, checks persisted SQL identifiers, exact predecessor SHA chain, timing-independent receipt digest and contiguous sequence ordering. An attacker who simply recalculates a matching SHA after forging a verdict cannot pass; an append cannot silently build on a corrupted ledger. This is a meaningful semantic improvement over M39's cross-lab run receipt checks.
2. **Frozen original 26-finding disposition:** New M40 read-only audit binds the exact unchanged original LAB_FINDINGS_CUMULATIVE.json Git-blob identity to local experiments. It separately accounts for **26 original OPEN_UNVERIFIED defects** and **2 earlier standalone research-gate-only fixes**. The audit never promotes self-declared experiments, including a syntactically valid REPAIR_DEMONSTRATED_IN_STATED_TEST_SCOPE_ONLY receipt, to original defect closure without independent counterexample, frozen baseline/candidate artifacts and human/third-party evidence.

### Evidence boundaries

- Each local experiment SHA proves only internal consistency. A malicious actor controlling this repository and database simultaneously can rewrite the code and whole chain; M40 cannot provide cryptographic or third-party independence.
- An all-true local Experiment payload may still declare a repair *in its simulated test scope*, but M40 records that as **unattested**, leaving the original historical finding open. It does not silently claim a real prior bug has been remediated.
- M40 does **not** actually replay a new original defect or validate a buyer pilot. It explicitly reports zero independently reproduced original counterexamples in this run.
- All **18 customer pilot human approval gates remain unmet**. There is no independently verified customer refund, public marketing authority, live bank/carrier action or real customer evidence.

### New or upgraded code

- freight/lab_experiment_ledger.py: strict source-to-saved-claim schema and negative verdict checks on read and append, plus local ledger sequence completeness.
- freight/lab_historical_disposition_m40.py: version-locked original historical register, 26 original / 2 research-gate distinction, safe per-finding JSON/HTML disposition report, no automatic closures.
- freight/test_lab_historical_disposition_m40.py: diverse adversarial real SQLite tests including forged-rehashed verdict, bad identity columns, extra fields, wrong boolean types, sequence gaps, invalid catalogue, synthetic repaired local assertion, unknown finding and before-output-writing rejection.
- freight/lab_phase4_control_center.py: fully integrated read-only M40 panel and original JSON/HTML alongside existing 14-lab research reports.
- .github/workflows/retally-original-finding-ledger-m40.yml: PR/manual-only inherited 14-lab and original evidence regressions, independent SQLite rehashed-forgery proof, metadata-only artifacts 14-day retention; no cron and no deployment.

Local reproduction:

    PYTHONPATH=. python -m pytest -q freight/test_lab_historical_disposition_m40.py freight/test_lab_experiment_ledger.py freight/test_lab_phase4_experiments.py
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m40
    # Inspect /tmp/retally-m40/historical_finding_disposition.html

The standalone M40 CLI accepts an **existing local** SQLite experiment ledger using --ledger and emits a report via --out. It will not create an empty ledger when the named input is missing; invalid inputs are rejected before any output file is written.

## Required work before closing any historic defect

Independently reproduce the *original* counterexample on pinned baseline bytes, apply a bounded patch to candidate bytes, show the same exploit is rejected and a known-good control still passes, freeze the relevant artifacts and obtain independent human acceptance. A local SHA/test assertion alone is insufficient. The 26 original findings remain open. The two gate-only corrected issues remain separate.
