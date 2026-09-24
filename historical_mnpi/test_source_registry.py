import hashlib
import json
import unittest

from historical_mnpi.source_registry import (
    SourceAdmissibility,
    SourceRecord,
    SourceRegistry,
    SourceType,
    USAGE_SCOPE,
)


def H(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def primary(
    source_id: str = "SEC:TEST:001",
    *,
    url: str = "https://www.sec.gov/files/litigation/complaints/test.pdf",
    sha256: str | None = None,
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_type=SourceType.SEC_COMPLAINT,
        admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
        publisher="U.S. Securities and Exchange Commission",
        title="Historical public complaint",
        url=url,
        publication_date="2015-08-11",
        sha256=sha256 or H(source_id),
        retrieved_at="2026-09-24T08:00:00Z",
        public_release_confirmed=True,
        case_id="SEC-TEST-CASE",
        docket_id="2:15-cv-00001",
        metadata={
            "historical_case": True,
            "source_family": ["SEC", "civil complaint"],
        },
    )


class SourceRegistryTests(unittest.TestCase):
    def test_primary_public_record_can_support_trade_fact_candidate(self):
        record = primary()
        self.assertTrue(record.can_establish_trade_fact)
        self.assertIn("CASE_FACT", record.fact_capabilities)
        self.assertIn("PUBLICATION_BOUNDARY_FACT", record.fact_capabilities)
        self.assertEqual(len(record.proof_hash), 64)
        self.assertEqual(record.to_dict()["usage_scope"], USAGE_SCOPE)

    def test_academic_replication_stays_reconstruction_not_primary_fact(self):
        record = SourceRecord(
            source_id="ACADEMIC:TEST:001",
            source_type=SourceType.ACADEMIC_REPLICATION,
            admissibility=SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION,
            publisher="Peer-reviewed journal",
            title="Historical replication archive",
            url="https://example.edu/replication/archive.zip",
            publication_date="2024-01-15",
            sha256=H("academic"),
            retrieved_at="2026-09-24T08:01:00+00:00",
            public_release_confirmed=True,
        )
        self.assertFalse(record.can_establish_trade_fact)
        self.assertEqual(
            record.fact_capabilities,
            ("ACADEMIC_RECONSTRUCTION_CANDIDATE",),
        )

    def test_secondary_index_is_discovery_only(self):
        record = SourceRecord(
            source_id="INDEX:TEST:001",
            source_type=SourceType.SECONDARY_INDEX,
            admissibility=SourceAdmissibility.DISCOVERY_ONLY,
            publisher="Public research index",
            title="Case discovery index",
            url="https://example.org/cases",
            publication_date="2023-01-01",
            sha256=H("index"),
            retrieved_at="2026-09-24T08:02:00Z",
            public_release_confirmed=True,
        )
        self.assertFalse(record.can_establish_trade_fact)
        self.assertEqual(record.fact_capabilities, ())

    def test_source_type_cannot_be_promoted_to_wrong_admissibility(self):
        with self.assertRaisesRegex(ValueError, "SECONDARY_INDEX"):
            SourceRecord(
                source_id="INDEX:BAD:001",
                source_type=SourceType.SECONDARY_INDEX,
                admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
                publisher="Index",
                title="Bad promotion",
                url="https://example.org/index",
                publication_date="2020-01-01",
                sha256=H("bad-index"),
                retrieved_at="2026-09-24T08:03:00Z",
                public_release_confirmed=True,
            )

        with self.assertRaisesRegex(ValueError, "ACADEMIC_REPLICATION"):
            SourceRecord(
                source_id="ACADEMIC:BAD:001",
                source_type=SourceType.ACADEMIC_REPLICATION,
                admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
                publisher="Journal",
                title="Bad academic promotion",
                url="https://example.org/archive.zip",
                publication_date="2020-01-01",
                sha256=H("bad-academic"),
                retrieved_at="2026-09-24T08:04:00Z",
                public_release_confirmed=True,
            )

    def test_nonpublic_or_unhashed_sources_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "already-public"):
            SourceRecord(
                source_id="SEC:PRIVATE:001",
                source_type=SourceType.SEC_COMPLAINT,
                admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
                publisher="SEC",
                title="Not yet public",
                url="https://www.sec.gov/example.pdf",
                publication_date="2020-01-01",
                sha256=H("private"),
                retrieved_at="2026-09-24T08:05:00Z",
                public_release_confirmed=False,
            )

        with self.assertRaisesRegex(ValueError, "sha256"):
            primary(sha256="not-a-hash")

    def test_timestamp_and_url_are_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            SourceRecord(
                source_id="SEC:TIME:001",
                source_type=SourceType.SEC_COMPLAINT,
                admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
                publisher="SEC",
                title="Naive timestamp",
                url="https://www.sec.gov/example.pdf",
                publication_date="2020-01-01",
                sha256=H("time"),
                retrieved_at="2026-09-24T08:05:00",
                public_release_confirmed=True,
            )

        with self.assertRaisesRegex(ValueError, "https"):
            SourceRecord(
                source_id="SEC:URL:001",
                source_type=SourceType.SEC_COMPLAINT,
                admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
                publisher="SEC",
                title="Insecure URL",
                url="http://www.sec.gov/example.pdf",
                publication_date="2020-01-01",
                sha256=H("url"),
                retrieved_at="2026-09-24T08:05:00Z",
                public_release_confirmed=True,
            )

    def test_registration_is_idempotent_but_conflicting_id_fails(self):
        registry = SourceRegistry()
        first = primary()
        self.assertIs(registry.register(first), first)
        self.assertEqual(registry.register(first), first)

        conflict = primary(
            sha256=H("different bytes"),
        )
        with self.assertRaisesRegex(ValueError, "different content"):
            registry.register(conflict)

    def test_duplicate_artifact_under_new_id_is_rejected(self):
        registry = SourceRegistry()
        first = primary()
        registry.register(first)
        duplicate = primary(
            source_id="SEC:TEST:002",
            sha256=first.sha256,
        )
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(duplicate)

    def test_registry_hash_is_order_independent(self):
        a = primary("SEC:TEST:001")
        b = primary(
            "SEC:TEST:002",
            url="https://www.sec.gov/files/litigation/complaints/test2.pdf",
        )

        left = SourceRegistry()
        left.register(a)
        left.register(b)

        right = SourceRegistry()
        right.register(b)
        right.register(a)

        self.assertEqual(left.registry_hash, right.registry_hash)
        self.assertEqual(left.to_dict(), right.to_dict())

    def test_json_round_trip_and_tamper_detection(self):
        registry = SourceRegistry()
        registry.register(primary())
        payload = registry.to_json()
        restored = SourceRegistry.from_json(payload)

        self.assertEqual(restored.registry_hash, registry.registry_hash)
        self.assertEqual(restored.to_dict(), registry.to_dict())

        tampered = json.loads(payload)
        tampered["sources"][0]["title"] = "Tampered title"
        with self.assertRaisesRegex(ValueError, "proof hash mismatch"):
            SourceRegistry.from_dict(tampered)

    def test_metadata_is_detached_from_mutable_input(self):
        metadata = {"tags": ["public", "historical"]}
        record = SourceRecord(
            source_id="SEC:META:001",
            source_type=SourceType.SEC_COMPLAINT,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            publisher="SEC",
            title="Immutable metadata",
            url="https://www.sec.gov/example-meta.pdf",
            publication_date="2020-01-01",
            sha256=H("meta"),
            retrieved_at="2026-09-24T08:06:00Z",
            public_release_confirmed=True,
            metadata=metadata,
        )
        before = record.proof_hash
        metadata["tags"].append("mutated")
        self.assertEqual(record.proof_hash, before)
        self.assertEqual(
            record.to_dict()["metadata"]["tags"],
            ["public", "historical"],
        )


if __name__ == "__main__":
    unittest.main()
