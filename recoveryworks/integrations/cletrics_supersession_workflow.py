"""Reviewed application workflow for Cletrics cloud supersession."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Any, Mapping

from recoveryworks.models import Branch, CaseState, RecoveryFinding
from recoveryworks.report import RecoveryScan360Report, build_scan360_report
from recoveryworks.runner import run_scan360_config
from recoveryworks.store import LocalBundleStore
from .cletrics import CletricsCloudBundle, load_cletrics_bundle
from .cletrics_continuous import (
    _authority_hashes,
    _job_fingerprint,
    _jobs,
    _verification_flags,
)
from .cletrics_registry import (
    CletricsProcessingReceipt,
    CletricsReceiptRegistry,
)
from .cletrics_supersession import (
    CloudSupersessionApproval,
    CloudSupersessionBinding,
    CloudSupersessionCandidate,
    approve_cloud_supersession,
)


@dataclass(frozen=True)
class CloudSupersessionPreview:
    candidate: CloudSupersessionCandidate
    bindings: tuple[CloudSupersessionBinding, ...]
    replacement_findings: tuple[RecoveryFinding, ...]
    proposed_bundle: CletricsCloudBundle
    proposed_authority_hashes: Mapping[str, str]
    proposed_verification_flags: Mapping[str, bool]
    proposed_config: Mapping[str, Any]
    preview_exceptions: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.as_dict(),
            "bindings": [
                {
                    "reference": binding.reference,
                    "incumbent_finding_id": binding.incumbent_finding_id,
                    "incumbent_proof_hash": binding.incumbent_proof_hash,
                    "incumbent_case_state": binding.incumbent_case_state,
                    "replacement_finding_id": binding.replacement_finding_id,
                    "replacement_proof_hash": binding.replacement_proof_hash,
                    "proof_hash": binding.proof_hash,
                }
                for binding in self.bindings
            ],
            "replacement_finding_ids": [
                finding.finding_id for finding in self.replacement_findings
            ],
            "preview_exceptions": [dict(item) for item in self.preview_exceptions],
            "ledger_mutation_allowed": False,
        }


@dataclass(frozen=True)
class CloudSupersessionApplyResult:
    approval: CloudSupersessionApproval
    superseded_finding_ids: tuple[str, ...]
    replacement_finding_ids: tuple[str, ...]
    state_head_hash: str | None
    registry_hash: str
    report: RecoveryScan360Report

    def as_dict(self) -> dict[str, Any]:
        return {
            "approval": self.approval.as_dict(),
            "superseded_finding_ids": list(self.superseded_finding_ids),
            "replacement_finding_ids": list(self.replacement_finding_ids),
            "state_head_hash": self.state_head_hash,
            "registry_hash": self.registry_hash,
            "report": self.report.as_dict(),
        }


def _matching_job(
    candidate: CloudSupersessionCandidate,
    config: Mapping[str, Any],
    base: Path,
) -> tuple[Mapping[str, Any], CletricsCloudBundle, dict[str, str], dict[str, bool]]:
    client_id = str(config.get("client_id") or "").strip()
    currency = str(config.get("currency") or "USD").strip().upper()
    if client_id != candidate.client_id:
        raise ValueError("supersession config client_id does not match candidate")
    rows = _jobs(config.get(candidate.mode))
    matches: list[
        tuple[Mapping[str, Any], CletricsCloudBundle, dict[str, str], dict[str, bool]]
    ] = []
    for job in rows:
        bundle_value = job.get("cletrics_bundle")
        if not bundle_value:
            continue
        path = Path(str(bundle_value))
        if not path.is_absolute():
            path = base / path
        flags = _verification_flags(candidate.mode, job)
        bundle = load_cletrics_bundle(
            path,
            charge_source_verified=flags["charge_source_verified"],
            meter_source_verified=flags["meter_source_verified"],
        )
        authority_hashes = _authority_hashes(candidate.mode, job, base)
        fingerprint = _job_fingerprint(
            mode=candidate.mode,
            bundle=bundle,
            authority_hashes=authority_hashes,
            verification_flags=flags,
            client_id=client_id,
            currency=currency,
        )
        if fingerprint == candidate.proposed_job_fingerprint:
            matches.append((job, bundle, authority_hashes, flags))
    if len(matches) != 1:
        raise ValueError(
            "supersession review requires exactly one job matching the proposed fingerprint"
        )
    job, bundle, authority_hashes, flags = matches[0]
    if (
        bundle.bundle_sha256 != candidate.proposed_bundle_sha256
        or bundle.manifest_sha256 != candidate.proposed_manifest_sha256
        or bundle.exported_at != candidate.proposed_exported_at
    ):
        raise ValueError("supersession proposed bundle no longer matches candidate")
    return job, bundle, authority_hashes, flags


def _in_scope(record, candidate: CloudSupersessionCandidate) -> bool:
    finding = record.finding
    if finding.branch is not Branch.CLOUD or finding.client_id != candidate.client_id:
        return False
    metadata = finding.metadata
    account = str(metadata.get("account_id") or "")
    service_date = str(metadata.get("service_date") or "")
    return (
        account == candidate.billing_account_id
        and candidate.period_start <= service_date <= candidate.period_end
    )


def prepare_cloud_supersession_preview(
    candidate: CloudSupersessionCandidate,
    proposed_config: Mapping[str, Any],
    *,
    state_path: str | Path,
    base_dir: str | Path = ".",
) -> CloudSupersessionPreview:
    base = Path(base_dir)
    live = LocalBundleStore(state_path).load()
    if live is None:
        raise ValueError("supersession requires an existing RecoveryOS ledger")

    job, bundle, authority_hashes, flags = _matching_job(
        candidate, proposed_config, base
    )
    preview_config = {
        "client_id": candidate.client_id,
        "currency": str(proposed_config.get("currency") or "USD").strip().upper(),
        candidate.mode: dict(job),
    }
    with tempfile.TemporaryDirectory() as directory:
        preview_state = Path(directory) / "preview-ledger.json"
        preview_run = run_scan360_config(
            preview_config,
            state_path=preview_state,
            base_dir=base,
        )
        proposed_ledger = LocalBundleStore(preview_state).load()
        if proposed_ledger is None:
            raise AssertionError("supersession preview failed to produce a ledger")

    incumbent_by_reference: dict[str, Any] = {}
    for record in live.records():
        if not _in_scope(record, candidate):
            continue
        if record.case_state in {CaseState.REJECTED, CaseState.SUPERSEDED}:
            continue
        previous = incumbent_by_reference.get(record.finding.reference)
        if previous is not None:
            raise ValueError(
                f"multiple active incumbents exist for cloud reference {record.finding.reference}"
            )
        incumbent_by_reference[record.finding.reference] = record

    replacement_by_reference: dict[str, RecoveryFinding] = {}
    for record in proposed_ledger.records():
        if not _in_scope(record, candidate):
            continue
        previous = replacement_by_reference.get(record.finding.reference)
        if previous is not None:
            raise ValueError(
                f"multiple proposed findings exist for cloud reference {record.finding.reference}"
            )
        replacement_by_reference[record.finding.reference] = record.finding

    bindings: list[CloudSupersessionBinding] = []
    replacement_findings: list[RecoveryFinding] = []
    for reference in sorted(
        set(incumbent_by_reference) | set(replacement_by_reference)
    ):
        incumbent = incumbent_by_reference.get(reference)
        replacement = replacement_by_reference.get(reference)
        if (
            incumbent is not None
            and replacement is not None
            and incumbent.finding.proof_hash == replacement.proof_hash
        ):
            continue
        bindings.append(
            CloudSupersessionBinding(
                reference=reference,
                incumbent_finding_id=(
                    incumbent.finding.finding_id if incumbent is not None else None
                ),
                incumbent_proof_hash=(
                    incumbent.finding.proof_hash if incumbent is not None else None
                ),
                incumbent_case_state=(
                    incumbent.case_state.value if incumbent is not None else None
                ),
                replacement_finding_id=(
                    replacement.finding_id if replacement is not None else None
                ),
                replacement_proof_hash=(
                    replacement.proof_hash if replacement is not None else None
                ),
            )
        )
        if replacement is not None:
            replacement_findings.append(replacement)

    return CloudSupersessionPreview(
        candidate=candidate,
        bindings=tuple(bindings),
        replacement_findings=tuple(
            sorted(replacement_findings, key=lambda item: item.finding_id)
        ),
        proposed_bundle=bundle,
        proposed_authority_hashes=authority_hashes,
        proposed_verification_flags=flags,
        proposed_config=preview_config,
        preview_exceptions=preview_run.exceptions,
    )


def approve_cloud_supersession_preview(
    preview: CloudSupersessionPreview,
    *,
    reviewer_id: str,
    review_note: str,
    approved_at: str,
) -> CloudSupersessionApproval:
    return approve_cloud_supersession(
        preview.candidate,
        bindings=preview.bindings,
        reviewer_id=reviewer_id,
        review_note=review_note,
        approved_at=approved_at,
    )


def apply_cloud_supersession(
    preview: CloudSupersessionPreview,
    approval: CloudSupersessionApproval,
    *,
    state_path: str | Path,
    registry_path: str | Path,
) -> CloudSupersessionApplyResult:
    if approval.candidate_id != preview.candidate.candidate_id:
        raise ValueError("supersession approval candidate mismatch")
    if approval.candidate_proof_hash != preview.candidate.proof_hash:
        raise ValueError("supersession approval candidate proof mismatch")
    if tuple(item.proof_hash for item in approval.bindings) != tuple(
        item.proof_hash for item in preview.bindings
    ):
        raise ValueError("supersession approval bindings do not match preview")

    store = LocalBundleStore(state_path)
    ledger = store.load()
    if ledger is None:
        raise ValueError("supersession requires an existing RecoveryOS ledger")
    loaded_head = ledger.journal.head_hash

    replacements = {
        finding.finding_id: finding for finding in preview.replacement_findings
    }
    superseded: list[str] = []
    for binding in approval.bindings:
        if binding.incumbent_finding_id is None:
            continue
        record = ledger.get(binding.incumbent_finding_id)
        if record.finding.proof_hash != binding.incumbent_proof_hash:
            raise ValueError("incumbent finding changed after supersession preview")
        if record.case_state.value != binding.incumbent_case_state:
            raise ValueError("incumbent case state changed after supersession preview")
        ledger.supersede(
            binding.incumbent_finding_id,
            replacement_finding_id=binding.replacement_finding_id,
            approval_hash=approval.proof_hash,
            reviewer_id=approval.reviewer_id,
            note=approval.review_note,
            occurred_at=approval.approved_at,
        )
        superseded.append(binding.incumbent_finding_id)

    replacement_ids: list[str] = []
    for binding in approval.bindings:
        if binding.replacement_finding_id is None:
            continue
        finding = replacements.get(binding.replacement_finding_id)
        if finding is None or finding.proof_hash != binding.replacement_proof_hash:
            raise ValueError("replacement finding does not match approved supersession")
        ledger.add(finding, occurred_at=approval.approved_at)
        replacement_ids.append(finding.finding_id)

    new_head = store.save(
        ledger,
        expected_head_hash=loaded_head,
        enforce_expected=True,
    )

    receipt = CletricsProcessingReceipt(
        job_fingerprint=preview.candidate.proposed_job_fingerprint,
        mode=preview.candidate.mode,
        bundle_sha256=preview.candidate.proposed_bundle_sha256,
        manifest_sha256=preview.candidate.proposed_manifest_sha256,
        client_id=preview.candidate.client_id,
        provider=preview.candidate.provider,
        billing_account_id=preview.candidate.billing_account_id,
        period_start=preview.candidate.period_start,
        period_end=preview.candidate.period_end,
        exported_at=preview.candidate.proposed_exported_at,
        authority_hashes=preview.proposed_authority_hashes,
        verification_flags=preview.proposed_verification_flags,
        scan_head_hash=new_head,
    )
    registry = CletricsReceiptRegistry(registry_path)
    if not registry.contains(preview.candidate.prior_job_fingerprint):
        raise ValueError("prior processing receipt disappeared before supersession")
    registry_hash = registry.replace(
        prior_job_fingerprint=preview.candidate.prior_job_fingerprint,
        replacement=receipt,
    )
    return CloudSupersessionApplyResult(
        approval=approval,
        superseded_finding_ids=tuple(sorted(superseded)),
        replacement_finding_ids=tuple(sorted(replacement_ids)),
        state_head_hash=new_head,
        registry_hash=registry_hash,
        report=build_scan360_report(ledger, preview.candidate.client_id),
    )
