from __future__ import annotations

from dataclasses import replace
import unittest

from recoveryworks.pilot_charter import (
    build_recoveryworks_pilot_charter,
    pilot_charter_request_from_dict,
)
from recoveryworks.pilot_kickoff import (
    build_external_pilot_kickoff_authorization,
    build_pilot_kickoff_gate,
)
from recoveryworks.test_pilot_charter import packet, request_dict


def charter():
    return build_recoveryworks_pilot_charter(
        packet(), pilot_charter_request_from_dict(request_dict())
    )


class PilotKickoffTests(unittest.TestCase):
    def test_verified_external_authorization_opens_read_only_kickoff_only(self):
        c = charter()
        auth = build_external_pilot_kickoff_authorization(
            c,
            authorized_by="buyer-controller",
            authorized_at="2026-09-24T14:00:00Z",
            expires_at="2026-09-25T14:00:00Z",
            retention_until="2026-10-31T23:59:59Z",
            source_hash="1" * 64,
            source_locator="buyer://authorization/kickoff-1",
            verified=True,
        )
        gate = build_pilot_kickoff_gate(
            c, auth, checked_at="2026-09-24T14:05:00Z"
        )
        self.assertEqual(
            gate.as_dict()["state"], "PILOT_KICKOFF_AUTHORIZED_READ_ONLY"
        )
        self.assertTrue(gate.customer_data_processing_authorized)
        self.assertTrue(gate.kickoff_authorized)
        self.assertFalse(gate.external_action_authorized)
        self.assertFalse(gate.provider_mutation_authorized)
        self.assertFalse(gate.invoice_authorized)
        self.assertFalse(gate.payment_collection_authorized)

    def test_unverified_or_expired_authorization_fails_closed(self):
        c = charter()
        with self.assertRaisesRegex(ValueError, "must be verified"):
            build_external_pilot_kickoff_authorization(
                c,
                authorized_by="buyer-controller",
                authorized_at="2026-09-24T14:00:00Z",
                expires_at="2026-09-25T14:00:00Z",
                retention_until="2026-10-31T23:59:59Z",
                source_hash="1" * 64,
                source_locator="buyer://authorization/kickoff-1",
                verified=False,
            )
        auth = build_external_pilot_kickoff_authorization(
            c,
            authorized_by="buyer-controller",
            authorized_at="2026-09-24T14:00:00Z",
            expires_at="2026-09-24T15:00:00Z",
            retention_until="2026-10-31T23:59:59Z",
            source_hash="1" * 64,
            source_locator="buyer://authorization/kickoff-1",
            verified=True,
        )
        with self.assertRaisesRegex(ValueError, "expired"):
            build_pilot_kickoff_gate(
                c, auth, checked_at="2026-09-24T15:00:00Z"
            )

    def test_scope_drift_from_charter_fails_closed(self):
        c = charter()
        auth = build_external_pilot_kickoff_authorization(
            c,
            authorized_by="buyer-controller",
            authorized_at="2026-09-24T14:00:00Z",
            expires_at="2026-09-25T14:00:00Z",
            retention_until="2026-10-31T23:59:59Z",
            source_hash="1" * 64,
            source_locator="buyer://authorization/kickoff-1",
            verified=True,
        )
        object.__setattr__(auth, "billing_account_scope", ("other-account",))
        with self.assertRaisesRegex(ValueError, "billing-account scope mismatch"):
            build_pilot_kickoff_gate(
                c, auth, checked_at="2026-09-24T14:05:00Z"
            )


if __name__ == "__main__":
    unittest.main()
