"""Deterministic evidence and truth engine for AI Business OS.

Claims are never accepted from prose confidence. A claim is evaluated against
explicit proof obligations and typed evidence. Missing, stale, inadmissible,
non-independent and contradictory evidence remain visible in the result.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any


VALID_STANCES = {"SUPPORTS", "CONTRADICTS"}
VALID_VERDICTS = {"PROVEN", "CONTESTED", "NOT_PROVEN", "UNKNOWN"}
VALID_STATUSES = {
    "SATISFIED",
    "MISSING",
    "STALE_OR_INADMISSIBLE",
    "INSUFFICIENT_SUPPORT",
    "INSUFFICIENT_INDEPENDENCE",
    "CONFLICTED",
    "CONTRADICTED",
}


@dataclasses.dataclass(frozen=True)
class Claim:
    claim_id: str
    subject: str
    statement: str
    context: dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.claim_id.strip() or not self.subject.strip() or not self.statement.strip():
            raise ValueError("claim_id, subject and statement are required")

    @property
    def sha256(self) -> str:
        return _sha(dataclasses.asdict(self))


@dataclasses.dataclass(frozen=True)
class ProofObligation:
    key: str
    description: str
    allowed_authorities: tuple[str, ...]
    min_supporting_sources: int = 1
    min_independent_groups: int = 1
    max_age_seconds: float | None = None
    required: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.description.strip():
            raise ValueError("obligation key and description are required")
        if not self.allowed_authorities:
            raise ValueError("allowed_authorities cannot be empty")
        if self.min_supporting_sources < 1:
            raise ValueError("min_supporting_sources must be >= 1")
        if self.min_independent_groups < 1:
            raise ValueError("min_independent_groups must be >= 1")
        if self.max_age_seconds is not None and self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be > 0")


@dataclasses.dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    obligation_key: str
    stance: str
    authority: str
    source_id: str
    independence_group: str
    observed_at: float
    source_ref: str
    source_sha256: str
    admissible: bool = True
    valid_until: float | None = None
    payload: dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.stance not in VALID_STANCES:
            raise ValueError(f"unsupported evidence stance: {self.stance}")
        for field_name in (
            "evidence_id",
            "obligation_key",
            "authority",
            "source_id",
            "independence_group",
            "source_ref",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} cannot be empty")
        _check_digest(self.source_sha256)
        if self.valid_until is not None and self.valid_until < self.observed_at:
            raise ValueError("valid_until cannot precede observed_at")

    @property
    def sha256(self) -> str:
        return _sha(dataclasses.asdict(self))


@dataclasses.dataclass(frozen=True)
class ObligationFinding:
    key: str
    status: str
    reason: str
    supporting_evidence_ids: tuple[str, ...]
    contradicting_evidence_ids: tuple[str, ...]
    rejected_evidence_ids: tuple[str, ...]
    independent_groups: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"unsupported obligation status: {self.status}")


@dataclasses.dataclass(frozen=True)
class TruthReceipt:
    claim_id: str
    claim_sha256: str
    verdict: str
    evaluated_at: float
    obligation_findings: tuple[ObligationFinding, ...]
    evidence_set_sha256: str

    def __post_init__(self) -> None:
        if self.verdict not in VALID_VERDICTS:
            raise ValueError(f"unsupported verdict: {self.verdict}")

    @property
    def sha256(self) -> str:
        return _sha(
            {
                "claim_id": self.claim_id,
                "claim_sha256": self.claim_sha256,
                "verdict": self.verdict,
                "evaluated_at": self.evaluated_at,
                "obligation_findings": [
                    dataclasses.asdict(x) for x in self.obligation_findings
                ],
                "evidence_set_sha256": self.evidence_set_sha256,
            }
        )


@dataclasses.dataclass(frozen=True)
class EvidenceAction:
    action_id: str
    obligation_key: str
    description: str
    authority: str
    independence_group: str
    cost_usd: float = 0.0
    available: bool = True
    deadline_at: float | None = None

    def __post_init__(self) -> None:
        if not self.action_id.strip() or not self.obligation_key.strip():
            raise ValueError("action_id and obligation_key are required")
        if not self.description.strip() or not self.authority.strip():
            raise ValueError("description and authority are required")
        if not self.independence_group.strip():
            raise ValueError("independence_group is required")
        if self.cost_usd < 0:
            raise ValueError("cost_usd cannot be negative")


@dataclasses.dataclass(frozen=True)
class RankedEvidenceAction:
    action: EvidenceAction
    baseline_verdict: str
    counterfactual_verdict: str
    obligations_improved: int
    potential_decision_gain: int
    priority_score: float


class TruthEngine:
    """Fail-closed proof evaluator and next-evidence planner."""

    VERDICT_RANK = {
        "UNKNOWN": 0,
        "NOT_PROVEN": 1,
        "CONTESTED": 1,
        "PROVEN": 3,
    }

    def evaluate(
        self,
        claim: Claim,
        obligations: tuple[ProofObligation, ...],
        evidence: tuple[EvidenceItem, ...],
        *,
        evaluated_at: float,
    ) -> TruthReceipt:
        if not obligations:
            raise ValueError("at least one proof obligation is required")
        keys = [x.key for x in obligations]
        if len(keys) != len(set(keys)):
            raise ValueError("proof obligation keys must be unique")

        by_key: dict[str, list[EvidenceItem]] = {}
        for item in evidence:
            by_key.setdefault(item.obligation_key, []).append(item)

        findings: list[ObligationFinding] = []
        usable_total = 0
        relevant_total = 0

        for obligation in obligations:
            relevant = by_key.get(obligation.key, [])
            relevant_total += len(relevant)
            supports: list[EvidenceItem] = []
            contradicts: list[EvidenceItem] = []
            rejected: list[EvidenceItem] = []

            for item in relevant:
                if not self._usable(item, obligation, evaluated_at):
                    rejected.append(item)
                    continue
                usable_total += 1
                if item.stance == "SUPPORTS":
                    supports.append(item)
                else:
                    contradicts.append(item)

            groups = sorted({x.independence_group for x in supports})

            if supports and contradicts:
                status = "CONFLICTED"
                reason = "admissible evidence both supports and contradicts the obligation"
            elif contradicts:
                status = "CONTRADICTED"
                reason = "admissible evidence contradicts the obligation"
            elif len(supports) < obligation.min_supporting_sources and supports:
                status = "INSUFFICIENT_SUPPORT"
                reason = (
                    f"need {obligation.min_supporting_sources} supporting source(s); "
                    f"have {len(supports)}"
                )
            elif supports and len(groups) < obligation.min_independent_groups:
                status = "INSUFFICIENT_INDEPENDENCE"
                reason = (
                    f"need {obligation.min_independent_groups} independent group(s); "
                    f"have {len(groups)}"
                )
            elif supports:
                status = "SATISFIED"
                reason = "support, authority, freshness and independence requirements satisfied"
            elif relevant:
                status = "STALE_OR_INADMISSIBLE"
                reason = "evidence exists but none is currently admissible and usable"
            else:
                status = "MISSING"
                reason = "no evidence supplied for obligation"

            findings.append(
                ObligationFinding(
                    key=obligation.key,
                    status=status,
                    reason=reason,
                    supporting_evidence_ids=tuple(x.evidence_id for x in supports),
                    contradicting_evidence_ids=tuple(
                        x.evidence_id for x in contradicts
                    ),
                    rejected_evidence_ids=tuple(x.evidence_id for x in rejected),
                    independent_groups=tuple(groups),
                )
            )

        required_by_key = {x.key: x for x in obligations if x.required}
        required_findings = [
            x for x in findings if x.key in required_by_key
        ]

        if any(
            x.status in {"CONFLICTED", "CONTRADICTED"}
            for x in required_findings
        ):
            verdict = "CONTESTED"
        elif required_findings and all(
            x.status == "SATISFIED" for x in required_findings
        ):
            verdict = "PROVEN"
        elif relevant_total == 0:
            verdict = "UNKNOWN"
        else:
            verdict = "NOT_PROVEN"

        evidence_set_sha256 = _sha(
            sorted(
                (
                    item.evidence_id,
                    item.sha256,
                )
                for item in evidence
            )
        )
        return TruthReceipt(
            claim_id=claim.claim_id,
            claim_sha256=claim.sha256,
            verdict=verdict,
            evaluated_at=float(evaluated_at),
            obligation_findings=tuple(findings),
            evidence_set_sha256=evidence_set_sha256,
        )

    def rank_next_evidence(
        self,
        claim: Claim,
        obligations: tuple[ProofObligation, ...],
        evidence: tuple[EvidenceItem, ...],
        actions: tuple[EvidenceAction, ...],
        *,
        evaluated_at: float,
    ) -> list[RankedEvidenceAction]:
        """Rank obtainable evidence by deterministic counterfactual usefulness.

        The score is not a probability or ROI forecast. Each candidate action is
        simulated as one fresh supporting evidence item and the engine measures
        whether that would improve proof status or the final verdict.
        """
        baseline = self.evaluate(
            claim, obligations, evidence, evaluated_at=evaluated_at
        )
        obligation_map = {x.key: x for x in obligations}
        baseline_status = {
            x.key: x.status for x in baseline.obligation_findings
        }
        existing_groups = {
            key: {
                item.independence_group
                for item in evidence
                if item.obligation_key == key
                and item.stance == "SUPPORTS"
            }
            for key in obligation_map
        }

        ranked: list[RankedEvidenceAction] = []
        for action in actions:
            obligation = obligation_map.get(action.obligation_key)
            if obligation is None or not action.available:
                continue
            if action.deadline_at is not None and action.deadline_at < evaluated_at:
                continue
            if action.authority not in obligation.allowed_authorities:
                continue
            if action.independence_group in existing_groups.get(
                action.obligation_key, set()
            ):
                continue

            hypothetical = EvidenceItem(
                evidence_id=f"hypothetical:{action.action_id}",
                obligation_key=action.obligation_key,
                stance="SUPPORTS",
                authority=action.authority,
                source_id=f"action:{action.action_id}",
                independence_group=action.independence_group,
                observed_at=evaluated_at,
                source_ref=f"hypothetical:{action.action_id}",
                source_sha256=_sha({"action_id": action.action_id}),
                admissible=True,
                valid_until=None,
                payload={"counterfactual": True},
            )
            counter = self.evaluate(
                claim,
                obligations,
                evidence + (hypothetical,),
                evaluated_at=evaluated_at,
            )
            counter_status = {
                x.key: x.status for x in counter.obligation_findings
            }

            improved = 0
            before = baseline_status[action.obligation_key]
            after = counter_status[action.obligation_key]
            if before != "SATISFIED" and after == "SATISFIED":
                improved = 1

            verdict_gain = max(
                0,
                self.VERDICT_RANK[counter.verdict]
                - self.VERDICT_RANK[baseline.verdict],
            )
            # Required blockers get extra weight. Cost is only a tiebreaking
            # friction term; this is not a financial-value prediction.
            required_weight = 2 if obligation.required else 1
            numerator = verdict_gain * 4 + improved * required_weight
            if numerator == 0:
                continue
            priority = numerator / (1.0 + action.cost_usd)

            ranked.append(
                RankedEvidenceAction(
                    action=action,
                    baseline_verdict=baseline.verdict,
                    counterfactual_verdict=counter.verdict,
                    obligations_improved=improved,
                    potential_decision_gain=verdict_gain,
                    priority_score=priority,
                )
            )

        ranked.sort(
            key=lambda x: (
                x.priority_score,
                x.potential_decision_gain,
                x.obligations_improved,
                -x.action.cost_usd,
                x.action.action_id,
            ),
            reverse=True,
        )
        return ranked

    @staticmethod
    def _usable(
        item: EvidenceItem,
        obligation: ProofObligation,
        evaluated_at: float,
    ) -> bool:
        if not item.admissible:
            return False
        if item.authority not in obligation.allowed_authorities:
            return False
        if item.observed_at > evaluated_at:
            return False
        if item.valid_until is not None and item.valid_until < evaluated_at:
            return False
        if obligation.max_age_seconds is not None:
            if evaluated_at - item.observed_at > obligation.max_age_seconds:
                return False
        return True


def _check_digest(value: str) -> None:
    if len(value) != 64:
        raise ValueError("source_sha256 must be a 64-character digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("source_sha256 must be hexadecimal") from exc


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
