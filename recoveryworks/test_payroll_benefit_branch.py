from recoveryworks.test_support import source_hash as H
from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.contract_billing import ContractRate, InvoiceCharge
from recoveryworks.branches.payroll_benefit import audit_payroll_benefit_billing
from recoveryworks.branches.payroll_benefit_csv import load_payroll_benefit_units_csv


def rate(*, verified=True, unit_rate=2_000_000):
    return ContractRate(
        counterparty_id="Benefit Carrier",
        service_id="MED-FAMILY",
        effective_from="2026-01-01",
        effective_to=None,
        fixed_cents=1000,
        included_units="0",
        unit_rate_micros=unit_rate,
        source_hash=H("rate-hash"),
        source_locator="file://rates.csv#row=2",
        verified=verified,
    )


def charge(*, verified=True, actual=4000):
    return InvoiceCharge(
        charge_id="B-1",
        counterparty_id="Benefit Carrier",
        account_id="employer-1",
        service_id="MED-FAMILY",
        service_date="2026-08-31",
        actual_cents=actual,
        source_hash=H("charge-hash"),
        source_locator="file://charges.csv#row=2",
        verified=verified,
    )


class PayrollBenefitRecoveryTests(unittest.TestCase):
    def test_deidentified_units_produce_validated_overcharge(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "units.csv"
            path.write_text(
                "Charge_ID,Record_ID,Units\n"
                "B-1,SURR-1,4\n"
                "B-1,SURR-2,6\n",
                encoding="utf-8",
            )
            units = load_payroll_benefit_units_csv(path, verified=True)
            batch = audit_payroll_benefit_billing(
                client_id="client",
                charges=(charge(),),
                rates=(rate(),),
                units=units,
            )
            self.assertEqual(batch.exceptions, ())
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.expected_cents, 3000)
            self.assertEqual(finding.actual_cents, 4000)
            self.assertEqual(finding.potential_recovery_cents, 1000)
            self.assertEqual(
                units[0].metadata["quantity_basis"],
                "deidentified_employer_billing_units",
            )

    def test_direct_identifier_column_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "units.csv"
            path.write_text(
                "Charge_ID,Record_ID,Units,SSN\n"
                "B-1,SURR-1,1,123-45-6789\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_payroll_benefit_units_csv(path)

    def test_duplicate_surrogate_record_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "units.csv"
            path.write_text(
                "Charge_ID,Record_ID,Units\n"
                "B-1,SURR-1,1\n"
                "B-1,SURR-1,1\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_payroll_benefit_units_csv(path)

    def test_missing_units_fails_closed_for_variable_contract(self):
        batch = audit_payroll_benefit_billing(
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
            units=(),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "MISSING_USAGE")

    def test_unverified_units_keep_candidate_in_review(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "units.csv"
            path.write_text(
                "Charge_ID,Record_ID,Units\nB-1,SURR-1,10\n",
                encoding="utf-8",
            )
            batch = audit_payroll_benefit_billing(
                client_id="client",
                charges=(charge(),),
                rates=(rate(),),
                units=load_payroll_benefit_units_csv(path, verified=False),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
