from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.pilot_execution_lifecycle import (
    PilotExecutionJournal,
    PilotExecutionState,
)
from recoveryworks.pilot_kickoff import (
    build_external_pilot_kickoff_authorization,
    build_pilot_kickoff_gate,
)
from recoveryworks.pilot_charter import (
    build_recoveryworks_pilot_charter,
    pilot_charter_request_from_dict,
)
from recoveryworks.test_pilot_charter import packet, request_dict


def kickoff():
    charter = build_recoveryworks_pilot_charter(
        packet(), pilot_charter_request_from_dict(request_dict())
    )
    auth = build_external_pilot_kickoff_authorization(
        charter,
        authorized_by="buyer-controller",
        authorized_at="2026-09-24T14:00:00Z",
        expires_at="2026-09-25T14:00:00Z",
        retention_until="2026-10-31T23:59:59Z",
        source_hash="1"*64,
        source_locator="buyer://auth/kickoff",
        verified=True,
    )
    return build_pilot_kickoff_gate(
        charter, auth, checked_at="2026-09-24T14:05:00Z"
    )


class PilotExecutionLifecycleTests(unittest.TestCase):
    def test_full_internal_lifecycle_is_hash_chained(self):
        with tempfile.TemporaryDirectory() as d:
            journal = PilotExecutionJournal(Path(d)/"pilot-journal.json")
            gate = kickoff()
            states = (
                PilotExecutionState.KICKOFF_AUTHORIZED,
                PilotExecutionState.INTAKE_FROZEN,
                PilotExecutionState.DIAGNOSTIC_COMPLETE,
                PilotExecutionState.EVIDENCE_REVIEW_COMPLETE,
                PilotExecutionState.BUYER_REVIEW_READY,
                PilotExecutionState.CLOSEOUT_READY,
                PilotExecutionState.CLOSED,
            )
            for i,state in enumerate(states, start=1):
                journal.append(
                    gate,
                    state=state,
                    actor_id=f"actor-{i}",
                    occurred_at=f"2026-09-24T14:{i+5:02d}:00Z",
                    evidence_hashes=(f"{i:x}"*64,) if i < 16 else ("f"*64,),
                    note=f"{state.value} recorded",
                )
            events=journal.events()
            self.assertEqual(len(events),7)
            self.assertIs(events[-1].state,PilotExecutionState.CLOSED)

    def test_invalid_transition_and_tamper_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"pilot-journal.json"
            journal=PilotExecutionJournal(path)
            gate=kickoff()
            journal.append(
                gate,state=PilotExecutionState.KICKOFF_AUTHORIZED,
                actor_id="operator",occurred_at="2026-09-24T14:06:00Z",
                evidence_hashes=("a"*64,),note="kickoff")
            with self.assertRaisesRegex(ValueError,"invalid pilot transition"):
                journal.append(
                    gate,state=PilotExecutionState.DIAGNOSTIC_COMPLETE,
                    actor_id="operator",occurred_at="2026-09-24T14:07:00Z",
                    evidence_hashes=("b"*64,),note="skip")
            raw=path.read_text(encoding="utf-8").replace("kickoff","tampered")
            path.write_text(raw,encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"hash|state|malformed"):
                journal.events()


if __name__=="__main__":
    unittest.main()
