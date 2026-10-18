from dataclasses import replace
import unittest
from recoveryworks.branches.parcel_rating import ParcelRateBand, ParcelRateContract, ParcelMeasurements, rate_parcel
from recoveryworks.branches.parcel import audit_parcel_charges
from recoveryworks.test_parcel_branch import charge
from recoveryworks.test_support import source_hash as H
from recoveryworks import RecoveryEngine, FindingState


def contract():
    return ParcelRateContract('C','Carrier A','GROUND','5','2026-01-01','2026-12-31','lb','in',
        '100','1',(ParcelRateBand('10',1000),ParcelRateBand('20',2000)),1000,800,1000,100,True,500,
        H('contract'),'fixture://contract','SIMULATED/reviewer',True)


def measurements():
    return ParcelMeasurements('SHIP-1','8','10','10','11','lb','in',H('measurements'),'fixture://measurements',True)


class ParcelRatingTests(unittest.TestCase):
    def test_dimensional_weight_discount_fuel_tax_exact_trace(self):
        # 11 lb dimensional => $20 band; 10% discount => $18; +$1; 10% fuel => $1.90; 5% tax => $1.05.
        assessed=rate_parcel(charge(),measurements(),contract())
        self.assertEqual(assessed.expected_total_cents,2195)
        self.assertEqual(assessed.metadata['billable_weight'],'11')
        batch=audit_parcel_charges(client_id='client-1',charges=(charge(),),assessments=(assessed,))
        finding=RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.potential_recovery_cents,805)
        self.assertEqual(finding.state,FindingState.VALIDATED)

    def test_unverified_measurement_cannot_validate(self):
        self.assertFalse(rate_parcel(charge(),replace(measurements(),verified=False),contract()).verified)

    def test_units_scope_and_missing_band_fail_closed(self):
        for measured in (replace(measurements(),weight_unit='kg'),replace(measurements(),shipment_id='OTHER'),replace(measurements(),actual_weight='100')):
            with self.subTest(measured=measured),self.assertRaises(ValueError):
                rate_parcel(charge(),measured,contract())
        with self.assertRaises(ValueError):
            rate_parcel(charge(),measurements(),replace(contract(),effective_to='2026-06-01'))

    def test_minimum_and_rounding_boundary(self):
        assessed=rate_parcel(charge(),replace(measurements(),height='10'),replace(contract(),discount_bps=5000))
        # $5 discounted rate raised to $8 minimum; +$1, +$0.90 fuel, +$0.50 tax.
        self.assertEqual(assessed.expected_total_cents,1040)
