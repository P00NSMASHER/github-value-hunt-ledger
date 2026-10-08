"""Adversarial offline evidence and financial proof tests; all source data fictional."""
import hashlib
from contextlib import closing
import hmac
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from freight.lab_assurance import (
    AssuranceRejected, Evidence, EvidenceVerifier, FeeEvent, TrustAnchor,
    canonical, verify_settlement,
)

BUYER="SIM-BUYER"; BU="SIM-DIVISION"; SRC=hashlib.sha256(b"buyer-invoice-source").hexdigest()
K_BUYER=b"buyer independent testing key..........."
K_PROVIDER=b"provider independent testing key........"
K_PAYMENT=b"payment observer testing key............"
K_APPROVER=b"independent approver testing key........."
KEYS={"buyer-signer":("BUYER",K_BUYER),"carrier-signer":("PROVIDER",K_PROVIDER),
      "bank-signer":("PAYMENT_OBSERVER",K_PAYMENT),"controller-signer":("ACCOUNTING_APPROVER",K_APPROVER)}
CLAIM="2026-10-09T12:00:00Z"


def stamp(kind, ident, issuer, asserted_at, **payload):
    payload={"buyer_id":BUYER,"business_unit":BU,**payload}
    obj=Evidence(ident,kind,issuer,asserted_at,payload,"")
    signature=hmac.new(KEYS[issuer][1],canonical(obj.message()),hashlib.sha256).hexdigest()
    return replace(obj,signature=signature)


def fee(kind,cents,when,eid=None,proof=None):
    return FeeEvent(eid or kind+str(cents),"case-1",kind,cents,when,proof)


SCHEMA="""
CREATE TABLE recovery_claims (buyer_id TEXT,business_unit TEXT,claim_id TEXT,reference TEXT,payer_id TEXT,
payee_id TEXT,currency TEXT,amount_cents INTEGER,issued_at TEXT,source_hash TEXT,fee_disqualified INTEGER);
CREATE TABLE settlement_events (buyer_id TEXT,business_unit TEXT,event_id TEXT,reference TEXT,payer_id TEXT,
payee_id TEXT,currency TEXT,amount_cents INTEGER,booked_at TEXT,source_hash TEXT,source_kind TEXT);
CREATE TABLE allocations (buyer_id TEXT,business_unit TEXT,allocation_id TEXT,claim_id TEXT,event_id TEXT,
amount_cents INTEGER,mode TEXT,fee_eligible_cents INTEGER,created_at TEXT);
CREATE TABLE counter_events (buyer_id TEXT,business_unit TEXT,counter_id TEXT,original_event_id TEXT,
currency TEXT,amount_cents INTEGER,observed_at TEXT,source_hash TEXT,source_kind TEXT);
CREATE TABLE reversal_edges (buyer_id TEXT,business_unit TEXT,reversal_id TEXT,counter_id TEXT,
allocation_id TEXT,amount_cents INTEGER,created_at TEXT);
"""


def populate(db):
    with closing(sqlite3.connect(db)) as c, c:
        c.executescript(SCHEMA)
        c.execute("INSERT INTO recovery_claims VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (BUYER,BU,"case-1","INV-100","SIM-CARRIER","SIM-BUYER","USD",1000,CLAIM,SRC,0))
        for event, amount, booked in [("credit-400",400,"2026-10-18T12:00:00Z"),
                                      ("credit-600",600,"2026-11-07T12:00:00Z")]:
            c.execute("INSERT INTO settlement_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (BUYER,BU,event,"INV-100","SIM-CARRIER","SIM-BUYER","USD",amount,booked,
                       hashlib.sha256(event.encode()).hexdigest(),"EXTERNAL"))
        for allocation,eid,amount,when in [("allocation-400","credit-400",400,"2026-10-18T13:00:00Z"),
                                            ("allocation-600","credit-600",600,"2026-11-07T13:00:00Z")]:
            c.execute("INSERT INTO allocations VALUES (?,?,?,?,?,?,?,?,?)",
                      (BUYER,BU,allocation,"case-1",eid,amount,"REVIEW",amount,when))
        c.execute("INSERT INTO counter_events VALUES (?,?,?,?,?,?,?,?,?)",
                  (BUYER,BU,"return-500","credit-600","USD",500,"2026-12-12T12:00:00Z",
                   hashlib.sha256(b"return-500").hexdigest(),"BANK-RETURN"))
        c.execute("INSERT INTO reversal_edges VALUES (?,?,?,?,?,?,?)",
                  (BUYER,BU,"reversal-500","return-500","allocation-600",500,"2026-12-12T13:00:00Z"))


