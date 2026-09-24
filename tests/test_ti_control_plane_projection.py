import copy
import unittest

from production.control_plane import (
    ProjectionContract,
    assignment_projection_errors,
    project_assignment,
    projection_sha256,
    validate_assignment_projection,
)


class GenericProjectionContractTests(unittest.TestCase):
    def contract(self):
        return ProjectionContract(
            name="starblox-block-assignment",
            protected_fields=(
                "work_id",
                "revision_sha256",
                "kind",
                "action",
                "inputs",
                "instructions",
                "tags",
            ),
            normalized_list_fields=(
                "inputs",
                "tags",
            ),
            required_candidate_fields=(
                "work_id",
                "revision_sha256",
                "kind",
                "action",
                "instructions",
            ),
        )

    def candidate(self):
        return {
            "work_id": "WORK:starblox:build:0123456789abcdef",
            "revision_sha256": "a" * 64,
            "kind": "build",
            "action": "execute",
            "inputs": None,
            "instructions": {
                "target": "demo",
                "steps": ["compile", "validate"],
            },
            "tags": ["demo"],
            "score": 91.5,
        }

    def test_projection_preserves_contract_and_adds_metadata(self):
        candidate = self.candidate()
        assignment = project_assignment(
            candidate,
            {
                "assignment_id": "ASSIGN:demo:01",
                "slot_id": "SLOT-01",
                "worker_id": "worker-7",
            },
            self.contract(),
        )
        self.assertEqual(assignment["work_id"], candidate["work_id"])
        self.assertEqual(assignment["inputs"], [])
        self.assertEqual(
            assignment["instructions"],
            candidate["instructions"],
        )
        self.assertEqual(assignment["slot_id"], "SLOT-01")
        self.assertRegex(
            assignment["projection_sha256"],
            r"^[a-f0-9]{64}$",
        )
        validate_assignment_projection(
            candidate,
            assignment,
            self.contract(),
        )

    def test_assignment_metadata_cannot_override_protected_state(self):
        for field in ("work_id", "instructions", "projection_sha256"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                    ValueError,
                    "cannot override protected fields",
                ):
                    project_assignment(
                        self.candidate(),
                        {field: "tampered"},
                        self.contract(),
                    )

    def test_nested_semantic_drift_is_detected(self):
        candidate = self.candidate()
        assignment = project_assignment(
            candidate,
            {"assignment_id": "ASSIGN:demo:01"},
            self.contract(),
        )
        assignment["instructions"]["target"] = "tampered"
        errors = assignment_projection_errors(
            candidate,
            assignment,
            self.contract(),
        )
        self.assertIn(
            "protected_field_drift:instructions",
            errors,
        )
        with self.assertRaisesRegex(
            ValueError,
            "protected_field_drift:instructions",
        ):
            validate_assignment_projection(
                candidate,
                assignment,
                self.contract(),
            )

    def test_projection_hash_detects_contract_or_candidate_drift(self):
        candidate = self.candidate()
        contract = self.contract()
        assignment = project_assignment(
            candidate,
            {"assignment_id": "ASSIGN:demo:01"},
            contract,
        )

        changed_candidate = copy.deepcopy(candidate)
        changed_candidate["action"] = "review"
        self.assertIn(
            "projection_hash_mismatch",
            assignment_projection_errors(
                changed_candidate,
                assignment,
                contract,
            ),
        )

        changed_contract = ProjectionContract(
            name=contract.name,
            protected_fields=contract.protected_fields + ("score",),
            normalized_list_fields=contract.normalized_list_fields,
            required_candidate_fields=contract.required_candidate_fields,
        )
        self.assertNotEqual(
            projection_sha256(candidate, contract),
            projection_sha256(candidate, changed_contract),
        )

    def test_missing_required_candidate_field_fails_closed(self):
        candidate = self.candidate()
        del candidate["work_id"]
        with self.assertRaisesRegex(
            ValueError,
            "missing required protected fields: work_id",
        ):
            project_assignment(
                candidate,
                {"assignment_id": "ASSIGN:demo:01"},
                self.contract(),
            )

    def test_list_normalization_is_explicit_and_typed(self):
        candidate = self.candidate()
        assignment = project_assignment(
            candidate,
            {"assignment_id": "ASSIGN:demo:01"},
            self.contract(),
        )
        self.assertEqual(assignment["inputs"], [])

        assignment["inputs"] = None
        validate_assignment_projection(
            candidate,
            assignment,
            self.contract(),
        )

        assignment["inputs"] = "not-a-list"
        self.assertIn(
            "protected_field_invalid:inputs",
            assignment_projection_errors(
                candidate,
                assignment,
                self.contract(),
            ),
        )

    def test_candidate_mutation_after_projection_is_detected(self):
        candidate = self.candidate()
        assignment = project_assignment(
            candidate,
            {"assignment_id": "ASSIGN:demo:01"},
            self.contract(),
        )
        candidate["tags"].append("new-tag")
        with self.assertRaisesRegex(
            ValueError,
            "protected_field_drift:tags",
        ):
            validate_assignment_projection(
                candidate,
                assignment,
                self.contract(),
            )

    def test_invalid_contract_definitions_fail_closed(self):
        with self.assertRaisesRegex(
            ValueError,
            "protected_fields must not be empty",
        ):
            ProjectionContract(
                name="x",
                protected_fields=(),
            )
        with self.assertRaisesRegex(
            ValueError,
            "normalized_list_fields must be protected fields",
        ):
            ProjectionContract(
                name="x",
                protected_fields=("work_id",),
                normalized_list_fields=("inputs",),
            )
        with self.assertRaisesRegex(
            ValueError,
            "required_candidate_fields must be protected fields",
        ):
            ProjectionContract(
                name="x",
                protected_fields=("work_id",),
                required_candidate_fields=("kind",),
            )


if __name__ == "__main__":
    unittest.main()
