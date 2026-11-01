"""Priority-2 freight evidence conformance, fictional sources and no real rights.

Original public-document extraction and external blind adjudications are tested
by their own frozen-source suites; these tests never claim external accuracy.
"""
from dataclasses import replace
from hashlib import sha256

import pytest

from freight.canonical_schema import build_record
from freight.original_pdf_extraction import _extract_page, KNOWN_ORIGINALS, bind_independent_shipment
from freight.priority2_evidence import (
    review_freight_rate, reconcile_invoice_evidence, witness_shipment_source,
    REQUIRED_SHIPMENT_FIELDS,
)
from freight.rate_authority import AuthorityBook, compile_authority
from freight.rating_engine import RATED, rate_record
from freight.scoped_reconciliation import ScopedTxn
from freight.sealed_real_accuracy import (
    ModelCall, TruthCall, PredictionSeal, TruthSeal, score_sealed_freight,
    prediction_seal_hash, truth_seal_hash,
)
from freight.test_phase0_recoveryos import ltl_record
from recoveryworks.reconciliation_kernel import ReconTxn


def witness(record=None):
    r = record or ltl_record()
    return witness_shipment_source(
        r.shipment, source_bytes=b"SYNTHETIC_BILL_OF_LADING_NOT_VALID_CUSTOMER_RECORD",
        source_kind="BILL_OF_LADING", supported_fields=REQUIRED_SHIPMENT_FIELDS,
    )


def row(txid, cents, ref, *, side="ORIGINAL_INVOICE", party="CARRIER-X", currency="USD"):
    major=f"{cents // 100}.{cents % 100:02d}"
    return ScopedTxn(
        ReconTxn(txid,major,"2026-09-10",currency,ref),
        buyer_id="BUYER-A",business_unit="UNIT-A",
        counterparty_id=party,origin=side,
    )


def input_rule(*, authority_id="AUTH", priority=10, verified=True,
               effective_from="2026-01-01", fixed_min=0,
               source_sha256="b"*64):
    return compile_authority({
        "authority_id":authority_id,
        "buyer_id":"BUYER-1", "business_unit":"BU-1",
        "customer_id":"CUSTOMER-1", "carrier_id":"CARRIER-A",
        "mode":"LTL","currency":"USD",
        "effective_from":effective_from,"priority":priority,
        "terms":{
            "per_cwt_cents":10000,
            "minimum_cents":fixed_min,
            "discount_bps":0,"fuel_bps":1000,
            "lane_multiplier_bps":10000,
            "class_multipliers_bps":{"70":10000},
            "accessorials":{"LIFTGATE":{"model":"FIXED","cents":5000}},
        }
    },source_sha256=source_sha256,verified_controlling_authority=verified)


def test_positive_rating_is_provisional_even_with_verified_compiled_terms():
    record=ltl_record()
    a=input_rule()
    native=rate_record(record,AuthorityBook((a,)))
    assert native.status==RATED and native.variance_cents is not None
    result=review_freight_rate(record,AuthorityBook((a,)),shipment_witness=witness(record))
    assert result.status=="REVIEW_REQUIRED"
    assert result.provisional_expected_cents==native.expected_total_cents
    assert result.provisional_variance_cents==native.variance_cents
    assert result.externally_verified_freight_error_cents is None
    assert result.externally_verified_cash_recovered_cents==0
    assert result.independent_accuracy_scored is False
    assert "BUYER_CONTRACT_RIGHTS_AND_TERMS_NOT_EXTERNALLY_AUTHENTICATED" in result.blockers
    assert "BANK_CLEARED_PAYMENT_NOT_INDEPENDENTLY_VERIFIED" in result.blockers
    assert "SHIPMENT_SOURCE_ISSUER_NOT_AUTHENTICATED" in result.blockers


def test_missing_rate_is_unresolved_without_auto_recovery():
    output=review_freight_rate(ltl_record(),AuthorityBook(()),shipment_witness=witness())
    assert "NO_EFFECTIVE_SHIPMENT_RATE_AUTHORITY" in output.blockers
    assert output.provisional_expected_cents is None and output.provisional_variance_cents is None
    assert output.externally_verified_freight_error_cents is None


def test_expired_or_future_contract_not_applied_to_shipment():
    r=ltl_record()
    old=input_rule(effective_from="2026-11-01")
    out=review_freight_rate(r,AuthorityBook((old,)),shipment_witness=witness(r))
    assert "NO_EFFECTIVE_SHIPMENT_RATE_AUTHORITY" in out.blockers


def test_unverified_rate_is_not_collectible_without_verification():
    record=ltl_record()
    a=input_rule(verified=False)
    out=review_freight_rate(record,AuthorityBook((a,)),shipment_witness=witness(record))
    assert "RATE_AUTHORITY_NOT_VERIFIED" in out.blockers
    assert out.provisional_expected_cents is None


