import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "supabase" / "functions" / "ai-business-os-runtime-gateway" / "index.ts"


class RuntimeGatewayWorkerContractTests(unittest.TestCase):
    def test_worker_claim_uses_typed_json_parameter(self):
        source = GATEWAY.read_text(encoding="utf-8")
        self.assertIn("sql.json(goalTypes)", source)
        self.assertNotIn("JSON.stringify(goalTypes)}::jsonb", source)

    def test_worker_gateway_remains_named_operation_only(self):
        source = GATEWAY.read_text(encoding="utf-8")
        for action in ("worker_claim", "worker_heartbeat", "worker_submit", "worker_fail"):
            self.assertIn(f'case "{action}"', source)
        self.assertNotIn("arbitrary_sql", source.lower())


if __name__ == "__main__":
    unittest.main()
