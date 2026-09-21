# Operational Audit Workflow

Freight Recovery now exposes one controlled pre-review workflow instead of requiring an operator to call each proof module manually.

## One-call path

`run_audit_workflow(request)` performs:

1. fail-closed invoice CSV inspection and normalization;
2. evidence-derived population freeze;
3. trusted-context authority/rule CSV normalization;
4. deterministic Finding Factory calculation;
5. deterministic review queue;
6. deterministic reviewer work packet;
7. canonical audit-run manifest.

The returned result preserves every intermediate proof object for downstream controlled use and emits one `result_hash` bound to the audit run and review state.

## Explicit workflow states

- **CLEAN** — every charge is clear under the supplied verified rules and no human review case remains.
- **REVIEW_REQUIRED** — at least one validated finding or unresolved evidence/rule case requires human review.

Missing rule/authority evidence is not a workflow crash. It becomes a `REVIEW_REQUIRED` case with an `ADD_APPLICABLE_RULE` action hint and no invented expected dollars.

## Trusted authority boundary

Rule CSV files cannot assert their own authority status.

The trusted workflow request supplies:

- buyer/business-unit scope;
- customer/carrier/currency scope;
- authority document ID;
- the original authority document bytes;
- whether that authority has been verified as controlling.

The workflow computes the original authority-document SHA-256 itself before creating normalized rules. A supplied string hash is not accepted by this orchestration layer.

## Result package

`write_audit_result_package` writes only:

- `audit-run-manifest.json`;
- `audit-summary.json`;
- `review-packet.md`;
- `PACKAGE_MANIFEST.json`.

It does not copy the source invoice CSV, rule CSVs, or authority documents into the result directory.

The output directory must be new or empty. The package manifest contains hashes and sizes for the emitted artifacts.

The review packet is still customer-derived audit material and must remain inside the approved customer-processing environment.

## Trusted-spec CLI

A controlled operator can run:

`python -m freight.audit_workflow trusted-spec.json output-directory`

The trusted spec references local source files and carries the operator-controlled authority verification state. Relative paths resolve from the trusted spec's directory.

This CLI does not authorize carrier contact, payment action, settlement acceptance, or money movement. Human review, external-action authorization, and settlement remain separate downstream stages.
