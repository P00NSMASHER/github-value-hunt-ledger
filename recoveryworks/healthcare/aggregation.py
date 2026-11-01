"""One economic loss owns one amount across procurement and AP/credit branches."""
from dataclasses import replace
from .models import AuditResult, CanonicalBatch, Hold


def combine_results(results: tuple[AuditResult, ...], batch: CanonicalBatch) -> AuditResult:
    if type(results) is not tuple or not results or type(batch) is not CanonicalBatch:
        raise ValueError('INVALID_RESULT_COMBINATION')
    grouped = {}
    holds = []
    for r in results:
        if (r.source_hash != batch.import_batch.original_hash or
                r.normalized_hash != batch.import_batch.normalized_hash or
                r.synthetic != batch.scope.synthetic):
            raise ValueError('RESULT_SCOPE_MISMATCH')
        holds.extend(r.holds)
        for f in r.findings:
            if f.scope not in batch.scope.scopes:
                raise ValueError('FINDING_SCOPE_MISMATCH')
            grouped.setdefault(f.economic_loss_id, []).append(f)
    output = []
    for loss, candidates in sorted(grouped.items()):
        if len({(x.scope, x.invoice_line_id, x.billed_cents) for x in candidates}) != 1:
            holds.append(Hold('ECONOMIC_LOSS_COLLISION', loss))
            continue
        # Final AP result is a refinement of procurement only, not an additional
        # recovery. It cannot overwrite a different procurement price truth.
        base_price = candidates[0].expected_cents + candidates[0].return_entitlement_cents
        if any((x.expected_cents + x.return_entitlement_cents) != base_price for x in candidates):
            holds.append(Hold('CONFLICTING_FINANCIAL_BASELINE', loss))
            continue
        winner = sorted(candidates, key=lambda x: (len(x.trace), x.paid_cents,
                                                 len(x.evidence)))[-1]
        if any(x.remaining_candidate_cents not in (0, winner.remaining_candidate_cents)
               for x in candidates):
            holds.append(Hold('CONFLICTING_RECOVERY_AMOUNTS', loss))
            continue
        output.append(winner)
    # A held line in a later pass cannot be resurrected from an earlier pass.
    blocked_ids = {h.record_id for h in holds}
    output = [f for f in output if f.invoice_line_id not in blocked_ids]
    holds = list({(h.code, h.record_id, h.evidence): h for h in holds}.values())
    holds.sort(key=lambda x: (x.code, x.record_id))
    return AuditResult(tuple(output), tuple(holds), len(output),
                       max(x.unassessed_lines for x in results),
                       max(x.skipped_cancelled_lines for x in results), batch.scope.synthetic,
                       batch.import_batch.original_hash, batch.import_batch.normalized_hash)
