import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "ai_business_os" / "runtime_service.py"
UI = ROOT / "ai_business_os" / "command_center_ui.py"


class CEOCommandCenterUIRouteContractTests(unittest.TestCase):
    def test_runtime_requires_hashed_access_code_and_signed_session(self):
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn('AIBOS_UI_ACCESS_SHA256', source)
        self.assertIn('AIBOS_UI_SESSION_SECRET', source)
        self.assertIn('validate_session(', source)
        self.assertNotIn('AIBOS_UI_ACCESS_CODE', source)

    def test_browser_never_receives_operator_or_runtime_token(self):
        ui = UI.read_text(encoding="utf-8")
        self.assertNotIn('AIBOS_RUNTIME_TOKEN', ui)
        self.assertNotIn('AIBOS_OPERATOR_TOKEN', ui)
        self.assertIn('HttpOnly; Secure; SameSite=Strict', ui)

    def test_ui_is_server_rendered_with_strict_csp(self):
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("script-src 'none'", source)
        self.assertIn('gateway.call("worker_status")', source)
        self.assertIn('path == "/ui/objective/propose"', source)
        self.assertIn('path == "/ui/objective/activate"', source)

    def test_step4_ui_does_not_decide_approvals(self):
        source = RUNTIME.read_text(encoding="utf-8")
        ui_block = source.split('if path.startswith("/ui/"):', 1)[1].split(
            'if not self._authorized():', 1
        )[0]
        self.assertNotIn('/ui/approval/decide', ui_block)
        ui = UI.read_text(encoding="utf-8")
        self.assertIn("Read-only in Step 4", ui)
        self.assertNotIn("/approval/decide", ui)


if __name__ == "__main__":
    unittest.main()
