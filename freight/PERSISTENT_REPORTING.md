# Persistent settlement reporting

The persistent reporting adapter connects the append-only settlement store to the
existing pilot metrics. It calculates recovery after applied returns and reversals,
and preserves the exact snapshot used for every total. This is a tested internal
reference implementation. It does not establish a deployed customer-data service
or prove that any customer has paid or recovered money.

## Report path

Use `build_persistent_pilot_report` in `freight/settlement_report.py` for reports
derived from `SettlementStore`. The original in-memory `RecoveryLedger` remains
available for isolated proof examples; it does not represent later returns.

`pilot_reporting.build_pilot_metrics` now accepts the small
`RecoveryCertificateSource` protocol: buyer/business-unit fields and a
`certificate(finding_id)` reader. Existing `RecoveryLedger` callers remain
compatible. The new persistent adapter implements the same certificate interface
without replaying net totals into mutable in-memory settlement events.

```python
from freight.settlement_report import (
    ClaimFindingBinding,
    assert_report_current,
    build_persistent_pilot_report,
    render_persistent_markdown,
)

# Existing authorized operational objects: truth, incumbent, store, reviews.
# Explicitly select and review each claim-to-finding binding.
bindings = (
    ClaimFindingBinding(claim_id, finding.finding_id, finding.proof_hash),
)
report = build_persistent_pilot_report(truth, incumbent, store, bindings, reviews)
assert_report_current(report, store)
markdown = render_persistent_markdown(report)
```

The caller must first resolve the current engagement and its report/data-processing
authorization. A report function cannot grant authorization, activate an engagement,
send a dispute, issue an invoice or record an actual customer outcome.

## Exact finding and claim boundary

Each included claim must bind to one positive, authority-validated finding from the
frozen truth. The adapter verifies finding/truth/incumbent hashes and rejects:

- a different buyer or business unit;
- a stale finding proof, unknown claim/finding, duplicate binding or omitted claim
  whose source already refers to the current frozen truth;
- a claim whose `source_hash` is not that exact finding's `proof_hash`;
- a claim reference other than the frozen invoice ID, payer other than its carrier,
  payee other than its customer, or currency mismatch;
- a claim amount above its validated finding capacity;
- incumbent claims that have not been marked fee-disqualified;
- a bound finding explicitly reviewed as unresolved or false positive.

This first version supports one claim per finding, including multiple payments on
that claim. Normalize carrier/customer identities through a reviewed upstream step.
Do not silently guess aliases or rewrite immutable legacy claims to make them pass.
Any migration from older claim-source conventions needs its own reviewed mapping
and migration record before that data can use this adapter.

Claims belonging to other frozen populations in the same buyer scope are not
counted. Standalone claim amounts never become validated finding dollars. The
entire scoped snapshot is retained so the selection is inspectable. Non-USD reports
are rejected by the existing USD metrics; no foreign currency is relabeled as dollars.

## Reversals and provenance

`SettlementStore.report_snapshot_json()` reads all six scoped tables in one SQLite
read transaction. Concurrent writes cannot mix pre-return allocations with a
post-return row set. It makes no writes and does not allocate or apply returns.

For each allocation, realized recovery is allocated cents minus reversal-edge cents.
Fee eligibility follows the same net amount only when the original claim is
fee-eligible. Fully returned payments contribute zero; a later replacement payment
contributes only its own current net amount. A known but unresolved counter-event
blocks a report if it could change any selected settlement's live allocation.
Ambiguous partial batch returns therefore cannot leave an optimistic recovery total.

The result includes:

- the unchanged pilot financial/review metrics;
- per-finding recovery certificates;
- truth, population, incumbent output, bindings and reviews hashes;
- the settlement snapshot hash and complete snapshot JSON;
- a report hash over those inputs, certificates and metrics.

Keep the full snapshot in the approved operational data store with its report and
audit-issued timestamp. It can contain customer rows and must not be copied into
Hunter, public Sites, research outcomes or the public website. Customer Markdown
contains financial totals and provenance hashes, not the raw snapshot rows.

Recheck `assert_report_current` immediately before using a report as current. A new
event requires regeneration and review; an old report remains a historical snapshot.
For a workflow that was approved against a known snapshot, pass
`expected_snapshot_hash` when rebuilding to reject a changed database state. This
is an optimistic freshness check, not a lock spanning a later send or payment action.

Hashes provide deterministic binding and change detection. They do not independently
authenticate the bank/carrier evidence, timestamp it, or replace the current
engagement's approved truth and review process.

Validated and challenger-only totals describe the frozen truth. Review dispositions
are shown separately; they do not silently rewrite that historical truth. If a
review changes a finding's validity, approve a new truth and rebuild the report.
An explicitly unresolved or false-positive finding cannot support a bound claim.

## Validation and remaining boundary

Synthetic tests cover full and partial returns, replacement payments, incumbent
fees, ambiguous batch returns, wrong proof/parties/currency, stale snapshots,
cross-buyer isolation and a concurrent writer during a snapshot read. Existing
settlement-store and pilot-report tests remain passing.

The end-to-end synthetic rehearsal now builds its report directly from the
persistent store. It records $45.00 realized/$20.00 fee-eligible before a $5.00
return, rejects reuse of that old report, and then reports $40.00 realized/$15.00
fee-eligible with new snapshot/report hashes. These are deliberately synthetic
amounts, not customer results. The report tests run in Freight CI, and the new
adapter is included in deterministic release provenance.

Deployment controls remain separate: verified operational storage, identity and
access enforcement, source-evidence ingestion, retention/deletion, backups,
monitoring and active buyer authorization are still required before processing
confidential customer records. No deployment/security gate is closed by this code.
