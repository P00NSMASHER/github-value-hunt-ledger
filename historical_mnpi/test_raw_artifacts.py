import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from historical_mnpi.raw_artifacts import (
    ArtifactImmutability,
    LocalContentAddressedArtifactStore,
    RawArtifactManifest,
    RawArtifactRecord,
    SourceArtifactRef,
    SourceLocatorKind,
    freeze_raw_artifact_manifest,
    verify_raw_artifact_manifest,
)
from historical_mnpi.source_registry import (
    SourceAdmissibility,
    SourceRecord,
    SourceRegistry,
    SourceType,
)


def H_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source(source_id: str, raw: bytes, *, url_suffix: str = "a") -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=SourceType.SEC_COMPLAINT,
        admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
        publisher="U.S. Securities and Exchange Commission",
        title="Historical complaint",
        url=f"https://www.sec.gov/files/litigation/complaints/{url_suffix}.pdf",
        publication_date="2015-08-11",
        sha256=H_bytes(raw),
        retrieved_at="2026-09-24T09:30:00Z",
        public_release_confirmed=True,
        case_id="SEC-CASE-1",
    )


class RawArtifactTests(unittest.TestCase):
    def test_retain_exact_bytes_and_read_back(self):
        raw = b"%PDF-1.7\npublic historical complaint bytes\n"
        src = source("SEC:RAW:001", raw)

        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            record = store.retain(
                src,
                raw,
                media_type="application/pdf",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:31:00Z",
                original_filename="complaint.pdf",
            )

            self.assertEqual(record.sha256, H_bytes(raw))
            self.assertEqual(record.artifact_id, "sha256:" + H_bytes(raw))
            self.assertEqual(record.size_bytes, len(raw))
            self.assertEqual(
                record.immutability,
                ArtifactImmutability.APPLICATION_ENFORCED_APPEND_ONLY,
            )
            self.assertEqual(store.read(record), raw)
            stored_path = (
                Path(root)
                / "sha256"
                / record.sha256[:2]
                / record.sha256
            )
            self.assertTrue(stored_path.is_file())

    def test_registered_hash_mismatch_fails_closed(self):
        registered = b"registered bytes"
        src = source("SEC:RAW:002", registered)

        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            with self.assertRaisesRegex(ValueError, "do not match"):
                store.retain(
                    src,
                    b"different bytes",
                    media_type="application/pdf",
                    acquired_at="2026-09-24T09:30:00Z",
                    stored_at="2026-09-24T09:31:00Z",
                )

    def test_existing_artifact_is_idempotent_not_overwritten(self):
        raw = b"same historical bytes"
        src = source("SEC:RAW:003", raw)

        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            first = store.retain(
                src,
                raw,
                media_type="text/html",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:31:00Z",
            )
            second = store.retain(
                src,
                raw,
                media_type="text/html",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:32:00Z",
            )
            self.assertEqual(first.sha256, second.sha256)
            self.assertEqual(store.read(second), raw)

    def test_read_detects_on_disk_tamper(self):
        raw = b"original"
        src = source("SEC:RAW:004", raw)

        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            record = store.retain(
                src,
                raw,
                media_type="application/pdf",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:31:00Z",
            )
            path = (
                Path(root)
                / "sha256"
                / record.sha256[:2]
                / record.sha256
            )
            os.chmod(path, 0o644)
            path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "size mismatch|hash mismatch"):
                store.read(record)

    def test_manifest_binds_exact_registry_source_set(self):
        raw_a = b"artifact A"
        raw_b = b"artifact B"
        src_a = source("SEC:RAW:005", raw_a, url_suffix="a")
        src_b = source("SEC:RAW:006", raw_b, url_suffix="b")
        registry = SourceRegistry()
        registry.register(src_a)
        registry.register(src_b)

        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            rec_a = store.retain(
                src_a,
                raw_a,
                media_type="application/pdf",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:31:00Z",
            )
            rec_b = store.retain(
                src_b,
                raw_b,
                media_type="application/pdf",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:31:30Z",
            )
            manifest = freeze_raw_artifact_manifest(
                registry,
                (rec_b, rec_a),
                created_at="2026-09-24T09:32:00Z",
                created_by="historical-corpus-ingest",
            )

        verify_raw_artifact_manifest(manifest, registry)
        self.assertEqual(manifest.source_registry_hash, registry.registry_hash)
        self.assertEqual(len(manifest.manifest_hash), 64)

    def test_manifest_rejects_missing_source_artifact(self):
        raw_a = b"artifact A"
        raw_b = b"artifact B"
        src_a = source("SEC:RAW:007", raw_a, url_suffix="a7")
        src_b = source("SEC:RAW:008", raw_b, url_suffix="b8")
        registry = SourceRegistry()
        registry.register(src_a)
        registry.register(src_b)

        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            rec_a = store.retain(
                src_a,
                raw_a,
                media_type="application/pdf",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:31:00Z",
            )
            with self.assertRaisesRegex(ValueError, "set mismatch"):
                freeze_raw_artifact_manifest(
                    registry,
                    (rec_a,),
                    created_at="2026-09-24T09:32:00Z",
                    created_by="historical-corpus-ingest",
                )

    def test_manifest_contains_no_raw_source_bytes(self):
        raw = b"SECRET TEST SENTINEL THAT MUST NOT ENTER MANIFEST"
        src = source("SEC:RAW:009", raw, url_suffix="raw9")
        registry = SourceRegistry()
        registry.register(src)

        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            rec = store.retain(
                src,
                raw,
                media_type="application/pdf",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:31:00Z",
            )
            manifest = freeze_raw_artifact_manifest(
                registry,
                (rec,),
                created_at="2026-09-24T09:32:00Z",
                created_by="historical-corpus-ingest",
            )

        payload = manifest.to_json()
        self.assertNotIn(raw.decode(), payload)
        self.assertIn(H_bytes(raw), payload)

    def test_source_artifact_ref_resolves_without_embedding_source(self):
        raw = b"table row evidence bytes"
        src = source("SEC:RAW:010", raw, url_suffix="raw10")
        registry = SourceRegistry()
        registry.register(src)

        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            rec = store.retain(
                src,
                raw,
                media_type="application/pdf",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:31:00Z",
            )
            manifest = freeze_raw_artifact_manifest(
                registry,
                (rec,),
                created_at="2026-09-24T09:32:00Z",
                created_by="historical-corpus-ingest",
            )

        ref = SourceArtifactRef(
            source_id=src.source_id,
            artifact_id=rec.artifact_id,
            artifact_sha256=rec.sha256,
            locator_kind=SourceLocatorKind.TABLE,
            locator="page=17;table=2;row=4",
            excerpt_sha256=H_bytes(b"row 4"),
        )
        resolved = manifest.resolve_ref(ref)
        self.assertEqual(resolved.proof_hash, rec.proof_hash)

    def test_provider_verified_immutability_requires_attestation(self):
        raw = b"provider immutable"
        src = source("SEC:RAW:011", raw, url_suffix="raw11")
        base = RawArtifactRecord(
            source_id=src.source_id,
            artifact_id="sha256:" + src.sha256,
            sha256=src.sha256,
            size_bytes=len(raw),
            media_type="application/pdf",
            storage_uri=f"cas://sha256/{src.sha256[:2]}/{src.sha256}",
            acquired_at="2026-09-24T09:30:00Z",
            stored_at="2026-09-24T09:31:00Z",
            immutability=ArtifactImmutability.APPLICATION_ENFORCED_APPEND_ONLY,
        )
        with self.assertRaisesRegex(ValueError, "attestation"):
            replace(
                base,
                immutability=ArtifactImmutability.PROVIDER_VERIFIED_IMMUTABLE,
            )

    def test_bad_filename_and_future_storage_time_fail_closed(self):
        raw = b"bad metadata"
        src = source("SEC:RAW:012", raw, url_suffix="raw12")
        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            with self.assertRaisesRegex(ValueError, "basename"):
                store.retain(
                    src,
                    raw,
                    media_type="application/pdf",
                    acquired_at="2026-09-24T09:30:00Z",
                    stored_at="2026-09-24T09:31:00Z",
                    original_filename="../complaint.pdf",
                )
            with self.assertRaisesRegex(ValueError, "precede"):
                store.retain(
                    src,
                    raw,
                    media_type="application/pdf",
                    acquired_at="2026-09-24T09:32:00Z",
                    stored_at="2026-09-24T09:31:00Z",
                )

    def test_manifest_integrity_detects_tamper(self):
        raw = b"manifest source"
        src = source("SEC:RAW:013", raw, url_suffix="raw13")
        registry = SourceRegistry()
        registry.register(src)

        with tempfile.TemporaryDirectory() as root:
            store = LocalContentAddressedArtifactStore(root)
            rec = store.retain(
                src,
                raw,
                media_type="application/pdf",
                acquired_at="2026-09-24T09:30:00Z",
                stored_at="2026-09-24T09:31:00Z",
            )
            manifest = freeze_raw_artifact_manifest(
                registry,
                (rec,),
                created_at="2026-09-24T09:32:00Z",
                created_by="historical-corpus-ingest",
            )

        tampered = replace(manifest, created_by="different-actor")
        with self.assertRaisesRegex(ValueError, "manifest hash mismatch"):
            tampered.verify_integrity()


if __name__ == "__main__":
    unittest.main()
