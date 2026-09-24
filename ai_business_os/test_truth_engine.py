import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_business_os.governance import GovernanceControlPlane
from ai_business_os.persistent_agents.runtime import AgentRuntime
from ai_business_os.truth_engine import TruthEngine, TruthEngineError


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class TruthEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = AgentRuntime(Path(self.tmp.name) / "runtime.sqlite3")
        self.gov = GovernanceControlPlane(self.runtime)
        self.engine = TruthEngine(self.runtime, self.gov)
        self.creator = self.runtime.register_agent("claim-creator")
        self.evaluator = self.runtime.register_agent("truth-evaluator")
        self.acquirer = self.runtime.register_agent("evidence-acquirer")

        self.gov.set_agent_policy(
            self.acquirer,
            allowed_classes=["READ", "EXTERNAL_WRITE"],
            allowed_action_keys=["bank.fetch", "contract.fetch"],
            human_approval_classes=["EXTERNAL_WRITE"],
            updated_by_principal="owner",
            principal_kind="HUMAN",
            evidence={"policy": "truth-acquisition"},
            max_cost_units_per_window=10.0,
        )

        self.engine.register_claim(
            claim_id="claim-1",
            subject="Freight invoice 100",
            statement="Invoice 100 contains a recoverable overcharge",
            created_by_agent_id=self.creator,
            obligations=[
                {
                    "key": "contract_rate",
                    "description": "Controlling contract establishes expected rate",
                    "allowed_authorities": ["PRIMARY_CONTRACT", "VERIFIED_LEDGER"],
                    "max_age_seconds": 1000,
                },
                {
                    "key": "payment",
                    "description": "Payment evidence proves money was actually paid",
                    "allowed_authorities": ["BANK"],
                },
            ],
        )

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def add_contract(
        self,
        evidence_id="contract-1",
        *,
        stance="SUPPORTS",
        authority="PRIMARY_CONTRACT",
        group="contract",
        observed_at=100.0,
        admissible=True,
        valid_until=None,
    ):
        return self.engine.add_evidence(
            "claim-1",
            evidence_id=evidence_id,
            obligation_key="contract_rate",
            stance=stance,
            authority=authority,
            source_id=evidence_id,
            independence_group=group,
            observed_at=observed_at,
            source_ref=f"source/{evidence_id}",
            source_sha256=digest(evidence_id),
            admissible=admissible,
            valid_until=valid_until,
            payload={"source": evidence_id},
            created_by_agent_id=self.creator,
        )

    def add_payment(self, evidence_id="bank-1", *, stance="SUPPORTS", group="bank"):
        return self.engine.add_evidence(
            "claim-1",
            evidence_id=evidence_id,
            obligation_key="payment",
            stance=stance,
            authority="BANK",
            source_id=evidence_id,
            independence_group=group,
            observed_at=100.0,
            source_ref=f"bank/{evidence_id}",
            source_sha256=digest(evidence_id),
            payload={"source": evidence_id},
            created_by_agent_id=self.creator,
        )

    def evaluate(self, at=200.0):
        return self.engine.evaluate(
            "claim-1",
            evaluator_agent_id=self.evaluator,
            evaluated_at=at,
        )

    def test_no_evidence_is_unknown_not_false(self):
        receipt = self.evaluate()
        self.assertEqual("UNKNOWN", receipt["verdict"])
        self.assertEqual(
            {"MISSING"},
            {f["status"] for f in receipt["findings"]},
        )

    def test_required_authoritative_support_proves_claim(self):
        self.add_contract()
        self.add_payment()
        receipt = self.evaluate()
        self.assertEqual("PROVEN", receipt["verdict"])
        self.assertTrue(all(f["status"] == "SATISFIED" for f in receipt["findings"]))

    def test_stale_evidence_is_visible_and_not_proof(self):
        self.add_contract(observed_at=0.0)
        self.add_payment()
        receipt = self.evaluate(at=2000.0)
        finding = next(f for f in receipt["findings"] if f["key"] == "contract_rate")
        self.assertEqual("STALE", finding["status"])
        self.assertEqual(["contract-1"], finding["stale_evidence_ids"])
        self.assertEqual("NOT_PROVEN", receipt["verdict"])

    def test_wrong_authority_is_inadmissible(self):
        self.add_contract(authority="MODEL")
        self.add_payment()
        receipt = self.evaluate()
        finding = next(f for f in receipt["findings"] if f["key"] == "contract_rate")
        self.assertEqual("INADMISSIBLE", finding["status"])
        self.assertEqual(["contract-1"], finding["inadmissible_evidence_ids"])
        self.assertEqual("NOT_PROVEN", receipt["verdict"])

    def test_future_observation_is_inadmissible(self):
        self.add_contract(observed_at=500.0)
        self.add_payment()
        receipt = self.evaluate(at=200.0)
        finding = next(f for f in receipt["findings"] if f["key"] == "contract_rate")
        self.assertEqual("INADMISSIBLE", finding["status"])
        self.assertEqual("NOT_PROVEN", receipt["verdict"])

    def test_contradiction_is_preserved_and_contested(self):
        self.add_contract("contract-support", group="contract")
        self.add_contract(
            "contract-contradiction",
            stance="CONTRADICTS",
            group="ledger",
            authority="VERIFIED_LEDGER",
        )
        self.add_payment()
        receipt = self.evaluate()
        finding = next(f for f in receipt["findings"] if f["key"] == "contract_rate")
        self.assertEqual("CONFLICTED", finding["status"])
        self.assertEqual("CONTESTED", receipt["verdict"])
        self.assertEqual(["contract-support"], finding["supporting_evidence_ids"])
        self.assertEqual(
            ["contract-contradiction"],
            finding["contradicting_evidence_ids"],
        )

    def test_insufficient_independence_fails_closed(self):
        self.engine.register_claim(
            claim_id="claim-independence",
            subject="Customer eligibility",
            statement="Two independent sources confirm eligibility",
            created_by_agent_id=self.creator,
            obligations=[
                {
                    "key": "eligibility",
                    "description": "Need independent corroboration",
                    "allowed_authorities": ["SYSTEM_A", "SYSTEM_B"],
                    "min_supporting_sources": 2,
                    "min_independent_groups": 2,
                }
            ],
        )
        for idx in [1, 2]:
            self.engine.add_evidence(
                "claim-independence",
                evidence_id=f"e{idx}",
                obligation_key="eligibility",
                stance="SUPPORTS",
                authority="SYSTEM_A",
                source_id=f"s{idx}",
                independence_group="same-source-family",
                observed_at=100,
                source_ref=f"ref/{idx}",
                source_sha256=digest(f"e{idx}"),
                created_by_agent_id=self.creator,
            )
        receipt = self.engine.evaluate(
            "claim-independence",
            evaluator_agent_id=self.evaluator,
            evaluated_at=200,
        )
        self.assertEqual("NOT_PROVEN", receipt["verdict"])
        self.assertEqual(
            "INSUFFICIENT_INDEPENDENCE",
            receipt["findings"][0]["status"],
        )

    def test_duplicate_evidence_is_rejected(self):
        self.add_contract("same")
        with self.assertRaises(TruthEngineError):
            self.add_contract("same")

    def test_bad_source_digest_fails_closed(self):
        with self.assertRaises(TruthEngineError):
            self.engine.add_evidence(
                "claim-1",
                evidence_id="bad",
                obligation_key="contract_rate",
                stance="SUPPORTS",
                authority="PRIMARY_CONTRACT",
                source_id="bad",
                independence_group="x",
                observed_at=100,
                source_ref="bad",
                source_sha256="not-a-digest",
                created_by_agent_id=self.creator,
            )

    def test_receipt_identity_changes_when_evidence_changes(self):
        first = self.evaluate()
        self.add_contract()
        second = self.evaluate()
        self.assertNotEqual(first["evidence_set_hash"], second["evidence_set_hash"])
        self.assertNotEqual(first["receipt_hash"], second["receipt_hash"])

    def test_next_best_evidence_ranks_actual_proof_gain(self):
        self.add_contract()
        receipt = self.evaluate()
        self.assertEqual("NOT_PROVEN", receipt["verdict"])

        self.engine.register_evidence_action(
            "claim-1",
            action_id="get-bank-proof",
            obligation_key="payment",
            description="Obtain bank settlement record",
            authority="BANK",
            independence_group="bank",
            action_key="bank.fetch",
            action_class="READ",
            action_parameters={"account": "authorized", "transaction": "invoice-100"},
            created_by_agent_id=self.creator,
            cost_units=2.0,
        )
        self.engine.register_evidence_action(
            "claim-1",
            action_id="wrong-authority",
            obligation_key="payment",
            description="Ask an unverified model",
            authority="MODEL",
            independence_group="model",
            action_key="bank.fetch",
            action_class="READ",
            action_parameters={"bad": True},
            created_by_agent_id=self.creator,
        )
        ranked = self.engine.rank_next_evidence(
            "claim-1",
            receipt_id=receipt["id"],
        )
        self.assertEqual(["get-bank-proof"], [item.action_id for item in ranked])
        self.assertEqual("PROVEN", ranked[0].counterfactual_verdict)
        self.assertGreater(ranked[0].potential_decision_gain, 0)

    def test_duplicate_independence_group_is_not_recommended(self):
        self.engine.register_claim(
            claim_id="claim-2",
            subject="Thing",
            statement="Two independent records support thing",
            created_by_agent_id=self.creator,
            obligations=[
                {
                    "key": "two_sources",
                    "description": "Need two independent sources",
                    "allowed_authorities": ["A", "B"],
                    "min_supporting_sources": 2,
                    "min_independent_groups": 2,
                }
            ],
        )
        self.engine.add_evidence(
            "claim-2",
            evidence_id="existing",
            obligation_key="two_sources",
            stance="SUPPORTS",
            authority="A",
            source_id="existing",
            independence_group="same",
            observed_at=100,
            source_ref="a/1",
            source_sha256=digest("existing"),
            created_by_agent_id=self.creator,
        )
        receipt = self.engine.evaluate(
            "claim-2",
            evaluator_agent_id=self.evaluator,
            evaluated_at=200,
        )
        self.engine.register_evidence_action(
            "claim-2",
            action_id="duplicate",
            obligation_key="two_sources",
            description="Get another source from same independence group",
            authority="A",
            independence_group="same",
            action_key="contract.fetch",
            action_class="READ",
            action_parameters={"source": "same"},
            created_by_agent_id=self.creator,
        )
        self.engine.register_evidence_action(
            "claim-2",
            action_id="independent",
            obligation_key="two_sources",
            description="Get independent source",
            authority="B",
            independence_group="independent",
            action_key="contract.fetch",
            action_class="READ",
            action_parameters={"source": "independent"},
            created_by_agent_id=self.creator,
        )
        ranked = self.engine.rank_next_evidence("claim-2", receipt_id=receipt["id"])
        self.assertEqual(["independent"], [item.action_id for item in ranked])

    def test_old_receipt_cannot_authorize_after_evidence_changes(self):
        self.add_contract()
        receipt = self.evaluate()
        self.engine.register_evidence_action(
            "claim-1",
            action_id="get-bank-proof",
            obligation_key="payment",
            description="Obtain bank settlement record",
            authority="BANK",
            independence_group="bank",
            action_key="bank.fetch",
            action_class="READ",
            action_parameters={"transaction": "invoice-100"},
            created_by_agent_id=self.creator,
        )
        self.add_payment()
        with self.assertRaises(TruthEngineError):
            self.engine.rank_next_evidence("claim-1", receipt_id=receipt["id"])

    def test_counterfactual_planning_never_persists_fake_evidence(self):
        self.add_contract()
        receipt = self.evaluate()
        self.engine.register_evidence_action(
            "claim-1",
            action_id="get-bank-proof",
            obligation_key="payment",
            description="Obtain bank settlement record",
            authority="BANK",
            independence_group="bank",
            action_key="bank.fetch",
            action_class="READ",
            action_parameters={"transaction": "invoice-100"},
            created_by_agent_id=self.creator,
        )
        before = self.runtime.conn.execute(
            "SELECT COUNT(*) AS n FROM truth_evidence WHERE claim_id='claim-1'"
        ).fetchone()["n"]
        self.engine.rank_next_evidence("claim-1", receipt_id=receipt["id"])
        after = self.runtime.conn.execute(
            "SELECT COUNT(*) AS n FROM truth_evidence WHERE claim_id='claim-1'"
        ).fetchone()["n"]
        self.assertEqual(before, after)

    def test_governed_evidence_acquisition_requires_step6_authorization(self):
        self.add_contract()
        receipt = self.evaluate()
        self.engine.register_evidence_action(
            "claim-1",
            action_id="get-bank-proof",
            obligation_key="payment",
            description="Obtain bank settlement record",
            authority="BANK",
            independence_group="bank",
            action_key="bank.fetch",
            action_class="READ",
            action_parameters={"transaction": "invoice-100"},
            created_by_agent_id=self.creator,
            cost_units=2.0,
        )
        request = self.engine.request_evidence_acquisition(
            "claim-1",
            receipt_id=receipt["id"],
            evidence_action_id="get-bank-proof",
            actor_agent_id=self.acquirer,
        )
        self.assertEqual("ALLOW", request["governance"]["decision"])
        self.assertEqual(len(request["governance"]["receipt_hash"]), 64)

    def test_external_evidence_acquisition_can_require_human_approval(self):
        self.add_contract()
        receipt = self.evaluate()
        self.engine.register_evidence_action(
            "claim-1",
            action_id="request-payment-proof",
            obligation_key="payment",
            description="Request externally held payment proof",
            authority="BANK",
            independence_group="external-bank",
            action_key="bank.fetch",
            action_class="EXTERNAL_WRITE",
            action_parameters={"request": "payment-proof"},
            created_by_agent_id=self.creator,
        )
        request = self.engine.request_evidence_acquisition(
            "claim-1",
            receipt_id=receipt["id"],
            evidence_action_id="request-payment-proof",
            actor_agent_id=self.acquirer,
        )
        self.assertEqual("REQUIRE_APPROVAL", request["governance"]["decision"])


if __name__ == "__main__":
    unittest.main()
