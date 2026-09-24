"""Independent acceptance gate for AI Business OS.

The executor may submit artifacts and claims, but cannot determine acceptance.
A separate auditor evaluates a manager-authored contract against evidence and
emits a content-addressed receipt.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any, Iterable


class AuditError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class Requirement:
    key: str
    evidence_key: str
    predicate: str = "truthy"
    expected: Any = None
    required: bool = True
    allowed_producers: tuple[str, ...] = ("CI", "SYSTEM", "HUMAN", "VERIFIER")
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "evidence_key": self.evidence_key,
            "predicate": self.predicate,
            "expected": self.expected,
            "required": self.required,
            "allowed_producers": list(self.allowed_producers),
            "description": self.description,
        }


@dataclasses.dataclass(frozen=True)
class AcceptanceContract:
    task_id: str
    requirements: tuple[Requirement, ...]
    manager: str

    def __post_init__(self) -> None:
        keys = [r.key for r in self.requirements]
        if len(keys) != len(set(keys)):
            raise AuditError("requirement keys must be unique")
        if not self.requirements:
            raise AuditError("contract must contain at least one requirement")

    @property
    def sha256(self) -> str:
        payload = {
            "task_id": self.task_id,
            "manager": self.manager,
            "requirements": [r.to_dict() for r in self.requirements],
        }
        return _sha(payload)


@dataclasses.dataclass(frozen=True)
class Evidence:
    key: str
    value: Any
    producer: str
    source_ref: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "producer": self.producer,
            "source_ref": self.source_ref,
        }


@dataclasses.dataclass(frozen=True)
class ExecutorSubmission:
    task_id: str
    executor: str
    result: dict[str, Any]
    evidence: tuple[Evidence, ...]

    @property
    def sha256(self) -> str:
        return _sha(
            {
                "task_id": self.task_id,
                "executor": self.executor,
                "result": self.result,
                "evidence": [e.to_dict() for e in self.evidence],
            }
        )


@dataclasses.dataclass(frozen=True)
class Finding:
    requirement_key: str
    passed: bool
    reason: str
    evidence_key: str
    source_ref: str | None


@dataclasses.dataclass(frozen=True)
class AuditReceipt:
    task_id: str
    auditor: str
    contract_sha256: str
    submission_sha256: str
    verdict: str
    findings: tuple[Finding, ...]

    @property
    def sha256(self) -> str:
        return _sha(
            {
                "task_id": self.task_id,
                "auditor": self.auditor,
                "contract_sha256": self.contract_sha256,
                "submission_sha256": self.submission_sha256,
                "verdict": self.verdict,
                "findings": [dataclasses.asdict(f) for f in self.findings],
            }
        )


class IndependentAuditor:
    """Deterministic acceptance evaluator.

    Executor-originated evidence is rejected by default because the executor
    must not be its own completion oracle. A contract may explicitly allow it
    for low-risk requirements if the manager chooses.
    """

    def __init__(self, auditor_id: str) -> None:
        self.auditor_id = auditor_id

    def audit(
        self,
        contract: AcceptanceContract,
        submission: ExecutorSubmission,
    ) -> AuditReceipt:
        if contract.task_id != submission.task_id:
            raise AuditError("submission task_id does not match contract")

        evidence_by_key: dict[str, list[Evidence]] = {}
        for item in submission.evidence:
            evidence_by_key.setdefault(item.key, []).append(item)

        findings: list[Finding] = []
        for req in contract.requirements:
            candidates = evidence_by_key.get(req.evidence_key, [])
            if not candidates:
                findings.append(
                    Finding(
                        requirement_key=req.key,
                        passed=not req.required,
                        reason="missing evidence" if req.required else "optional evidence absent",
                        evidence_key=req.evidence_key,
                        source_ref=None,
                    )
                )
                continue

            accepted_candidate = None
            rejected_producers: list[str] = []
            for candidate in candidates:
                if candidate.producer not in req.allowed_producers:
                    rejected_producers.append(candidate.producer)
                    continue
                accepted_candidate = candidate
                break

            if accepted_candidate is None:
                findings.append(
                    Finding(
                        requirement_key=req.key,
                        passed=False,
                        reason=(
                            "no evidence from an allowed producer; got "
                            + ",".join(sorted(set(rejected_producers)))
                        ),
                        evidence_key=req.evidence_key,
                        source_ref=candidates[0].source_ref,
                    )
                )
                continue

            passed, reason = _evaluate(
                req.predicate,
                accepted_candidate.value,
                req.expected,
            )
            findings.append(
                Finding(
                    requirement_key=req.key,
                    passed=passed,
                    reason=reason,
                    evidence_key=req.evidence_key,
                    source_ref=accepted_candidate.source_ref,
                )
            )

        verdict = "ACCEPTED" if all(f.passed for f in findings) else "REJECTED"
        return AuditReceipt(
            task_id=contract.task_id,
            auditor=self.auditor_id,
            contract_sha256=contract.sha256,
            submission_sha256=submission.sha256,
            verdict=verdict,
            findings=tuple(findings),
        )


def _evaluate(predicate: str, actual: Any, expected: Any) -> tuple[bool, str]:
    if predicate == "truthy":
        ok = bool(actual)
        return ok, "truthy evidence" if ok else "evidence is falsey"
    if predicate == "nonempty":
        ok = actual is not None and hasattr(actual, "__len__") and len(actual) > 0
        return ok, "non-empty evidence" if ok else "evidence is empty"
    if predicate == "equals":
        ok = actual == expected
        return ok, "matched expected value" if ok else f"expected {expected!r}, got {actual!r}"
    if predicate == "gte":
        try:
            ok = actual >= expected
        except TypeError as exc:
            raise AuditError("gte requires comparable values") from exc
        return ok, f"{actual!r} >= {expected!r}" if ok else f"{actual!r} < {expected!r}"
    if predicate == "lte":
        try:
            ok = actual <= expected
        except TypeError as exc:
            raise AuditError("lte requires comparable values") from exc
        return ok, f"{actual!r} <= {expected!r}" if ok else f"{actual!r} > {expected!r}"
    if predicate == "contains":
        try:
            ok = expected in actual
        except TypeError as exc:
            raise AuditError("contains requires a container value") from exc
        return ok, "expected value present" if ok else "expected value absent"
    if predicate == "sha256_matches":
        if isinstance(actual, str):
            raw = actual.encode("utf-8")
        elif isinstance(actual, bytes):
            raw = actual
        else:
            raw = _canonical(actual).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        ok = digest == expected
        return ok, "sha256 matched" if ok else f"sha256 mismatch: {digest}"
    raise AuditError(f"unsupported predicate: {predicate}")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
