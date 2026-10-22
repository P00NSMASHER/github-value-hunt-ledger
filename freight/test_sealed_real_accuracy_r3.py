"""R3: a real missing label stays unknown; synthetic trial cannot authorize claims."""
from dataclasses import replace

import pytest

from freight.sealed_real_accuracy import (
    ModelCall, TruthCall, PredictionSeal, TruthSeal,
    prediction_seal_hash, truth_seal_hash, score_sealed_freight,
)

OUTPUT_AT = "2026-10-18T12:00:00+00:00"
TRUTH_AT = "2026-10-18T13:00:00+00:00"
UNSEAL_AT = "2026-10-18T14:00:00+00:00"


def case(i, true, pred, *, complete=True, cents=None):
    value = (100 if true == "POSITIVE" else 0) if cents is None else cents
    result = TruthCall(
        case_id=str(i), truth_label=true, adjudicated_overcharge_cents=value,
        original_invoice_sha256="a"*64,
        applicable_rate_sha256=("b"*64 if complete else None),
        bank_payment_sha256=("c"*64 if complete else None),
        adjudication_sha256=("d"*64 if complete else None),
        source_complete=complete,
    )
    model = ModelCall(str(i), pred, 100 if pred == "POSITIVE" else 0, "f"*64)
    return result, model


def freeze(pairs):
    true = tuple(x for x, _ in pairs)
    pred = tuple(x for _, x in pairs)
    model = PredictionSeal(
        "model operator", OUTPUT_AT, pred,
        prediction_seal_hash("model operator", OUTPUT_AT, pred),
    )
    truth = TruthSeal(
        "truth owner", "reviewer A", "reviewer B", TRUTH_AT, true,
        truth_seal_hash("truth owner", "reviewer A", "reviewer B", TRUTH_AT, true),
    )
    return model, truth


def test_blinded_unknown_population_110_not_claimed_correct_or_negative():
    pairs = [case(i, "UNRESOLVED", "REVIEW", complete=False) for i in range(110)]
    m, t = freeze(pairs)
    result = score_sealed_freight(
        m, t, joint_unseal_at=UNSEAL_AT,
        study_kind="REAL_EXTERNAL_REVIEW_PENDING")
    assert result.population_count == result.unresolved_truth_count == 110
    assert result.complete_independent_truth_count == 0
    assert result.precision is None
    assert result.observed_positive_recall_including_reviews is None
    assert result.false_positive_rate is None
    assert result.method_status == "INSUFFICIENT_INDEPENDENT_LABELS"
    assert result.publication_claim_approved is False


def test_synthetic_gold_math_includes_reviews_in_denominator():
    pairs = [
        case(1, "POSITIVE", "POSITIVE"),
        case(2, "POSITIVE", "REVIEW"),
        case(3, "NEGATIVE", "NEGATIVE"),
        case(4, "NEGATIVE", "POSITIVE"),
        case(5, "NEGATIVE", "REVIEW"),
        case(6, "UNRESOLVED", "REVIEW", complete=False),
    ]
    m, t = freeze(pairs)
    score = score_sealed_freight(
        m, t, joint_unseal_at=UNSEAL_AT,
        study_kind="SYNTHETIC_REHEARSAL")
    assert score.complete_independent_truth_count == 5
    assert score.unresolved_truth_count == 1
    assert (score.true_positive, score.true_negative, score.false_positive,
            score.false_negative) == (1, 1, 1, 0)
    assert (score.positive_review_abstentions, score.negative_review_abstentions) == (1, 1)
    assert score.precision == 0.5
    assert score.observed_positive_recall_including_reviews == 0.5
    assert score.false_positive_rate == 1/3
    assert score.precision_wilson_95["lower_95"] < 0.5
    assert score.false_positive_rate_wilson_95["upper_95"] > 1/3
    assert score.method_status == "INTERNAL_SYNTHETIC_REHEARSAL_ONLY"
    assert score.publication_claim_approved is False


