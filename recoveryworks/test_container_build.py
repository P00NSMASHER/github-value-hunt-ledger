from __future__ import annotations

from pathlib import Path
import re
import unittest

from recoveryworks.container_build import build_container_build_manifest


class ContainerBuildProvenanceTests(unittest.TestCase):
    def test_production_dockerfile_and_empty_lock_are_frozen(self):
        manifest = build_container_build_manifest(
            source_commit="a" * 40,
            dockerfile_path="recoveryworks/deploy/Dockerfile.production",
            dependency_lock_path="recoveryworks/requirements.production.lock",
        )
        self.assertEqual(manifest.runtime_dependency_count, 0)
        self.assertEqual(
            manifest.runtime_source_roots,
            ("recoveryworks", "freight"),
        )
        self.assertEqual(manifest.third_party_runtime_dependencies, ())
        self.assertIn("@sha256:", manifest.base_image_ref)
        self.assertEqual(len(manifest.proof_hash), 64)

    def test_dockerfile_uses_nonroot_entrypoint_and_digest_base(self):
        text = Path("recoveryworks/deploy/Dockerfile.production").read_text(
            encoding="utf-8"
        )
        first = text.splitlines()[0]
        self.assertRegex(first, r"^FROM .+@sha256:[0-9a-f]{64}$")
        self.assertIn("USER 65532:65532", text)
        self.assertIn("COPY freight /app/freight", text)
        self.assertIn(
            "python -m compileall -q /app/recoveryworks /app/freight",
            text,
        )
        self.assertIn("COPY freight /app/freight", text)
        self.assertIn(
            'ENTRYPOINT ["python", "-m", "recoveryworks.pilot_runner"]',
            text,
        )
        self.assertNotIn(":latest", text)


if __name__ == "__main__":
    unittest.main()
