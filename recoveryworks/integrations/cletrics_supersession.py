"""Hash-bound review candidates for changed Cletrics processing authority.

This module is deliberately candidate-only. It identifies exactly what changed
between a completed processing receipt and a proposed same-scope reprocessing
job. It does not reject, replace, or mutate a RecoveryOS ledger record.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Mapping

from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_utc_timestamp,
)
from .cletrics import CletricsCloudBundle
from .cletrics_registry import CletricsProcessingReceipt


_ALLOWED_REASONS = {
    "BUNDLE_CHANGED",
    "MANIFEST_CHANGED",
    "AUTHORITY_CHANGED",
    "VERIFICATION_CHANGED",
}


@dataclass(frozen=True)
class CloudSupersessionCandidate:
    candidate_id: str
    prior_job_fingerprint: str
    proposed_job_fingerprint: str
    mode: str
    client_id: str
    provider: str
    billing_account_id: str
    period_start: str
    period_end: str
    prior_exported_at: str
    proposed_exported_at: str
    prior_bundle_sha256: str
    proposed_bundle_sha256: str
    prior_manifest_sha256: str
    proposed_manifest_sha256: str
    prior_authority_hashes: Mapping[str, str]
    proposed_authority_hashes: Mapping[str, str]
    prior_verification_flags: Mapping[str, bool]
    proposed_verification_flags: Mapping[str, bool]
    change_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "prior_job_fingerprint",
            "proposed_job_fingerprint",
            "prior_bundle_sha256",
            "proposed_bundle_sha256",
            "prior_manifest_sha256",
            "proposed_manifest_sha256",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        for name in ("mode", "client_id", "provider", "billing_account_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
            object.__setattr__(self, name, value.strip())
        try:
            start = date.fromisoformat(self.period_start).isoformat()
            end = date.fromisoformat(self.period_end).isoformat()
        except ValueError as exc:
            raise ValueError("supersession period must be YYYY-MM-DD") from exc
        if end < start:
            raise ValueError("period_end cannot predate period_start")
        object.__setattr__(self, "period_start", start)
        object.__setattr__(self, "period_end", end)
        object.__setattr__(
            self,
            "prior_exported_at",
            normalize_utc_timestamp("prior_exported_at", self.prior_exported_at),
        )
        object.__setattr__(
            self,
            "proposed_exported_at",
            normalize_utc_timestamp("proposed_exported_at", self.proposed_exported_at),
        )

        prior_hashes = {
            str(key): normalize_sha256(f"prior_authority_hashes.{key}", value)
            for key, value in self.prior_authority_hashes.items()
        }
        proposed_hashes = {
            str(key): normalize_sha256(f"proposed_authority_hashes.{key}", value)
            for key, value in self.proposed_authority_hashes.items()
        }
        object.__setattr__(
            self,
            "prior_authority_hashes",
            freeze_json(prior_hashes, name="prior_authority_hashes"),
        )
        object.__setattr__(
            self,
            "proposed_authority_hashes",
            freeze_json(proposed_hashes, name="proposed_authority_hashes"),
        )

        def flags(name: str, raw: Mapping[str, bool]) -> Mapping[str, bool]:
            normalized: dict[str, bool] = {}
            for key, value in raw.items():
                if type(value) is not bool:
                    raise ValueError(f"{name}.{key} must be boolean")
                normalized[str(key)] = value
            return freeze_json(normalized, name=name)

        object.__setattr__(
            self,
            "prior_verification_flags",
            flags("prior_verification_flags", self.prior_verification_flags),
        )
        object.__setattr__(
            self,
            "proposed_verification_flags",
            flags("proposed_verification_flags", self.proposed_verification_flags),
        )

        reasons = tuple(sorted(set(self.change_reasons)))
        if not reasons or any(reason not in _ALLOWED_REASONS for reason in reasons):
            raise ValueError("invalid or empty supersession change reasons")
        object.__setattr__(self, "change_reasons", reasons)

        expected = "cletrics-supersession:" + canonical_hash(self._identity())
        if self.candidate_id != expected:
            raise ValueError("candidate_id does not bind the exact supersession payload")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "prior_job_fingerprint": self.prior_job_fingerprint,
            "proposed_job_fingerprint": self.proposed_job_fingerprint,
            "mode": self.mode,
            "client_id": self.client_id,
            "provider": self.provider,
            "billing_account_id": self.billing_account_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "prior_exported_at": self.prior_exported_at,
            "proposed_exported_at": self.proposed_exported_at,
            "prior_bundle_sha256": self.prior_bundle_sha256,
            "proposed_bundle_sha256": self.proposed_bundle_sha256,
            "prior_manifest_sha256": self.prior_manifest_sha256,
            "proposed_manifest_sha256": self.proposed_manifest_sha256,
            "prior_authority_hashes": dict(self.prior_authority_hashes),
            "proposed_authority_hashes": dict(self.proposed_authority_hashes),
            "prior_verification_flags": dict(self.prior_verification_flags),
            "proposed_verification_flags": dict(self.proposed_verification_flags),
            "change_reasons": list(self.change_reasons),
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "proof_hash": self.proof_hash,
            "review_state": "REVIEW_REQUIRED",
            "ledger_mutation_allowed": False,
        }


def build_cloud_supersession_candidate(
    prior: CletricsProcessingReceipt,
    *,
    proposed_job_fingerprint: str,
    proposed_bundle: CletricsCloudBundle,
    proposed_authority_hashes: Mapping[str, str],
    proposed_verification_flags: Mapping[str, bool],
) -> CloudSupersessionCandidate:
    if (
        prior.client_id != proposed_bundle.client_id
        or prior.provider != proposed_bundle.provider
        or prior.billing_account_id != proposed_bundle.billing_account_id
        or prior.period_start != proposed_bundle.period_start
        or prior.period_end != proposed_bundle.period_end
    ):
        raise ValueError("supersession candidate scope does not match prior receipt")

    reasons: list[str] = []
    if prior.bundle_sha256 != proposed_bundle.bundle_sha256:
        reasons.append("BUNDLE_CHANGED")
    if prior.manifest_sha256 != proposed_bundle.manifest_sha256:
        reasons.append("MANIFEST_CHANGED")
    if dict(prior.authority_hashes) != dict(proposed_authority_hashes):
        reasons.append("AUTHORITY_CHANGED")
    if dict(prior.verification_flags) != dict(proposed_verification_flags):
        reasons.append("VERIFICATION_CHANGED")
    if not reasons:
        raise ValueError("supersession candidate requires a material processing change")

    identity = {
        "schema": 1,
        "prior_job_fingerprint": prior.job_fingerprint,
        "proposed_job_fingerprint": proposed_job_fingerprint,
        "mode": prior.mode,
        "client_id": prior.client_id,
        "provider": prior.provider,
        "billing_account_id": prior.billing_account_id,
        "period_start": prior.period_start,
        "period_end": prior.period_end,
        "prior_exported_at": prior.exported_at,
        "proposed_exported_at": proposed_bundle.exported_at,
        "prior_bundle_sha256": prior.bundle_sha256,
        "proposed_bundle_sha256": proposed_bundle.bundle_sha256,
        "prior_manifest_sha256": prior.manifest_sha256,
        "proposed_manifest_sha256": proposed_bundle.manifest_sha256,
        "prior_authority_hashes": dict(prior.authority_hashes),
        "proposed_authority_hashes": dict(proposed_authority_hashes),
        "prior_verification_flags": dict(prior.verification_flags),
        "proposed_verification_flags": dict(proposed_verification_flags),
        "change_reasons": sorted(reasons),
    }
    return CloudSupersessionCandidate(
        candidate_id="cletrics-supersession:" + canonical_hash(identity),
        prior_job_fingerprint=prior.job_fingerprint,
        proposed_job_fingerprint=proposed_job_fingerprint,
        mode=prior.mode,
        client_id=prior.client_id,
        provider=prior.provider,
        billing_account_id=prior.billing_account_id,
        period_start=prior.period_start,
        period_end=prior.period_end,
        prior_exported_at=prior.exported_at,
        proposed_exported_at=proposed_bundle.exported_at,
        prior_bundle_sha256=prior.bundle_sha256,
        proposed_bundle_sha256=proposed_bundle.bundle_sha256,
        prior_manifest_sha256=prior.manifest_sha256,
        proposed_manifest_sha256=proposed_bundle.manifest_sha256,
        prior_authority_hashes=prior.authority_hashes,
        proposed_authority_hashes=proposed_authority_hashes,
        prior_verification_flags=prior.verification_flags,
        proposed_verification_flags=proposed_verification_flags,
        change_reasons=tuple(reasons),
    )


@dataclass(frozen=True)
class CloudSupersessionBinding:
    reference: str
    incumbent_finding_id: str | None
    incumbent_proof_hash: str | None
    incumbent_case_state: str | None
    replacement_finding_id: str | None
    replacement_proof_hash: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.reference, str) or not self.reference.strip():
            raise ValueError("reference is required")
        object.__setattr__(self, "reference", self.reference.strip())
        pairs = (
            ("incumbent", self.incumbent_finding_id, self.incumbent_proof_hash),
            ("replacement", self.replacement_finding_id, self.replacement_proof_hash),
        )
        present = 0
        for label, finding_id, proof_hash in pairs:
            if finding_id is None and proof_hash is None:
                continue
            if finding_id is None or proof_hash is None:
                raise ValueError(f"{label} finding id/proof must be supplied together")
            if not isinstance(finding_id, str) or not finding_id.strip():
                raise ValueError(f"{label}_finding_id is required")
            normalize_sha256(f"{label}_proof_hash", proof_hash)
            present += 1
        if present == 0:
            raise ValueError("supersession binding must contain incumbent or replacement")
        if self.incumbent_case_state is not None and self.incumbent_finding_id is None:
            raise ValueError("incumbent_case_state requires an incumbent finding")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class CloudSupersessionApproval:
    approval_id: str
    candidate_id: str
    candidate_proof_hash: str
    reviewer_id: str
    review_note: str
    approved_at: str
    bindings: tuple[CloudSupersessionBinding, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_proof_hash",
            normalize_sha256("candidate_proof_hash", self.candidate_proof_hash),
        )
        for name in ("candidate_id", "reviewer_id", "review_note"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(
            self,
            "approved_at",
            normalize_utc_timestamp("approved_at", self.approved_at),
        )
        bindings = tuple(sorted(self.bindings, key=lambda item: item.reference))
        if len({item.reference for item in bindings}) != len(bindings):
            raise ValueError("supersession approval has duplicate references")
        for binding in bindings:
            if binding.incumbent_case_state not in {None, "REVIEW", "VALIDATED"}:
                raise ValueError(
                    "only REVIEW/VALIDATED incumbents may be superseded"
                )
        object.__setattr__(self, "bindings", bindings)
        expected = "cloud-supersession-approval:" + canonical_hash(self._identity())
        if self.approval_id != expected:
            raise ValueError("approval_id does not bind the supersession approval")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "candidate_id": self.candidate_id,
            "candidate_proof_hash": self.candidate_proof_hash,
            "reviewer_id": self.reviewer_id,
            "review_note": self.review_note,
            "approved_at": self.approved_at,
            "binding_hashes": [binding.proof_hash for binding in self.bindings],
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "proof_hash": self.proof_hash,
            "decision": "APPROVE",
        }


def approve_cloud_supersession(
    candidate: CloudSupersessionCandidate,
    *,
    bindings: tuple[CloudSupersessionBinding, ...],
    reviewer_id: str,
    review_note: str,
    approved_at: str,
) -> CloudSupersessionApproval:
    approved_at = normalize_utc_timestamp("approved_at", approved_at)
    identity = {
        "schema": 1,
        "candidate_id": candidate.candidate_id,
        "candidate_proof_hash": candidate.proof_hash,
        "reviewer_id": reviewer_id.strip(),
        "review_note": review_note.strip(),
        "approved_at": approved_at,
        "binding_hashes": [
            binding.proof_hash
            for binding in sorted(bindings, key=lambda item: item.reference)
        ],
    }
    return CloudSupersessionApproval(
        approval_id="cloud-supersession-approval:" + canonical_hash(identity),
        candidate_id=candidate.candidate_id,
        candidate_proof_hash=candidate.proof_hash,
        reviewer_id=reviewer_id,
        review_note=review_note,
        approved_at=approved_at,
        bindings=bindings,
    )
