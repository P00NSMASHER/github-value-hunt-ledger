"""Read-only evidence exports. Reports are never supplier demands or cash attestations."""
import csv
import io
import json
from dataclasses import asdict
from .models import AuditResult, CanonicalBatch


def build_report(result: AuditResult, batch: CanonicalBatch) -> dict:
    if type(result) is not AuditResult or type(batch) is not CanonicalBatch:
        raise ValueError('INVALID_REPORT_INPUT')
    if (result.source_hash != batch.import_batch.original_hash or
            result.normalized_hash != batch.import_batch.normalized_hash or
            result.synthetic != batch.scope.synthetic):
        raise ValueError('REPORT_EVIDENCE_SCOPE_MISMATCH')
    rows = [
        {'economic_loss_id': f.economic_loss_id, 'scope': asdict(f.scope),
         'invoice_line_id': f.invoice_line_id, 'status': f.status,
         'billed_cents': f.billed_cents, 'expected_cents': f.expected_cents,
         'paid_cents': f.paid_cents, 'gross_price_variance_cents': f.gross_price_variance_cents,
         'return_entitlement_cents': f.return_entitlement_cents,
         'payment_above_invoice_cents': f.payment_above_invoice_cents,
         'remaining_candidate_cents': f.remaining_candidate_cents,
         'issued_unapplied_cents': f.issued_unapplied_cents,
         'net_issued_credit_cents': f.net_issued_credit_cents,
         'applied_credit_cents': f.applied_credit_cents,
         'refunded_credit_cents': f.refunded_credit_cents,
         'unpaid_discrepancy_cents': f.unpaid_discrepancy_cents,
         'verified_realized_cents': 0,
         'simulated_new_realized_cents': f.simulated_new_realized_cents if result.synthetic else 0,
         'evidence': [asdict(x) for x in f.evidence],
         'trace': [{'step': k, 'value': v} for k, v in f.trace]}
        for f in result.findings
    ]
    import_batch = batch.import_batch
    return {
        'schema': 'retally_healthcare_review_v1',
        'environment': 'SYNTHETIC' if result.synthetic else 'NONPRODUCTION_UNVERIFIED',
        'report_status': 'INCOMPLETE' if result.holds or result.unassessed_lines or not import_batch.complete
                         else 'REVIEW_ONLY',
        'not_a_claim': True,
        'verified_realized_cents': 0,
        'currency': 'USD',
        'as_of': batch.scope.as_of,
        'audit_start': batch.scope.audit_start,
        'source_hash': import_batch.original_hash,
        'normalized_hash': import_batch.normalized_hash,
        'population': {
            'declared': import_batch.declared_rows, 'observed': import_batch.observed_rows,
            'accepted': import_batch.accepted_rows, 'rejected': import_batch.rejected_rows,
            'missing': import_batch.missing_rows, 'deduplicated': batch.duplicate_rows,
            'assessed_invoice_lines': result.assessed_lines,
            'unassessed_invoice_lines': result.unassessed_lines,
            'skipped_cancelled_invoice_lines': result.skipped_cancelled_lines,
        },
        'review_candidate_cents': result.remaining_candidate_cents,
        'holds': [{'code': h.code, 'record_id': h.record_id,
                   'evidence': [asdict(x) for x in h.evidence]} for h in result.holds],
        'findings': rows,
    }


def _sheet_safe(value) -> str:
    string = str(value)
    if string.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
        return "'" + string
    return string


def export_report(report: dict, format: str = 'json') -> bytes:
    if type(report) is not dict or report.get('schema') != 'retally_healthcare_review_v1':
        raise ValueError('INVALID_REPORT')
    if format == 'json':
        return (json.dumps(report, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
    if format == 'csv':
        target = io.StringIO(newline='')
        writer = csv.writer(target, lineterminator='\r\n')
        header = ['economic_loss_id', 'buyer_id', 'facility_id', 'supplier_id',
                  'account_id', 'invoice_line_id', 'currency', 'status',
                  'billed_cents', 'expected_cents', 'paid_cents',
                  'review_candidate_cents', 'issued_unapplied_cents',
                  'verified_realized_cents', 'source_locators']
        writer.writerow(header)
        for row in report.get('findings', []):
            scope = row['scope']
            cells = [row['economic_loss_id'], scope['buyer_id'], scope['facility_id'],
                     scope['supplier_id'], scope['account_id'], row['invoice_line_id'],
                     scope['currency'], row['status'], row['billed_cents'],
                     row['expected_cents'], row['paid_cents'], row['remaining_candidate_cents'],
                     row['issued_unapplied_cents'], row['verified_realized_cents'],
                     ';'.join(x['locator'] for x in row['evidence'])]
            writer.writerow([_sheet_safe(x) for x in cells])
        return target.getvalue().encode('utf-8')
    raise ValueError('UNSUPPORTED_REPORT_FORMAT')
