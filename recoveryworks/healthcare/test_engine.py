"""Independently specified synthetic contract, payment and credit outcomes."""
import hashlib
import json
import unittest
from dataclasses import asdict, replace
from decimal import Decimal

from recoveryworks.healthcare.models import (
    ScopeKey, SourceRef, ApprovedScope, ImportBatch, CanonicalBatch, InvoiceLine,
    ProductIdentity, ContractAuthority, PackConversion, ReceiptEvent, ReceiptAllocation,
    QuantityDecision, PaymentEvent, PaymentAllocation, CreditEvent, ReturnEntitlement,
)
from recoveryworks.healthcare.ingestion import import_json, validate_batch


SCOPE = ScopeKey('client-1', 'buyer-1', 'facility-1', 'supplier-1', 'acct-1', 'USD')
OTHER = ScopeKey('client-1', 'buyer-1', 'facility-2', 'supplier-1', 'acct-1', 'USD')
SOURCE = SourceRef('b' * 64, 'synthetic:1')


def fixture(*, billed=31000, contract_price='28', invoice_qty='10', invoice_unit='CASE',
            receipt_qty='10', receipt_unit='CASE', scope=SCOPE, paid=(31000,), credits=(),
            extra=(), invoice_date='2026-03-15', order_date='2026-03-01',
            receipt_date='2026-03-14', quantity_decisions=(), pack=()):
    records = [
        ProductIdentity('product-1', scope, SOURCE, 'GLOVE-100', '2026-01-01'),
        ContractAuthority('contract-1', scope, SOURCE, 'product-1', 'CASE', contract_price,
                          'ORDER_DATE', '2026-01-01'),
        InvoiceLine('invoice-line-1', scope, SOURCE, 'INV-123', 'product-1', 'po-1',
                    invoice_qty, invoice_unit, billed, invoice_date, order_date),
        ReceiptEvent('receipt-1', scope, SOURCE, 'product-1', 'po-1', receipt_qty,
                     receipt_unit, receipt_date),
        ReceiptAllocation('ra-1', scope, SOURCE, 'receipt-1', 'invoice-line-1', receipt_qty),
    ]
    for i, amount in enumerate(paid, 1):
        records.extend([
            PaymentEvent(f'pay-{i}', scope, SOURCE, f'bank-ref-{i}', amount, '2026-03-20'),
            PaymentAllocation(f'pa-{i}', scope, SOURCE, f'pay-{i}', 'invoice-line-1', amount),
        ])
    records.extend(credits)
    records.extend(extra)
    records.extend(quantity_decisions)
    records.extend(pack)
    return make_batch(records)


def make_batch(records, as_of='2026-04-30', audit_start='2026-03-10', scopes=(SCOPE, OTHER)):
    from recoveryworks.healthcare.models import TABLE_TYPES
    record_names = {cls: name for name, cls in TABLE_TYPES.items()}
    tables = {'schema_version': 1}
    for record in records:
        tables.setdefault(record_names[type(record)], []).append(asdict(record))
    if 'invoices' not in tables:
        tables['invoices'] = []
    data = json.dumps(tables, separators=(',', ':'), sort_keys=True).encode()
    counts = tuple(sorted((k, len(v)) for k, v in tables.items() if k != 'schema_version'))
    scope = ApprovedScope(scopes, hashlib.sha256(data).hexdigest(), counts,
                          '2026-01-01', '2026-12-31', as_of, audit_start, True)
    return validate_batch(import_json(data, scope), scope)


def run(batch):
    from recoveryworks.healthcare.engine import run_audit
    from recoveryworks.healthcare.models import RuleSetVersion
    return run_audit(batch, RuleSetVersion('a' * 40, 'b' * 64, ('fixed_pack_v1',)))


