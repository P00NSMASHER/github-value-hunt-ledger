"""Continuous Cletrics -> RecoveryOS ingestion with exact-job deduplication."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.branches.cloud_remediation import (
    CloudRemediationPlan,
    build_cloud_remediation_plan,
)
from recoveryworks.branches.cloud_savings import (
    CloudSavingsReport,
    build_cloud_savings_report,
)
from recoveryworks.branches.cloud_signals import CloudSignal
from recoveryworks.models import canonical_hash
from recoveryworks.runner import Scan360RunResult, run_scan360_config
from .cletrics import CletricsCloudBundle, load_cletrics_bundle
from .cletrics_registry import (
    CletricsProcessingReceipt,
    CletricsReceiptRegistry,
)
from .cletrics_supersession import (
    CloudSupersessionCandidate,
    build_cloud_supersession_candidate,
)


_CLETRICS_SECTIONS = ("cloud", "cloud_discount", "cloud_commitment")


@dataclass(frozen=True)
class ContinuousCletricsResult:
    scan: Scan360RunResult
    new_job_fingerprints: tuple[str, ...]
    duplicate_job_fingerprints: tuple[str, ...]
    supersession_required_fingerprints: tuple[str, ...]
    supersession_candidates: tuple[CloudSupersessionCandidate, ...]
    registry_hash: str
    cloud_signals: tuple[CloudSignal, ...]
    savings_report: CloudSavingsReport
    remediation_plan: CloudRemediationPlan | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "scan": self.scan.as_dict(),
            "new_job_fingerprints": list(self.new_job_fingerprints),
            "duplicate_job_fingerprints": list(self.duplicate_job_fingerprints),
            "supersession_required_fingerprints": list(
                self.supersession_required_fingerprints
            ),
            "supersession_candidates": [
                candidate.as_dict() for candidate in self.supersession_candidates
            ],
            "registry_hash": self.registry_hash,
            "cloud_signals": [signal.as_dict() for signal in self.cloud_signals],
            "financial_surfaces": {
                "recovery": self.scan.report.as_dict(),
                "savings": self.savings_report.as_dict(),
            },
            "remediation_plan": (
                self.remediation_plan.as_dict()
                if self.remediation_plan is not None
                else None
            ),
        }


def _jobs(section: Any) -> tuple[Mapping[str, Any], ...]:
    if section is None:
        return ()
    if isinstance(section, Mapping):
        return (section,)
    if isinstance(section, list) and all(isinstance(item, Mapping) for item in section):
        return tuple(section)
    raise ValueError("Cletrics continuous section must be an object or list")


def _file_hash(base: Path, value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    path = Path(value.strip())
    if not path.is_absolute():
        path = base / path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bool(job: Mapping[str, Any], key: str) -> bool:
    value = job.get(key, False)
    if type(value) is not bool:
        raise ValueError(f"{key} must be boolean")
    return value


def _authority_hashes(
    mode: str,
    job: Mapping[str, Any],
    base: Path,
) -> dict[str, str]:
    hashes = {
        "rates_csv": _file_hash(
            base, job.get("rates_csv"), name=f"{mode}.rates_csv"
        )
    }
    if mode == "cloud_discount":
        hashes["discounts_csv"] = _file_hash(
            base, job.get("discounts_csv"), name="cloud_discount.discounts_csv"
        )
    elif mode == "cloud_commitment":
        hashes["commitments_csv"] = _file_hash(
            base,
            job.get("commitments_csv"),
            name="cloud_commitment.commitments_csv",
        )
        hashes["allocations_csv"] = _file_hash(
            base,
            job.get("allocations_csv"),
            name="cloud_commitment.allocations_csv",
        )
    return hashes


def _verification_flags(mode: str, job: Mapping[str, Any]) -> dict[str, bool]:
    keys = [
        "charge_source_verified",
        "meter_source_verified",
        "rate_source_verified",
    ]
    if mode == "cloud_discount":
        keys.append("discount_source_verified")
    elif mode == "cloud_commitment":
        keys.extend(("commitment_source_verified", "allocation_source_verified"))
    return {key: _bool(job, key) for key in keys}


def _job_fingerprint(
    *,
    mode: str,
    bundle: CletricsCloudBundle,
    authority_hashes: Mapping[str, str],
    verification_flags: Mapping[str, bool],
    client_id: str,
    currency: str,
) -> str:
    return canonical_hash({
        "schema": 1,
        "mode": mode,
        "bundle_sha256": bundle.bundle_sha256,
        "manifest_sha256": bundle.manifest_sha256,
        "authority_hashes": dict(sorted(authority_hashes.items())),
        "verification_flags": dict(sorted(verification_flags.items())),
        "client_id": client_id,
        "currency": currency,
    })


def run_continuous_cletrics_scan(
    config: Mapping[str, Any],
    *,
    state_path: str | Path,
    registry_path: str | Path,
    base_dir: str | Path = ".",
) -> ContinuousCletricsResult:
    if not isinstance(config, Mapping):
        raise ValueError("config must be an object")
    client_id = str(config.get("client_id") or "").strip()
    if not client_id:
        raise ValueError("client_id is required")
    currency = str(config.get("currency") or "USD").strip().upper()
    base = Path(base_dir)
    registry = CletricsReceiptRegistry(registry_path)
    existing_receipts = registry.receipts()
    seen = {receipt.job_fingerprint for receipt in existing_receipts}

    filtered = dict(config)
    new_fingerprints: list[str] = []
    duplicate_fingerprints: list[str] = []
    supersession_required: list[str] = []
    supersession_candidates: list[CloudSupersessionCandidate] = []
    pending_receipts: list[tuple[str, str, CletricsCloudBundle, dict[str, str], dict[str, bool]]] = []
    signal_index: dict[str, CloudSignal] = {}

    for mode in _CLETRICS_SECTIONS:
        original = config.get(mode)
        rows = _jobs(original)
        if not rows:
            continue
        keep: list[Mapping[str, Any]] = []
        for job_index, job in enumerate(rows):
            bundle_value = job.get("cletrics_bundle")
            if not bundle_value:
                keep.append(job)
                continue
            bundle_path = Path(str(bundle_value))
            if not bundle_path.is_absolute():
                bundle_path = base / bundle_path
            flags = _verification_flags(mode, job)
            bundle = load_cletrics_bundle(
                bundle_path,
                charge_source_verified=flags["charge_source_verified"],
                meter_source_verified=flags["meter_source_verified"],
            )
            if bundle.client_id != client_id or bundle.currency != currency:
                raise ValueError(
                    f"{mode}[{job_index}] Cletrics scope does not match continuous scan"
                )
            for signal in bundle.signals:
                previous = signal_index.get(signal.signal_id)
                if previous is not None and previous.proof_hash != signal.proof_hash:
                    raise ValueError(
                        f"conflicting cloud signal_id: {signal.signal_id}"
                    )
                signal_index[signal.signal_id] = signal
            authority_hashes = _authority_hashes(mode, job, base)
            fingerprint = _job_fingerprint(
                mode=mode,
                bundle=bundle,
                authority_hashes=authority_hashes,
                verification_flags=flags,
                client_id=client_id,
                currency=currency,
            )
            if fingerprint in seen or fingerprint in new_fingerprints:
                duplicate_fingerprints.append(fingerprint)
                continue
            prior_scope = [
                receipt
                for receipt in existing_receipts
                if receipt.mode == mode
                and receipt.provider == bundle.provider
                and receipt.billing_account_id == bundle.billing_account_id
                and receipt.period_start == bundle.period_start
                and receipt.period_end == bundle.period_end
            ]
            if prior_scope:
                if len(prior_scope) != 1:
                    raise ValueError(
                        f"{mode}[{job_index}] has ambiguous prior processing receipts"
                    )
                supersession_required.append(fingerprint)
                supersession_candidates.append(
                    build_cloud_supersession_candidate(
                        prior_scope[0],
                        proposed_job_fingerprint=fingerprint,
                        proposed_bundle=bundle,
                        proposed_authority_hashes=authority_hashes,
                        proposed_verification_flags=flags,
                    )
                )
                continue
            new_fingerprints.append(fingerprint)
            keep.append(job)
            pending_receipts.append(
                (fingerprint, mode, bundle, authority_hashes, flags)
            )
        if isinstance(original, Mapping):
            if keep:
                filtered[mode] = keep[0]
            else:
                filtered.pop(mode, None)
        else:
            if keep:
                filtered[mode] = keep
            else:
                filtered.pop(mode, None)

    scan = run_scan360_config(
        filtered,
        state_path=state_path,
        base_dir=base,
    )

    for signal in scan.cloud_signals:
        previous = signal_index.get(signal.signal_id)
        if previous is not None and previous.proof_hash != signal.proof_hash:
            raise ValueError(f"conflicting cloud signal_id: {signal.signal_id}")
        signal_index[signal.signal_id] = signal
    combined_signals = tuple(signal_index[key] for key in sorted(signal_index))

    receipts = [
        CletricsProcessingReceipt(
            job_fingerprint=fingerprint,
            mode=mode,
            bundle_sha256=bundle.bundle_sha256,
            manifest_sha256=bundle.manifest_sha256,
            client_id=client_id,
            provider=bundle.provider,
            billing_account_id=bundle.billing_account_id,
            period_start=bundle.period_start,
            period_end=bundle.period_end,
            exported_at=bundle.exported_at,
            authority_hashes=authority_hashes,
            verification_flags=flags,
            scan_head_hash=scan.state_head_hash,
        )
        for fingerprint, mode, bundle, authority_hashes, flags in pending_receipts
    ]
    registry_hash = (
        registry.record(receipts)
        if receipts
        else registry.state_hash()
    )
    if registry_hash is None:
        registry_hash = registry.record(())

    savings_report = build_cloud_savings_report(combined_signals)
    remediation_cfg = config.get("cloud_remediation")
    remediation_plan = None
    if remediation_cfg is not None:
        if not isinstance(remediation_cfg, Mapping):
            raise ValueError("cloud_remediation must be an object")
        enabled = remediation_cfg.get("enabled", False)
        if type(enabled) is not bool:
            raise ValueError("cloud_remediation.enabled must be boolean")
        execute = remediation_cfg.get("execute", False)
        if type(execute) is not bool:
            raise ValueError("cloud_remediation.execute must be boolean")
        if execute:
            raise ValueError(
                "RecoveryOS remediation integration is plan-only; execution is unsupported"
            )
        if enabled:
            remediation_plan = build_cloud_remediation_plan(combined_signals)

    return ContinuousCletricsResult(
        scan=scan,
        new_job_fingerprints=tuple(sorted(new_fingerprints)),
        duplicate_job_fingerprints=tuple(sorted(duplicate_fingerprints)),
        supersession_required_fingerprints=tuple(
            sorted(supersession_required)
        ),
        supersession_candidates=tuple(
            sorted(supersession_candidates, key=lambda item: item.candidate_id)
        ),
        registry_hash=registry_hash,
        cloud_signals=combined_signals,
        savings_report=savings_report,
        remediation_plan=remediation_plan,
    )
