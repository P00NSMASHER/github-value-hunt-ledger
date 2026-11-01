"""Run a strictly synthetic healthcare purchasing-recovery example, without I/O."""
import hashlib
import json
from dataclasses import asdict
from .ingestion import import_json, validate_batch
from .engine import run_audit
from .models import (
    ApprovedScope, ScopeKey, SourceRef, ProductIdentity, ContractAuthority,
    InvoiceLine, ReceiptEvent, ReceiptAllocation, PaymentEvent, PaymentAllocation,
    CreditEvent, RuleSetVersion,
)
from .reporting import build_report, export_report


def synthetic_example() -> dict:
    scope = ScopeKey('synthetic-client', 'synthetic-buyer', 'synthetic-facility',
                     'synthetic-supplier', 'synthetic-account', 'USD')
    source = SourceRef('1' * 64, 'synthetic-fixture-only', 'synthetic')
    items = {
        'products': [ProductIdentity('product-1', scope, source, 'EXAMPLE-SUPPLY', '2026-01-01')],
        'contracts': [ContractAuthority('contract-1', scope, source, 'product-1',
                                         'CASE', '28', 'ORDER_DATE', '2026-01-01')],
        'invoices': [InvoiceLine('line-1', scope, source, 'INV-SYNTHETIC-1', 'product-1',
                                 'po-1', '100', 'CASE', 310000, '2026-03-15', '2026-03-01')],
        'receipts': [ReceiptEvent('receipt-1', scope, source, 'product-1',
                                  'po-1', '100', 'CASE', '2026-03-14')],
        'receipt_allocations': [ReceiptAllocation('ra-1', scope, source, 'receipt-1', 'line-1', '100')],
        'payments': [PaymentEvent('pay-1', scope, source, 'bank-ref-1', 310000, '2026-03-20')],
        'payment_allocations': [PaymentAllocation('pa-1', scope, source, 'pay-1', 'line-1', 310000)],
        'credits': [
            CreditEvent('credit-issued', scope, source, 'line-1', 'memo-1',
                        10000, '2026-03-22', 'ISSUED'),
            CreditEvent('credit-applied', scope, source, 'line-1', 'memo-1',
                        10000, '2026-03-25', 'APPLIED'),
        ],
    }
    payload = {'schema_version': 1}
    for name, rows in items.items():
        payload[name] = [asdict(x) for x in rows]
    raw = json.dumps(payload, sort_keys=True).encode('utf-8')
    approved = ApprovedScope((scope,), hashlib.sha256(raw).hexdigest(),
                             tuple(sorted((k, len(v)) for k, v in items.items())),
                             '2026-01-01', '2026-12-31', '2026-04-30', '2026-03-01', True)
    batch = validate_batch(import_json(raw, approved), approved)
    result = run_audit(batch, RuleSetVersion('0' * 40, '0' * 64, ('SYNTHETIC_FIXED_PACK',)))
    return build_report(result, batch)


if __name__ == '__main__':
    print(export_report(synthetic_example()).decode('utf-8'), end='')
