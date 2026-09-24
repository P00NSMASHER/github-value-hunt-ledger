"""Seeded adversarial certification for the RecoveryWorks commercial proof chain.

The harness is deterministic and read-only. It starts from a known-good chain,
injects one controlled adversarial mutation per case, and requires the unified
commercial invariant verifier to return a structured BLOCKED result with the
expected invariant code. A verifier crash or false negative fails certification.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import hashlib
import random
from typing import Any, Callable, Mapping

from recoveryworks.commercial_operational_invariants import (
    CommercialOperationalInvariantState,
    verify_commercial_operational_invariants,
)
from recoveryworks.models import canonical_hash, normalize_sha256
from recoveryworks.recurring_assurance_lifecycle import (
    RecurringAssuranceLifecycleState,
)


class AdversarialVector(str, Enum):
    PROOF_TAMPERING = "PROOF_TAMPERING"
    CROSS_TENANT_SUBSTITUTION = "CROSS_TENANT_SUBSTITUTION"
    AMOUNT_SURFACE_CONFUSION = "AMOUNT_SURFACE_CONFUSION"
    STALE_AUTHORIZATION = "STALE_AUTHORIZATION"
    DUPLICATE_SETTLEMENT = "DUPLICATE_SETTLEMENT"
    REPLAYED_RECEIPT = "REPLAYED_RECEIPT"
    LIFECYCLE_STATE_SKIPPING = "LIFECYCLE_STATE_SKIPPING"


class AdversarialCertificationState(str, Enum):
    PASS = "PASS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class AdversarialCaseResult:
    case_id: str
    vector: AdversarialVector
    iteration: int
    mutation: str
    expected_failure_codes: tuple[str, ...]
    observed_failure_codes: tuple[str, ...]
    blocked: bool
    verifier_report_proof_hash: str | None
    verifier_error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.vector, AdversarialVector):
            raise ValueError("vector must be AdversarialVector")
        if type(self.iteration) is not int or self.iteration < 0:
            raise ValueError("iteration must be non-negative")
        if not self.mutation:
            raise ValueError("mutation description is required")
        expected = tuple(sorted(set(self.expected_failure_codes)))
        observed = tuple(sorted(set(self.observed_failure_codes)))
        if not expected:
            raise ValueError("adversarial case requires expected failure codes")
        object.__setattr__(self, "expected_failure_codes", expected)
        object.__setattr__(self, "observed_failure_codes", observed)
        if self.verifier_report_proof_hash is not None:
            object.__setattr__(
                self,
                "verifier_report_proof_hash",
                normalize_sha256(
                    "verifier_report_proof_hash",
                    self.verifier_report_proof_hash,
                ),
            )
        expected_id = "recoveryworks-adversarial-case:" + canonical_hash(
            self._identity()
        )
        if self.case_id != expected_id:
            raise ValueError("case_id does not bind adversarial case")

    @property
    def passed(self) -> bool:
        return (
            self.blocked
            and self.verifier_error is None
            and set(self.expected_failure_codes).issubset(
                self.observed_failure_codes
            )
        )

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "vector": self.vector.value,
            "iteration": self.iteration,
            "mutation": self.mutation,
            "expected_failure_codes": list(self.expected_failure_codes),
            "observed_failure_codes": list(self.observed_failure_codes),
            "blocked": self.blocked,
            "verifier_report_proof_hash": self.verifier_report_proof_hash,
            "verifier_error": self.verifier_error,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "case_id": self.case_id,
            "proof_hash": self.proof_hash,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class ProductionAdversarialCertification:
    certification_id: str
    seed: int
    iterations_per_vector: int
    baseline_report_proof_hash: str
    state: AdversarialCertificationState
    cases: tuple[AdversarialCaseResult, ...]
    external_actions_performed: bool = False
    automatic_repair_performed: bool = False

    def __post_init__(self) -> None:
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")
        if type(self.iterations_per_vector) is not int or not 1 <= self.iterations_per_vector <= 100:
            raise ValueError("iterations_per_vector must be in 1..100")
        object.__setattr__(
            self,
            "baseline_report_proof_hash",
            normalize_sha256(
                "baseline_report_proof_hash", self.baseline_report_proof_hash
            ),
        )
        if not isinstance(self.state, AdversarialCertificationState):
            raise ValueError("state must be AdversarialCertificationState")
        cases = tuple(
            sorted(
                self.cases,
                key=lambda item: (item.vector.value, item.iteration, item.case_id),
            )
        )
        object.__setattr__(self, "cases", cases)
        expected_count = len(AdversarialVector) * self.iterations_per_vector
        if len(cases) != expected_count:
            raise ValueError("certification case count is incomplete")
        expected_vectors = set(AdversarialVector)
        actual_vectors = {case.vector for case in cases}
        if actual_vectors != expected_vectors:
            raise ValueError("certification vector coverage is incomplete")
        expected_state = (
            AdversarialCertificationState.PASS
            if all(case.passed for case in cases)
            else AdversarialCertificationState.FAILED
        )
        if self.state is not expected_state:
            raise ValueError("certification state does not match case results")
        if self.external_actions_performed or self.automatic_repair_performed:
            raise ValueError("adversarial certification must remain read-only")
        expected_id = "recoveryworks-adversarial-certification:" + canonical_hash(
            self._identity()
        )
        if self.certification_id != expected_id:
            raise ValueError("certification_id does not bind adversarial certification")

    @property
    def total_cases(self) -> int:
        return len(self.cases)

    @property
    def false_negative_count(self) -> int:
        return sum(not case.passed for case in self.cases)

    @property
    def vector_counts(self) -> dict[str, int]:
        return {
            vector.value: sum(case.vector is vector for case in self.cases)
            for vector in AdversarialVector
        }

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "seed": self.seed,
            "iterations_per_vector": self.iterations_per_vector,
            "baseline_report_proof_hash": self.baseline_report_proof_hash,
            "state": self.state.value,
            "case_hashes": [case.proof_hash for case in self.cases],
            "external_actions_performed": False,
            "automatic_repair_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "certification_id": self.certification_id,
            "proof_hash": self.proof_hash,
            "total_cases": self.total_cases,
            "false_negative_count": self.false_negative_count,
            "vector_counts": self.vector_counts,
            "cases": [case.as_dict() for case in self.cases],
        }


def _junk_hash(seed: int, vector: AdversarialVector, iteration: int, label: str) -> str:
    return hashlib.sha256(
        f"{seed}|{vector.value}|{iteration}|{label}".encode("utf-8")
    ).hexdigest()


def _mutate(
    chain: dict[str, Any],
    *,
    vector: AdversarialVector,
    iteration: int,
    rng: random.Random,
    seed: int,
) -> tuple[str, tuple[str, ...]]:
    if vector is AdversarialVector.PROOF_TAMPERING:
        targets = (
            (
                "invoice_handoff",
                "draft_proof_hash",
                "INVOICE_HANDOFF_BINDING",
            ),
            (
                "issued_invoice",
                "issuance_receipt_proof_hash",
                "EXTERNAL_INVOICE_BINDING",
            ),
            (
                "recurring_activation",
                "agreement_receipt_proof_hash",
                "RECURRING_LIFECYCLE_BINDING",
            ),
        )
        key, field, expected = rng.choice(targets)
        object.__setattr__(
            chain[key],
            field,
            _junk_hash(seed, vector, iteration, f"{key}.{field}"),
        )
        return f"tampered {key}.{field}", (expected,)

    if vector is AdversarialVector.CROSS_TENANT_SUBSTITUTION:
        targets = (
            ("kickoff_authorization", "PILOT_AUTHORIZATION_BINDING"),
            ("issued_invoice", "EXTERNAL_INVOICE_BINDING"),
            ("recurring_activation", "RECURRING_LIFECYCLE_BINDING"),
        )
        key, expected = rng.choice(targets)
        object.__setattr__(
            chain[key],
            "buyer_id",
            f"substituted-buyer-{iteration}-{rng.randrange(1_000_000)}",
        )
        return f"substituted buyer_id on {key}", (expected,)

    if vector is AdversarialVector.AMOUNT_SURFACE_CONFUSION:
        source_field = rng.choice(
            ("validated_recovery_cents", "prospective_savings_cents")
        )
        object.__setattr__(
            chain["fee_readiness"],
            "recovered_cash_cents",
            getattr(chain["closeout"], source_field),
        )
        return (
            f"replaced recovered cash with closeout.{source_field}",
            ("RECOVERED_CASH_AMOUNT_SURFACE",),
        )

    if vector is AdversarialVector.STALE_AUTHORIZATION:
        expiry = rng.choice(
            ("2026-09-24T15:00:00Z", "2026-09-24T15:30:00Z")
        )
        object.__setattr__(
            chain["kickoff_authorization"],
            "expires_at",
            expiry,
        )
        return (
            f"forced pilot authorization expiry to {expiry} before closeout",
            ("LIFECYCLE_CHRONOLOGY_AND_FRESHNESS",),
        )

    if vector is AdversarialVector.DUPLICATE_SETTLEMENT:
        original = chain["settlement_receipts"][0]
        duplicate = deepcopy(original)
        object.__setattr__(
            duplicate,
            "source_hash",
            _junk_hash(seed, vector, iteration, "duplicate-source"),
        )
        object.__setattr__(
            duplicate,
            "source_locator",
            f"bank://duplicate/{iteration}",
        )
        chain["settlement_receipts"] = (original, duplicate)
        return (
            "inserted distinct evidence receipt with duplicate settlement_reference",
            ("INDEPENDENT_SETTLEMENT_RECONCILIATION",),
        )

    if vector is AdversarialVector.REPLAYED_RECEIPT:
        original = chain["settlement_receipts"][0]
        chain["settlement_receipts"] = (original, original)
        return (
            "replayed exact settlement receipt twice",
            ("INDEPENDENT_SETTLEMENT_RECONCILIATION",),
        )

    if vector is AdversarialVector.LIFECYCLE_STATE_SKIPPING:
        targets = (
            (
                "recurring_activation",
                "readiness_proof_hash",
                chain["recurring_authorization"].proof_hash,
                "RECURRING_LIFECYCLE_BINDING",
            ),
            (
                "recurring_lifecycle",
                "activation_receipt_proof_hash",
                chain["recurring_readiness"].proof_hash,
                "RECURRING_LIFECYCLE_BINDING",
            ),
            (
                "recurring_lifecycle",
                "state",
                RecurringAssuranceLifecycleState.DEACTIVATED,
                "RECURRING_LIFECYCLE_STATE_INTEGRITY",
            ),
            (
                "recurring_lifecycle",
                "active_until",
                "2026-10-15T00:00:00Z",
                "RECURRING_LIFECYCLE_STATE_INTEGRITY",
            ),
            (
                "recurring_lifecycle",
                "deactivation_receipt_proof_hash",
                _junk_hash(seed, vector, iteration, "forged-deactivation"),
                "RECURRING_LIFECYCLE_STATE_INTEGRITY",
            ),
        )
        key, field, substituted_value, expected = rng.choice(targets)
        object.__setattr__(chain[key], field, substituted_value)
        return (
            f"skipped lifecycle state by substituting {key}.{field}",
            (expected,),
        )

    raise AssertionError(f"unhandled adversarial vector: {vector.value}")


def run_commercial_adversarial_certification(
    chain_factory: Callable[[], Mapping[str, Any]],
    *,
    seed: int = 41001,
    iterations_per_vector: int = 8,
) -> ProductionAdversarialCertification:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    if type(iterations_per_vector) is not int or not 1 <= iterations_per_vector <= 100:
        raise ValueError("iterations_per_vector must be in 1..100")

    baseline_chain = dict(chain_factory())
    baseline = verify_commercial_operational_invariants(**baseline_chain)
    if baseline.state is not CommercialOperationalInvariantState.PASS:
        raise ValueError(
            "baseline chain must pass before adversarial certification: "
            + ", ".join(baseline.failed_codes)
        )

    rng = random.Random(seed)
    cases: list[AdversarialCaseResult] = []
    for vector in AdversarialVector:
        for iteration in range(iterations_per_vector):
            chain = dict(chain_factory())
            mutation, expected_codes = _mutate(
                chain,
                vector=vector,
                iteration=iteration,
                rng=rng,
                seed=seed,
            )
            observed_codes: tuple[str, ...] = ()
            blocked = False
            report_hash = None
            error = None
            try:
                report = verify_commercial_operational_invariants(**chain)
                observed_codes = report.failed_codes
                blocked = (
                    report.state is CommercialOperationalInvariantState.BLOCKED
                )
                report_hash = report.proof_hash
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

            identity = {
                "schema": 1,
                "vector": vector.value,
                "iteration": iteration,
                "mutation": mutation,
                "expected_failure_codes": list(sorted(set(expected_codes))),
                "observed_failure_codes": list(sorted(set(observed_codes))),
                "blocked": blocked,
                "verifier_report_proof_hash": report_hash,
                "verifier_error": error,
            }
            cases.append(
                AdversarialCaseResult(
                    case_id="recoveryworks-adversarial-case:"
                    + canonical_hash(identity),
                    vector=vector,
                    iteration=iteration,
                    mutation=mutation,
                    expected_failure_codes=expected_codes,
                    observed_failure_codes=observed_codes,
                    blocked=blocked,
                    verifier_report_proof_hash=report_hash,
                    verifier_error=error,
                )
            )

    case_tuple = tuple(
        sorted(
            cases,
            key=lambda item: (item.vector.value, item.iteration, item.case_id),
        )
    )
    state = (
        AdversarialCertificationState.PASS
        if all(case.passed for case in case_tuple)
        else AdversarialCertificationState.FAILED
    )
    identity = {
        "schema": 1,
        "seed": seed,
        "iterations_per_vector": iterations_per_vector,
        "baseline_report_proof_hash": baseline.proof_hash,
        "state": state.value,
        "case_hashes": [case.proof_hash for case in case_tuple],
        "external_actions_performed": False,
        "automatic_repair_performed": False,
    }
    return ProductionAdversarialCertification(
        certification_id="recoveryworks-adversarial-certification:"
        + canonical_hash(identity),
        seed=seed,
        iterations_per_vector=iterations_per_vector,
        baseline_report_proof_hash=baseline.proof_hash,
        state=state,
        cases=case_tuple,
        external_actions_performed=False,
        automatic_repair_performed=False,
    )
