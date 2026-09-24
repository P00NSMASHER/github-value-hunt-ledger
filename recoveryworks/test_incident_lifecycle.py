from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.incident_lifecycle import (
    IncidentLifecycleJournal,
    IncidentLifecycleState,
    build_incident_closure,
    build_post_incident_review,
)
from recoveryworks.incident_rollback import (
    ValidatedRollbackReceipt,
)
from recoveryworks.test_incident_rollback import IncidentRollbackTests


class IncidentLifecycleTests(unittest.TestCase):
    def fixture(self, root: Path):
        helper = IncidentRollbackTests()
        current, target, rollback = helper.releases(root)
        incident = __import__(
            "recoveryworks.incident_rollback",
            fromlist=["assess_post_deployment_incident"],
        ).assess_post_deployment_incident(
            current,
            helper.snapshot(current, healthy=False),
            detected_at="2026-09-24T14:01:00Z",
        )
        class Receipt:
            proof_hash = "a" * 64
        validated = ValidatedRollbackReceipt(
            receipt=Receipt(),
            post_rollback_snapshot_proof_hash="b" * 64,
        )
        return incident, validated

    def test_hash_chained_lifecycle_closure_and_review(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            incident, validated = self.fixture(root)
            journal = IncidentLifecycleJournal(root / "private" / "incident.json")
            states = (
                IncidentLifecycleState.DETECTED,
                IncidentLifecycleState.ACKNOWLEDGED,
                IncidentLifecycleState.ESCALATED,
                IncidentLifecycleState.ROLLBACK_APPROVED,
                IncidentLifecycleState.ROLLBACK_HANDOFF,
                IncidentLifecycleState.ROLLBACK_VERIFIED,
                IncidentLifecycleState.RECOVERY_CONFIRMED,
                IncidentLifecycleState.CLOSED,
                IncidentLifecycleState.REVIEWED,
            )
            for index, state in enumerate(states, start=1):
                journal.append(
                    incident,
                    state=state,
                    actor_id=f"actor-{index}",
                    occurred_at=f"2026-09-24T14:{index+1:02d}:00Z",
                    note=f"{state.value} recorded",
                    evidence_hashes=(validated.proof_hash,)
                    if state in {
                        IncidentLifecycleState.ROLLBACK_VERIFIED,
                        IncidentLifecycleState.RECOVERY_CONFIRMED,
                    }
                    else (),
                )
            events = journal.events()
            self.assertEqual(len(events), 9)
            self.assertEqual(events[-1].state, IncidentLifecycleState.REVIEWED)

            closure = build_incident_closure(
                incident,
                validated,
                recovered_environment_snapshot_proof_hash="c" * 64,
                closed_by="incident-commander",
                closed_at="2026-09-24T14:10:00Z",
                closure_reason="Known-good release restored and verified.",
            )
            review = build_post_incident_review(
                incident,
                closure,
                reviewer_id="post-incident-reviewer",
                reviewed_at="2026-09-24T15:00:00Z",
                root_cause="Deployment regression.",
                contributing_factors=("Insufficient canary coverage.",),
                corrective_actions=("Expand release smoke coverage.",),
                preventive_actions=("Require canary evidence before production.",),
                followup_owner_id="platform-owner",
                followup_due_at="2026-10-01T12:00:00Z",
            )
            self.assertEqual(
                review.as_dict()["state"], "POST_INCIDENT_REVIEW_RECORDED"
            )
            self.assertFalse(review.actions_executed)

    def test_invalid_transition_and_journal_tamper_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            incident, _ = self.fixture(root)
            journal = IncidentLifecycleJournal(root / "private" / "incident.json")
            journal.append(
                incident,
                state=IncidentLifecycleState.DETECTED,
                actor_id="detector",
                occurred_at="2026-09-24T14:02:00Z",
                note="detected",
            )
            with self.assertRaisesRegex(ValueError, "invalid incident transition"):
                journal.append(
                    incident,
                    state=IncidentLifecycleState.CLOSED,
                    actor_id="actor",
                    occurred_at="2026-09-24T14:03:00Z",
                    note="invalid close",
                )
            path = root / "private" / "incident.json"
            raw = path.read_text(encoding="utf-8").replace("detected", "tampered")
            path.write_text(raw, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash|state"):
                journal.events()


if __name__ == "__main__":
    unittest.main()
