from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from recoveryworks.branches.cloud_commitment import (
    CloudCommitmentAuthority, CommitmentAllocation, audit_cloud_commitment_billing,
)
from recoveryworks.branches.cloud_discount import (
    CloudDiscountAuthority, DiscountAppliesTo, audit_cloud_discount_billing,
)
from recoveryworks.branches.contract_billing import ContractRate, InvoiceCharge, UsageRecord
from recoveryworks.engine import RecoveryEngine
from recoveryworks.integrations.cletrics import CLETRICS_BUNDLE_TYPE
from recoveryworks.models import FindingState
from recoveryworks.runner import run_scan360_config


def H(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def rate(*, verified=True, unit_rate=2_000_000):
    return ContractRate(
        counterparty_id="AWS",service_id="compute",effective_from="2026-01-01",
        effective_to=None,fixed_cents=1000,included_units="0",
        unit_rate_micros=unit_rate,source_hash=H("base-rate"),
        source_locator="file://base-rates.csv#row=2",verified=verified,
    )


def charge(*, actual=4000, verified=True):
    return InvoiceCharge(
        charge_id="C-1",counterparty_id="AWS",account_id="acct-1",
        service_id="compute",service_date="2026-08-31",actual_cents=actual,
        source_hash=H("invoice"),source_locator="bundle://cletrics/billing.csv#row=2",
        verified=verified,
    )


def usage(*, units="10", verified=True):
    return UsageRecord(
        charge_id="C-1",units=units,source_hash=H("meter"),
        source_locator="bundle://cletrics/meter.csv#charge=C-1",verified=verified,
    )


def bundle(path: Path) -> None:
    charges=(
        b"Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
        b"C-1,AWS,acct-1,compute,2026-08-31,40.00\n"
    )
    meter=b"Charge_ID,Meter_Record_ID,Usage_Units\nC-1,M-1,10\n"
    entries=[]
    for role,name,raw,kind in [
        ("invoice_charges","billing/charges.csv",charges,"provider_billing_export"),
        ("meter_usage","usage/meter.csv",meter,"provider_meter_export"),
    ]:
        entries.append({
            "role":role,"path":name,"sha256":hashlib.sha256(raw).hexdigest(),
            "size_bytes":len(raw),"transformation_id":"test-v1",
            "source":{"kind":kind,"locator":f"provider://{role}","sha256":H(kind),"acquired_at":"2026-09-23T20:00:00Z"},
        })
    manifest={
        "schema":1,"bundle_type":CLETRICS_BUNDLE_TYPE,"client_id":"client-1",
        "provider":"aws","billing_account_id":"acct-1","currency":"USD",
        "period_start":"2026-08-01","period_end":"2026-08-31",
        "exported_at":"2026-09-23T21:00:00Z",
        "cletrics":{"release":"test","commit":"a"*40,"image_digest":None},
        "entries":entries,
    }
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("manifest.json",json.dumps(manifest,sort_keys=True,separators=(",",":")))
        z.writestr("billing/charges.csv",charges); z.writestr("usage/meter.csv",meter)


class DiscountTests(unittest.TestCase):
    def auth(self,*,verified=True,bps=1000):
        return CloudDiscountAuthority(
            counterparty_id="AWS",account_id="acct-1",service_id="compute",
            effective_from="2026-01-01",effective_to=None,discount_bps=bps,
            applies_to=DiscountAppliesTo.VARIABLE,source_hash=H("discount"),
            source_locator="file://discount.csv#row=2",verified=verified,
        )

    def test_verified_discount_validates(self):
        batch=audit_cloud_discount_billing(
            client_id="client",charges=(charge(),),rates=(rate(),),
            discounts=(self.auth(),),usage=(usage(),),
        )
        finding=RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state,FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents,2800)
        self.assertEqual(finding.potential_recovery_cents,1200)

    def test_unverified_discount_stays_review(self):
        batch=audit_cloud_discount_billing(
            client_id="client",charges=(charge(),),rates=(rate(),),
            discounts=(self.auth(verified=False),),usage=(usage(),),
        )
        self.assertIs(RecoveryEngine().evaluate(batch.observations[0]).state,FindingState.REVIEW)

    def test_overlapping_discount_fails_closed(self):
        batch=audit_cloud_discount_billing(
            client_id="client",charges=(charge(),),rates=(rate(),),
            discounts=(self.auth(),self.auth(bps=1500)),usage=(usage(),),
        )
        self.assertEqual(batch.observations,())
        self.assertEqual(batch.exceptions[0].code,"OVERLAPPING_DISCOUNT_AUTHORITIES")


