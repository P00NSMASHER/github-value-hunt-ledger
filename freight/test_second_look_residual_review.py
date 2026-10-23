"""Second-look residual and economic-identity guard regressions.

These are synthetic classification tests, not evidence of buyer/customer yield.
Matching an incumbent issue may hide *partial* unresolved residuals; they must
reach human review without ever becoming fee-eligible or net-new automatically.
"""
import pytest

from freight.incumbent_challenge import (
    ChallengeCandidate,
    IncumbentMatter,
    challenge_incumbent,
    freeze_incumbent_snapshot,
)

ECONOMIC_KEY = "INV-1|SHIP-1|FUEL"


def _snapshot(*matters: IncumbentMatter):
    return freeze_incumbent_snapshot(
        buyer_id="TEST-BUYER",
        business_unit="TEST-BU",
        population_hash="p" * 64,
        source_hash="s" * 64,
        matters=matters,
    )


def _matter(matter_id: str, amount: int, state: str = "AUTOMATIC_CREDIT"):
    return IncumbentMatter(
        matter_id, ECONOMIC_KEY, state, amount, "a" * 64,
    )


def _candidate(variance: int = 1_000):
    return ChallengeCandidate(
        "C1", ECONOMIC_KEY, "r" * 64, "FUEL",
        2_000, 2_000 - variance, 950_000,
        evidence_hashes=("e" * 64,),
    )


def test_partial_incumbent_credit_routes_remaining_issue_to_review():
    batch = challenge_incumbent(_snapshot(_matter("M1", 200)), (_candidate(1_000),))
    item = batch.dispositions[0]
    assert item.attribution_state == "REVIEW"
    assert item.matched_incumbent_matter_ids == ("M1",)
    assert "POTENTIAL_INCUMBENT_RESIDUAL" in item.blocker_codes
    assert item.net_new_candidate_cents == 0
    assert batch.challenger_only_cents == 0
    assert batch.review_cents == 1_000


def test_overlapping_incumbent_matters_are_not_blindly_summed_as_full_coverage():
    # Two known records might describe the same credit/claim. Without external
    # allocation evidence, summing 500+500 cannot prove a 750-cent issue covered.
    snapshot = _snapshot(_matter("M1", 500), _matter("M2", 500, "OPEN_CLAIM"))
    item = challenge_incumbent(snapshot, (_candidate(750),)).dispositions[0]
    assert item.attribution_state == "REVIEW"
    assert item.matched_incumbent_matter_ids == ("M1", "M2")
    assert "POTENTIAL_INCUMBENT_RESIDUAL" in item.blocker_codes
    assert item.net_new_candidate_cents == 0


def test_fully_incumbent_known_issue_remains_excluded():
    item = challenge_incumbent(_snapshot(_matter("M1", 1_000)), (_candidate(800),)).dispositions[0]
    assert item.attribution_state == "INCUMBENT_KNOWN"
    assert item.net_new_candidate_cents == 0


def test_genuinely_unmatched_candidate_is_distinct_from_known_credit():
    batch = challenge_incumbent(_snapshot(), (_candidate(),))
    assert batch.dispositions[0].attribution_state == "CHALLENGER_ONLY"
    assert batch.challenger_only_cents == 1_000
    # The candidate is still not externally adjudicated or realized recovery.


def test_noncanonical_economic_key_cannot_evade_incumbent_matching():
    with pytest.raises(ValueError, match="canonical"):
        IncumbentMatter("M1", " " + ECONOMIC_KEY, "FINDING", 100, "a" * 64)
    with pytest.raises(ValueError, match="canonical"):
        ChallengeCandidate("C1", ECONOMIC_KEY + " ", "r" * 64, "FUEL", 2_000, 1_000, 950_000)
    with pytest.raises(ValueError, match="canonical"):
        ChallengeCandidate("C1", "Cafe\u0301", "r" * 64, "FUEL", 2_000, 1_000, 950_000)