def test_conflicting_rate_versions_do_not_auto_resolve_by_priority():
    record=ltl_record()
    hi=input_rule(authority_id="HIGH",priority=100,source_sha256="c"*64)
    lo=input_rule(authority_id="LOW",priority=1,fixed_min=99999,source_sha256="d"*64)
    native=rate_record(record,AuthorityBook((hi,lo)))
    assert native.status==RATED
    review=review_freight_rate(record,AuthorityBook((hi,lo)),shipment_witness=witness(record))
    assert "MULTIPLE_OVERLAPPING_RATE_AUTHORITIES_NEED_INDEPENDENT_SUPERSESSION" in review.blockers
    assert review.provisional_expected_cents is None
    assert review.provisional_variance_cents is None


def test_gov_rejected_tender_reference_prevents_false_positive():
    # GAO B-221594: arithmetic on an unenforceable tender was NOT a valid
    # collection. This synthetic analogue never asserts the actual case labels.
    record=ltl_record()
    tender=input_rule(authority_id="REJECTED_LOWER_TENDER")
    review=review_freight_rate(
        record,AuthorityBook((tender,)),shipment_witness=witness(record),
        rejected_authority_hashes=(tender.authority_hash,),
    )
    assert "REJECTED_OR_DISPUTED_RATE_TENDER" in review.blockers
    assert review.provisional_expected_cents is None
    assert review.externally_verified_cash_recovered_cents==0


def test_source_witness_cannot_be_reassigned_to_different_shipment():
    record=ltl_record()
    other=replace(record.shipment,actual_weight_grams=record.shipment.actual_weight_grams+1)
    updated=build_record(
        buyer_id=record.buyer_id,business_unit=record.business_unit,
        invoice_id=record.invoice_id,invoice_date=record.invoice_date,
        customer_id=record.customer_id,currency=record.currency,
        shipment=other,charges=record.charges,sources=record.sources,
    )
    result=review_freight_rate(updated,AuthorityBook((input_rule(),)),shipment_witness=witness(record))
    assert "SHIPMENT_WITNESS_FACTS_CONFLICT" in result.blockers


def test_witness_requires_independently_supplied_shipment_document_and_fields():
    record=ltl_record()
    with pytest.raises(ValueError,match="support"):
        witness_shipment_source(record.shipment,source_bytes=b"synthetic",
                                source_kind="BILL_OF_LADING",
                                supported_fields=("shipment_id","carrier_id"))
    with pytest.raises(ValueError,match="bytes"):
        witness_shipment_source(record.shipment,source_bytes=b"",source_kind="BILL_OF_LADING",
                                supported_fields=REQUIRED_SHIPMENT_FIELDS)
    with pytest.raises(ValueError,match="type"):
        witness_shipment_source(record.shipment,source_bytes=b"synthetic",source_kind="FAKE_BANK",
                                supported_fields=REQUIRED_SHIPMENT_FIELDS)


def test_no_invoice_hash_can_be_reused_as_governing_rate_source():
    record=ltl_record()
    a=input_rule(source_sha256=record.sources[0].sha256)
    output=review_freight_rate(record,AuthorityBook((a,)),shipment_witness=witness(record))
    assert "RATE_AUTHORITY_NOT_INDEPENDENT_FROM_INVOICE" in output.blockers


def test_original_discount_face_unchanged_and_shipment_not_invented():
    source=KNOWN_ORIGINALS["GLOBALTRANZ"]["sha256"]
    page=("Invoice Date Pick-Up Date Invoice No\n"
          "05/13/2025 04/25/2025 30794056\n"
          "Pieces Pallet Description Class Weight Charges\n"
          "1\n0\nTiles 175 200\n"
          "542.78\n78.91\n-280.61\n"
          "Total: 200.00 341.08 USD\n")
    found=_extract_page("GLOBALTRANZ",page,4,source)
    assert found is not None and found.signed_net_cents==34108
    assert found.adjustment_cents==28061
    with pytest.raises(ValueError,match="ShipmentFacts"):
        bind_independent_shipment(
            found,buyer_id="B",business_unit="U",customer_id="C",
            currency="USD",shipment=None,observed_at="2026-10-21T12:00:00.000000Z",
        )


