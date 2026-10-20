"""Two-manifest, fail-closed freight evidence scoring.

Truth and prediction are frozen independently. Missing rights, full provenance,
reviewer independence or a verified authority means UNRESOLVED, not a "negative".
This module is an internal scoring *instrument*, not approval to publish an
external performance claim. Use freight.audit_acceptance for customer release.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import sqrt
import re
from typing import Iterable

from freight.contracts import canonical_hash

_SHA = re.compile(r"^[0-9a-f]{64}$")
TRUTH = {"POSITIVE", "NEGATIVE", "UNRESOLVED"}
PREDICTED = {"POSITIVE", "NEGATIVE", "REVIEW"}


def _sha(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError(label + " must be lowercase SHA-256")
    return value


def _time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(label + " requires timezone-aware ISO-8601") from exc


def _distinct_roles(roles: Iterable[str]) -> None:
    entries = list(roles)
    if any(not isinstance(x, str) or not x.strip() for x in entries):
        raise ValueError("independent roles must be nonempty")
    if len(entries) != len(set(entries)):
        raise ValueError("independent reviewer/truth/model roles must be distinct")


@dataclass(frozen=True)
class ModelCall:
    case_id: str
    predicted_label: str
    predicted_variance_cents: int
    model_output_sha256: str

    def __post_init__(self):
        if not self.case_id or not isinstance(self.case_id, str):
            raise ValueError("case identity required")
        if self.predicted_label not in PREDICTED:
            raise ValueError("unsupported prediction label")
        if type(self.predicted_variance_cents) is not int or self.predicted_variance_cents < 0:
            raise ValueError("predicted money must be nonnegative exact cents")
        _sha(self.model_output_sha256, "model_output_sha256")
        if self.predicted_label != "POSITIVE" and self.predicted_variance_cents:
            raise ValueError("negative/review decisions may not assert predicted recovery")


@dataclass(frozen=True)
class TruthCall:
    case_id: str
    truth_label: str
    adjudicated_overcharge_cents: int
    original_invoice_sha256: str
    applicable_rate_sha256: str | None
    bank_payment_sha256: str | None
    adjudication_sha256: str | None
    source_complete: bool

    def __post_init__(self):
        if not isinstance(self.case_id, str) or not self.case_id:
            raise ValueError("truth case_id required")
        if self.truth_label not in TRUTH:
            raise ValueError("unknown freight truth label")
        if type(self.adjudicated_overcharge_cents) is not int or self.adjudicated_overcharge_cents < 0:
            raise ValueError("truth cents must be nonnegative")
        _sha(self.original_invoice_sha256, "original invoice")
        for key in ("applicable_rate_sha256", "bank_payment_sha256", "adjudication_sha256"):
            candidate = getattr(self, key)
            if candidate is not None:
                _sha(candidate, key)
        if type(self.source_complete) is not bool:
            raise ValueError("source_complete must be boolean")
        if self.truth_label == "POSITIVE" and self.adjudicated_overcharge_cents <= 0:
            raise ValueError("positive truth must have positive adjudicated cents")
        if self.truth_label in {"NEGATIVE", "UNRESOLVED"} and self.adjudicated_overcharge_cents:
            raise ValueError("no-money truth must have zero adjudicated overcharge")


@dataclass(frozen=True)
class PredictionSeal:
    operator_id: str
    frozen_at: str
    cases: tuple[ModelCall, ...]
    supplied_seal_sha256: str

    def __post_init__(self):
        _time(self.frozen_at, "model freeze")
        if not self.cases or len({x.case_id for x in self.cases}) != len(self.cases):
            raise ValueError("model manifest must have unique case IDs")
        _sha(self.supplied_seal_sha256, "model seal")


@dataclass(frozen=True)
class TruthSeal:
    truth_owner_id: str
    reviewer_one_id: str
    reviewer_two_id: str
    frozen_at: str
    cases: tuple[TruthCall, ...]
    supplied_seal_sha256: str

    def __post_init__(self):
        _distinct_roles((self.truth_owner_id, self.reviewer_one_id, self.reviewer_two_id))
        _time(self.frozen_at, "truth freeze")
        if not self.cases or len({x.case_id for x in self.cases}) != len(self.cases):
            raise ValueError("truth manifest must have unique case IDs")
        _sha(self.supplied_seal_sha256, "truth seal")


def prediction_seal_hash(operator: str, frozen_at: str, cases: Iterable[ModelCall]) -> str:
    return canonical_hash({
        "schema": 1, "operator": operator, "frozen": frozen_at,
        "model_calls": [asdict(c) for c in sorted(cases, key=lambda c: c.case_id)],
    })


def truth_seal_hash(owner: str, reviewer_one: str, reviewer_two: str,
                    frozen_at: str, cases: Iterable[TruthCall]) -> str:
    return canonical_hash({
        "schema": 1, "owner": owner, "reviewer_one": reviewer_one,
        "reviewer_two": reviewer_two, "frozen": frozen_at,
        "truth_calls": [asdict(c) for c in sorted(cases, key=lambda c: c.case_id)],
    })


def _wilson(success: int, total: int) -> dict | None:
    if total == 0:
        return None
    z = 1.959963984540054
    phat = success / total
    den = 1 + z*z/total
    mid = (phat + z*z/(2*total))/den
    err = z*sqrt((phat*(1-phat)+z*z/(4*total))/total)/den
    return {"point": phat, "lower_95": max(0.0, mid-err),
            "upper_95": min(1.0, mid+err)}


def _eligible_truth(case: TruthCall) -> bool:
    hashes = [
        case.original_invoice_sha256,
        case.applicable_rate_sha256,
        case.bank_payment_sha256,
        case.adjudication_sha256,
    ]
    return (
        case.source_complete
        and case.truth_label in {"POSITIVE", "NEGATIVE"}
        and all(hashes)
        and len(set(hashes)) == 4
    )


@dataclass(frozen=True)
class IndependentAccuracyReport:
    population_count: int
    complete_independent_truth_count: int
    unresolved_truth_count: int
    scored_automatic_decisions: int
    review_abstentions: int
    true_positive: int
    true_negative: int
    false_positive: int
    false_negative: int
    positive_review_abstentions: int
    negative_review_abstentions: int
    precision: float | None
    observed_positive_recall_including_reviews: float | None
    false_positive_rate: float | None
    precision_wilson_95: dict | None
    false_positive_rate_wilson_95: dict | None
    method_status: str
    publication_claim_approved: bool
    report_hash: str
    source_claimed_complete_cases_unverified: int = 0
    unsupported_automatic_positive_calls: int = 0


def score_sealed_freight(
    model: PredictionSeal,
    truth: TruthSeal,
    *,
    joint_unseal_at: str,
    study_kind: str,
) -> IndependentAccuracyReport:
    """Never score unknown cases or pretend self-submitted attestations are proof.

    This scoring path can calculate conditional metrics from *eligible* separate
    manifests, but always needs independent external verification and the
    existing buyer pilot acceptance gate before publication.
    """
    if study_kind not in {"SYNTHETIC_REHEARSAL", "REAL_EXTERNAL_REVIEW_PENDING"}:
        raise ValueError("study kind must explicitly distinguish simulations")
    _distinct_roles((model.operator_id, truth.truth_owner_id,
                     truth.reviewer_one_id, truth.reviewer_two_id))
    unseal = _time(joint_unseal_at, "joint unseal")
    if _time(model.frozen_at, "model frozen") >= unseal:
        raise ValueError("model outputs were not frozen before unseal")
    if _time(truth.frozen_at, "truth frozen") >= unseal:
        raise ValueError("independent truth was not frozen before unseal")
    if model.supplied_seal_sha256 != prediction_seal_hash(
            model.operator_id, model.frozen_at, model.cases):
        raise ValueError("model freeze hash mismatch")
    if truth.supplied_seal_sha256 != truth_seal_hash(
            truth.truth_owner_id, truth.reviewer_one_id,
            truth.reviewer_two_id, truth.frozen_at, truth.cases):
        raise ValueError("truth freeze hash mismatch")
    by_model = {x.case_id: x for x in model.cases}
    by_truth = {x.case_id: x for x in truth.cases}
    if by_model.keys() != by_truth.keys():
        raise ValueError("sealed truth/model case populations differ")
    tp = tn = fp = fn = abstain_positive = abstain_negative = unknown = 0
    claimed_complete = sum(_eligible_truth(t) for t in by_truth.values())
    unsupported_positive = 0
    for case_id in sorted(by_truth):
        t = by_truth[case_id]
        p = by_model[case_id]
        # The presence of four unrelated SHA strings and different *claimed*
        # reviewer names is not proof of their identity, the bank issuer, the
        # controlling rate, or a blind independent adjudication. Real cases
        # must be externally authenticated by a separate trusted gate, which
        # is NOT implemented by this self-contained scoring instrument.
        if study_kind == "REAL_EXTERNAL_REVIEW_PENDING" or not _eligible_truth(t):
            unknown += 1
            unsupported_positive += int(p.predicted_label == "POSITIVE")
            continue
        if p.predicted_label == "REVIEW":
            if t.truth_label == "POSITIVE":
                abstain_positive += 1
            else:
                abstain_negative += 1
        elif p.predicted_label == "POSITIVE":
            if t.truth_label == "POSITIVE":
                tp += 1
            else:
                fp += 1
        elif t.truth_label == "NEGATIVE":
            tn += 1
        else:
            fn += 1
    known = tp+tn+fp+fn+abstain_positive+abstain_negative
    if known + unknown != len(model.cases):
        raise ValueError("blind count conservation violated")
    precision = tp/(tp+fp) if tp+fp else None
    recall_den = tp+fn+abstain_positive
    recall = tp/recall_den if recall_den else None
    fp_den = tn+fp+abstain_negative
    fpr = fp/fp_den if fp_den else None
    method = (
        "EXTERNAL_PROVENANCE_AUTHENTICATION_REQUIRED"
        if study_kind == "REAL_EXTERNAL_REVIEW_PENDING" and claimed_complete
        else "INSUFFICIENT_INDEPENDENT_LABELS" if known == 0
        else "INTERNAL_SYNTHETIC_REHEARSAL_ONLY"
    )
    metrics = {
        "population": len(model.cases), "known": known, "unknown": unknown,
        "TP": tp, "TN": tn, "FP": fp, "FN": fn,
        "abstained_positive": abstain_positive, "abstained_negative": abstain_negative,
        "precision": precision, "recall": recall, "fpr": fpr,
        "model_seal": model.supplied_seal_sha256,
        "truth_seal": truth.supplied_seal_sha256, "unseal": joint_unseal_at,
        "method": method, "claim_approved": False,
        "source_claimed_complete_unverified": claimed_complete,
        "unsupported_automatic_positive_calls": unsupported_positive,
    }
    return IndependentAccuracyReport(
        len(model.cases), known, unknown, tp+tn+fp+fn,
        abstain_positive+abstain_negative, tp, tn, fp, fn,
        abstain_positive, abstain_negative, precision, recall, fpr,
        _wilson(tp, tp+fp), _wilson(fp, fp_den),
        method, False, canonical_hash(metrics),
        claimed_complete if study_kind == "REAL_EXTERNAL_REVIEW_PENDING" else 0,
        unsupported_positive,
    )
