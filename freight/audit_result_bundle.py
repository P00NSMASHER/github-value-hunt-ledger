"""Deterministic Freight Recovery audit-result bundle.

This package is for the approved customer-processing environment. It contains
derived customer audit evidence, but deliberately excludes raw source files.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from freight.audit_workflow import (
    AuditWorkflowResult,
    AuditWorkflowState,
    render_workflow_summary,
)
from freight.review_packet import render_review_packet_markdown
from freight.remediation_plan import render_remediation_plan_markdown


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class AuditResultBundleReceipt:
    state: str
    run_hash: str
    entry_count: int
    manifest_sha256: str
    bundle_sha256: str


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def build_audit_result_entries(result: AuditWorkflowResult) -> dict[str, bytes]:
    if result.state == AuditWorkflowState.BLOCKED.value:
        raise ValueError("blocked audit workflow cannot produce an audit-result bundle")
    if result.summary is None or result.artifacts is None:
        raise ValueError("successful audit workflow is missing summary/artifacts")

    summary = result.summary
    artifacts = result.artifacts
    if summary.run_hash != artifacts.manifest.run_hash:
        raise ValueError("workflow summary run hash does not match audit manifest")
    if summary.state != result.state:
        raise ValueError("workflow summary state mismatch")

    rules = tuple(
        rule
        for batch in artifacts.rule_batches
        for rule in batch.rules
    )

    return {
        "summary.json": _json_bytes(asdict(summary)),
        "summary.md": render_workflow_summary(result).encode("utf-8"),
        "audit-run-manifest.json": _json_bytes(asdict(artifacts.manifest)),
        "truth-manifest.json": _json_bytes(asdict(artifacts.factory.truth)),
        "derivations.json": _json_bytes(
            [asdict(item) for item in artifacts.factory.derivations]
        ),
        "normalized-charges.json": _json_bytes(
            [asdict(item) for item in artifacts.invoice_batch.charges]
        ),
        "normalized-rules.json": _json_bytes(
            [asdict(item) for item in rules]
        ),
        "review-queue.json": _json_bytes(asdict(artifacts.review_queue)),
        "review-routing.json": _json_bytes(asdict(artifacts.review_routing)),
        "remediation-plan.json": _json_bytes(asdict(artifacts.remediation_plan)),
        "remediation-plan.md": render_remediation_plan_markdown(
            artifacts.remediation_plan
        ).encode("utf-8"),
        "review-packet.json": _json_bytes(asdict(artifacts.review_packet)),
        "review-packet.md": render_review_packet_markdown(
            artifacts.review_packet
        ).encode("utf-8"),
    }


def _bundle_manifest(result: AuditWorkflowResult, entries: dict[str, bytes]) -> dict:
    assert result.summary is not None
    rows = [
        {
            "path": path,
            "size_bytes": len(data),
            "sha256": _sha(data),
        }
        for path, data in sorted(entries.items())
    ]
    return {
        "schema_version": 1,
        "product": "Freight Recovery",
        "bundle_type": "AUDIT_RESULT",
        "state": result.state,
        "run_hash": result.summary.run_hash,
        "customer_data_included": True,
        "raw_source_files_included": False,
        "claim_boundary": [
            "Contains normalized/derived customer audit evidence.",
            "Does not include raw invoice, rate, contract or settlement source files.",
            "Discrepancy amounts are not realized savings.",
            "Review routing separates buyer-ready cases from evidence remediation/rerun cases.",
            "The remediation plan states required evidence and forbids manual promotion in place.",
            "Buyer review, external action and settlement remain separate downstream states.",
            "Bundle must remain inside an approved customer-processing environment.",
        ],
        "entries": rows,
    }


def build_audit_result_bundle(
    result: AuditWorkflowResult,
    destination: Path,
) -> AuditResultBundleReceipt:
    entries = build_audit_result_entries(result)
    manifest = _bundle_manifest(result, entries)
    manifest_bytes = _json_bytes(manifest)
    all_entries = {
        **entries,
        "RESULT_BUNDLE_MANIFEST.json": manifest_bytes,
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for path, data in sorted(all_entries.items()):
            info = zipfile.ZipInfo(path, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)

    assert result.summary is not None
    return AuditResultBundleReceipt(
        state=result.state,
        run_hash=result.summary.run_hash,
        entry_count=len(all_entries),
        manifest_sha256=_sha(manifest_bytes),
        bundle_sha256=_sha(destination.read_bytes()),
    )


def verify_audit_result_bundle(
    result: AuditWorkflowResult,
    bundle: Path,
) -> None:
    expected_entries = build_audit_result_entries(result)
    expected_manifest = _bundle_manifest(result, expected_entries)

    with zipfile.ZipFile(bundle, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate audit-result bundle entry")
        if "RESULT_BUNDLE_MANIFEST.json" not in names:
            raise ValueError("audit-result bundle manifest missing")

        manifest = json.loads(archive.read("RESULT_BUNDLE_MANIFEST.json"))
        if manifest != expected_manifest:
            raise ValueError("audit-result bundle manifest does not match workflow")
        if manifest.get("customer_data_included") is not True:
            raise ValueError("audit-result bundle must declare customer-derived data")
        if manifest.get("raw_source_files_included") is not False:
            raise ValueError("audit-result bundle must not claim raw source inclusion")

        rows = {
            row["path"]: row
            for row in manifest.get("entries", [])
        }
        if set(rows) != set(expected_entries):
            raise ValueError("audit-result bundle manifest entry set mismatch")
        if set(names) != set(expected_entries) | {"RESULT_BUNDLE_MANIFEST.json"}:
            raise ValueError("audit-result bundle archive entry set mismatch")

        for path, expected in expected_entries.items():
            actual = archive.read(path)
            if actual != expected:
                raise ValueError("audit-result bundle entry differs from workflow: " + path)
            row = rows[path]
            if row.get("sha256") != _sha(actual):
                raise ValueError("audit-result bundle entry hash mismatch: " + path)
            if row.get("size_bytes") != len(actual):
                raise ValueError("audit-result bundle entry size mismatch: " + path)
