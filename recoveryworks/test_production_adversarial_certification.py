from __future__ import annotations

import unittest

from recoveryworks.production_adversarial_certification import (
    AdversarialCertificationState,
    AdversarialVector,
    run_commercial_adversarial_certification,
)
from recoveryworks.test_commercial_operational_invariants import full_chain


class ProductionAdversarialCertificationTests(unittest.TestCase):
    def test_seeded_property_matrix_covers_all_attack_vectors(self):
        result = run_commercial_adversarial_certification(
            full_chain,
            seed=41001,
            iterations_per_vector=6,
        )
        self.assertIs(result.state, AdversarialCertificationState.PASS)
        self.assertEqual(result.total_cases, len(AdversarialVector) * 6)
        self.assertEqual(result.false_negative_count, 0)
        self.assertEqual(
            set(result.vector_counts),
            {vector.value for vector in AdversarialVector},
        )
        self.assertTrue(all(count == 6 for count in result.vector_counts.values()))
        self.assertFalse(result.external_actions_performed)
        self.assertFalse(result.automatic_repair_performed)

    def test_same_seed_produces_same_certification_proof(self):
        first = run_commercial_adversarial_certification(
            full_chain,
            seed=9917,
            iterations_per_vector=2,
        )
        second = run_commercial_adversarial_certification(
            full_chain,
            seed=9917,
            iterations_per_vector=2,
        )
        self.assertEqual(first.proof_hash, second.proof_hash)
        self.assertEqual(
            [case.mutation for case in first.cases],
            [case.mutation for case in second.cases],
        )

    def test_broken_baseline_is_not_certified(self):
        def broken_factory():
            chain = full_chain()
            object.__setattr__(
                chain["issued_invoice"],
                "buyer_id",
                "wrong-baseline-buyer",
            )
            return chain

        with self.assertRaisesRegex(ValueError, "baseline chain must pass"):
            run_commercial_adversarial_certification(
                broken_factory,
                seed=5,
                iterations_per_vector=1,
            )


if __name__ == "__main__":
    unittest.main()
