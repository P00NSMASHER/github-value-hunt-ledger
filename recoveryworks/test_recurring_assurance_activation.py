from __future__ import annotations

import unittest

from recoveryworks.commercial_agreement_gate import (
    build_external_finalized_commercial_agreement,
)
from recoveryworks.pilot_closeout_acknowledgment import (
    ContinuationInterest,
    verify_buyer_closeout_acknowledgment,
)
from recoveryworks.recurring_assurance_activation import (
    build_external_recurring_assurance_authorization,
    build_recurring_assurance_activation_readiness,
)
from recoveryworks.test_commercial_agreement_gate import fixture
from recoveryworks.test_pilot_closeout_acknowledgment import closeout, receipt


class RecurringAssuranceActivationTests(unittest.TestCase):
    def test_separate_external_authorization_opens_readiness_only(self):
        charter,snapshot,ack,agreement=fixture(
            monthly_assurance_fee_cents=300000,
            monthly_assurance_separately_accepted=True)
        auth=build_external_recurring_assurance_authorization(
            charter,ack,agreement,
            service_start_at="2026-10-01T00:00:00Z",
            service_end_at="2027-10-01T00:00:00Z",
            authorization_reference="buyer-auth-monthly-001",
            source_hash="8"*64,
            source_locator="buyer://monthly-assurance/001",
            verified=True,externally_authorized=True)
        ready=build_recurring_assurance_activation_readiness(
            charter,ack,agreement,auth)
        self.assertEqual(
            ready.as_dict()["state"],"MONTHLY_ASSURANCE_ACTIVATION_READY")
        self.assertFalse(ready.service_started)
        self.assertFalse(ready.invoice_schedule_started)
        self.assertFalse(ready.provider_calls_started)
        self.assertFalse(ready.provider_mutation_authorized)

    def test_interest_or_agreement_acceptance_missing_fails_closed(self):
        charter,snapshot=closeout()
        stop_ack=verify_buyer_closeout_acknowledgment(
            snapshot,charter,
            receipt(
                charter,snapshot,
                continuation_interest=ContinuationInterest.STOP_AFTER_PILOT))
        agreement=build_external_finalized_commercial_agreement(
            charter,stop_ack,
            agreement_reference="agreement-stop",currency="USD",
            diagnostic_fee_cents=0,recovered_cash_success_fee_bps=0,
            monthly_assurance_fee_cents=300000,payment_terms_days=30,
            diagnostic_fee_applicable=False,success_fee_applicable=False,
            monthly_assurance_separately_accepted=True,
            effective_at="2026-09-24T16:30:00Z",
            source_hash="9"*64,source_locator="agreement://stop",
            verified=True,externally_finalized=True)
        with self.assertRaisesRegex(ValueError,"continuation interest"):
            build_external_recurring_assurance_authorization(
                charter,stop_ack,agreement,
                service_start_at="2026-10-01T00:00:00Z",
                service_end_at="2027-10-01T00:00:00Z",
                authorization_reference="auth",
                source_hash="a"*64,source_locator="buyer://auth",
                verified=True,externally_authorized=True)

        charter2,snapshot2,ack2,agreement2=fixture(
            monthly_assurance_separately_accepted=False)
        with self.assertRaisesRegex(ValueError,"did not separately accept"):
            build_external_recurring_assurance_authorization(
                charter2,ack2,agreement2,
                service_start_at="2026-10-01T00:00:00Z",
                service_end_at="2027-10-01T00:00:00Z",
                authorization_reference="auth2",
                source_hash="b"*64,source_locator="buyer://auth2",
                verified=True,externally_authorized=True)

    def test_unverified_recurring_authorization_fails_closed(self):
        charter,snapshot,ack,agreement=fixture(
            monthly_assurance_separately_accepted=True)
        with self.assertRaisesRegex(ValueError,"externally verified"):
            build_external_recurring_assurance_authorization(
                charter,ack,agreement,
                service_start_at="2026-10-01T00:00:00Z",
                service_end_at="2027-10-01T00:00:00Z",
                authorization_reference="auth",
                source_hash="c"*64,source_locator="buyer://auth",
                verified=False,externally_authorized=True)


if __name__=="__main__":
    unittest.main()
