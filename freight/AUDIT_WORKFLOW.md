# Single-call Audit Workflow

`freight.audit_workflow.run_audit_workflow` is the controlled orchestration boundary for one pre-review Freight Recovery audit.

It performs, in order:

1. guarded invoice-charge CSV ingestion;
2. evidence-derived population freeze;
3. zero or more trusted-context authority-rule CSV ingestions;
4. deterministic Finding Factory derivation;
5. deterministic human-review queue;
6. deterministic reviewer work packet;
7. canonical audit-run manifest.

## States

The workflow returns one of three explicit states.

- **CLEAN** — every normalized charge is within one verified applicable rule and there are no reviewer work cases.
- **REVIEW_REQUIRED** — the pipeline completed and issued an audit-run manifest, but one or more cases require a human. This includes validated discrepancies, unverified authority, missing rules, and ambiguous rules.
- **BLOCKED** — an input or internal proof boundary failed. No audit-run manifest is issued.

A missing rule set is not a pipeline error. The workflow can complete with zero rule batches and produce `REVIEW_REQUIRED` cases whose expected amount is not established. A malformed supplied rule file is different: it blocks at `RULE_INGEST`.

## Fail-closed stages

Blocked results identify the stage and a stable error code:

- `INVOICE_INGEST_FAILED`
- `POPULATION_FREEZE_FAILED`
- `RULE_INGEST_FAILED`
- `FINDING_DERIVATION_FAILED`
- `REVIEW_QUEUE_FAILED`
- `REVIEW_PACKET_FAILED`
- `RUN_MANIFEST_FAILED`

Programming exceptions outside expected validation failures are intentionally not converted into successful workflow results.

## Output boundary

Successful results contain the full in-memory audit artifacts for use inside the approved customer-processing environment plus a minimized summary containing counts, state, discrepancies, and the canonical audit-run hash.

The workflow does **not** perform buyer confirmation, contact a carrier, submit a dispute, accept a settlement, or claim a discrepancy is realized savings. Those remain separately authorized downstream transitions.
