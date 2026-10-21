from dataclasses import replace
import unittest
from recoveryworks.branches.procurement import audit_procurement_lines
from recoveryworks.test_procurement_branch import line, authority, quantity


class ProcurementUnitTests(unittest.TestCase):
    def test_reviewed_case_to_each_conversion(self):
        approved=replace(quantity(qty='2'),quantity_unit='CASE',price_units_per_quantity_unit='12',
                         conversion_basis='Reviewed SKU pack size',conversion_reviewer_id='SIMULATED/reviewer')
        result=audit_procurement_lines(client_id='client-1',invoice_lines=(line(actual=30000),),
            authorities=(replace(authority(price=1000),price_unit='EACH'),),quantity_approvals=(approved,))
        self.assertEqual(result.observations[0].expected_cents,24000)
        self.assertEqual(result.observations[0].metadata['effective_price_quantity'],'24')

    def test_mismatch_without_conversion_cannot_validate(self):
        result=audit_procurement_lines(client_id='client-1',invoice_lines=(line(),),
            authorities=(replace(authority(),price_unit='EACH'),),
            quantity_approvals=(replace(quantity(),quantity_unit='CASE'),))
        self.assertFalse(result.observations)
        self.assertEqual(result.exceptions[0].code,'MISSING_UNIT_CONVERSION')

    def test_conversion_requires_basis_and_reviewer(self):
        with self.assertRaises(ValueError):
            replace(quantity(),quantity_unit='CASE',price_units_per_quantity_unit='12')
