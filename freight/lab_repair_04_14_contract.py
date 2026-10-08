"""RETALLY repaired Labs 04-14 evidence receipt gate.

This guards the *review/handoff* metadata for the separately downloadable,
isolated source-code patches. It does not replace the fixed lab engines,
prove any externally sourced invoice, or authenticate the hosted application.

Historical audits and PR #284/#286 remain owned by other branches.
"""
from __future__ import annotations

import re
from typing import Any

FINDINGS = frozenset({
    "Y-01", "Y-02", "Y-03", "Y-04",
    "X-01", "X-02", "X-03", "X-04", "X-05", "Z-01",
})
SOURCE_SHA256 = "7c670a91a1a411480b35d054b821f483744267b9c07acda9fe974d910888ed81"
ARCHIVE_SHA256 = "dc730dece0e9b8bbe92638bae551fc80e9720cf7a43c10ce2e4e8c6b0ee0729d"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class IncompleteRepairEvidence(ValueError):
    """A synthetic code-patch receipt does not satisfy its asserted scope."""


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise IncompleteRepairEvidence(message)


def validate_isolated_repair_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Verify narrow, attributable local evidence; never approve production."""
    ensure(isinstance(receipt, dict), "missing repair receipt")
    ensure(receipt.get("scope") == "ISOLATED_OFFLINE_SYNTHETIC_REPAIRS_ONLY",
           "repair scope must remain synthetic and isolated")
    ensure(receipt.get("production_modified") is False,
           "no production mutation is permitted")
    ensure(receipt.get("original_downloads_modified") is False,
           "historical evidence must not be overwritten")
    ids = receipt.get("assigned_findings")
    ensure(isinstance(ids, dict) and set(ids) == FINDINGS,
           "all ten non-overlapping legacy finding IDs must be identified")
    evidence = receipt.get("evidence")
    ensure(isinstance(evidence, dict), "two lab-lane receipts required")
    expected = {
        "labs04_10": (84, 10000, 70000, 509932),
        "labs11_14": (176, 10000, 40000, 195423),
    }
    for lane, (tests, inputs, cases, events) in expected.items():
        item = evidence.get(lane)
        ensure(isinstance(item, dict), f"missing {lane} evidence")
        for key, value in (
            ("regressions_passed", tests),
            ("regressions_total", tests),
            ("source_invoices", inputs),
            ("simulated_cases", cases),
            ("synthetic_events", events),
        ):
            ensure(type(item.get(key)) is int and item[key] == value,
                   f"{lane}: inconsistent {key}")
        ensure(item.get("source_bound_case_replay") is True,
               f"{lane}: structural-only replay cannot claim source anchoring")
        ensure(item.get("source_anchor_sha256") == SOURCE_SHA256,
               f"{lane}: wrong original fictional invoice source")
    unproven = receipt.get("not_yet_fixed")
    ensure(isinstance(unproven, dict), "unresolved gates must be visible")
    for key in ("unified_state_machine", "real_tenant_entitlement",
                "production_Retally_RecoveryOS", "legacy_7m_and_4m_archives"):
        ensure(isinstance(unproven.get(key), str) and unproven[key],
               f"missing unresolved gate: {key}")
    return {
        "status": "ACCEPTED_SYNTHETIC_PATCH_RECEIPT_ONLY",
        "finding_ids": sorted(FINDINGS),
        "historical_full_populations_recaptured": False,
        "hosted_product_verified": False,
        "customer_realized_cash_proven": False,
        "production_release_authorized": False,
    }


def validate_download_integrity_receipt(files: dict, archive_sha256: str) -> None:
    ensure(archive_sha256 == ARCHIVE_SHA256 and bool(HEX64.fullmatch(archive_sha256)),
           "wrong repaired artifact checksum")
    rows = files.get("files") if isinstance(files, dict) else None
    ensure(isinstance(rows, list) and len(rows) >= 600,
           "complete repair file manifest required")
    identities: set[str] = set()
    for row in rows:
        ensure(isinstance(row, dict), "invalid manifest entry")
        path = row.get("path")
        ensure(isinstance(path, str) and path and path not in identities,
               "duplicate/missing manifest path")
        ensure(not path.startswith("/") and "\\" not in path and
               ".." not in path.split("/"), "path traversal in manifest")
        identities.add(path)
        ensure(type(row.get("size_bytes")) is int and row["size_bytes"] >= 0,
               "invalid file size")
        ensure(isinstance(row.get("sha256"), str) and HEX64.fullmatch(row["sha256"]),
               "source file digest missing")


def full_scale_release_state(*, current_full_source_replay: bool,
                             old_7m_regenerated: bool,
                             old_4m_regenerated: bool,
                             real_buyer_evidence: bool,
                             verified_hosted_staging: bool) -> dict:
    """No asserted boolean grants real deployment without external review."""
    blockers: list[str] = []
    if not current_full_source_replay:
        blockers.append("FULL_INDEPENDENT_SOURCE_REPLAY_MISSING")
    if not old_7m_regenerated:
        blockers.append("LABS04_10_NEW_7M_REGENERATION_MISSING")
    if not old_4m_regenerated:
        blockers.append("LABS11_14_NEW_4M_REGENERATION_MISSING")
    if not real_buyer_evidence:
        blockers.append("REAL_BUYER_DATA_AND_BANK_EVIDENCE_MISSING")
    if not verified_hosted_staging:
        blockers.append("HOSTED_RECOVERYOS_STAGING_NOT_VERIFIED")
    return {
        "status": "BLOCKED" if blockers else "REVIEW_REQUIRED",
        "blockers": blockers,
        "automatically_deploy": False,
        "automatically_merge_other_chats_branches": False,
        "financial_integrity_certification": False,
        "manual_release_review_required": True,
    }
