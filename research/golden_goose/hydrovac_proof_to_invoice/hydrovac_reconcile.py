"""Offline, read-only synthetic hydrovac proof-to-invoice reconciliation.

NOT an invoice generator, collection entitlement, customer prospecting program,
legal determination or proof that a customer actually owes a balance.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation


def _day(s):
    if not isinstance(s, str):
        raise ValueError('Date must be an ISO string')
    v = date.fromisoformat(s)
    if v.isoformat() != s:
        raise ValueError('Date must be canonical YYYY-MM-DD')
    return v


def _d(v):
    if isinstance(v, bool):
        raise ValueError('Boolean not a number')
    z = Decimal(str(v))
    if not z.is_finite() or z < 0:
        raise ValueError('Non-finite or negative monetary quantity')
    return z


def inspect(job, *, as_of='2026-10-29', grace_days=30):
    """Fail closed, with only review/clear results. `gross_variance_usd` is *not collectible*."""
    ident = str(job.get('job_id', 'UNKNOWN'))

    def verdict(code, value='0.00'):
        return {'job_id': ident, 'status': code, 'gross_variance_usd': str(Decimal(value).quantize(Decimal('0.01'))), 'collectible_usd': None}

    try:
        today = _day(as_of)
        work = _day(job['service_date'])
        if grace_days < 0 or isinstance(grace_days, bool) or not isinstance(grace_days, int):
            return verdict('REVIEW_INVALID_GRACE')
        if work > today:
            return verdict('REVIEW_FUTURE_EVIDENCE')
        all_invoices = job.get('invoices', [])
        if not isinstance(all_invoices, list):
            return verdict('REVIEW_BAD_INVOICES')
        if any(_day(x['issued_on']) > today for x in all_invoices):
            return verdict('REVIEW_FUTURE_EVIDENCE')
        ids = [x['invoice_line_id'] for x in all_invoices]
        if len(ids) != len(set(ids)):
            return verdict('REVIEW_DUPLICATE_INVOICE_LINE')
        if job.get('approved_at') and _day(job['approved_at']) > today:
            return verdict('REVIEW_FUTURE_EVIDENCE')
        card = job.get('rate_card')
        if card and card.get('effective_on') and _day(card['effective_on']) > today:
            return verdict('REVIEW_FUTURE_EVIDENCE')
        if job.get('waiver'):
            return verdict('REVIEW_WAIVER')
        if job.get('credit'):
            return verdict('REVIEW_EXISTING_CREDIT')
        if job.get('scope_dispute'):
            return verdict('REVIEW_SCOPE_DISPUTE')
        if not job.get('approved_at') or not job.get('manifest_approved'):
            return verdict('REVIEW_PROOF')
        if not card or not card.get('signed') or not card.get('effective_on'):
            return verdict('REVIEW_RATE_AUTHORITY')
        if _day(card['effective_on']) > work:
            return verdict('REVIEW_RATE_AUTHORITY')
        rate = _d(card['hourly_rate'])
        dump = _d(card['dump_fee'])
        expected_hours = _d(job['approved_billable_hours'])
        expected_dumps = _d(job['approved_dump_loads'])
        if (today - work).days < grace_days:
            return verdict('REVIEW_WITHIN_GRACE')
        issued = [x for x in all_invoices if x['state'] == 'ISSUED']
        if not issued and all_invoices:
            return verdict('REVIEW_DRAFT_ONLY')
        expected = expected_hours * rate + expected_dumps * dump
        if not issued:
            return verdict('POTENTIAL_UNINVOICED_JOB', expected)
        actual_hours = sum((_d(x['hours_qty']) for x in issued), Decimal(0))
        actual_dumps = sum((_d(x['dump_qty']) for x in issued), Decimal(0))
        if actual_hours > expected_hours or actual_dumps > expected_dumps:
            return verdict('REVIEW_OVERBILLING_OR_RECONCILIATION')
        diff = (expected_hours - actual_hours) * rate + (expected_dumps - actual_dumps) * dump
        if diff:
            if actual_hours < expected_hours and actual_dumps < expected_dumps:
                code = 'POTENTIAL_MULTIPLE_COMPONENT_GAP'
            elif actual_hours < expected_hours:
                code = 'POTENTIAL_HOURS_GAP'
            else:
                code = 'POTENTIAL_DISPOSAL_GAP'
            return verdict(code, diff)
        return verdict('CLEAR_RECONCILED')
    except (ValueError, KeyError, TypeError, ArithmeticError, InvalidOperation, OverflowError):
        return verdict('REVIEW_INVALID_INPUT')


def summarize(jobs, *, as_of='2026-10-29'):
    results = [inspect(j, as_of=as_of) for j in jobs]
    candidate = [x for x in results if x['status'].startswith('POTENTIAL_')]
    return {'total_jobs': len(jobs), 'candidate_discrepancies': len(candidate),
            'review_only': sum(x['status'].startswith('REVIEW_') for x in results),
            'clear': sum(x['status'] == 'CLEAR_RECONCILED' for x in results),
            'illustrative_candidate_gross_usd': str(sum((Decimal(x['gross_variance_usd']) for x in candidate), Decimal(0)).quantize(Decimal('0.01'))),
            'verified_collectible_usd': None, 'verified_customer_revenue_usd': 0,
            'rows': results}