def test_scoped_source_reference_groups_can_scale_to_273_fictional_invoices():
    # Structural shape of the Pennine benchmark, not its genuine financial rows.
    # 178 singleton groups, 22 doubles, 17 triples = 273 invoice declarations.
    sizes=[1]*178+[2]*22+[3]*17
    assert len(sizes)==217 and sum(sizes)==273
    originals=[];declared=[];next_index=0
    for g,n in enumerate(sizes):
        ref=f"SYN-PAY-{g:04d}";party=f"SYN-CARRIER-{g % 7}"
        cents=0
        for _ in range(n):
            amount=10000+next_index
            originals.append(row(f"SYN-INVOICE-{next_index}",amount,ref,party=party))
            cents+=amount;next_index+=1
        declared.append(row(f"SYN-PAYMENT-{g}",cents,ref,
                            side="CUSTOMER_DECLARATION",party=party))
    output=reconcile_invoice_evidence(originals,declared)
    assert output.invoices==273 and output.counterpart_declarations==217
    assert output.source_declared_matches==273
    assert output.source_declared_counterpart_matches==217
    assert output.invoice_unknown==output.counterpart_unknown==0
    assert output.authentic_bank_proof_established is False
    assert output.real_freight_detection_accuracy is None
    assert len(output.rows)==490
    reordered=reconcile_invoice_evidence(reversed(originals),reversed(declared))
    assert reordered.receipt_sha256==output.receipt_sha256


def test_orphan_payment_and_original_remain_explicit_unknown():
    originals=[row("I-1",100,"R-A"),row("I-2",200,"R-B")]
    declared=[row("D-1",100,"R-A",side="CUSTOMER_DECLARATION"),
              row("D-2",300,"R-X",side="CUSTOMER_DECLARATION")]
    result=reconcile_invoice_evidence(originals,declared)
    assert result.source_declared_matches==1
    assert result.invoice_unknown==1 and result.counterpart_unknown==1
    unknown=[x for x in result.rows if x.status=="UNKNOWN"]
    assert len(unknown)==2
    assert all(x.independently_verified_payment is False for x in result.rows)


def test_one_penny_difference_never_turns_into_verified_cash():
    result=reconcile_invoice_evidence(
        [row("I",10000,"REMIT")],
        [row("D",10001,"REMIT",side="CUSTOMER_DECLARATION")],
    )
    assert result.source_declared_matches==0
    assert result.invoice_unknown==1 and result.counterpart_unknown==1
    assert result.authentic_bank_proof_established is False


def test_cross_vendor_reused_payment_reference_is_not_a_join():
    result=reconcile_invoice_evidence(
        [row("I",10000,"SAME",party="A")],
        [row("D",10000,"SAME",side="CUSTOMER_DECLARATION",party="B")],
    )
    assert result.source_declared_matches==0
    assert result.invoice_unknown==1 and result.counterpart_unknown==1


def test_oversized_group_is_held_not_implicitly_split_or_silently_lost():
    originals=[row(f"I-{i}",10000+i,"SAME") for i in range(33)]
    declared=[row("D-0",sum(10000+i for i in range(33)),"SAME",
                  side="CUSTOMER_DECLARATION")]
    out=reconcile_invoice_evidence(originals,declared,max_group_size=32)
    assert out.source_declared_matches==0 and out.invoice_unknown==33
    assert out.counterpart_unknown==1
    assert sum(x.reason=="GROUP_BOUNDS_EXCEEDED" for x in out.rows)==34


def test_duplicate_financial_rows_fail_before_matching():
    with pytest.raises(ValueError,match="duplicate"):
        reconcile_invoice_evidence([row("I",100,"A"),row("I",100,"B")],[])


def test_real_110_invoice_label_census_remains_unknown():
    # No actual customer labels or reviewer identities can be manufactured.
    model=tuple(ModelCall(f"SYN-{i}", "REVIEW",0,
                          sha256(f"prediction-{i}".encode()).hexdigest()) for i in range(110))
    truth=tuple(TruthCall(
        f"SYN-{i}","UNRESOLVED",0,
        sha256(f"original-{i}".encode()).hexdigest(),
        None,None,None,False,
    ) for i in range(110))
    m_when="2026-10-19T12:00:00Z";t_when="2026-10-19T12:30:00Z"
    sealed_m=PredictionSeal("SYN-MODEL-ROLE",m_when,model,
        prediction_seal_hash("SYN-MODEL-ROLE",m_when,model))
    sealed_t=TruthSeal("SYN-TRUTH-ROLE","SYN-REVIEWER-A","SYN-REVIEWER-B",
        t_when,truth,truth_seal_hash("SYN-TRUTH-ROLE",
        "SYN-REVIEWER-A","SYN-REVIEWER-B",t_when,truth))
    report=score_sealed_freight(
        sealed_m,sealed_t,joint_unseal_at="2026-10-20T00:00:00Z",
        study_kind="REAL_EXTERNAL_REVIEW_PENDING",
    )
    assert report.population_count==110
    assert report.unresolved_truth_count==110
    assert report.complete_independent_truth_count==0
    assert report.precision is None
    assert report.publication_claim_approved is False
