import hashlib
import unittest

from ai_business_os.command_center_ui import (
    access_code_matches,
    csrf_matches,
    csrf_token,
    issue_session,
    render_dashboard,
    render_login,
    validate_session,
)


class CommandCenterUISecurityTests(unittest.TestCase):
    def test_access_code_is_compared_by_hash(self):
        expected = hashlib.sha256(b"correct horse battery staple").hexdigest()
        self.assertTrue(access_code_matches("correct horse battery staple", expected))
        self.assertFalse(access_code_matches("wrong", expected))

    def test_session_is_signed_principal_bound_and_expires(self):
        token = issue_session("session-secret", "human:ceo-ui", now=1000, ttl_seconds=300)
        self.assertIsNotNone(
            validate_session(token, "session-secret", "human:ceo-ui", now=1100)
        )
        self.assertIsNone(
            validate_session(token, "wrong-secret", "human:ceo-ui", now=1100)
        )
        self.assertIsNone(
            validate_session(token, "session-secret", "human:other", now=1100)
        )
        self.assertIsNone(
            validate_session(token, "session-secret", "human:ceo-ui", now=1400)
        )

    def test_csrf_is_bound_to_session(self):
        token = issue_session("session-secret", "human:ceo-ui", now=1000)
        csrf = csrf_token(token, "session-secret")
        self.assertTrue(csrf_matches(token, "session-secret", csrf))
        self.assertFalse(csrf_matches(token + "x", "session-secret", csrf))

    def test_login_does_not_embed_production_tokens(self):
        page = render_login()
        self.assertIn("CEO Command Center", page)
        self.assertNotIn("AIBOS_RUNTIME_TOKEN", page)
        self.assertNotIn("AIBOS_OPERATOR_TOKEN", page)

    def test_dashboard_is_server_rendered_and_approval_queue_is_read_only(self):
        token = issue_session("session-secret", "human:ceo-ui", now=1000)
        page = render_dashboard(
            {
                "runtime": {
                    "ok": True,
                    "schema_fingerprint": "a" * 64,
                    "worker": {"running": True, "ticks": 4, "claims": 1, "submitted": 1, "failed": 0},
                },
                "command_center": {
                    "schema_fingerprint": "a" * 64,
                    "businesses": [{"slug": "starblox", "name": "StarBlox"}],
                    "pending_approvals": [
                        {
                            "request_key": "approval-1",
                            "title": "Review external send",
                            "action_key": "gmail.send",
                            "predicted_risk": "medium",
                            "expected_money_cents": 0,
                            "expires_at": "2026-10-01T00:00:00Z",
                        }
                    ],
                    "planning": {"summary": {"verify_items": 3}},
                },
                "planning_inputs": {
                    "agents": [{"agent_id": "agent-chief", "display_name": "Chief", "role_key": "CHIEF_OF_STAFF", "status": "ACTIVE"}],
                    "initiatives": [],
                    "data_gaps": [],
                    "open_goals": [],
                },
                "worker_status": {"heartbeats": [], "leases": [], "recent_runs": []},
            },
            principal="human:ceo-ui",
            session_token=token,
            session_secret="session-secret",
        )
        self.assertIn("StarBlox", page)
        self.assertIn("Review external send", page)
        self.assertIn("Read-only in Step 4", page)
        self.assertNotIn("/approval/decide", page)
        self.assertNotIn("AIBOS_RUNTIME_TOKEN", page)


if __name__ == "__main__":
    unittest.main()
