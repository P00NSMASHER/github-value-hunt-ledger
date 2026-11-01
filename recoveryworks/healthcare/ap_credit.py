"""Disbursement and credit reconciliation; never equates issuance with realized cash."""
from collections import defaultdict
from dataclasses import replace

from .models import (
    AuditResult, CanonicalBatch, CreditEvent, Hold, InvoiceLine, PaymentAllocation,
    PaymentEvent, ReturnEntitlement, RuleSetVersion,
)
from .procurement import audit_procurement, _refs

_CREDIT_BASE = {'ISSUED', 'APPLIED', 'REFUNDED'}
_CREDIT_KINDS = _CREDIT_BASE | {'REVERSAL_' + x for x in _CREDIT_BASE}


def _payment_ledger(batch: CanonicalBatch):
    invoices = {(x.scope, x.id): x for x in batch.of_type(InvoiceLine)}
    payments = {(x.scope, x.id): x for x in batch.of_type(PaymentEvent)}
    event_allocs = defaultdict(list)
    line_ledger = defaultdict(int)
    line_sources = defaultdict(list)
    holds = []
    blocked = set()

    for a in batch.of_type(PaymentAllocation):
        pk, ik = (a.scope, a.payment_id), (a.scope, a.invoice_line_id)
        if ik in invoices and invoices[ik].status != 'ACTIVE':
            holds.append(Hold('PAYMENT_ON_INACTIVE_INVOICE', a.invoice_line_id, (a.source,)))
            blocked.add(ik)
        if pk not in payments or ik not in invoices:
            holds.append(Hold('ORPHAN_PAYMENT_ALLOCATION', a.id, (a.source,)))
            if ik in invoices:
                blocked.add(ik)
            continue
        if a.amount_cents <= 0:
            holds.append(Hold('NONPOSITIVE_PAYMENT_ALLOCATION', a.invoice_line_id, (a.source,)))
            blocked.add(ik)
            continue
        event_allocs[pk].append(a)

    # A single bank identifier may fund several invoices, but cannot be silently
    # interpreted as two distinct payments when the export has multiple rows.
    references = defaultdict(list)
    for p in payments.values():
        if p.kind == 'PAYMENT':
            references[(p.scope, p.external_reference)].append(p)
    for group in references.values():
        if len(group) > 1:
            for p in group:
                holds.append(Hold('REUSED_PAYMENT_REFERENCE', p.id, (p.source,)))
                blocked.update((a.scope, a.invoice_line_id) for a in event_allocs.get((p.scope, p.id), ()))

    originals = defaultdict(list)
    reversals = defaultdict(list)
    for p in payments.values():
        pk = (p.scope, p.id)
        allocations = event_allocs.get(pk, ())
        if p.kind not in ('PAYMENT', 'REVERSAL') or p.amount_cents <= 0 or p.event_date > batch.scope.as_of:
            holds.append(Hold('INVALID_PAYMENT_EVENT', p.id, (p.source,)))
            blocked.update((a.scope, a.invoice_line_id) for a in allocations)
            continue
        if p.kind == 'PAYMENT' and p.reversal_of_id is not None:
            holds.append(Hold('INVALID_PAYMENT_REVERSAL_LINK', p.id, (p.source,)))
            blocked.update((a.scope, a.invoice_line_id) for a in allocations)
            continue
        if sum(a.amount_cents for a in allocations) != p.amount_cents:
            holds.append(Hold('INCOMPLETE_PAYMENT_ALLOCATION', p.id, (p.source,)))
            blocked.update((a.scope, a.invoice_line_id) for a in allocations)
            continue
        if p.kind == 'PAYMENT':
            originals[pk] = allocations
        else:
            if p.reversal_of_id is None:
                holds.append(Hold('MISSING_PAYMENT_REVERSAL_ORIGINAL', p.id, (p.source,)))
                blocked.update((a.scope, a.invoice_line_id) for a in allocations)
                continue
            reversals[(p.scope, p.reversal_of_id)].append((p, allocations))

    for key, reversed_events in reversals.items():
        original = payments.get(key)
        original_allocs = originals.get(key, ())
        original_line_totals = defaultdict(int)
        reversed_line_totals = defaultdict(int)
        for alloc in original_allocs:
            original_line_totals[(alloc.scope, alloc.invoice_line_id)] += alloc.amount_cents
        for rev, rev_allocs in reversed_events:
            if original is None or original.kind != 'PAYMENT' or rev.event_date < original.event_date:
                holds.append(Hold('INVALID_PAYMENT_REVERSAL_ORIGINAL', rev.id, (rev.source,)))
                blocked.update((a.scope, a.invoice_line_id) for a in rev_allocs)
            for a in rev_allocs:
                reversed_line_totals[(a.scope, a.invoice_line_id)] += a.amount_cents
        if sum(reversed_line_totals.values()) > (original.amount_cents if original else 0) or any(
            n > original_line_totals[k] for k, n in reversed_line_totals.items()
        ):
            for rev, allocs in reversed_events:
                holds.append(Hold('PAYMENT_OVER_REVERSAL', rev.id, (rev.source,)))
                blocked.update((a.scope, a.invoice_line_id) for a in allocs)
            blocked.update(original_line_totals)

    for key, allocs in originals.items():
        payment = payments[key]
        for a in allocs:
            ik = (a.scope, a.invoice_line_id)
            line_ledger[ik] += a.amount_cents
            line_sources[ik].extend((payment.source, a.source))
    for key, reversed_events in reversals.items():
        for rev, allocs in reversed_events:
            for a in allocs:
                ik = (a.scope, a.invoice_line_id)
                line_ledger[ik] -= a.amount_cents
                line_sources[ik].extend((rev.source, a.source))

    for ik, net in line_ledger.items():
        if net < 0:
            holds.append(Hold('NEGATIVE_NET_PAYMENT', ik[1]))
            blocked.add(ik)
    return line_ledger, line_sources, holds, blocked


