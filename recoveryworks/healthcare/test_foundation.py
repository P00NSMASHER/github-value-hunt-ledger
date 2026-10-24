"""Independent examples for the new engine's strict intake and arithmetic."""
import hashlib
import importlib
import json
import unittest
from decimal import Decimal, localcontext


def module(test, name):
    try:
        return importlib.import_module('recoveryworks.healthcare.' + name)
    except ModuleNotFoundError as exc:
        test.fail('required engine module not implemented: ' + exc.name)


class MoneyTests(unittest.TestCase):
    def setUp(self):
        self.m = module(self, 'money')

    def test_fractional_cent_price(self):
        self.assertEqual(self.m.extend_price(Decimal('0.0049'), Decimal('1000')), 490)

    def test_round_once_at_line_end(self):
        self.assertEqual(self.m.extend_price(Decimal('0.005'), Decimal('3')), 2)

    def test_explicit_half_even(self):
        self.assertEqual(self.m.extend_price(Decimal('0.005'), Decimal('1'), 'HALF_EVEN'), 0)

    def test_decimal_context_cannot_change_result(self):
        with localcontext() as ctx:
            ctx.prec = 3
            self.assertEqual(self.m.extend_price(Decimal('28.123456'), Decimal('1000')), 2812346)

    def test_reject_unsafe_decimal_values(self):
        for value in (True, 1, 0.1, Decimal('0.1'), 'NaN', 'Infinity', '1e3', '-1', '', ' 1', '1,000', '1\n', '1.0000000000001'):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    self.m.parse_decimal(value)

    def test_reject_oversized_money(self):
        with self.assertRaises(ValueError):
            self.m.extend_price(Decimal('999999999999'), Decimal('999999999999'))

    def test_fraction_quantity_is_exact(self):
        self.assertEqual(self.m.extend_price(Decimal('28'), Decimal('0.2')), 560)


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.i = module(self, 'ingestion')
        self.m = module(self, 'models')
        self.scope = self.m.ScopeKey('client', 'buyer', 'facility', 'supplier', 'account', 'USD')

    def permit(self, data, counts=()):
        return self.m.ApprovedScope((self.scope,), hashlib.sha256(data).hexdigest(), counts,
                                    '2026-01-01', '2026-12-31', '2026-10-21', '2026-10-01', True)

    def test_empty_population_is_not_clean_audit(self):
        data = b'{"schema_version":1,"invoices":[]}'
        batch = self.i.import_json(data, self.permit(data, (('invoices', 0),)))
        self.assertIn('EMPTY_POPULATION', [h.code for h in batch.holds])
        self.assertFalse(batch.complete)

    def test_declared_row_gap_is_explicit(self):
        data = b'{"schema_version":1,"invoices":[]}'
        batch = self.i.import_json(data, self.permit(data, (('invoices', 1),)))
        self.assertEqual(batch.missing_rows, 1)
        self.assertIn('INCOMPLETE_POPULATION', [h.code for h in batch.holds])

    def test_changed_upload_invalidates_scope(self):
        data = b'{"schema_version":1,"invoices":[]}'
        with self.assertRaisesRegex(ValueError, 'SOURCE_HASH_MISMATCH'):
            self.i.import_json(data + b' ', self.permit(data))

    def test_duplicate_json_keys_rejected(self):
        data = b'{"schema_version":1,"invoices":[],"invoices":[]}'
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
            self.i.import_json(data, self.permit(data))

    def test_unknown_top_level_fields_rejected(self):
        data = b'{"schema_version":1,"invoices":[],"verified":true}'
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_FIELD'):
            self.i.import_json(data, self.permit(data))

    def test_unknown_record_type_not_silently_dropped(self):
        data = b'{"schema_version":1,"patient_records":[{}]}'
        with self.assertRaises(ValueError):
            self.i.import_json(data, self.permit(data))

    def test_currency_has_no_default(self):
        with self.assertRaises(ValueError):
            self.m.ScopeKey('client','buyer','facility','supplier','account','')

    def test_float_and_boolean_cents_are_not_money(self):
        for amount in (1.0, True, -1, 2**63):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.m.check_cents(amount)

    def test_control_characters_and_unicode_aliases_in_ids_rejected(self):
        for name in ('supplier\n', 'supplier\x00', ' supplier', 'ｓupplier'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.m.ScopeKey('client', 'buyer', 'facility', name, 'account', 'USD')

    def test_source_hash_is_not_a_verification_flag(self):
        with self.assertRaises(TypeError):
            self.m.SourceRef('a' * 64, 'row:1', verified=True)

    def test_manifest_counts_cannot_be_boolean(self):
        data = b'{"schema_version":1,"invoices":[]}'
        with self.assertRaises(ValueError):
            self.permit(data, (('invoices', True),))

    def test_date_and_scope_are_immutable(self):
        with self.assertRaises(Exception):
            self.scope.facility_id = 'elsewhere'


if __name__ == '__main__':
    unittest.main()