@pytest.mark.parametrize("mutation,expected", [
    ("tamper_model", "model freeze hash"),
    ("tamper_truth", "truth freeze hash"),
    ("late_model", "not frozen before unseal"),
    ("late_truth", "not frozen before unseal"),
    ("same_reviewer", "roles must be distinct"),
    ("wrong_population", "populations differ"),
])
def test_blind_freeze_cannot_be_replayed_after_reveal_or_with_conflicts(mutation, expected):
    m, t = freeze([case(1, "POSITIVE", "POSITIVE"), case(2, "NEGATIVE", "NEGATIVE")])
    if mutation == "tamper_model":
        m = replace(m, cases=(replace(m.cases[0], predicted_label="REVIEW",
                                   predicted_variance_cents=0), m.cases[1]))
    if mutation == "tamper_truth":
        t = replace(t, cases=(replace(t.cases[0], truth_label="UNRESOLVED",
                                   adjudicated_overcharge_cents=0), t.cases[1]))
    if mutation == "late_model":
        m = replace(m, frozen_at=UNSEAL_AT)
    if mutation == "late_truth":
        t = replace(t, frozen_at=UNSEAL_AT)
    if mutation == "same_reviewer":
        t = replace(t, reviewer_two_id=m.operator_id)
    if mutation == "wrong_population":
        t = replace(t, cases=t.cases[:1],
                    supplied_seal_sha256=truth_seal_hash(
                        t.truth_owner_id, t.reviewer_one_id, t.reviewer_two_id,
                        t.frozen_at, t.cases[:1]))
    with pytest.raises(ValueError, match=expected):
        score_sealed_freight(
            m, t, joint_unseal_at=UNSEAL_AT,
            study_kind="REAL_EXTERNAL_REVIEW_PENDING")


def test_self_claimed_complete_real_evidence_cannot_manufacture_independence():
    # Four distinct SHA strings and separately named fictional reviewers are
    # a synthetic proof of parsing, never independent external adjudication.
    model, truth = freeze([case(1, "POSITIVE", "POSITIVE"),
                           case(2, "NEGATIVE", "NEGATIVE")])
    report = score_sealed_freight(
        model, truth, joint_unseal_at=UNSEAL_AT,
        study_kind="REAL_EXTERNAL_REVIEW_PENDING")
    assert report.complete_independent_truth_count == 0
    assert report.unresolved_truth_count == 2
    assert report.source_claimed_complete_cases_unverified == 2
    assert report.unsupported_automatic_positive_calls == 1
    assert report.precision is None
    assert report.false_positive_rate is None
    assert report.publication_claim_approved is False
    assert report.method_status == "EXTERNAL_PROVENANCE_AUTHENTICATION_REQUIRED"


def test_missing_or_reused_corroboration_is_unresolved():
    t, m = case(1, "POSITIVE", "POSITIVE")
    invalid_rate = replace(t, applicable_rate_sha256=t.original_invoice_sha256)
    missing_bank = replace(t, bank_payment_sha256=None)
    for modified in (invalid_rate, missing_bank):
        mm, tt = freeze([(modified, m)])
        report = score_sealed_freight(mm, tt, joint_unseal_at=UNSEAL_AT,
                                     study_kind="REAL_EXTERNAL_REVIEW_PENDING")
        assert report.complete_independent_truth_count == 0
        assert report.unresolved_truth_count == 1
        assert report.precision is None
        assert report.publication_claim_approved is False


def test_conflicting_money_and_labels_are_rejected():
    with pytest.raises(ValueError, match="positive truth"):
        case(1, "POSITIVE", "REVIEW", cents=0)
    with pytest.raises(ValueError, match="no-money truth"):
        case(1, "NEGATIVE", "REVIEW", cents=100)
    with pytest.raises(ValueError, match="negative/review"):
        ModelCall("x", "NEGATIVE", 100, "f"*64)


def test_reordering_does_not_change_sealed_math():
    pairs = [case(i, "NEGATIVE", "NEGATIVE") for i in range(50)]
    m, t = freeze(pairs)
    report = score_sealed_freight(m, t, joint_unseal_at=UNSEAL_AT,
                                  study_kind="SYNTHETIC_REHEARSAL")
    reordered = list(reversed(pairs))
    m2, t2 = freeze(reordered)
    again = score_sealed_freight(m2, t2, joint_unseal_at=UNSEAL_AT,
                                 study_kind="SYNTHETIC_REHEARSAL")
    assert report.report_hash == again.report_hash
    assert report.complete_independent_truth_count == 50
    assert report.precision is None
    assert report.false_positive_rate == 0


def test_report_hash_distinguishes_study_kind_even_when_every_case_is_unknown():
    """One study population must not have the same evidence receipt in two tiers."""
    model, truth = freeze([case(1, "UNRESOLVED", "REVIEW", complete=False)])
    synthetic = score_sealed_freight(
        model, truth, joint_unseal_at=UNSEAL_AT,
        study_kind="SYNTHETIC_REHEARSAL",
    )
    pending_real = score_sealed_freight(
        model, truth, joint_unseal_at=UNSEAL_AT,
        study_kind="REAL_EXTERNAL_REVIEW_PENDING",
    )
    assert synthetic.method_status == pending_real.method_status == "INSUFFICIENT_INDEPENDENT_LABELS"
    assert synthetic.complete_independent_truth_count == pending_real.complete_independent_truth_count == 0
    assert synthetic.unresolved_truth_count == pending_real.unresolved_truth_count == 1
    assert synthetic.precision is pending_real.precision is None
    assert not synthetic.publication_claim_approved and not pending_real.publication_claim_approved
    assert synthetic.report_hash != pending_real.report_hash
