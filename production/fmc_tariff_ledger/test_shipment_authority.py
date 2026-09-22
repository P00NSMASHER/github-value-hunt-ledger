import sqlite3
import tempfile
import unittest
from pathlib import Path

import crawler
import shipment_authority as authority
import shaq_route_crawl


class ShipmentAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        self.rate_db = root / "rates.sqlite"
        self.fmc_db = root / "fmc.sqlite"
        self.rates = shaq_route_crawl.init_db(self.rate_db)
        self.rates.row_factory = sqlite3.Row
        self.fmc = crawler.init_db(self.fmc_db)
        self.fmc.row_factory = sqlite3.Row
        self._seed_fmc_entity("123456", "COSCO TEST CARRIER")

    def tearDown(self):
        self.rates.close()
        self.fmc.close()
        self.td.cleanup()

    def _seed_fmc_entity(self, org, name):
        self.fmc.execute(
            """INSERT INTO entities(entity_class, organization_no, legal_name, trade_name, active)
               VALUES ('vocc', ?, ?, '', 1)""",
            (org, name),
        )
        eid = self.fmc.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.fmc.execute(
            """INSERT INTO tariff_locations(
                 entity_id, canonical_url, directory_url, directory_snapshot_sha256,
                 first_seen_at, last_seen_at
               ) VALUES (?, 'https://carrier.test/tariff','https://fmc.test','x','now','now')""",
            (eid,),
        )
        self.fmc.commit()

    def add_fmc_rule(
        self,
        *,
        rule_type="demurrage",
        amount="100",
        effective="2026-01-01",
        version="T1",
        digest="a" * 64,
    ):
        loc = self.fmc.execute("SELECT id FROM tariff_locations").fetchone()[0]
        url = f"https://carrier.test/{version}-{digest[:6]}"
        self.fmc.execute(
            """INSERT INTO snapshots(
                 tariff_location_id, requested_url, final_url, fetched_at,
                 http_status, content_type, byte_count, sha256, blob_relpath,
                 parser_status, source_version, effective_from
               ) VALUES (?, ?, ?, 'now',200,'text/html',10,?,'blobs/x',
                         'parsed:html',?,?)""",
            (loc, url, url, digest, version, effective),
        )
        sid = self.fmc.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.fmc.execute(
            """INSERT INTO terms(
                 snapshot_id, entity_class, organization_no, legal_name,
                 rule_type, term_kind, amount_value, currency, unit,
                 effective_from, source_version, evidence_locator,
                 evidence_excerpt, confidence, parser_version, created_at
               ) VALUES (?, 'vocc','123456','COSCO TEST CARRIER',?,
                         'money',?,'USD','per day',?,?,'rule:21','evidence',
                         0.95,'test','now')""",
            (sid, rule_type, amount, effective, version),
        )
        self.fmc.commit()

    def add_rate(
        self,
        *,
        amount="5000",
        kind="CARRIER_CONTRACT",
        identity="REVIEWED_EXACT",
        org="123456",
        valid_from="2026-05-01",
        valid_to="2026-06-30",
        origin="Shanghai",
        destination="Chancay",
        container="40HQ",
        source_label="AUTHORIZED_CONTRACT_CORPUS",
        rate_basis="per container",
        source_url="authorized://contract-corpus",
    ):
        self.rates.execute(
            """INSERT INTO shaq_rates(
                 origin_raw,destination_raw,carrier_raw,carrier_normalized,
                 fmc_organization_no,fmc_identity_status,container_type,
                 amount_value,currency,valid_from,valid_to,rate_basis,
                 source_url,rate_kind,source_label,source_contract_reference,
                 evidence_excerpt,parser_confidence,parser_version,created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'now')""",
            (
                origin, destination, "COSCO", "COSCO", org, identity, container,
                amount, "USD", valid_from, valid_to, rate_basis,
                source_url, kind, source_label, "C-001",
                "contract row", 1.0, "test",
            ),
        )
        self.rates.commit()

    def envelope(self, **overrides):
        values = dict(
            fmc_organization_no="123456",
            shipment_date="2026-06-01",
            origin="Shanghai",
            destination="Chancay",
            container_type="40HQ",
            currency="USD",
            rule_types=["demurrage"],
        )
        values.update(overrides)
        return authority.build_envelope(self.rates, self.fmc, **values)

    def test_resolved_contract_plus_rule_builds_ready_envelope(self):
        self.add_rate()
        self.add_fmc_rule()
        result = self.envelope()
        self.assertEqual(result["status"], "AUTHORITY_ENVELOPE_READY")
        self.assertEqual(result["base_rate_authority"]["amount_value"], "5000")
        self.assertEqual(result["asserted_recovery"], "0.00")

    def test_benchmark_only_rate_never_authorizes_base(self):
        self.add_rate(
            kind="PUBLISHER_CARRIER_RATE",
            identity="UNRESOLVED",
            org=None,
            source_label="SHAQ_PUBLIC_ROUTE_PAGE",
        )
        self.add_fmc_rule()
        result = self.envelope()
        self.assertEqual(result["status"], "NOT_READY_FOR_MONEY_ASSERTION")
        self.assertEqual(
            result["base_rate_authority"]["status"],
            "NO_AUTHORITY_READY_CONTRACT_RATE",
        )

    def test_same_amount_with_conflicting_contract_basis_abstains(self):
        self.add_rate(amount="5000", rate_basis="per container")
        self.add_rate(
            amount="5000",
            rate_basis="per shipment",
            source_label="SECOND_AUTHORIZED_SOURCE",
            source_url="authorized://contract-corpus-2",
        )
        self.add_fmc_rule()
        result = self.envelope()
        self.assertEqual(
            result["base_rate_authority"]["status"],
            "AMBIGUOUS_CONTRACT_RATE_BASIS",
        )
        self.assertEqual(result["status"], "NOT_READY_FOR_MONEY_ASSERTION")
        self.assertIn(
            "AMBIGUOUS_CONTRACT_RATE_BASIS",
            result["blockers"],
        )

    def test_two_contract_amounts_on_same_latest_period_abstain(self):
        self.add_rate(amount="5000")
        self.add_rate(amount="5200", source_label="SECOND_AUTHORIZED_SOURCE")
        self.add_fmc_rule()
        result = self.envelope()
        self.assertEqual(
            result["base_rate_authority"]["status"],
            "AMBIGUOUS_CONTRACT_RATE",
        )
        self.assertEqual(result["status"], "NOT_READY_FOR_MONEY_ASSERTION")

    def test_latest_explicit_contract_period_wins(self):
        self.add_rate(amount="4800", valid_from="2026-01-01", valid_to="2026-12-31")
        self.add_rate(amount="5000", valid_from="2026-05-01", valid_to="2026-06-30")
        self.add_fmc_rule()
        result = self.envelope()
        self.assertEqual(result["base_rate_authority"]["amount_value"], "5000")

    def test_ambiguous_tariff_version_blocks_full_envelope(self):
        self.add_rate()
        self.add_fmc_rule(version="REV-A", amount="100", digest="a" * 64)
        self.add_fmc_rule(version="REV-B", amount="125", digest="b" * 64)
        result = self.envelope()
        self.assertEqual(result["status"], "NOT_READY_FOR_MONEY_ASSERTION")
        self.assertIn("AMBIGUOUS_TARIFF_AUTHORITY", result["blockers"])

    def test_exact_lane_match_only(self):
        self.add_rate(origin="Shanghai", destination="Chancay")
        self.add_fmc_rule()
        result = self.envelope(origin="Shanghai Port")
        self.assertEqual(
            result["base_rate_authority"]["status"],
            "NO_AUTHORITY_READY_CONTRACT_RATE",
        )


if __name__ == "__main__":
    unittest.main()
