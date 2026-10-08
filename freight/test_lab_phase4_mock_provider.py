"""Isolated mock callback transactions; no bank, customer or hosted database access."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from freight.lab_phase4_mock_provider import MockCallback,MockProviderLedger


def event(state="SUBMITTED",ref="provider-1",time="2026-10-08T11:00:00Z",**changes):
    vals=dict(tenant="fictional-tenant",instruction="synthetic-payment",
              state=state,provider="MOCK-CARRIER",provider_reference=ref,
              amount_cents=1000,source_sha256="a"*64,actor_id="mock-provider-system",
              occurred_at=time)
    vals.update(changes)
    return MockCallback(**vals)


class MockProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger=MockProviderLedger(Path(self.tmp.name)/"mock-only.sqlite3")

    def test_duplicate_callbacks_are_atomic_under_concurrency(self):
        payload=event()
        with ThreadPoolExecutor(max_workers=10) as pool:
            outcomes=list(pool.map(lambda _:self.ledger.submit(payload,instruction_authorized=True),range(30)))
        self.assertEqual(sum(not x.replay for x in outcomes),1)
        self.assertEqual(len(set(x.event_id for x in outcomes)),1)
        self.assertEqual(len(self.ledger.verify(payload.tenant,payload.instruction)),1)

    def test_retry_after_full_settlement_returns_first_record(self):
        initial=self.ledger.submit(event(),instruction_authorized=True)
        self.ledger.submit(event("ACCEPTED","provider-2","2026-10-08T12:00:00Z"),instruction_authorized=True)
        self.ledger.submit(event("SETTLED","provider-3","2026-10-08T13:00:00Z"),instruction_authorized=True)
        self.ledger.submit(event("REVERSED","provider-4","2026-10-09T13:00:00Z"),instruction_authorized=True)
        retry=self.ledger.submit(event(),instruction_authorized=True)
        self.assertTrue(retry.replay)
        self.assertEqual(initial.event_id,retry.event_id)
        self.assertEqual(len(self.ledger.verify("fictional-tenant","synthetic-payment")),4)

    def test_provider_reference_conflict_rejected(self):
        self.ledger.submit(event(),instruction_authorized=True)
        for bad in [replace(event(),amount_cents=500),
                    replace(event(),source_sha256="b"*64),
                    replace(event(),actor_id="other-actor")]:
            with self.assertRaisesRegex(ValueError,"CONFLICTING_PROVIDER_REPLAY"):
                self.ledger.submit(bad,instruction_authorized=True)

    def test_different_tenant_same_reference_is_separate(self):
        a=self.ledger.submit(event(),instruction_authorized=True)
        b=self.ledger.submit(event(tenant="other-fictional-tenant"),instruction_authorized=True)
        self.assertNotEqual(a.event_id,b.event_id)
        self.assertEqual(len(self.ledger.verify("fictional-tenant","synthetic-payment")),1)
        self.assertEqual(len(self.ledger.verify("other-fictional-tenant","synthetic-payment")),1)

    def test_out_of_order_state_and_time_rejected(self):
        self.ledger.submit(event(),instruction_authorized=True)
        for incoming in [event("SETTLED","no-ack","2026-10-08T13:00:00Z"),
                         event("ACCEPTED","bad-time","2026-10-07T13:00:00Z")]:
            with self.assertRaises(ValueError):
                self.ledger.submit(incoming,instruction_authorized=True)

    def test_unknown_outcome_requires_manual_resolution(self):
        self.ledger.submit(event(),instruction_authorized=True)
        self.ledger.submit(event("OUTCOME_UNKNOWN","unknown","2026-10-08T12:00:00Z"),
                          instruction_authorized=True)
        with self.assertRaisesRegex(ValueError,"INVALID_PROVIDER_TRANSITION"):
            self.ledger.submit(event("SUBMITTED","resend","2026-10-08T13:00:00Z"),
                               instruction_authorized=True)

    def test_authorization_failure_is_closed(self):
        with self.assertRaisesRegex(ValueError,"BUYER_AUTHORIZATION_NOT_VERIFIED"):
            self.ledger.submit(event(),instruction_authorized=False)
        self.assertEqual(self.ledger.verify("fictional-tenant","synthetic-payment"),())

    def test_committed_reply_loss_simulation_replays_without_second_effect(self):
        payload=event()
        self.ledger.submit(payload,instruction_authorized=True)
        # Deliberately discard the first successful return, reopen file on retry.
        after_restart=MockProviderLedger(self.ledger.path)
        outcome=after_restart.submit(payload,instruction_authorized=True)
        self.assertTrue(outcome.replay)
        self.assertEqual(len(after_restart.verify(payload.tenant,payload.instruction)),1)

    def test_invalid_amount_and_utc_required(self):
        for bad in [replace(event(),amount_cents=True),
                    replace(event(),amount_cents=-1),
                    replace(event(),occurred_at="2026-10-08T11:00:00"),
                    replace(event(),source_sha256="invalid")]:
            with self.assertRaises(ValueError):
                self.ledger.submit(bad,instruction_authorized=True)


if __name__=="__main__":
    unittest.main()
