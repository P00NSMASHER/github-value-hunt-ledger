"""Verifier-gated self-improvement for AI Business OS.

Agents may propose candidate skills, prompts, or workflows. Shared/global use is
blocked until independent held-out evidence proves the candidate improves on
the baseline without hard regressions. Eligibility is not promotion.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any


class PromotionError(ValueError):
    pass


ALLOWED_SPLITS = {"train", "confirm", "heldout", "adversarial", "canary"}


@dataclasses.dataclass(frozen=True)
class SkillCandidate:
    candidate_id: str
    skill_id: str
    baseline_version: str
    candidate_version: str
    artifact_sha256: str
    mutation_scope: str
    proposer: str

    def __post_init__(self) -> None:
        if self.baseline_version == self.candidate_version:
            raise PromotionError("candidate_version must differ from baseline_version")
        if len(self.artifact_sha256) != 64:
            raise PromotionError("artifact_sha256 must be a 64-character digest")


@dataclasses.dataclass(frozen=True)
class EvaluationEvidence:
    split: str
    dataset_sha256: str
    baseline_score: float
    candidate_score: float
    passed: bool
    hard_regressions: int = 0
    verifier: str = "VERIFIER"
    evidence_ref: str = ""

    def __post_init__(self) -> None:
        if self.split not in ALLOWED_SPLITS:
            raise PromotionError(f"unsupported evaluation split: {self.split}")
        if len(self.dataset_sha256) != 64:
            raise PromotionError("dataset_sha256 must be a 64-character digest")
        if self.hard_regressions < 0:
            raise PromotionError("hard_regressions cannot be negative")


@dataclasses.dataclass(frozen=True)
class PromotionDecision:
    candidate_id: str
    skill_id: str
    state: str
    reasons: tuple[str, ...]
    evidence_sha256: str

    @property
    def sha256(self) -> str:
        return _sha(dataclasses.asdict(self))


class PromotionGate:
    """Independent gate for skill/prompt/workflow promotion.

    A normal candidate must pass distinct confirm, heldout and adversarial
    datasets with no hard regressions and a configured improvement margin.
    Canary evidence is additionally required for GLOBAL_ELIGIBLE.

    This gate never writes a global skill itself.
    """

    def __init__(
        self,
        *,
        minimum_delta: float = 0.0,
        required_splits: tuple[str, ...] = ("confirm", "heldout", "adversarial"),
    ) -> None:
        self.minimum_delta = float(minimum_delta)
        self.required_splits = required_splits
        unknown = set(required_splits) - ALLOWED_SPLITS
        if unknown:
            raise PromotionError(f"unsupported required split(s): {sorted(unknown)}")

    def evaluate(
        self,
        candidate: SkillCandidate,
        evidence: tuple[EvaluationEvidence, ...],
    ) -> PromotionDecision:
        reasons: list[str] = []
        by_split: dict[str, list[EvaluationEvidence]] = {}
        for item in evidence:
            by_split.setdefault(item.split, []).append(item)

        missing = [split for split in self.required_splits if split not in by_split]
        if missing:
            reasons.append("missing required split(s): " + ",".join(missing))

        # Evaluation identity must remain independent across promotion splits.
        promotion_items = [
            item
            for item in evidence
            if item.split in set(self.required_splits) | {"canary"}
        ]
        hashes = [item.dataset_sha256 for item in promotion_items]
        if len(hashes) != len(set(hashes)):
            reasons.append("evaluation split dataset hashes are not independent")

        for split in self.required_splits:
            items = by_split.get(split, [])
            if len(items) > 1:
                reasons.append(f"multiple ambiguous evidence rows for {split}")
                continue
            if not items:
                continue
            item = items[0]
            if item.verifier in {"EXECUTOR", candidate.proposer}:
                reasons.append(f"{split} evidence was not independently verified")
            if not item.passed:
                reasons.append(f"{split} verifier marked candidate failed")
            if item.hard_regressions:
                reasons.append(f"{split} has {item.hard_regressions} hard regression(s)")
            delta = item.candidate_score - item.baseline_score
            if delta < self.minimum_delta:
                reasons.append(
                    f"{split} improvement {delta:.6f} is below minimum {self.minimum_delta:.6f}"
                )

        if reasons:
            state = "REJECTED"
        else:
            state = "READY_FOR_CANARY"

        canary_items = by_split.get("canary", [])
        if state == "READY_FOR_CANARY" and canary_items:
            if len(canary_items) != 1:
                reasons.append("multiple ambiguous canary evidence rows")
                state = "REJECTED"
            else:
                canary = canary_items[0]
                if canary.verifier in {"EXECUTOR", candidate.proposer}:
                    reasons.append("canary evidence was not independently verified")
                    state = "REJECTED"
                elif not canary.passed or canary.hard_regressions:
                    reasons.append("canary failed or contains a hard regression")
                    state = "REJECTED"
                elif (
                    canary.candidate_score - canary.baseline_score
                    < self.minimum_delta
                ):
                    reasons.append("canary did not meet the improvement threshold")
                    state = "REJECTED"
                else:
                    state = "GLOBAL_ELIGIBLE"

        evidence_hash = _sha(
            {
                "candidate": dataclasses.asdict(candidate),
                "evidence": [dataclasses.asdict(item) for item in evidence],
                "minimum_delta": self.minimum_delta,
                "required_splits": list(self.required_splits),
            }
        )
        if not reasons:
            reasons.append(
                "independent evaluation requirements satisfied"
                if state == "READY_FOR_CANARY"
                else "independent evaluation plus canary requirements satisfied"
            )
        return PromotionDecision(
            candidate_id=candidate.candidate_id,
            skill_id=candidate.skill_id,
            state=state,
            reasons=tuple(reasons),
            evidence_sha256=evidence_hash,
        )


class GlobalSkillRegistry:
    """Tiny explicit-approval registry.

    GLOBAL_ELIGIBLE is intentionally not equivalent to GLOBAL. Promotion needs
    a separate Integrator approval, preserving a human/governance boundary.
    """

    def __init__(self) -> None:
        self._versions: dict[str, str] = {}
        self._receipts: list[dict[str, Any]] = []

    def current_version(self, skill_id: str) -> str | None:
        return self._versions.get(skill_id)

    def promote(
        self,
        candidate: SkillCandidate,
        decision: PromotionDecision,
        *,
        approver_role: str,
        approver_id: str,
    ) -> dict[str, Any]:
        if decision.candidate_id != candidate.candidate_id:
            raise PromotionError("decision does not bind to candidate")
        if decision.state != "GLOBAL_ELIGIBLE":
            raise PromotionError("candidate is not GLOBAL_ELIGIBLE")
        if approver_role != "INTEGRATOR":
            raise PermissionError("only INTEGRATOR may perform global promotion")

        receipt = {
            "skill_id": candidate.skill_id,
            "from_version": self._versions.get(
                candidate.skill_id, candidate.baseline_version
            ),
            "to_version": candidate.candidate_version,
            "candidate_id": candidate.candidate_id,
            "decision_sha256": decision.sha256,
            "approver_role": approver_role,
            "approver_id": approver_id,
        }
        receipt["sha256"] = _sha(receipt)
        self._versions[candidate.skill_id] = candidate.candidate_version
        self._receipts.append(receipt)
        return dict(receipt)

    @property
    def receipts(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(x) for x in self._receipts)


def _sha(value: Any) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
