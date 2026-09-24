import json
import zipfile

import pytest

from freight.synthetic_pilot_bundle import (
    build_synthetic_pilot_bundle,
    verify_synthetic_pilot_bundle,
)


EXPECTED_ENTRIES = {
    "README.md",
    "EXECUTIVE_REPORT.md",
    "REVIEW_PACKET.md",
    "REHEARSAL_RECEIPT.json",
    "TRACE_SUMMARY.txt",
    "inputs/invoices.csv",
    "inputs/verified-rules.csv",
    "inputs/candidate-rules.csv",
    "inputs/settlements.csv",
    "inputs/returns.csv",
    "BUNDLE_MANIFEST.json",
}


def test_controlled_synthetic_bundle_is_buyer_safe_and_verifiable(tmp_path):
    bundle = tmp_path / "synthetic-pilot-demo.zip"
    built = build_synthetic_pilot_bundle(bundle)
    verified = verify_synthetic_pilot_bundle(bundle)
    assert built == verified
    assert built["entry_count"] == len(EXPECTED_ENTRIES)
    assert built["scenario_id"] == "freight-recovery-controlled-demo-v1"

    with zipfile.ZipFile(bundle) as archive:
        assert set(archive.namelist()) == EXPECTED_ENTRIES
        manifest = json.loads(archive.read("BUNDLE_MANIFEST.json"))
        receipt = json.loads(archive.read("REHEARSAL_RECEIPT.json"))
        readme = archive.read("README.md").decode("utf-8")
        report = archive.read("EXECUTIVE_REPORT.md").decode("utf-8")

    assert manifest["synthetic"] is True
    assert manifest["customer_data_included"] is False
    assert manifest["external_action_performed"] is False
    assert manifest["commercial_value_claimed"] is False
    assert receipt["carrier_action_external_action_simulated"] is True
    assert receipt["carrier_action_external_action_performed"] is False
    assert receipt["commercial_value_claimed"] is False
    assert receipt["metrics"]["realized_cents"] == 4_000
    assert "no email or carrier contact" in readme
    assert "SYNTHETIC / NO CUSTOMER DATA" in report
    assert "Discrepancy and validated dollars are not realized savings" in report


def test_controlled_synthetic_bundle_is_byte_deterministic(tmp_path):
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    first_receipt = build_synthetic_pilot_bundle(first)
    second_receipt = build_synthetic_pilot_bundle(second)
    assert first_receipt == second_receipt
    assert first.read_bytes() == second.read_bytes()


def test_duplicate_or_tampered_bundle_entry_is_rejected(tmp_path):
    bundle = tmp_path / "tampered.zip"
    build_synthetic_pilot_bundle(bundle)
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(bundle, "a") as archive:
            archive.writestr("inputs/invoices.csv", b"tampered")
    with pytest.raises(ValueError, match="duplicate synthetic bundle entry"):
        verify_synthetic_pilot_bundle(bundle)


def test_reformatted_or_extended_manifest_is_rejected(tmp_path):
    source = tmp_path / "source.zip"
    tampered = tmp_path / "tampered.zip"
    build_synthetic_pilot_bundle(source)
    with zipfile.ZipFile(source, "r") as original, zipfile.ZipFile(tampered, "w") as output:
        for info in original.infolist():
            data = original.read(info.filename)
            if info.filename == "BUNDLE_MANIFEST.json":
                manifest = json.loads(data)
                manifest["unsupported_claim"] = True
                data = json.dumps(manifest, sort_keys=True).encode("utf-8")
            output.writestr(info, data)
    with pytest.raises(ValueError, match="size mismatch|manifest differs"):
        verify_synthetic_pilot_bundle(tampered)
