"""Safeguards against upgrading a narrow offline patch into an unearned PASS."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from freight.lab_repair_04_14_contract import (
    ARCHIVE_SHA256, FINDINGS, IncompleteRepairEvidence,
    SOURCE_SHA256, full_scale_release_state,
    validate_download_integrity_receipt,
    validate_isolated_repair_receipt,
)


def receipt():
    return {
        "scope": "ISOLATED_OFFLINE_SYNTHETIC_REPAIRS_ONLY",
        "production_modified": False,
        "original_downloads_modified": False,
        "assigned_findings": {x: "synthetic tested" for x in FINDINGS},
        "evidence": {
            "labs04_10": {
                "regressions_passed": 84, "regressions_total": 84,
                "source_invoices": 10000, "simulated_cases": 70000,
                "synthetic_events": 509932, "source_bound_case_replay": True,
                "source_anchor_sha256": SOURCE_SHA256,
            },
            "labs11_14": {
                "regressions_passed": 176, "regressions_total": 176,
                "source_invoices": 10000, "simulated_cases": 40000,
                "synthetic_events": 195423, "source_bound_case_replay": True,
                "source_anchor_sha256": SOURCE_SHA256,
            },
        },
        "not_yet_fixed": {
            "unified_state_machine": "Other chat owns original",
            "real_tenant_entitlement": "Not independently signed",
            "production_Retally_RecoveryOS": "Not deployed",
            "legacy_7m_and_4m_archives": "Must be regenerated",
        },
    }


def test_positive_receipt_is_narrow_and_never_deployment_authorization():
    result = validate_isolated_repair_receipt(receipt())
    assert result["status"] == "ACCEPTED_SYNTHETIC_PATCH_RECEIPT_ONLY"
    assert len(result["finding_ids"]) == 10
    assert result["hosted_product_verified"] is False
    assert result["production_release_authorized"] is False


@pytest.mark.parametrize("mutation", [
    lambda r: r["evidence"]["labs04_10"].update(source_bound_case_replay=False),
    lambda r: r["evidence"]["labs11_14"].update(source_anchor_sha256="0"*64),
    lambda r: r["evidence"]["labs04_10"].update(simulated_cases=7_000_000),
    lambda r: r["evidence"]["labs11_14"].update(regressions_passed=175),
    lambda r: r.update(production_modified=True),
    lambda r: r["assigned_findings"].pop("Y-01"),
    lambda r: r["not_yet_fixed"].pop("legacy_7m_and_4m_archives"),
])
def test_missing_or_exaggerated_evidence_is_rejected(mutation):
    r=receipt()
    mutation(r)
    with pytest.raises(IncompleteRepairEvidence):
        validate_isolated_repair_receipt(r)


def test_unverified_four_million_and_seven_million_always_block():
    r=full_scale_release_state(current_full_source_replay=True,
          old_7m_regenerated=False,old_4m_regenerated=False,
          real_buyer_evidence=False,verified_hosted_staging=False)
    assert r["status"]=="BLOCKED"
    assert "LABS04_10_NEW_7M_REGENERATION_MISSING" in r["blockers"]
    assert "LABS11_14_NEW_4M_REGENERATION_MISSING" in r["blockers"]
    assert r["automatically_deploy"] is False


def test_even_all_inputs_asserted_true_do_not_automatically_certify_money():
    r=full_scale_release_state(current_full_source_replay=True,
         old_7m_regenerated=True,old_4m_regenerated=True,
         real_buyer_evidence=True,verified_hosted_staging=True)
    assert r["status"]=="REVIEW_REQUIRED"
    assert r["automatically_deploy"] is False
    assert r["financial_integrity_certification"] is False


def test_duplicate_archive_or_path_fails_closed():
    valid={"files":[{"path":f"fictional/{i}.json",
           "size_bytes":i,"sha256":hashlib.sha256(str(i).encode()).hexdigest()}
           for i in range(640)]}
    validate_download_integrity_receipt(valid,ARCHIVE_SHA256)
    valid["files"][1]["path"]=valid["files"][0]["path"]
    with pytest.raises(IncompleteRepairEvidence):
        validate_download_integrity_receipt(valid,ARCHIVE_SHA256)


def test_archive_checksum_is_not_accepted_from_untrusted_supplied_value():
    good={"files":[{"path":f"fictional/{i}.json",
           "size_bytes":i,"sha256":hashlib.sha256(str(i).encode()).hexdigest()}
           for i in range(640)]}
    with pytest.raises(IncompleteRepairEvidence):
        validate_download_integrity_receipt(good,"0"*64)