class EngineTests(unittest.TestCase):
    def one(self, batch):
        result = run(batch)
        self.assertEqual([x.code for x in result.holds], [], f'holds: {result.holds!r}')
        self.assertEqual(len(result.findings), 1)
        return result.findings[0], result

    def test_contract_price_and_full_payment(self):
        f, r = self.one(fixture())
        self.assertEqual((f.billed_cents, f.expected_cents, f.gross_price_variance_cents),
                         (31000, 28000, 3000))
        self.assertEqual((f.paid_cents, f.remaining_candidate_cents, f.unpaid_discrepancy_cents),
                         (31000, 3000, 0))
        self.assertEqual(r.verified_realized_cents, 0)
        self.assertEqual(f.status, 'REVIEW')
        self.assertTrue(f.evidence)
        self.assertTrue(f.trace)

    def test_unpaid_overcharge_is_not_recovered_or_funded(self):
        f, _ = self.one(fixture(paid=()))
        self.assertEqual((f.gross_price_variance_cents, f.funded_exposure_cents,
                          f.remaining_candidate_cents, f.unpaid_discrepancy_cents), (3000, 0, 0, 3000))

    def test_split_payments_are_not_duplicates(self):
        f, _ = self.one(fixture(billed=10000, contract_price='100', invoice_qty='1',
                                 receipt_qty='1', paid=(4000, 6000)))
        self.assertEqual(f.payment_above_invoice_cents, 0)
        self.assertEqual(f.remaining_candidate_cents, 0)

    def test_true_double_payment_is_one_candidate(self):
        f, _ = self.one(fixture(billed=10000, contract_price='100', invoice_qty='1',
                                 receipt_qty='1', paid=(10000, 10000)))
        self.assertEqual(f.paid_cents, 20000)
        self.assertEqual(f.payment_above_invoice_cents, 10000)
        self.assertEqual(f.remaining_candidate_cents, 10000)

    def test_repeated_payment_export_same_id_deduplicates(self):
        b = fixture(billed=10000, contract_price='100', invoice_qty='1',
                    receipt_qty='1', paid=(10000,))
        records = tuple(b.records) + tuple(x for x in b.records if isinstance(x, (PaymentEvent, PaymentAllocation)))
        f, _ = self.one(make_batch(records))
        self.assertEqual(f.paid_cents, 10000)

    def test_reused_bank_payment_reference_requires_hold(self):
        b = fixture(billed=10000, contract_price='100', invoice_qty='1', receipt_qty='1', paid=(10000,))
        records = list(b.records)
        records.extend([
            PaymentEvent('pay-2', SCOPE, SOURCE, 'bank-ref-1', 10000, '2026-03-22'),
            PaymentAllocation('pa-2', SCOPE, SOURCE, 'pay-2', 'invoice-line-1', 10000),
        ])
        result = run(make_batch(records))
        self.assertIn('REUSED_PAYMENT_REFERENCE', {h.code for h in result.holds})
        self.assertEqual(result.remaining_candidate_cents, 0)

    def test_payment_reversal_reduces_exposure(self):
        b = fixture(billed=10000, contract_price='100', invoice_qty='1', receipt_qty='1', paid=(10000, 10000))
        records = list(b.records) + [
            PaymentEvent('reversal-1', SCOPE, SOURCE, 'bank-reversal-1', 10000, '2026-03-26', 'REVERSAL', 'pay-2'),
            PaymentAllocation('rev-pa-1', SCOPE, SOURCE, 'reversal-1', 'invoice-line-1', 10000),
        ]
        f, _ = self.one(make_batch(records))
        self.assertEqual((f.paid_cents, f.payment_above_invoice_cents), (10000, 0))

    def test_overreversal_is_held(self):
        b = fixture(billed=10000, contract_price='100', invoice_qty='1', receipt_qty='1', paid=(10000,))
        records = list(b.records) + [
            PaymentEvent('reversal-1', SCOPE, SOURCE, 'bank-reversal-1', 11000, '2026-03-26', 'REVERSAL', 'pay-1'),
            PaymentAllocation('rev-pa-1', SCOPE, SOURCE, 'reversal-1', 'invoice-line-1', 11000),
        ]
        r = run(make_batch(records))
        self.assertIn('PAYMENT_OVER_REVERSAL', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_partial_credit_applied_and_unapplied(self):
        credits = (
            CreditEvent('ci', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 5000, '2026-03-21', 'ISSUED'),
            CreditEvent('ca', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 3000, '2026-03-22', 'APPLIED'),
        )
        f, r = self.one(fixture(billed=10000, contract_price='100', invoice_qty='1',
                                receipt_qty='1', paid=(10000, 10000), credits=credits))
        self.assertEqual((f.net_issued_credit_cents, f.applied_credit_cents,
                          f.issued_unapplied_cents, f.remaining_candidate_cents), (5000, 3000, 2000, 7000))
        self.assertEqual(r.verified_realized_cents, 0)

    def test_completing_credit_application_does_not_double_count_issuance(self):
        credits = (
            CreditEvent('ci', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 5000, '2026-03-21', 'ISSUED'),
            CreditEvent('ca', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 3000, '2026-03-22', 'APPLIED'),
            CreditEvent('ca2', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 2000, '2026-03-26', 'APPLIED'),
        )
        f, _ = self.one(fixture(billed=10000, contract_price='100', invoice_qty='1',
                                 receipt_qty='1', paid=(10000, 10000), credits=credits))
        self.assertEqual((f.applied_credit_cents, f.issued_unapplied_cents, f.remaining_candidate_cents),
                         (5000, 0, 5000))

    def test_existing_credit_reduces_not_creates_recovery(self):
        credits = (
            CreditEvent('ci', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 10000, '2026-03-01', 'ISSUED'),
            CreditEvent('ca', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 10000, '2026-03-05', 'APPLIED'),
        )
        f, _ = self.one(fixture(credits=credits))
        self.assertEqual(f.remaining_candidate_cents, 0)
        self.assertEqual(f.simulated_new_realized_cents, 0)

    def test_issued_credit_without_application_is_not_recovered(self):
        credits = (CreditEvent('ci', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 3000,
                               '2026-03-21', 'ISSUED'),)
        f, _ = self.one(fixture(credits=credits))
        self.assertEqual(f.issued_unapplied_cents, 3000)
        self.assertEqual(f.remaining_candidate_cents, 3000)
        self.assertEqual(f.simulated_new_realized_cents, 0)

    def test_credit_applied_more_than_issued_is_held(self):
        credits = (
            CreditEvent('ci', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 1000, '2026-03-21', 'ISSUED'),
            CreditEvent('ca', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 3000, '2026-03-22', 'APPLIED'),
        )
        r = run(fixture(credits=credits))
        self.assertIn('CREDIT_OVER_APPLIED', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_return_entitlement_requires_approved_documentation(self):
        entitlement = ReturnEntitlement('return-1', SCOPE, SOURCE, 'invoice-line-1',
                                         5000, 1000, '2026-03-18')
        r = run(fixture(extra=(entitlement,)))
        self.assertIn('RETURN_EVIDENCE_INCOMPLETE', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_documented_return_subtracts_restocking(self):
        entitlement = ReturnEntitlement('return-1', SCOPE, SOURCE, 'invoice-line-1',
                                         5000, 1000, '2026-03-18', SOURCE, SOURCE, SOURCE)
        f, _ = self.one(fixture(billed=10000, contract_price='100', invoice_qty='1',
                                 receipt_qty='1', paid=(10000,), extra=(entitlement,)))
        self.assertEqual((f.return_entitlement_cents, f.expected_cents,
                          f.remaining_candidate_cents), (4000, 6000, 4000))

    def test_pack_conversion_is_explicit(self):
        conv = PackConversion('pack-1', SCOPE, SOURCE, 'product-1', 'BOX', 'CASE', '0.1',
                              '2026-01-01')
        f, _ = self.one(fixture(billed=5600, invoice_qty='20', invoice_unit='BOX',
                                 receipt_qty='20', receipt_unit='BOX', paid=(5600,),
                                 pack=(conv,)))
        self.assertEqual((f.expected_cents, f.remaining_candidate_cents), (5600, 0))

    def test_missing_pack_conversion_is_held(self):
        r = run(fixture(billed=5600, invoice_qty='20', invoice_unit='BOX', receipt_qty='20',
                        receipt_unit='BOX', paid=(5600,)))
        self.assertIn('MISSING_PACK_CONVERSION', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_changed_governing_date_selects_old_order_contract(self):
        b = fixture(invoice_date='2026-03-15', order_date='2026-03-01')
        records = list(b.records)
        old = next(x for x in records if isinstance(x, ContractAuthority))
        records[records.index(old)] = replace(old, effective_to='2026-03-05')
        records.append(replace(old, id='new-contract', unit_price='99', effective_from='2026-03-06'))
        f, _ = self.one(make_batch(records))
        self.assertEqual(f.expected_cents, 28000)

    def test_overlapping_contracts_are_held(self):
        b = fixture()
        old = next(x for x in b.records if isinstance(x, ContractAuthority))
        r = run(make_batch(list(b.records) + [replace(old, id='overlap', unit_price='27')]))
        self.assertIn('OVERLAPPING_AUTHORITIES', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_wrong_facility_authority_not_eligible(self):
        b = fixture()
        records = [replace(x, scope=OTHER) if isinstance(x, ContractAuthority) else x for x in b.records]
        r = run(make_batch(records))
        self.assertIn('NO_CONTROLLING_AUTHORITY', {h.code for h in r.holds})

    def test_receipt_cannot_be_allocated_twice(self):
        b = fixture(billed=10000, contract_price='100', invoice_qty='1', receipt_qty='1', paid=(10000,))
        invoice = next(x for x in b.records if isinstance(x, InvoiceLine))
        records = list(b.records) + [
            replace(invoice, id='invoice-line-2', invoice_number='INV-124'),
            ReceiptAllocation('ra-2', SCOPE, SOURCE, 'receipt-1', 'invoice-line-2', '1'),
        ]
        r = run(make_batch(records))
        self.assertIn('OVERALLOCATED_RECEIPT', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_four_plus_six_split_receipts_and_invoices(self):
        b = fixture(billed=4000, contract_price='100', invoice_qty='4',
                    receipt_qty='4', paid=(4000,))
        invoice = next(x for x in b.records if isinstance(x, InvoiceLine))
        receipt = next(x for x in b.records if isinstance(x, ReceiptEvent))
        records = list(b.records) + [
            replace(invoice, id='invoice-line-2', invoice_number='INV-124', quantity='6', amount_cents=6000),
            replace(receipt, id='receipt-2', quantity='6'),
            ReceiptAllocation('ra-2', SCOPE, SOURCE, 'receipt-2', 'invoice-line-2', '6'),
            PaymentEvent('pay-2', SCOPE, SOURCE, 'bank-ref-2', 6000, '2026-03-20'),
            PaymentAllocation('pa-2', SCOPE, SOURCE, 'pay-2', 'invoice-line-2', 6000),
        ]
        r = run(make_batch(records))
        self.assertEqual(r.remaining_candidate_cents, 0)
        self.assertEqual(r.assessed_lines, 2)
        self.assertEqual(r.holds, ())

    def test_invoice_before_receipt_is_held(self):
        b = fixture()
        receipt = next(x for x in b.records if isinstance(x, ReceiptEvent))
        records = [replace(x, receipt_date='2026-05-01') if x == receipt else x for x in b.records]
        r = run(make_batch(records, as_of='2026-04-30'))
        self.assertIn('RECEIPT_OUTSIDE_SNAPSHOT', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_source_and_economic_ownership_does_not_sum_twice(self):
        b = fixture()
        from recoveryworks.healthcare.procurement import audit_procurement
        from recoveryworks.healthcare.ap_credit import audit_ap_credit
        from recoveryworks.healthcare.aggregation import combine_results
        from recoveryworks.healthcare.models import RuleSetVersion
        rules = RuleSetVersion('a' * 40, 'b' * 64, ('fixed_pack_v1',))
        p = audit_procurement(b, rules)
        a = audit_ap_credit(b, rules)
        combined = combine_results((p, a), b)
        self.assertEqual(combined.remaining_candidate_cents, 3000)
        self.assertEqual(len(combined.findings), 1)

    def test_conflicting_repeated_rows_are_held(self):
        b = fixture()
        pay = next(x for x in b.records if isinstance(x, PaymentEvent))
        records = list(b.records) + [replace(pay, amount_cents=12300)]
        r = run(make_batch(records))
        self.assertIn('CONFLICTING_RECORD_ID', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_quantity_shortfall_requires_explicit_decision(self):
        b = fixture(billed=31000, contract_price='28', invoice_qty='10',
                    receipt_qty='8', paid=(31000,))
        r = run(b)
        self.assertIn('BILLING_EXCEEDS_RECEIPT_UNRESOLVED', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_approved_quantity_shortfall_is_mathematically_bounded(self):
        d = QuantityDecision('qd-1', SCOPE, SOURCE, 'invoice-line-1', '8', 'CASE', '2026-03-20')
        f, _ = self.one(fixture(billed=31000, receipt_qty='8',
                                 quantity_decisions=(d,), paid=(31000,)))
        self.assertEqual((f.expected_cents, f.remaining_candidate_cents), (22400, 8600))

    def test_quantity_decision_wrong_unit_is_not_assumed_equivalent(self):
        d = QuantityDecision('qd-1', SCOPE, SOURCE, 'invoice-line-1', '8', 'BOX', '2026-03-20')
        r = run(fixture(billed=31000, receipt_qty='8', quantity_decisions=(d,)))
        self.assertIn('MISSING_PACK_CONVERSION', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_duplicate_economic_invoice_with_different_row_id_is_held(self):
        b = fixture()
        original = next(x for x in b.records if isinstance(x, InvoiceLine))
        duplicate = replace(original, id='invoice-line-2')
        r = run(make_batch(list(b.records) + [duplicate]))
        self.assertIn('DUPLICATE_ECONOMIC_INVOICE_LINE', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_reversal_of_credit_application_restores_open_exposure(self):
        credits = (
            CreditEvent('ci', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 5000, '2026-03-21', 'ISSUED'),
            CreditEvent('ca', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 3000, '2026-03-22', 'APPLIED'),
            CreditEvent('cr', SCOPE, SOURCE, 'invoice-line-1', 'memo-1', 2000, '2026-03-24',
                        'REVERSAL_APPLIED', 'ca'),
        )
        f, _ = self.one(fixture(billed=10000, contract_price='100', invoice_qty='1',
                                 receipt_qty='1', paid=(10000, 10000), credits=credits))
        self.assertEqual((f.applied_credit_cents, f.issued_unapplied_cents,
                          f.remaining_candidate_cents), (1000, 4000, 9000))

    def test_split_partial_payment_reversal_keeps_true_net_paid(self):
        b = fixture(billed=10000, contract_price='100', invoice_qty='1',
                    receipt_qty='1', paid=(10000, 10000))
        r = list(b.records) + [
            PaymentEvent('pr-1', SCOPE, SOURCE, 'reverse-1', 2500, '2026-03-25', 'REVERSAL', 'pay-2'),
            PaymentAllocation('pra-1', SCOPE, SOURCE, 'pr-1', 'invoice-line-1', 2500),
        ]
        f, _ = self.one(make_batch(r))
        self.assertEqual((f.paid_cents, f.remaining_candidate_cents), (17500, 7500))

    def test_payment_on_cancelled_invoice_creates_hold(self):
        b = fixture()
        invoice = next(x for x in b.records if isinstance(x, InvoiceLine))
        r = run(make_batch([replace(x, status='CANCELLED') if x == invoice else x
                            for x in b.records]))
        self.assertIn('PAYMENT_ON_INACTIVE_INVOICE', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_reordering_source_rows_cannot_change_findings(self):
        import random
        b = fixture()
        old = run(b)
        records = list(b.records)
        random.Random(29).shuffle(records)
        new = run(make_batch(records))
        self.assertEqual((old.remaining_candidate_cents, old.findings[0].economic_loss_id),
                         (new.remaining_candidate_cents, new.findings[0].economic_loss_id))

    def test_same_invoice_number_different_facility_does_not_join(self):
        b = fixture(billed=10000, contract_price='100', invoice_qty='1', receipt_qty='1', paid=(10000,))
        other_invoice = next(x for x in b.records if isinstance(x, InvoiceLine))
        # Same supplier/account reference but different facility and no authority.
        r = run(make_batch(list(b.records) + [replace(other_invoice, scope=OTHER,
                                                       id='invoice-line-2')]))
        self.assertIn('MISSING_PRODUCT', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_full_engine_property_money_allocation_2000_cases(self):
        """Deterministic generated synthetic positives/negatives with independent integer oracle."""
        import random
        rng = random.Random(3281)
        for trial in range(2000):
            unit_cents = rng.randint(1, 20000)
            quantity = rng.randint(1, 30)
            expected = unit_cents * quantity
            billing_over = rng.randint(0, 10000)
            billed = expected + billing_over
            paid = rng.randint(0, billed + 20000)
            # Split without creating multiple logical payments unintentionally.
            first = rng.randint(0, paid)
            payments = tuple(x for x in (first, paid-first) if x)
            batch = fixture(billed=billed, contract_price=str(Decimal(unit_cents) / 100),
                            invoice_qty=str(quantity), receipt_qty=str(quantity), paid=payments)
            observed = run(batch)
            with self.subTest(trial=trial):
                self.assertFalse(observed.holds)
                self.assertEqual(observed.findings[0].expected_cents, expected)
                self.assertEqual(observed.findings[0].remaining_candidate_cents,
                                 max(0, paid - expected))
                self.assertEqual(observed.verified_realized_cents, 0)

    def test_10000_exact_decimal_arithmetic_invariants(self):
        """The oracle is integer cents, not a copy of the engine's multiplication."""
        import random
        from recoveryworks.healthcare.money import extend_price
        rng = random.Random(10000)
        for _ in range(10000):
            cents = rng.randint(0, 200000)
            quantity = rng.randint(0, 100000)
            self.assertEqual(extend_price(Decimal(cents) / 100, Decimal(quantity)), cents * quantity)

    def test_supplier_invoice_number_reissued_on_new_date_is_held(self):
        b = fixture()
        invoice = next(x for x in b.records if isinstance(x, InvoiceLine))
        revised = replace(invoice, id='reissued-line', invoice_date='2026-03-18')
        r = run(make_batch(list(b.records) + [revised]))
        self.assertIn('DUPLICATE_ECONOMIC_INVOICE_LINE', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_duplicate_credit_disclosure_with_new_event_id_is_held(self):
        credit = CreditEvent('ci', SCOPE, SOURCE, 'invoice-line-1', 'memo-1',
                             3000, '2026-03-21', 'ISSUED')
        duplicate = replace(credit, id='ci-reexport')
        r = run(fixture(credits=(credit, duplicate)))
        self.assertIn('DUPLICATE_CREDIT_EVENT', {h.code for h in r.holds})
        self.assertEqual(r.remaining_candidate_cents, 0)

    def test_missing_critical_state_fields_never_default_to_verified(self):
        b = fixture()
        from recoveryworks.healthcare.models import TABLE_TYPES
        table_names = {v: k for k, v in TABLE_TYPES.items()}
        raw_original = {'schema_version': 1}
        for row in b.records:
            raw_original.setdefault(table_names[type(row)], []).append(asdict(row))
        for table, key in [('products', 'category'), ('invoices', 'status'),
                           ('invoices', 'line_number'), ('invoices', 'unsupported_components'),
                           ('contracts', 'rounding'), ('contracts', 'quantity_basis'),
                           ('receipts', 'accepted'), ('payments', 'kind')]:
            raw = json.loads(json.dumps(raw_original))
            del raw[table][0][key]
            data = json.dumps(raw).encode()
            counts = tuple(sorted((k, len(v)) for k, v in raw.items() if k != 'schema_version'))
            approval = ApprovedScope((SCOPE,), hashlib.sha256(data).hexdigest(), counts,
                                      '2026-01-01','2026-12-31','2026-04-30','2026-03-10', True)
            batch = import_json(data, approval)
            with self.subTest(table=table, field=key):
                self.assertIn('MISSING_CRITICAL_FIELD', {h.code for h in batch.holds})
                self.assertFalse(batch.complete)

    def test_missing_original_source_system_is_held(self):
        b = fixture()
        from recoveryworks.healthcare.models import TABLE_TYPES
        names = {v: k for k, v in TABLE_TYPES.items()}
        raw = {'schema_version': 1}
        for row in b.records:
            raw.setdefault(names[type(row)], []).append(asdict(row))
        del raw['invoices'][0]['source']['system']
        data = json.dumps(raw).encode()
        counts = tuple(sorted((k, len(v)) for k, v in raw.items() if k != 'schema_version'))
        scope = ApprovedScope((SCOPE,), hashlib.sha256(data).hexdigest(), counts,
                              '2026-01-01', '2026-12-31', '2026-04-30', '2026-03-10', True)
        result = import_json(data, scope)
        self.assertIn('MISSING_SOURCE_ORIGIN', {h.code for h in result.holds})


if __name__ == '__main__':
    unittest.main()
