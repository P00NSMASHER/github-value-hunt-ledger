# Audit Result Bundle

A successful Freight Recovery audit workflow can be packaged into one deterministic ZIP for use inside the approved customer-processing environment.

The bundle contains:

- workflow summary JSON + Markdown;
- canonical audit-run manifest;
- frozen truth manifest;
- all deterministic derivations;
- normalized charge rows;
- normalized rule rows;
- review queue;
- deterministic review routing;
- evidence-remediation plan JSON + Markdown;
- reviewer work packet JSON + Markdown;
- a bundle manifest with SHA-256 and byte size for every entry.

## Data boundary

The bundle explicitly declares:

- `customer_data_included=true`;
- `raw_source_files_included=false`.

It contains normalized/derived customer audit evidence and therefore must remain inside an approved customer-processing environment. It deliberately does **not** embed the raw invoice export, raw rate CSV, original rate confirmation, contract, settlement record, or other source document bytes.

The normalized objects retain hashes that point back to those source files.

## State boundary

Only successful `CLEAN` or `REVIEW_REQUIRED` workflows can produce an audit-result bundle. A `BLOCKED` workflow cannot issue one.

The included `review-routing.json` states which exact review-case hashes are buyer-review-ready and which require evidence remediation. Any remediation case carries `rerun_required=true`; it is not silently promoted into the buyer-review path.

The included `remediation-plan.json` and `remediation-plan.md` state the evidence category required for every remediation case and the exact rerun action. They explicitly forbid editing/promoting prior findings in place.

The bundle stops at the pre-human-decision audit state. It does not prove:

- buyer confirmation;
- carrier contact or dispute submission;
- settlement acceptance;
- issued credit/refund/remittance;
- realized savings.

Those remain separately authorized downstream proof states.

## Determinism

ZIP timestamps, entry ordering, JSON serialization, and the bundle manifest are deterministic. Identical workflow proof objects produce identical bundle bytes and SHA-256.

Verification rebuilds the expected entries from the workflow result and rejects:

- missing/duplicate entries;
- altered manifest metadata;
- altered entry bytes;
- wrong entry hashes or sizes;
- a bundle from a different audit run.
