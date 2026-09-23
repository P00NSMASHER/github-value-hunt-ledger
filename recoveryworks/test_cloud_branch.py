from recoveryworks.test_support import source_hash as H
from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.cloud import audit_cloud_billing
from recoveryworks.branches.cloud_csv import load_cloud_meter_csv
from recoveryworks.branches.contract_billing import ContractRate, InvoiceCharge


def rate(*, verified=True, unit_rate=2_000_000):
    return ContractRate(
        counterparty_id="CloudCo",
        service_id="compute",
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
        charge_id="C-1",
        counterparty_id="CloudCo",
        account_id="acct",
        service_id="compute",
        service_date="2026-08-31",
        actual_cents=actual,
        source_hash=H("charge-hash"),
        source_locator="file://charges.csv#row=2",
        verified=verified,
    )


class CloudRecoveryTests(unittest.TestCase):
    def test_raw_meter_usage_produces_validated_contract_overcharge(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "meter.csv"
            path.write_text(
                "Charge_ID,Meter_Record_ID,Usage_Units\n"
                "C-1,M-1,4\n"
                "C-1,M-2,6\n",
                encoding="utf-8",
            )
            usage = load_cloud_meter_csv(path, verified=True)
            batch = audit_cloud_billing(
                client_id="client",
                charges=(charge(),),
                rates=(rate(),),
                usage=usage,
            )
            self.assertEqual(batch.exceptions, ())
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.expected_cents, 3000)
            self.assertEqual(finding.actual_cents, 4000)
            self.assertEqual(finding.potential_recovery_cents, 1000)
            self.assertEqual(usage[0].metadata["meter_record_count"], 2)

    def test_duplicate_meter_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "meter.csv"
            path.write_text(
                "Charge_ID,Meter_Record_ID,Usage_Units\n"
                "C-1,M-1,4\n"
                "C-1,M-1,6\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_cloud_meter_csv(path)

    def test_variable_cloud_rate_without_usage_is_exception(self):
        batch = audit_cloud_billing(
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
            usage=(),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "MISSING_USAGE")

    def test_unverified_meter_keeps_candidate_in_review(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "meter.csv"
            path.write_text(
                "Charge_ID,Meter_Record_ID,Usage_Units\nC-1,M-1,10\n",
                encoding="utf-8",
            )
            batch = audit_cloud_billing(
                client_id="client",
                charges=(charge(),),
                rates=(rate(),),
                usage=load_cloud_meter_csv(path, verified=False),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
