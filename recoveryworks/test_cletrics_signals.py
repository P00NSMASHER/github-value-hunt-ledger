from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from recoveryworks.integrations.cletrics import CLETRICS_BUNDLE_TYPE, load_cletrics_bundle
from recoveryworks.runner import run_scan360_config


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def entry(role: str, path: str, raw: bytes, source_kind: str) -> dict:
    return {
        "role": role,
        "path": path,
        "sha256": sha(raw),
        "size_bytes": len(raw),
        "transformation_id": f"test-{role}-v1",
        "source": {
            "kind": source_kind,
            "locator": f"cletrics-db://{role}",
            "sha256": sha((source_kind + "-raw").encode()),
            "acquired_at": "2026-09-23T22:00:00-04:00",
        },
    }


def build_signal_bundle(path: Path) -> Path:
    charges=(
        b"Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
        b"C-1,AWS,acct-1,compute,2026-08-31,40.00\n"
    )
    meter=(
        b"Charge_ID,Meter_Record_ID,Usage_Units\n"
        b"C-1,M-1,10\n"
    )
    anomalies=(
        b"Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,Region,"
        b"Severity,Detection_Method,Metric_Name,Z_Score,Baseline_Value,Actual_Value,"
        b"Estimated_Cost_Impact,Confidence\n"
        b"A-1,2026-09-23T20:00:00Z,aws,acct-1,compute,i-1,us-east-1,"
        b"P1,zscore,cost_estimate,4.2,10,100,999999.99,0.90\n"
    )
    recon=(
        b"Signal_ID,Detected_At,Provider,Account_ID,Service_ID,SKU_Key,"
        b"Estimated_Cost,Actual_Cost,Error_Pct,Drift_Direction\n"
        b"R-1,2026-09-23T21:00:00Z,aws,acct-1,compute,m7i,30.00,40.00,33.33,over\n"
    )
    manifest={
        "schema":1,
        "bundle_type":CLETRICS_BUNDLE_TYPE,
        "client_id":"client-1",
        "provider":"aws",
        "billing_account_id":"acct-1",
        "currency":"USD",
        "period_start":"2026-08-01",
        "period_end":"2026-08-31",
        "exported_at":"2026-09-23T22:01:00-04:00",
        "cletrics":{"release":"test","commit":"a"*40,"image_digest":None},
        "entries":[
            entry("invoice_charges","billing/charges.csv",charges,"provider_billing_export"),
            entry("meter_usage","usage/meter.csv",meter,"provider_meter_export"),
            entry("anomaly_signals","signals/anomalies.csv",anomalies,"anomaly_events"),
            entry("reconciliation_signals","signals/reconciliation.csv",recon,"reconciliation"),
        ],
    }
    manifest_raw=json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()
    with zipfile.ZipFile(path,"w") as archive:
        archive.writestr("manifest.json",manifest_raw)
        archive.writestr("billing/charges.csv",charges)
        archive.writestr("usage/meter.csv",meter)
        archive.writestr("signals/anomalies.csv",anomalies)
        archive.writestr("signals/reconciliation.csv",recon)
    return path


class CletricsSignalTests(unittest.TestCase):
    def test_signal_roles_are_non_money_objects(self):
        with tempfile.TemporaryDirectory() as d:
            bundle=load_cletrics_bundle(build_signal_bundle(Path(d)/"signals.zip"))
            self.assertEqual(len(bundle.signals),2)
            anomaly=next(s for s in bundle.signals if s.signal_id=="A-1")
            recon=next(s for s in bundle.signals if s.signal_id=="R-1")
            self.assertEqual(anomaly.estimated_impact_cents,99_999_999)
            self.assertEqual(anomaly.confidence,"0.90")
            self.assertEqual(recon.estimated_impact_cents,1000)
            self.assertFalse(hasattr(anomaly,"to_recovery_observation"))
            self.assertFalse(hasattr(recon,"to_recovery_observation"))

    def test_signals_do_not_inflate_recovery_totals(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            build_signal_bundle(root/"signals.zip")
            (root/"rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,Included_Units,Unit_Rate\n"
                "AWS,compute,2026-01-01,,10.00,0,2.00\n",
                encoding="utf-8",
            )
            result=run_scan360_config(
                {
                    "client_id":"client-1",
                    "currency":"USD",
                    "cloud":{
                        "cletrics_bundle":"signals.zip",
                        "rates_csv":"rates.csv",
                        "charge_source_verified":True,
                        "meter_source_verified":True,
                        "rate_source_verified":True,
                    },
                },
                state_path=root/"ledger.json",
                base_dir=root,
            )
            self.assertEqual(len(result.cloud_signals),2)
            self.assertEqual(result.report.totals["validated_cents"],1000)
            self.assertEqual(result.report.totals["potential_cents"],1000)
            self.assertGreater(max(s.estimated_impact_cents or 0 for s in result.cloud_signals),1000)
            self.assertEqual(len(result.as_dict()["cloud_signals"]),2)

    def test_duplicate_conflicting_signal_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=build_signal_bundle(root/"signals.zip")
            with zipfile.ZipFile(path,"r") as archive:
                manifest=json.loads(archive.read("manifest.json"))
                charges=archive.read("billing/charges.csv")
                meter=archive.read("usage/meter.csv")
                anomalies=archive.read("signals/anomalies.csv")
            recon=(
                b"Signal_ID,Detected_At,Provider,Account_ID,Service_ID,SKU_Key,"
                b"Estimated_Cost,Actual_Cost,Error_Pct,Drift_Direction\n"
                b"A-1,2026-09-23T21:00:00Z,aws,acct-1,compute,m7i,30.00,50.00,66.67,over\n"
            )
            for row in manifest["entries"]:
                if row["role"]=="reconciliation_signals":
                    row["sha256"]=sha(recon); row["size_bytes"]=len(recon)
            manifest_raw=json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()
            with zipfile.ZipFile(path,"w") as archive:
                archive.writestr("manifest.json",manifest_raw)
                archive.writestr("billing/charges.csv",charges)
                archive.writestr("usage/meter.csv",meter)
                archive.writestr("signals/anomalies.csv",anomalies)
                archive.writestr("signals/reconciliation.csv",recon)
            with self.assertRaisesRegex(ValueError,"conflicting Cletrics signal_id"):
                load_cletrics_bundle(path)


if __name__=="__main__":
    unittest.main()