def assertions_and_fees():
    proofs=[
        stamp("SOURCE_OWNER","source-proof","buyer-signer","2026-10-01T10:00:00Z",
              claim_id="case-1",reference="INV-100",payer_id="SIM-CARRIER",payee_id="SIM-BUYER",
              currency="USD",amount_cents=1000,issued_at=CLAIM,source_hash=SRC,economic_issue_id="accessorial-100"),
        stamp("FEE_CONTRACT","terms-v1","buyer-signer","2026-10-01T10:00:00Z",
              claim_id="case-1",currency="USD",source_hash=SRC,fee_bps=2000,
              fee_cap_cents=400,effective_from="2026-10-01T00:00:00Z",
              effective_until="2027-01-01T00:00:00Z",revoked_at="2026-11-20T00:00:00Z"),
    ]
    for eid,amount,booked in [("credit-400",400,"2026-10-18T12:00:00Z"),
                              ("credit-600",600,"2026-11-07T12:00:00Z")]:
        proofs.append(stamp("CREDIT_RECEIPT","proof-"+eid,"carrier-signer",booked,
                            event_id=eid,reference="INV-100",payer_id="SIM-CARRIER",
                            payee_id="SIM-BUYER",currency="USD",amount_cents=amount,
                            source_hash=hashlib.sha256(eid.encode()).hexdigest(),booked_at=booked))
    proofs.append(stamp("CREDIT_RETURN","proof-return","carrier-signer","2026-12-12T12:00:00Z",
                        counter_id="return-500",original_event_id="credit-600",currency="USD",
                        amount_cents=500,observed_at="2026-12-12T12:00:00Z",
                        source_hash=hashlib.sha256(b"return-500").hexdigest()))
    events=[fee("ACCRUE",80,"2026-10-19T12:00:00Z","a80"),
            fee("INVOICE",80,"2026-10-19T13:00:00Z","i80"),
            fee("ACCRUE",120,"2026-11-08T12:00:00Z","a120"),
            fee("INVOICE",120,"2026-11-08T13:00:00Z","i120"),
            fee("COLLECT",150,"2026-11-09T10:00:00Z","pay150","proof-pay150"),
            fee("REDUCE",100,"2026-12-13T12:00:00Z","reduce100"),
            fee("CREDIT_NOTE",100,"2026-12-13T13:00:00Z","note100"),
            fee("REFUND",50,"2026-12-14T10:00:00Z","refund50","proof-refund50")]
    proofs.append(stamp("FEE_PAYMENT","proof-pay150","bank-signer","2026-11-09T10:01:00Z",
                        fee_event_id="pay150",claim_id="case-1",currency="USD",amount_cents=150))
    proofs.append(stamp("FEE_REFUND","proof-refund50","bank-signer","2026-12-14T10:01:00Z",
                        fee_event_id="refund50",claim_id="case-1",currency="USD",amount_cents=50))
    return proofs,events


def verifier():
    anchors=[TrustAnchor(issuer,role,key,"2026-01-01T00:00:00Z")
             for issuer,(role,key) in KEYS.items()]
    return EvidenceVerifier(anchors,as_of="2027-01-01T00:00:00Z")


class AssuranceProofTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/"settlement.sqlite"
        populate(self.db)
        self.proofs,self.events=assertions_and_fees()
        self.verifier=verifier()

    def verify(self,proofs=None,events=None,**kwargs):
        return verify_settlement(self.db,buyer_id=BUYER,business_unit=BU,
            assertions=self.proofs if proofs is None else proofs,
            fee_events=self.events if events is None else events,
            verifier=self.verifier,**kwargs)

    def rejects(self,code,proofs=None,events=None,**kwargs):
        with self.assertRaises(AssuranceRejected) as caught:
            self.verify(proofs=proofs,events=events,**kwargs)
        self.assertEqual(caught.exception.code,code)

    def test_positive_retained_recovery_fee_and_refund(self):
        receipt=self.verify()
        self.assertEqual(receipt.status,"PASS_SYNTHETIC_ONLY")
        self.assertEqual(receipt.scope,"SIGNED_SYNTHETIC_EVIDENCE_ONLY")
        self.assertEqual(receipt.verified_claims,1)
        self.assertEqual(receipt.verified_receipts,2)
        self.assertEqual(receipt.currency_totals["USD"],{
            "recovered_cents":500,"earned_fee_cents":100,
            "invoiced_fee_cents":100,"collected_fee_cents":100,
            "fee_receivable_cents":0,"fee_refund_due_cents":0,"written_off_cents":0})
        self.assertEqual(len(receipt.receipt_hash),64)

    def test_reversal_before_refund_emits_refund_liability(self):
        receipt=self.verify(events=self.events[:-1])
        self.assertEqual(receipt.currency_totals["USD"]["fee_refund_due_cents"],50)
        self.assertEqual(receipt.currency_totals["USD"]["fee_receivable_cents"],0)

    def test_no_payment_evidence_is_rejected(self):
        self.rejects("MISSING_FEE_PAYMENT",proofs=[p for p in self.proofs if p.kind!="FEE_PAYMENT"])

    def test_no_refund_evidence_is_rejected(self):
        self.rejects("MISSING_FEE_REFUND",proofs=[p for p in self.proofs if p.kind!="FEE_REFUND"])

    def test_self_rehashed_unsigned_receipt_rejected(self):
        altered=[replace(p,payload={**p.payload,"amount_cents":999999}) if p.evidence_id=="proof-credit-400" else p for p in self.proofs]
        self.rejects("EVIDENCE_SIGNATURE_INVALID",proofs=altered)

    def test_unknown_source_issuer_rejected(self):
        altered=[replace(p,issuer="intruder") if p.kind=="SOURCE_OWNER" else p for p in self.proofs]
        self.rejects("UNTRUSTED_EVIDENCE_ISSUER",proofs=altered)

    def test_changed_tenant_rejected(self):
        altered=[replace(p,payload={**p.payload,"buyer_id":"OTHER"}) if p.kind=="CREDIT_RECEIPT" else p for p in self.proofs]
        self.rejects("EVIDENCE_SIGNATURE_INVALID",proofs=altered)

    def test_original_credit_changed_without_provider_signer_rejected(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE settlement_events SET amount_cents=4000 WHERE event_id='credit-400'")
        self.rejects("CREDIT_PROVENANCE_MISMATCH")

    def test_forged_claim_amount_rejected(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE recovery_claims SET amount_cents=100000 WHERE claim_id='case-1'")
        self.rejects("SOURCE_OWNER_BINDING_MISMATCH")

    def test_fee_rate_amendment_after_claim_rejected(self):
        contract=[p for p in self.proofs if p.kind=="FEE_CONTRACT"][0]
        updated=stamp("FEE_CONTRACT","terms-v1","buyer-signer","2026-11-01T00:00:00Z",**contract.payload)
        self.rejects("FEE_TERMS_NOT_SIGNED_BEFORE_CLAIM",
                     proofs=[updated if p.kind=="FEE_CONTRACT" else p for p in self.proofs])

    def test_fee_invoice_without_reversal_credit_note_rejected(self):
        self.rejects("FEE_INVOICE_NOT_RECONCILED",
                     events=[x for x in self.events if x.kind!="CREDIT_NOTE"])

    def test_fee_accrual_without_decrease_after_reversal_rejected(self):
        self.rejects("FEE_ACCRUED_BEFORE_SUPPORTED_CREDIT",
                     events=[x for x in self.events if x.kind!="REDUCE"])

    def test_phantom_early_accrual_rejected(self):
        earlier=[replace(x,occurred_at="2026-10-10T00:00:00Z") if x.event_id=="a80" else x for x in self.events]
        self.rejects("FEE_ACCRUED_BEFORE_SUPPORTED_CREDIT",events=earlier)

    def test_negative_cents_rejected(self):
        events=[replace(x,amount_cents=-2) if x.event_id=="a80" else x for x in self.events]
        self.rejects("INVALID_FEE_AMOUNT",events=events)

    def test_duplicate_fees_rejected(self):
        self.rejects("DUPLICATE_FEE_EVENT",events=self.events+[self.events[0]])

    def test_credit_double_allocated_to_other_issue_rejected(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("INSERT INTO allocations VALUES (?,?,?,?,?,?,?,?,?)",
                        (BUYER,BU,"extra","case-1","credit-400",400,"REVIEW",400,"2026-10-18T14:00:00Z"))
        self.rejects("RECEIPT_OVER_ALLOCATED")

    def test_missing_credit_provenance_rejected(self):
        self.rejects("MISSING_CREDIT_RECEIPT",proofs=[x for x in self.proofs if x.evidence_id!="proof-credit-600"])

    def test_unsupported_fee_writeoff_rejected(self):
        events=[x for x in self.events if x.event_id not in ("refund50",)]
        events.append(fee("WRITE_OFF",1,"2026-12-14T12:00:00Z","writeoff-1",None))
        self.rejects("MISSING_WRITE_OFF_APPROVAL",events=events)

    def test_wrong_reversal_reference_rejected(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE reversal_edges SET allocation_id='allocation-400'")
        self.rejects("REVERSAL_WRONG_RECEIPT")

    def test_return_over_original_cap_rejected(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE counter_events SET amount_cents=700")
        # Stored return no longer agrees with signed evidence, which is stronger.
        self.rejects("CREDIT_RETURN_PROVENANCE_MISMATCH")

    def test_summary_cannot_silently_inflate_recovery(self):
        self.rejects("REPORTED_FINANCIAL_TOTAL_MISMATCH",reported_totals={"USD":{"recovered_cents":999999}})

    def test_without_owner_claim_proof_fails_closed(self):
        self.rejects("MISSING_SOURCE_OWNER",proofs=[x for x in self.proofs if x.kind!="SOURCE_OWNER"])

    def test_duplicate_evidence_identity(self):
        self.rejects("DUPLICATE_EVIDENCE_ID",proofs=self.proofs+[self.proofs[0]])

    def test_empty_population_fails(self):
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("DELETE FROM reversal_edges")
            con.execute("DELETE FROM allocations")
            con.execute("DELETE FROM counter_events")
            con.execute("DELETE FROM settlement_events")
            con.execute("DELETE FROM recovery_claims")
        self.rejects("EMPTY_CLAIM_POPULATION")


if __name__=="__main__":
    unittest.main()
