import sqlite3
import tempfile
import unittest
from pathlib import Path

import shaq_route_crawl
import shaq_source_policy as policy


class ShaqSourcePolicyTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = Path(self.td.name) / "x.sqlite"
        self.conn = shaq_route_crawl.init_db(self.db)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """INSERT INTO shaq_rates(
                 origin_raw,destination_raw,carrier_raw,carrier_normalized,
                 fmc_identity_status,container_type,amount_value,currency,
                 source_url,rate_kind,source_label,evidence_excerpt,
                 parser_confidence,parser_version,created_at
               ) VALUES ('Shanghai','Chancay','COSCO','COSCO','UNRESOLVED',
                         '40HQ','5060','USD',
                         'https://shaq-log.com/q/a',
                         'PUBLISHER_CARRIER_RATE','SHAQ_PUBLIC_ROUTE_PAGE',
                         'row',0.99,'test','now')"""
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.td.cleanup()

    def test_contract_promotion_blocked_without_authorization(self):
        cid = policy.record_source_classification(
            self.conn,
            dataset_key="SHAQ_151K_COSCO_CONTRACT_CORPUS",
            match_field="source_label",
            source_pattern="SHAQ_PUBLIC_ROUTE_PAGE",
            rate_kind="CARRIER_CONTRACT",
            evidence="hypothesis only",
            reviewed=True,
        )
        result = policy.apply_classification(self.conn, cid)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("DATASET_AUTHORIZATION_NOT_RECORDED", result["blockers"])
        kind = self.conn.execute("SELECT rate_kind FROM shaq_rates").fetchone()[0]
        self.assertEqual(kind, "PUBLISHER_CARRIER_RATE")

    def test_unreviewed_classification_cannot_apply(self):
        cid = policy.record_source_classification(
            self.conn,
            dataset_key=None,
            match_field="source_label",
            source_pattern="SHAQ_PUBLIC_ROUTE_PAGE",
            rate_kind="SPOT_MARKET",
            evidence="research observation",
            reviewed=False,
        )
        result = policy.apply_classification(self.conn, cid)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("CLASSIFICATION_NOT_REVIEWED", result["blockers"])

    def test_authorization_plus_review_allows_explicit_promotion(self):
        policy.record_dataset_authorization(
            self.conn,
            dataset_key="AUTHORIZED_TEST_CORPUS",
            authorization_scope="commercial ingestion and use",
            evidence_note="test fixture authorization",
        )
        cid = policy.record_source_classification(
            self.conn,
            dataset_key="AUTHORIZED_TEST_CORPUS",
            match_field="source_label",
            source_pattern="SHAQ_PUBLIC_ROUTE_PAGE",
            rate_kind="CARRIER_CONTRACT",
            evidence="reviewed fixture lineage",
            reviewed=True,
        )
        result = policy.apply_classification(self.conn, cid)
        self.assertEqual(result["status"], "APPLIED")
        kind = self.conn.execute("SELECT rate_kind FROM shaq_rates").fetchone()[0]
        self.assertEqual(kind, "CARRIER_CONTRACT")
        audit = self.conn.execute(
            "SELECT matching_rate_rows, updated_rate_rows FROM shaq_classification_applications"
        ).fetchone()
        self.assertEqual(tuple(audit), (1, 1))

    def test_url_prefix_classification_is_bounded(self):
        self.conn.execute(
            """INSERT INTO shaq_rates(
                 origin_raw,destination_raw,carrier_raw,carrier_normalized,
                 fmc_identity_status,container_type,amount_value,currency,
                 source_url,rate_kind,source_label,evidence_excerpt,
                 parser_confidence,parser_version,created_at
               ) VALUES ('Shanghai','Hamburg','COSCO','COSCO','UNRESOLVED',
                         '40HQ','3400','USD',
                         'https://other.example/rate',
                         'SPOT_MARKET','OTHER','row',0.99,'test','now')"""
        )
        self.conn.commit()
        cid = policy.record_source_classification(
            self.conn,
            dataset_key=None,
            match_field="source_url_prefix",
            source_pattern="https://shaq-log.com/q/",
            rate_kind="PUBLISHER_CARRIER_RATE",
            evidence="public route page family",
            reviewed=True,
        )
        result = policy.apply_classification(self.conn, cid)
        self.assertEqual(result["matching_rows"], 1)
        other = self.conn.execute(
            "SELECT rate_kind FROM shaq_rates WHERE source_label='OTHER'"
        ).fetchone()[0]
        self.assertEqual(other, "SPOT_MARKET")


if __name__ == "__main__":
    unittest.main()
