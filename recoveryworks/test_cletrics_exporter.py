from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.integrations.cletrics import load_cletrics_bundle
from recoveryworks.integrations.cletrics_exporter import (
    CletricsSourceArtifact,
    export_cletrics_focus_snapshot,
)


class CletricsFocusExporterTests(unittest.TestCase):
    def source(self, path: Path, kind: str) -> CletricsSourceArtifact:
        return CletricsSourceArtifact(
            path=path,
            kind=kind,
            locator=f"test://{kind}",
            acquired_at="2026-09-23T20:00:00Z",
        )

    def test_focus_and_independent_meter_export_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            focus = root / "focus.csv"
            focus.write_text(
                "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
                "BilledCost,BillingCurrency,ResourceId,RegionId,SkuId,InvoiceId,"
                "EffectiveCost,ListCost,ContractedCost\n"
                "AWS,payer-1,EC2,2026-08-31T00:00:00Z,40.00,USD,"
                "i-123,us-east-1,m7i.2xlarge,INV-1,30.00,50.00,35.00\n",
                encoding="utf-8",
            )
            meter = root / "meter.csv"
            meter.write_text(
                "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
                "M-1,4,i-123,EC2,2026-08-31\n"
                "M-2,6,i-123,EC2,2026-08-31\n",
                encoding="utf-8",
            )
            anomaly = root / "anomaly.csv"
            anomaly.write_text(
                "Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Severity,"
                "Detection_Method,Metric_Name,Estimated_Cost_Impact,Confidence\n"
                "A-1,2026-09-01T00:00:00Z,aws,payer-1,EC2,HIGH,zscore,cost,50,0.9\n",
                encoding="utf-8",
            )
            output = root / "bundle.zip"
            receipt = export_cletrics_focus_snapshot(
                output_path=output,
                client_id="client-1",
                focus=self.source(focus, "cletrics_focus_export"),
                meter=self.source(meter, "cletrics_meter_export"),
                anomaly=self.source(anomaly, "cletrics_anomaly_output"),
                cletrics_release="1.3.13",
                cletrics_commit="a" * 40,
                exported_at="2026-09-01T01:00:00Z",
                period_start="2026-08-01",
                period_end="2026-08-31",
            )
            self.assertEqual(receipt.charge_count, 1)
            self.assertEqual(receipt.meter_record_count, 2)
            self.assertEqual(receipt.signal_roles, ("anomaly_signals",))

            bundle = load_cletrics_bundle(
                output,
                charge_source_verified=True,
                meter_source_verified=True,
            )
            self.assertEqual(bundle.provider, "aws")
            self.assertEqual(bundle.billing_account_id, "payer-1")
            self.assertEqual(bundle.currency, "USD")
            self.assertEqual(len(bundle.charges), 1)
            self.assertTrue(bundle.charges[0].charge_id.startswith("focus:"))
            self.assertEqual(bundle.charges[0].actual_cents, 4000)
            self.assertEqual(bundle.charges[0].metadata["provider_fields"]["Resource_ID"], "i-123")
            self.assertEqual(len(bundle.usage), 1)
            self.assertEqual(bundle.usage[0].units, "10")
            self.assertEqual(len(bundle.signals), 1)

    def test_ambiguous_natural_meter_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            focus = root / "focus.csv"
            focus.write_text(
                "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
                "BilledCost,BillingCurrency,ResourceId\n"
                "AWS,payer-1,EC2,2026-08-31T00:00:00Z,10.00,USD,i-123\n"
                "AWS,payer-1,EC2,2026-08-31T00:00:00Z,20.00,USD,i-123\n",
                encoding="utf-8",
            )
            meter = root / "meter.csv"
            meter.write_text(
                "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
                "M-1,4,i-123,EC2,2026-08-31\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "ambiguous or unmatched"):
                export_cletrics_focus_snapshot(
                    output_path=root / "bundle.zip",
                    client_id="client-1",
                    focus=self.source(focus, "focus"),
                    meter=self.source(meter, "meter"),
                    cletrics_release="test",
                    cletrics_commit="b" * 40,
                    exported_at="2026-09-01T00:00:00Z",
                    period_start="2026-08-01",
                    period_end="2026-08-31",
                )

    def test_multi_currency_focus_export_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            focus = root / "focus.csv"
            focus.write_text(
                "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
                "BilledCost,BillingCurrency\n"
                "AWS,payer-1,EC2,2026-08-31,10.00,USD\n"
                "AWS,payer-1,S3,2026-08-31,10.00,EUR\n",
                encoding="utf-8",
            )
            meter = root / "meter.csv"
            meter.write_text(
                "Charge_ID,Meter_Record_ID,Usage_Units\nx,M-1,1\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "one currency"):
                export_cletrics_focus_snapshot(
                    output_path=root / "bundle.zip",
                    client_id="client-1",
                    focus=self.source(focus, "focus"),
                    meter=self.source(meter, "meter"),
                    cletrics_release="test",
                    cletrics_commit="c" * 40,
                    exported_at="2026-09-01T00:00:00Z",
                    period_start="2026-08-01",
                    period_end="2026-08-31",
                )


if __name__ == "__main__":
    unittest.main()
