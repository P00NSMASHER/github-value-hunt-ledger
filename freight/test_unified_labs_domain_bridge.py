"""Real RecoveryOS domain tests for the five-step fictional unified laboratory.

Full staging digital twin is delivered in the portable offline artifact;
these exercises specifically import existing repository rating and PaymentOS
modules rather than misreporting the twin as the deployed product.
"""
import hashlib
import pytest
from dataclasses import replace

from freight.unified_labs_domain_bridge import (
    FictionalReleaseAuthorization, lab_reconciliation_manifest,
    run_actual_domain_shadow, real_customer_release_gate
)


def contract(case="parcel_positive", **overrides):
    data = dict(
        tenant="SIM-TENANT-1",
        source_invoice_id="INV-"+case,
        source_customer_id="FICTIONAL-GOLD-CUSTOMER",
        source_sha256=hashlib.sha256(("source:"+case).encode()).hexdigest(),
        buyer_signed_scope=True,
        reviewer_independent=True,
        buyer_action_approved=True,
        provider_reconciled=True,
        fee_bps=2000,
    )
    data.update(overrides)
    return FictionalReleaseAuthorization(**data)


def test_legacy_five_laboratory_branches_still_separately_tracked():
    m=lab_reconciliation_manifest()
    assert set(m["draft_pull_requests"])=={263,264,271,272,273}
    assert m["all_draft_labs_integrated_into_production"] is False
    assert m["requires_human_merge_review"]


def test_actual_repo_rating_payment_lifecycle_settled_with_separate_reconciliation():
    out=run_actual_domain_shadow(rating_case_id="parcel_positive",authorization=contract())
    assert out["rating_engine_status"]=="RATED"
    assert out["allowed_fake_submission"] is True
    assert out["fictitious_carrier_state"]=="SETTLED"
    assert out["buyer_reconciled_cents"]>0
    assert out["fee_eligible_cents"]==out["buyer_reconciled_cents"]*2000//10000
    assert out["real_bank_amount_cents"]==0
    assert out["live_recoveryos_api_tested"] is False


def test_provider_settled_does_not_mean_buyer_reconciled():
    out=run_actual_domain_shadow(rating_case_id="parcel_positive",
                                 authorization=contract(provider_reconciled=False))
    assert out["carrier_reported_settled_cents"]>0
    assert out["buyer_reconciled_cents"]==0
    assert out["fee_eligible_cents"]==0


def test_provider_credit_reversal_erases_positive_cash():
    out=run_actual_domain_shadow(
        rating_case_id="parcel_positive",authorization=contract(),
        model_provider_states=("SUBMITTED","ACCEPTED","SETTLED","REVERSED"))
    assert out["fictitious_carrier_state"]=="REVERSED"
    assert out["carrier_reported_settled_cents"]==0
    assert out["buyer_reconciled_cents"]==0
    assert out["fee_eligible_cents"]==0


@pytest.mark.parametrize("override",[
    {"buyer_signed_scope":False},
    {"reviewer_independent":False},
    {"buyer_action_approved":False},
    {"revoked":True},
])
def test_missing_authorization_or_independent_review_fails_closed(override):
    out=run_actual_domain_shadow(rating_case_id="parcel_positive",authorization=contract(**override))
    assert out["allowed_fake_submission"] is False
    assert out["carrier_reported_settled_cents"]==0


def test_negative_invoice_cannot_be_recovered():
    out=run_actual_domain_shadow(rating_case_id="parcel_negative",
                                 authorization=contract("parcel_negative"))
    assert out["allowed_fake_submission"] is False
    assert out["fee_eligible_cents"]==0


def test_review_required_not_auto_promoted():
    out=run_actual_domain_shadow(rating_case_id="parcel_missing_zone_review",
                                 authorization=contract("parcel_missing_zone_review"))
    assert out["rating_engine_status"]=="REVIEW_REQUIRED"
    assert out["carrier_reported_settled_cents"]==0


def test_wrong_invoice_identity_rejected():
    with pytest.raises(ValueError,match="invoice ID"):
        run_actual_domain_shadow(rating_case_id="parcel_positive",
                                 authorization=contract(source_invoice_id="INV-UNRELATED"))


def test_wrong_source_sha_rejected():
    with pytest.raises(ValueError,match="source proof hash"):
        run_actual_domain_shadow(rating_case_id="parcel_positive",
                                 authorization=contract(source_sha256="0"*64))


def test_wrong_customer_scope_rejected():
    with pytest.raises(ValueError,match="customer scope"):
        run_actual_domain_shadow(rating_case_id="parcel_positive",
                                 authorization=contract(source_customer_id="FICTIONAL-SOMEONE-ELSE"))


def test_unknown_case_does_not_promote_money():
    with pytest.raises(ValueError,match="unknown frozen rating fixture"):
        run_actual_domain_shadow(rating_case_id="UNKNOWN",authorization=contract())


def test_wrong_live_tenant_prefix_rejected():
    with pytest.raises(ValueError,match="synthetic tenant"):
        run_actual_domain_shadow(rating_case_id="parcel_positive",
                                 authorization=contract(tenant="ACTUAL-TENANT"))


def test_fee_terms_rejected_above_bound():
    with pytest.raises(ValueError,match="fee basis"):
        run_actual_domain_shadow(rating_case_id="parcel_positive",
                                 authorization=contract(fee_bps=8000))


def test_any_real_customer_proof_requires_external_approval():
    out=real_customer_release_gate(
        externally_adjudicated_truth=False,buyer_signed=False,
        real_bank_confirmation=False,tenant_isolation_verified=False)
    assert out["status"]=="BLOCKED_EXTERNAL_REAL_CUSTOMER_PROOF"
    assert len(out["blockers"])==4
    assert out["automatic_customer_claims"] is False


def test_even_external_evidence_does_not_automatically_authorize_deploy():
    out=real_customer_release_gate(
        externally_adjudicated_truth=True,buyer_signed=True,
        real_bank_confirmation=True,tenant_isolation_verified=True)
    assert out["status"]=="REVIEW_REQUIRED"
    assert out["automatic_production_deployment"] is False


def test_fake_provider_cannot_skip_to_settlement():
    with pytest.raises(ValueError,match="invalid payment transition"):
        run_actual_domain_shadow(
            rating_case_id="parcel_positive",authorization=contract(),
            model_provider_states=("SETTLED",))
