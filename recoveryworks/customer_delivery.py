"""Portable customer reports: exact cents, currency separation and evidence references."""
from __future__ import annotations
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json


def csv_cell(value):
    text = str(value)
    # Spreadsheet programs may evaluate formulas after whitespace/control prefixes.
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


def build_delivery(state):
    cases = []
    totals = {}
    for record in state['cases']:
        currency = record['currency']
        bucket = totals.setdefault(currency, {'potential_cents': 0, 'net_received_cents': 0,
                                             'net_fee_cents': 0, 'remaining_cents': 0})
        # Rejected cases remain visible but are excluded from payable opportunity totals.
        if record['state'] != 'REJECTED':
            bucket['potential_cents'] += record['potential_cents']
            bucket['remaining_cents'] += record['remaining_cents']
        bucket['net_received_cents'] += record['recovered_cents']
        bucket['net_fee_cents'] += record['fee_cents']
        cases.append({key: record[key] for key in (
            'finding_id', 'branch', 'counterparty', 'reference', 'state', 'currency',
            'potential_cents', 'recovered_cents', 'fee_cents', 'remaining_cents',
            'hold', 'record_hash', 'evidence')})
    payload = {
        'schema': 1, 'client_id': state['client_id'], 'simulation': state['simulation'],
        'generated_at': datetime.now(timezone.utc).isoformat(), 'journal_head': state['head_hash'],
        'purpose': 'Customer audit progress report; not a claim submission, invoice or bank attestation.',
        'commercially_validated': False,
        # The local ledger records operator-entered receipt events. No trusted
        # issuer/bank verifier is wired into this private workbench yet. Preserve
        # those provisional amounts for reconciliation, but NEVER export a
        # numeric independently verified realized-cash amount.
        'external_cash_verification_status': 'NOT_VERIFIED',
        'independently_verified_realized_recovery_cents': None,
        'externally_verified_recovery_claim_approved': False,
        'totals_by_currency': totals, 'cases': cases,
        'intake_status': {branch: {'analysis_ready': item['analysis_ready'], 'blockers': item['blockers'],
                                 'scope_hash': item['record']['scope_hash'] if item['record'] else None,
                                 'scope': item['record']['scope'] if item['record'] else None}
                          for branch, item in state['onboarding'].items()},
        'notes': ['Potential is not recovered money. Holds and rejected cases require attention.',
                  'Net receipts and fees reflect reviewed ledger postings, not independently authenticated bank balances.',
                  'No bank/carrier issuer-verification integration exists; do not describe any displayed receipt as independently confirmed cash.',
                  'Different currencies are never combined or converted.',
                  'Source completeness and account/period scope rely on the recorded customer and reviewer attestations.']}
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    report_hash = hashlib.sha256(raw.encode()).hexdigest()
    fields = ('finding_id', 'branch', 'counterparty', 'reference', 'state', 'currency',
              'potential_cents', 'recovered_cents', 'fee_cents', 'remaining_cents', 'hold', 'record_hash')
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(('simulation', *fields))
    for record in cases:
        writer.writerow([str(state['simulation']).lower(), *(csv_cell(record[key] if record[key] is not None else '') for key in fields)])
    escape = lambda value: html.escape(str(value), quote=True)
    rows = ''.join('<tr>' + ''.join('<td>' + escape(record[key] if record[key] is not None else '') + '</td>' for key in fields) + '</tr>' for record in cases)
    summary = ''.join('<li>' + escape(currency) + ': potential ' + str(value['potential_cents']) +
                      '; net receipts ' + str(value['net_received_cents']) + '; net fees ' + str(value['net_fee_cents']) +
                      ' (all amounts in cents)</li>' for currency, value in sorted(totals.items()))
    document = ('<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
                '<title>RETALLY customer audit report</title><style>body{font:15px system-ui;margin:32px;color:#18342a}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:8px;text-align:left;overflow-wrap:anywhere}.scroll{overflow:auto}h1{color:#007653}@media print{body{margin:10px;font-size:9px}}</style>'
                '<h1>RETALLY customer audit report</h1><p>' + ('SIMULATION — synthetic records, no actual recoveries.' if state['simulation'] else 'PRIVATE — customer financial information.') +
                '</p><p><strong>Cash verification: NOT VERIFIED.</strong> No displayed receipt is independently authenticated by a bank or carrier; verified realized customer cash is not established.</p><p>Client: ' + escape(state['client_id']) + '</p><p>' + escape(payload['purpose']) +
                '</p><ul>' + summary + '</ul><div class="scroll"><table><thead><tr>' +
                ''.join('<th>' + escape(key.replace('_', ' ')) + '</th>' for key in fields) +
                '</tr></thead><tbody>' + rows + '</tbody></table></div><ul>' +
                ''.join('<li>' + escape(note) + '</li>' for note in payload['notes']) +
                '</ul><p>Canonical JSON SHA-256: ' + report_hash + '</p><p>Journal head: ' + escape(state['head_hash']) + '</p></html>')
    return {'json': raw, 'csv': output.getvalue(), 'html': document, 'sha256': report_hash,
            'simulation': state['simulation']}