def _credits(batch: CanonicalBatch):
    invoices = {(x.scope, x.id): x for x in batch.of_type(InvoiceLine)}
    groups = defaultdict(list)
    holds = []
    blocked = set()
    for c in batch.of_type(CreditEvent):
        ik = (c.scope, c.invoice_line_id)
        if ik not in invoices:
            holds.append(Hold('ORPHAN_CREDIT', c.id, (c.source,)))
            continue
        if c.kind not in _CREDIT_KINDS or c.amount_cents <= 0 or c.event_date > batch.scope.as_of:
            holds.append(Hold('INVALID_CREDIT_EVENT', c.invoice_line_id, (c.source,)))
            blocked.add(ik)
            continue
        groups[(c.scope, c.invoice_line_id, c.credit_id)].append(c)

    ledger = defaultdict(lambda: {'ISSUED': 0, 'APPLIED': 0, 'REFUNDED': 0, 'NEW_REALIZED': 0, 'SOURCES': []})
    for (scope, invoice_line_id, memo_id), events in groups.items():
        ik = (scope, invoice_line_id)
        # Same memo line reported with a different row/event ID is ambiguous,
        # not a second credit earned or applied.
        duplicate_fingerprints = set()
        for e in events:
            signature = (e.kind, e.amount_cents, e.event_date, e.reversal_of_id, e.source)
            if signature in duplicate_fingerprints:
                holds.append(Hold('DUPLICATE_CREDIT_EVENT', invoice_line_id, (e.source,)))
                blocked.add(ik)
            duplicate_fingerprints.add(signature)
        event_by_id = {x.id: x for x in events}
        corrected = defaultdict(int)
        reversals = defaultdict(int)
        for e in events:
            if e.kind.startswith('REVERSAL_'):
                prior = event_by_id.get(e.reversal_of_id)
                base_kind = e.kind.removeprefix('REVERSAL_')
                if prior is None or prior.kind != base_kind or prior.event_date > e.event_date:
                    holds.append(Hold('INVALID_CREDIT_REVERSAL', invoice_line_id, (e.source,)))
                    blocked.add(ik)
                    continue
                reversals[prior.id] += e.amount_cents
            elif e.reversal_of_id is not None:
                holds.append(Hold('INVALID_CREDIT_REVERSAL_LINK', invoice_line_id, (e.source,)))
                blocked.add(ik)
            else:
                corrected[e.kind] += e.amount_cents
        for prior_id, reversed_cents in reversals.items():
            prior = event_by_id[prior_id]
            if reversed_cents > prior.amount_cents:
                holds.append(Hold('CREDIT_OVER_REVERSAL', invoice_line_id, (prior.source,)))
                blocked.add(ik)
            corrected[prior.kind] -= reversed_cents
        if (corrected['APPLIED'] or corrected['REFUNDED']) and not corrected['ISSUED']:
            holds.append(Hold('CREDIT_WITHOUT_ISSUANCE', invoice_line_id, _refs(*(x.source for x in events))))
            blocked.add(ik)
        if corrected['APPLIED'] + corrected['REFUNDED'] > corrected['ISSUED']:
            holds.append(Hold('CREDIT_OVER_APPLIED', invoice_line_id, _refs(*(x.source for x in events))))
            blocked.add(ik)
        issue_dates = [e.event_date for e in events if e.kind == 'ISSUED']
        if issue_dates and any(e.event_date < min(issue_dates) for e in events
                               if e.kind in ('APPLIED', 'REFUNDED')):
            holds.append(Hold('CREDIT_DATE_ORDER', invoice_line_id, _refs(*(x.source for x in events))))
            blocked.add(ik)
        item = ledger[ik]
        for kind in _CREDIT_BASE:
            item[kind] += corrected[kind]
        if batch.scope.synthetic:
            # Only synthetic illustrations; issuer-authenticated recovered cash is always 0.
            item['NEW_REALIZED'] += sum(e.amount_cents for e in events
                                        if e.kind in ('APPLIED', 'REFUNDED') and
                                        e.event_date >= batch.scope.audit_start)
            item['NEW_REALIZED'] -= sum(e.amount_cents for e in events
                                        if e.kind in ('REVERSAL_APPLIED', 'REVERSAL_REFUNDED') and
                                        e.event_date >= batch.scope.audit_start)
        item['SOURCES'].extend(x.source for x in events)
    return ledger, holds, blocked


