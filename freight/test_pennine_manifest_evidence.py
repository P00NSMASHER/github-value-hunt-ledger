"""Synthetic, offline provenance red controls for pinned Pennine source contracts.

No original invoice bytes, payment identifiers, or customer records are used.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch


class PennineDualManifestTests(unittest.TestCase):
    def test_mismatched_source_registries_stop_before_any_download(self):
        from freight.public_pennine_integration import SOURCES
        from freight.real_document_lab import benchmark_pennine

        original = dict(SOURCES)
        route, source_sha, rows = original["2026-04"]
        bad_manifests = {
            "source_hash": {**original, "2026-04": (route, "0" * 64, rows)},
            "source_route": {**original, "2026-04": ("different/277", source_sha, rows)},
            "source_count": {**original, "2026-04": (route, source_sha, rows + 1)},
            "month_omitted": {
                month: spec for month, spec in original.items()
                if month != "2026-04"
            },
        }
        for case, corrupted in bad_manifests.items():
            with self.subTest(case=case), patch.dict(
                "freight.public_pennine_integration.SOURCES", corrupted, clear=True,
            ), patch(
                "freight.real_document_lab.fetch_public",
                side_effect=AssertionError("FETCH_BEFORE_MANIFEST_VALIDATION"),
            ) as fetch:
                with self.assertRaisesRegex(
                    ValueError, "PUBLIC_PENNINE_SOURCE_MANIFEST_MISMATCH"
                ):
                    benchmark_pennine()
                fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
