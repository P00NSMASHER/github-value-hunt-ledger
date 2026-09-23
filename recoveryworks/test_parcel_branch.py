from recoveryworks.test_support import source_hash as H
from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.parcel import (
    ParcelCharge,
    ParcelExpectedAssessment,
    audit_parcel_charges,
)
from recoveryworks.branches.parcel_csv import (
    load_parcel_assessments_csv,
    load_parcel_charges_csv,
)


def charge(*, verified=True, weight="10", actual=3000):
    return ParcelCharge(
        shipment_id="SHIP-1",
        invoice_id="INV-1",
        shipper_id="client-1",
        carrier_id="Carrier A",
        ship_date="2026-08-15",
        service_code="GROUND",
        zone="5",
        billed_weight=weight,
        actual_total_cents=actual,
        source_hash=H("charge-hash"),
        source_locator="file://charges.csv#row=2",
        verified=verified,
    )


def assessment(*, verified=True, weight="10", expected=2200):
    return ParcelExpectedAssessment(
        assessment_id="A-1",
        shipment_id="SHIP-1",
        carrier_id="Carrier A",
        ship_date="2026-08-15",
        service_code="GROUND",
        zone="5",
        billed_weight=weight,
        expected_total_cents=expected,
        rate_basis="Reviewed contract rate + approved accessorial schedule",
        source_hash=H("assessment-hash"),
        source_locator="file://assessments.csv#row=2",
        verified=verified,
        rate_snapshot_date="2026-08-01" if verified else None,
        rate_reviewer_id="parcel-reviewer-1" if verified else None,
    )


class ParcelRecoveryTests(unittest.TestCase):
    def test_verified_parcel_overcharge_is_validated(self):
        batch = audit_parcel_charges(
            client_id="client-1",
            charges=(charge(),),
            assessments=(assessment(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 800)
        self.assertEqual(finding.metadata["rate_reviewer_id"], "parcel-reviewer-1")

    def test_weight_identity_mismatch_fails_closed(self):
        batch = audit_parcel_charges(
            client_id="client-1",
            charges=(charge(weight="10"),),
            assessments=(assessment(weight="12"),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(
            batch.exceptions[0].code,
            "PARCEL_ASSESSMENT_IDENTITY_MISMATCH",
        )

    def test_verified_assessment_requires_reviewer_and_snapshot(self):
        with self.assertRaises(ValueError):
            ParcelExpectedAssessment(
                assessment_id="A",
                shipment_id="S",
                carrier_id="C",
                ship_date="2026-08-15",
                service_code="GROUND",
                zone="5",
                billed_weight="1",
                expected_total_cents=100,
                rate_basis="rate",
                source_hash=H("h"),
                source_locator="file://x",
                verified=True,
            )

    def test_csv_files_preserve_hash_and_row_locator(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "charges.csv").write_text(
                "Shipment_ID,Invoice_ID,Shipper_ID,Carrier_ID,Ship_Date,Service_Code,"
                "Zone,Billed_Weight,Actual_Total\n"
                "SHIP-1,INV-1,client-1,Carrier A,2026-08-15,GROUND,5,10,30.00\n",
                encoding="utf-8",
            )
            (root / "assessments.csv").write_text(
                "Assessment_ID,Shipment_ID,Carrier_ID,Ship_Date,Service_Code,Zone,"
                "Billed_Weight,Expected_Total,Rate_Basis,Rate_Snapshot_Date,Rate_Reviewer_ID\n"
                "A-1,SHIP-1,Carrier A,2026-08-15,GROUND,5,10,22.00,"
                "Reviewed rate,2026-08-01,reviewer-1\n",
                encoding="utf-8",
            )
            charges = load_parcel_charges_csv(root / "charges.csv", verified=True)
            assessments = load_parcel_assessments_csv(
                root / "assessments.csv", verified=True
            )
            self.assertTrue(charges[0].source_hash)
            self.assertIn("#row=2", charges[0].source_locator)
            self.assertTrue(assessments[0].source_hash)


if __name__ == "__main__":
    unittest.main()