class CommitmentTests(unittest.TestCase):
    def commitment(self,*,verified=True,committed_rate=1_000_000):
        return CloudCommitmentAuthority(
            counterparty_id="AWS",account_id="acct-1",service_id="compute",
            effective_from="2026-01-01",effective_to=None,commitment_type="savings_plan",
            committed_unit_rate_micros=committed_rate,source_hash=H("commitment"),
            source_locator="file://commitments.csv#row=2",verified=verified,
        )

    def allocation(self,*,units="6",verified=True):
        return CommitmentAllocation(
            charge_id="C-1",entitled_units=units,source_hash=H("allocation"),
            source_locator="file://allocation.csv#row=2",verified=verified,
        )

    def test_only_evidenced_covered_units_get_commitment_rate(self):
        batch=audit_cloud_commitment_billing(
            client_id="client",charges=(charge(),),rates=(rate(),),
            commitments=(self.commitment(),),allocations=(self.allocation(),),usage=(usage(),),
        )
        finding=RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state,FindingState.VALIDATED)
        self.assertEqual(finding.metadata["covered_units"],"6")
        self.assertEqual(finding.metadata["uncovered_units"],"4")
        self.assertEqual(finding.expected_cents,2400)

    def test_unused_commitment_is_context_not_credit(self):
        batch=audit_cloud_commitment_billing(
            client_id="client",charges=(charge(actual=2500),),rates=(rate(),),
            commitments=(self.commitment(),),allocations=(self.allocation(units="100"),),
            usage=(usage(),),
        )
        finding=RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.metadata["covered_units"],"10")
        self.assertEqual(finding.metadata["unused_entitled_units"],"90")
        self.assertEqual(finding.expected_cents,2000)
        self.assertEqual(finding.potential_recovery_cents,500)

    def test_missing_or_unverified_allocation_fails_or_reviews(self):
        missing=audit_cloud_commitment_billing(
            client_id="client",charges=(charge(),),rates=(rate(),),
            commitments=(self.commitment(),),allocations=(),usage=(usage(),),
        )
        self.assertEqual(missing.observations,())
        self.assertEqual(missing.exceptions[0].code,"MISSING_COMMITMENT_ALLOCATION")
        unverified=audit_cloud_commitment_billing(
            client_id="client",charges=(charge(),),rates=(rate(),),
            commitments=(self.commitment(),),allocations=(self.allocation(verified=False),),
            usage=(usage(),),
        )
        self.assertIs(RecoveryEngine().evaluate(unverified.observations[0]).state,FindingState.REVIEW)

    def test_commitment_rate_above_base_fails_closed(self):
        batch=audit_cloud_commitment_billing(
            client_id="client",charges=(charge(),),rates=(rate(),),
            commitments=(self.commitment(committed_rate=3_000_000),),
            allocations=(self.allocation(),),usage=(usage(),),
        )
        self.assertEqual(batch.observations,())
        self.assertEqual(batch.exceptions[0].code,"COMMITMENT_RATE_EXCEEDS_BASE_RATE")


class RunnerAuthorityTests(unittest.TestCase):
    def test_discount_and_commitment_modes_use_reviewed_authorities(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); bundle(root/"cletrics.zip")
            (root/"rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,Included_Units,Unit_Rate\n"
                "AWS,compute,2026-01-01,,10.00,0,2.00\n",encoding="utf-8")
            (root/"discounts.csv").write_text(
                "Counterparty,Account_ID,Service_ID,Effective_From,Effective_To,Discount_BPS,Applies_To\n"
                "AWS,acct-1,compute,2026-01-01,,1000,VARIABLE\n",encoding="utf-8")
            discount=run_scan360_config(
                {"client_id":"client-1","currency":"USD","cloud_discount":{
                    "cletrics_bundle":"cletrics.zip","rates_csv":"rates.csv","discounts_csv":"discounts.csv",
                    "charge_source_verified":True,"meter_source_verified":True,
                    "rate_source_verified":True,"discount_source_verified":True,
                }},
                state_path=root/"discount-ledger.json",base_dir=root)
            self.assertEqual(discount.report.totals["validated_cents"],1200)

            (root/"commitments.csv").write_text(
                "Counterparty,Account_ID,Service_ID,Effective_From,Effective_To,Commitment_Type,Committed_Unit_Rate\n"
                "AWS,acct-1,compute,2026-01-01,,savings_plan,1.00\n",encoding="utf-8")
            (root/"allocations.csv").write_text(
                "Charge_ID,Allocation_ID,Entitled_Units\nC-1,ALLOC-1,6\n",encoding="utf-8")
            commitment=run_scan360_config(
                {"client_id":"client-1","currency":"USD","cloud_commitment":{
                    "cletrics_bundle":"cletrics.zip","rates_csv":"rates.csv",
                    "commitments_csv":"commitments.csv","allocations_csv":"allocations.csv",
                    "charge_source_verified":True,"meter_source_verified":True,
                    "rate_source_verified":True,"commitment_source_verified":True,
                    "allocation_source_verified":True,
                }},
                state_path=root/"commit-ledger.json",base_dir=root)
            self.assertEqual(commitment.report.totals["validated_cents"],1600)


if __name__=="__main__":
    unittest.main()
