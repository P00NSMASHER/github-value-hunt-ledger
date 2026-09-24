import math
import unittest

from production.control_plane import (
    WorkIdentity,
    WorkSpec,
    build_work_identity,
    canonical_json_text,
    validate_work_identity,
)


class GenericControlPlaneIdentityTests(unittest.TestCase):
    def spec(self, semantic=None, **overrides):
        values = {
            "namespace": "starblox",
            "kind": "build",
            "source_id": "STAR:demo-001",
            "semantic": semantic
            or {
                "target": "demo",
                "steps": ["compile", "validate"],
            },
        }
        values.update(overrides)
        return WorkSpec(**values)

    def test_mapping_order_does_not_change_identity(self):
        left = self.spec(
            {
                "target": "demo",
                "steps": ["compile", "validate"],
                "options": {"safe": True, "retries": 0},
            }
        )
        right = self.spec(
            {
                "options": {"retries": 0, "safe": True},
                "steps": ["compile", "validate"],
                "target": "demo",
            }
        )
        self.assertEqual(
            build_work_identity(left),
            build_work_identity(right),
        )

    def test_semantic_change_changes_full_revision_and_work_id(self):
        first = build_work_identity(
            self.spec({"target": "alpha"})
        )
        second = build_work_identity(
            self.spec({"target": "beta"})
        )
        self.assertNotEqual(
            first.revision_sha256,
            second.revision_sha256,
        )
        self.assertNotEqual(first.work_id, second.work_id)

    def test_namespace_kind_and_source_are_identity_bound(self):
        base = build_work_identity(self.spec())
        other_namespace = build_work_identity(
            self.spec(namespace="other-product")
        )
        other_kind = build_work_identity(
            self.spec(kind="evaluate")
        )
        other_source = build_work_identity(
            self.spec(source_id="STAR:demo-002")
        )
        self.assertNotEqual(base, other_namespace)
        self.assertNotEqual(base, other_kind)
        self.assertNotEqual(base, other_source)

    def test_identity_keeps_full_sha_and_short_display_id(self):
        identity = build_work_identity(self.spec())
        self.assertRegex(
            identity.revision_sha256,
            r"^[a-f0-9]{64}$",
        )
        prefix = "WORK:starblox:build:"
        self.assertTrue(identity.work_id.startswith(prefix))
        self.assertEqual(
            len(identity.work_id.removeprefix(prefix)),
            16,
        )
        validate_work_identity(identity)

    def test_work_spec_is_snapshot_not_live_mapping(self):
        semantic = {"target": "alpha", "nested": {"value": 1}}
        spec = self.spec(semantic)
        semantic["target"] = "mutated"
        semantic["nested"]["value"] = 2
        self.assertEqual(
            spec.semantic,
            {"nested": {"value": 1}, "target": "alpha"},
        )

        copy = spec.semantic
        copy["target"] = "local-mutation"
        self.assertEqual(spec.semantic["target"], "alpha")

    def test_nonfinite_and_non_json_native_values_fail_closed(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.spec({"value": value})
        with self.assertRaises(TypeError):
            self.spec({"value": {1, 2, 3}})
        with self.assertRaises(TypeError):
            self.spec({1: "non-string-key"})

    def test_canonical_json_preserves_unicode_without_ascii_escape(self):
        self.assertEqual(
            canonical_json_text({"label": "星"}),
            '{"label":"星"}',
        )

    def test_tampered_payload_fails_validation(self):
        good = build_work_identity(self.spec())
        tampered = WorkIdentity(
            work_id=good.work_id,
            revision_sha256=good.revision_sha256,
            identity_payload={
                **good.identity_payload,
                "semantic": {"target": "tampered"},
            },
        )
        with self.assertRaisesRegex(
            ValueError,
            "revision_sha256 does not match",
        ):
            validate_work_identity(tampered)

    def test_tampered_revision_fails_validation(self):
        good = build_work_identity(self.spec())
        tampered = WorkIdentity(
            work_id=good.work_id,
            revision_sha256="0" * 64,
            identity_payload=good.identity_payload,
        )
        with self.assertRaisesRegex(
            ValueError,
            "revision_sha256 does not match",
        ):
            validate_work_identity(tampered)

    def test_tampered_work_id_fails_validation(self):
        good = build_work_identity(self.spec())
        tampered = WorkIdentity(
            work_id="WORK:starblox:build:" + "0" * 16,
            revision_sha256=good.revision_sha256,
            identity_payload=good.identity_payload,
        )
        with self.assertRaisesRegex(
            ValueError,
            "work_id does not match",
        ):
            validate_work_identity(tampered)

    def test_invalid_tokens_and_schema_fail_closed(self):
        with self.assertRaises(ValueError):
            self.spec(namespace="StarBlox")
        with self.assertRaises(ValueError):
            self.spec(kind="bad kind")
        with self.assertRaises(ValueError):
            self.spec(source_id=" ")
        with self.assertRaises(ValueError):
            self.spec(schema_version=2)


if __name__ == "__main__":
    unittest.main()
