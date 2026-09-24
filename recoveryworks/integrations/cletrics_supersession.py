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
