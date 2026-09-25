"""Fail-closed verification and adversarial certification for the production chain."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import hashlib
import random
from typing import Any, Callable, Mapping

from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.production_admission import ProductionAdmissionGate
from recoveryworks.release_control import (
    EnvironmentPromotionGate,
    RecoveryWorksReleaseManifest,
    ReleaseEnvironment,
)
from recoveryworks.release_deployment_handoff import (
    ReleaseDeploymentHandoff,
    ValidatedDeploymentReceipt,
)
from recoveryworks.release_package_integrity import ReleasePackageIntegrityReceipt


class ProductionChainState(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ProductionChainCheck:
    code: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ProductionChainInvariantReport:
    state: ProductionChainState
    checks: tuple[ProductionChainCheck, ...]
    release_id: str
    release_proof_hash: str
    checked_at: str
    external_actions_performed: bool = False
    automatic_repair_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "release_proof_hash",
            normalize_sha256("release_proof_hash", self.release_proof_hash),
        )
        object.__setattr__(
            self, "checked_at", normalize_utc_timestamp("checked_at", self.checked_at)
        )
        expected = (
            ProductionChainState.PASS
            if all(check.passed for check in self.checks)
            else ProductionChainState.BLOCKED
        )
        if self.state is not expected:
            raise ValueError("production chain state does not match checks")
        if self.external_actions_performed or self.automatic_repair_performed:
            raise ValueError("production chain verifier must remain read-only")

    @property
    def failed_codes(self) -> tuple[str, ...]:
        return tuple(check.code for check in self.checks if not check.passed)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "state": self.state.value,
            "checks": [
                {"code": c.code, "passed": c.passed, "detail": c.detail}
                for c in self.checks
            ],
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "checked_at": self.checked_at,
            "external_actions_performed": False,
            "automatic_repair_performed": False,
        })


def verify_production_chain(
    *,
    release: RecoveryWorksReleaseManifest,
    promotion_gate: EnvironmentPromotionGate,
    package_integrity: ReleasePackageIntegrityReceipt,
    admission: ProductionAdmissionGate,
    handoff: ReleaseDeploymentHandoff,
    post_deployment: ValidatedDeploymentReceipt,
    checked_at: str,
    previously_consumed_package_receipts: tuple[str, ...] = (),
) -> ProductionChainInvariantReport:
    checks: list[ProductionChainCheck] = []

    def add(code: str, passed: bool, detail: str) -> None:
        checks.append(ProductionChainCheck(code, bool(passed), detail))

    add(
        "RELEASE_PACKAGE_BINDING",
        package_integrity.verified
        and not package_integrity.external_actions_performed
        and package_integrity.release_id == release.release_id
        and package_integrity.release_proof_hash == release.proof_hash
        and package_integrity.promotion_gate_proof_hash == promotion_gate.proof_hash
        and package_integrity.adversarial_certification_proof_hash
        == promotion_gate.adversarial_certification_proof_hash,
        "durable package receipt must bind exact release, gate, and commercial certification",
    )
    consumed = {
        normalize_sha256("consumed_package_receipt", value)
        for value in previously_consumed_package_receipts
    }
    add(
        "RELEASE_PACKAGE_REPLAY",
        package_integrity.proof_hash not in consumed,
        "explicitly consumed release package receipt cannot be reused",
    )
    add(
        "PROMOTION_STATE_INTEGRITY",
        promotion_gate.environment is ReleaseEnvironment.PRODUCTION
        and promotion_gate.promotion_ready
        and not promotion_gate.promotion_execution_enabled
        and not promotion_gate.deployment_performed
        and promotion_gate.release_id == release.release_id
        and promotion_gate.release_proof_hash == release.proof_hash,
        "production promotion must remain ready, non-executing, and release-bound",
    )
    add(
        "ADMISSION_PACKAGE_BINDING",
        admission.admitted
        and not admission.deployment_execution_enabled
        and admission.release_id == release.release_id
        and admission.release_proof_hash == release.proof_hash
        and admission.promotion_gate_proof_hash == promotion_gate.proof_hash
        and admission.release_package_integrity_proof_hash
        == package_integrity.proof_hash
        and admission.container_image_digest == release.container_image_digest
        and admission.source_commit == release.source_commit,
        "admission must bind exact release, package, gate, image, and source",
    )
    add(
        "HANDOFF_ADMISSION_BINDING",
        handoff.release_id == release.release_id
        and handoff.release_proof_hash == release.proof_hash
        and handoff.promotion_gate_id == promotion_gate.gate_id
        and handoff.promotion_gate_proof_hash == promotion_gate.proof_hash
        and handoff.production_admission_id == admission.admission_id
        and handoff.production_admission_proof_hash == admission.proof_hash
        and handoff.container_image_digest == release.container_image_digest
        and handoff.source_commit == release.source_commit
        and handoff.production_deployment_proof_hash
        == release.production_deployment_proof_hash,
        "handoff must bind exact promotion, admission, release, image, source, and deployment contract",
    )
    deployed_at = normalize_utc_timestamp(
        "deployed_at", post_deployment.receipt.deployed_at
    )
    add(
        "HANDOFF_FRESHNESS",
        handoff.issued_at <= deployed_at <= handoff.expires_at,
        "deployment receipt must fall inside the authorized handoff window",
    )
    add(
        "POST_DEPLOYMENT_BINDING",
        post_deployment.verified
        and not post_deployment.external_actions_performed
        and post_deployment.handoff_id == handoff.handoff_id
        and post_deployment.handoff_proof_hash == handoff.proof_hash
        and post_deployment.production_admission_id == admission.admission_id
        and post_deployment.production_admission_proof_hash == admission.proof_hash
        and post_deployment.release_id == release.release_id
        and post_deployment.release_proof_hash == release.proof_hash
        and post_deployment.container_image_digest == release.container_image_digest
        and post_deployment.source_commit == release.source_commit
        and post_deployment.production_deployment_proof_hash
        == release.production_deployment_proof_hash,
        "post-deployment proof must bind exact handoff, admission, release, image, source, and deployment contract",
    )
    add(
        "NO_EXECUTION_ESCALATION",
        not promotion_gate.promotion_execution_enabled
        and not promotion_gate.deployment_performed
        and not admission.deployment_execution_enabled
        and handoff.credentials_embedded is False
        and handoff.deployment_performed_by_recoveryos is False
        and post_deployment.external_actions_performed is False,
        "RecoveryWorks proof chain cannot claim or perform deployment/external actions",
    )
    state = (
        ProductionChainState.PASS
        if all(check.passed for check in checks)
        else ProductionChainState.BLOCKED
    )
    return ProductionChainInvariantReport(
        state=state,
        checks=tuple(checks),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        checked_at=checked_at,
        external_actions_performed=False,
        automatic_repair_performed=False,
    )


class ProductionChainAdversarialVector(str, Enum):
    PROOF_TAMPERING = "PROOF_TAMPERING"
    CROSS_RELEASE_SUBSTITUTION = "CROSS_RELEASE_SUBSTITUTION"
    REPLAYED_PACKAGE_RECEIPT = "REPLAYED_PACKAGE_RECEIPT"
    STALE_HANDOFF = "STALE_HANDOFF"
    STATE_SKIPPING = "STATE_SKIPPING"
    POST_DEPLOYMENT_IDENTITY_TAMPERING = "POST_DEPLOYMENT_IDENTITY_TAMPERING"


@dataclass(frozen=True)
class ProductionChainAdversarialCase:
    vector: ProductionChainAdversarialVector
    iteration: int
    mutation: str
    expected_code: str
    observed_codes: tuple[str, ...]
    blocked: bool

    @property
    def passed(self) -> bool:
        return self.blocked and self.expected_code in self.observed_codes

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "vector": self.vector.value,
            "iteration": self.iteration,
            "mutation": self.mutation,
            "expected_code": self.expected_code,
            "observed_codes": list(self.observed_codes),
            "blocked": self.blocked,
        })


@dataclass(frozen=True)
class ProductionChainAdversarialCertification:
    source_revision: str
    baseline_report_proof_hash: str
    seed: int
    iterations_per_vector: int
    cases: tuple[ProductionChainAdversarialCase, ...]
    external_actions_performed: bool = False
    automatic_repair_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "baseline_report_proof_hash",
            normalize_sha256(
                "baseline_report_proof_hash", self.baseline_report_proof_hash
            ),
        )
        if any(not case.passed for case in self.cases):
            raise ValueError("production chain adversarial certification contains failures")
        expected = len(ProductionChainAdversarialVector) * self.iterations_per_vector
        if len(self.cases) != expected:
            raise ValueError("production chain adversarial coverage is incomplete")
        if self.external_actions_performed or self.automatic_repair_performed:
            raise ValueError("production chain adversarial certification must be read-only")

    @property
    def false_negative_count(self) -> int:
        return sum(not case.passed for case in self.cases)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "source_revision": self.source_revision,
            "baseline_report_proof_hash": self.baseline_report_proof_hash,
            "seed": self.seed,
            "iterations_per_vector": self.iterations_per_vector,
            "case_hashes": [case.proof_hash for case in self.cases],
            "external_actions_performed": False,
            "automatic_repair_performed": False,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_revision": self.source_revision,
            "baseline_report_proof_hash": self.baseline_report_proof_hash,
            "seed": self.seed,
            "iterations_per_vector": self.iterations_per_vector,
            "total_cases": len(self.cases),
            "false_negative_count": self.false_negative_count,
            "proof_hash": self.proof_hash,
            "external_actions_performed": False,
            "automatic_repair_performed": False,
            "state": "PASS",
        }


def _junk(seed: int, vector: ProductionChainAdversarialVector, iteration: int) -> str:
    return hashlib.sha256(f"{seed}|{vector.value}|{iteration}".encode()).hexdigest()


def run_production_chain_adversarial_certification(
    chain_factory: Callable[[], Mapping[str, Any]],
    *,
    source_revision: str,
    seed: int = 49001,
    iterations_per_vector: int = 4,
) -> ProductionChainAdversarialCertification:
    baseline_chain = dict(chain_factory())
    baseline = verify_production_chain(**baseline_chain)
    if baseline.state is not ProductionChainState.PASS:
        raise ValueError("production chain baseline must pass before red-team certification")

    rng = random.Random(seed)
    cases: list[ProductionChainAdversarialCase] = []
    for vector in ProductionChainAdversarialVector:
        for iteration in range(iterations_per_vector):
            chain = deepcopy(dict(chain_factory()))
            if vector is ProductionChainAdversarialVector.PROOF_TAMPERING:
                object.__setattr__(
                    chain["admission"],
                    "release_proof_hash",
                    _junk(seed, vector, iteration),
                )
                mutation, expected = "tampered admission release proof", "ADMISSION_PACKAGE_BINDING"
            elif vector is ProductionChainAdversarialVector.CROSS_RELEASE_SUBSTITUTION:
                object.__setattr__(
                    chain["handoff"],
                    "release_id",
                    f"substituted-release-{rng.randrange(1_000_000)}",
                )
                mutation, expected = "substituted handoff release", "HANDOFF_ADMISSION_BINDING"
            elif vector is ProductionChainAdversarialVector.REPLAYED_PACKAGE_RECEIPT:
                chain["previously_consumed_package_receipts"] = (
                    chain["package_integrity"].proof_hash,
                )
                mutation, expected = "replayed consumed package receipt", "RELEASE_PACKAGE_REPLAY"
            elif vector is ProductionChainAdversarialVector.STALE_HANDOFF:
                object.__setattr__(
                    chain["post_deployment"].receipt,
                    "deployed_at",
                    "2099-01-01T00:00:00Z",
                )
                mutation, expected = "forced deployment outside handoff window", "HANDOFF_FRESHNESS"
            elif vector is ProductionChainAdversarialVector.STATE_SKIPPING:
                target = rng.choice(("promotion", "admission"))
                if target == "promotion":
                    object.__setattr__(
                        chain["promotion_gate"], "promotion_execution_enabled", True
                    )
                    expected = "PROMOTION_STATE_INTEGRITY"
                else:
                    object.__setattr__(
                        chain["admission"], "deployment_execution_enabled", True
                    )
                    expected = "ADMISSION_PACKAGE_BINDING"
                mutation = f"forced {target} execution state"
            elif vector is ProductionChainAdversarialVector.POST_DEPLOYMENT_IDENTITY_TAMPERING:
                object.__setattr__(
                    chain["post_deployment"],
                    "container_image_digest",
                    _junk(seed, vector, iteration),
                )
                mutation, expected = "tampered deployed image digest", "POST_DEPLOYMENT_BINDING"
            else:
                raise AssertionError(vector)

            report = verify_production_chain(**chain)
            cases.append(
                ProductionChainAdversarialCase(
                    vector=vector,
                    iteration=iteration,
                    mutation=mutation,
                    expected_code=expected,
                    observed_codes=report.failed_codes,
                    blocked=report.state is ProductionChainState.BLOCKED,
                )
            )

    return ProductionChainAdversarialCertification(
        source_revision=source_revision,
        baseline_report_proof_hash=baseline.proof_hash,
        seed=seed,
        iterations_per_vector=iterations_per_vector,
        cases=tuple(cases),
        external_actions_performed=False,
        automatic_repair_performed=False,
    )
