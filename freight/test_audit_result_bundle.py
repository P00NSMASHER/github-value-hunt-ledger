import json
import zipfile
from dataclasses import replace

import pytest

from freight.audit_result_bundle import (
    build_audit_result_bundle,
    verify_audit_result_bundle,
)
from freight.audit_workflow import RuleCSVInput, run_audit_workflow


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def workflow(*, clean=False):
    billed = 9000 if clean else 12500
    return run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(
            INVOICE_HEADER
            + f"I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,{billed}\n"
        ).encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="September accepted charges",
        rule_inputs=(
            RuleCSVInput(
                filename="rules.csv",
                data=(RULE_HEADER + "DETENTION,FIXED,2026-09-01,,10000,\n").encode(),
                customer_id="C",
                carrier_id="K",
                currency="USD",
                authority_document_id="rate",
                source_document_sha256="a" * 64,
                verified_controlling_authority=True,
            ),
        ),
    )


def test_review_required_result_builds_and_verifies_bundle(tmp_path):
    result = workflow()
    path = tmp_path / "result.zip"
    receipt = build_audit_result_bundle(result, path)
    verify_audit_result_bundle(result, path)

    assert receipt.state == "REVIEW_REQUIRED"
    assert receipt.run_hash == result.summary.run_hash
    assert receipt.entry_count == 11
    assert len(receipt.bundle_sha256) == 64
    assert len(receipt.manifest_sha256) == 64

    with zipfile.ZipFile(path, "r") as archive:
        manifest = json.loads(archive.read("RESULT_BUNDLE_MANIFEST.json"))
        assert manifest["customer_data_included"] is True
        assert manifest["raw_source_files_included"] is False
        assert manifest["run_hash"] == result.summary.run_hash
        assert "review-packet.md" in archive.namelist()
        assert "normalized-charges.json" in archive.namelist()
        assert "normalized-rules.json" in archive.namelist()


def test_clean_result_also_has_canonical_bundle(tmp_path):
    result = workflow(clean=True)
    assert result.state == "CLEAN"
    path = tmp_path / "clean.zip"
    receipt = build_audit_result_bundle(result, path)
    verify_audit_result_bundle(result, path)
    assert receipt.state == "CLEAN"
    with zipfile.ZipFile(path, "r") as archive:
        packet = json.loads(archive.read("review-packet.json"))
        assert packet["cases"] == []


def test_bundle_bytes_are_deterministic(tmp_path):
    result = workflow()
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    receipt_a = build_audit_result_bundle(result, a)
    receipt_b = build_audit_result_bundle(result, b)
    assert a.read_bytes() == b.read_bytes()
    assert receipt_a == receipt_b


def test_raw_source_files_are_not_embedded(tmp_path):
    result = workflow()
    path = tmp_path / "result.zip"
    build_audit_result_bundle(result, path)
    blob = path.read_bytes()
    assert INVOICE_HEADER.encode() not in blob
    assert RULE_HEADER.encode() not in blob
    assert b"charges.csv" not in blob
    assert b"rules.csv" not in blob


def test_blocked_workflow_cannot_produce_result_bundle(tmp_path):
    result = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=b"bad,row\n",
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="period",
    )
    assert result.state == "BLOCKED"
    with pytest.raises(ValueError, match="blocked"):
        build_audit_result_bundle(result, tmp_path / "blocked.zip")


def test_tampered_bundle_is_rejected(tmp_path):
    result = workflow()
    path = tmp_path / "result.zip"
    build_audit_result_bundle(result, path)

    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
        tampered, "w", compression=zipfile.ZIP_STORED
    ) as target:
        for name in source.namelist():
            data = source.read(name)
            if name == "summary.json":
                data = data + b" "
            target.writestr(name, data)

    with pytest.raises(ValueError, match="differs|manifest"):
        verify_audit_result_bundle(result, tampered)


def test_result_from_other_run_cannot_verify_bundle(tmp_path):
    result = workflow()
    clean = workflow(clean=True)
    path = tmp_path / "result.zip"
    build_audit_result_bundle(result, path)
    with pytest.raises(ValueError, match="manifest"):
        verify_audit_result_bundle(clean, path)