def _returns(batch: CanonicalBatch):
    invoices = {(x.scope, x.id): x for x in batch.of_type(InvoiceLine)}
    ledger = defaultdict(lambda: [0, []])
    holds = []
    blocked = set()
    fingerprints = set()
    for item in batch.of_type(ReturnEntitlement):
        ik = item.scope, item.invoice_line_id
        if ik not in invoices:
            holds.append(Hold('ORPHAN_RETURN', item.id, (item.source,)))
            continue
        if item.decision_date > batch.scope.as_of or item.restocking_cents > item.approved_gross_cents:
            holds.append(Hold('INVALID_RETURN_ENTITLEMENT', item.invoice_line_id, (item.source,)))
            blocked.add(ik)
            continue
        if not item.authority_source or not item.receipt_source or (item.notice_required and not item.notice_source):
            holds.append(Hold('RETURN_EVIDENCE_INCOMPLETE', item.invoice_line_id, (item.source,)))
            blocked.add(ik)
            continue
        fingerprint = (ik, item.source, item.authority_source)
        if fingerprint in fingerprints:
            holds.append(Hold('DUPLICATE_RETURN_ENTITLEMENT_SOURCE', item.invoice_line_id, (item.source,)))
            blocked.add(ik)
            continue
        fingerprints.add(fingerprint)
        ledger[ik][0] += item.approved_gross_cents - item.restocking_cents
        ledger[ik][1].extend((item.source, item.authority_source, item.receipt_source))
        if item.notice_source:
            ledger[ik][1].append(item.notice_source)
    return ledger, holds, blocked


def audit_ap_credit(batch: CanonicalBatch, rules: RuleSetVersion) -> AuditResult:
    primary = audit_procurement(batch, rules)
    # Cross-record failures (including payments on cancelled invoices) must be
    # visible even when there are no eligible purchasing findings.
    if batch.holds or not batch.import_batch.complete:
        return primary
    payments, payment_evidence, ph, pb = _payment_ledger(batch)
    credits, ch, cb = _credits(batch)
    returns, rh, rb = _returns(batch)
    holds = list(primary.holds) + ph + ch + rh
    blocked = pb | cb | rb
    findings = []
    for p in primary.findings:
        ik = (p.scope, p.invoice_line_id)
        if ik in blocked:
            continue
        returned, return_evidence = returns[ik]
        if returned > p.expected_cents:
            holds.append(Hold('RETURN_EXCEEDS_OBLIGATION', p.invoice_line_id, tuple(return_evidence)))
            continue
        expected = p.expected_cents - returned
        paid = payments[ik]
        if paid < 0:
            holds.append(Hold('NEGATIVE_NET_PAYMENT', p.invoice_line_id))
            continue
        exposure = max(0, paid - expected)
        credit = credits[ik]
        issued, applied, refunded = credit['ISSUED'], credit['APPLIED'], credit['REFUNDED']
        if applied + refunded > issued:
            holds.append(Hold('CREDIT_OVER_APPLIED', p.invoice_line_id, tuple(credit['SOURCES'])))
            continue
        remaining = max(0, exposure - applied - refunded)
        issued_unapplied = issued - applied - refunded
        unpaid = max(0, max(0, p.billed_cents - expected) - exposure)
        trace = p.trace + (
            ('return_entitlement_cents', str(returned)),
            ('expected_after_return_cents', str(expected)),
            ('net_payment_cents', str(paid)),
            ('funded_exposure_cents', str(exposure)),
            ('issued_credit_cents', str(issued)),
            ('applied_credit_cents', str(applied)),
            ('refunded_credit_cents', str(refunded)),
            ('remaining_candidate_cents', str(remaining)),
        )
        findings.append(replace(
            p, expected_cents=expected, paid_cents=paid, return_entitlement_cents=returned,
            payment_above_invoice_cents=max(0, paid - p.billed_cents),
            funded_exposure_cents=exposure,
            net_issued_credit_cents=issued, applied_credit_cents=applied,
            refunded_credit_cents=refunded, remaining_candidate_cents=remaining,
            issued_unapplied_cents=issued_unapplied, unpaid_discrepancy_cents=unpaid,
            simulated_new_realized_cents=max(0, credit['NEW_REALIZED']) if batch.scope.synthetic else 0,
            evidence=_refs(*p.evidence, *payment_evidence[ik], *credit['SOURCES'], *return_evidence),
            trace=trace,
        ))
    holds.sort(key=lambda x: (x.code, x.record_id))
    return AuditResult(tuple(findings), tuple(holds), len(findings),
                       primary.unassessed_lines + len(primary.findings) - len(findings),
                       primary.skipped_cancelled_lines, batch.scope.synthetic,
                       batch.import_batch.original_hash, batch.import_batch.normalized_hash)
