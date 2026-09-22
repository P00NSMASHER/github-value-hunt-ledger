import sqlite3
import tempfile
import unittest
from pathlib import Path

import audit_pass_through as audit
import crawler


class PassThroughAuditTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = Path(self.td.name) / "ledger.sqlite"
        self.conn = crawler.init_db(self.db)
        self.conn.row_factory = sqlite3.Row
        self._entity("oti", "NVO001", "NVO EXAMPLE")
        self._entity("vocc", "VOC001", "VOCC EXAMPLE")

    def tearDown(self):
        self.conn.close()
        self.td.cleanup()

    def _entity(self, cls, org, name):
        self.conn.execute(
            """INSERT INTO entities(entity_class, organization_no, legal_name, trade_name, active)
               VALUES (?, ?, ?, '', 1)""",
            (cls, org, name),
        )
        eid = self.conn.execute(
            "SELECT id FROM entities WHERE organization_no=?", (org,)
        ).fetchone()[0]
        self.conn.execute(
            """INSERT INTO tariff_locations(
                 entity_id, canonical_url, directory_url, directory_snapshot_sha256,
                 first_seen_at, last_seen_at
               ) VALUES (?, ?, 'https://fmc.test', 'x', 'now', 'now')""",
            (eid, f"https://{org.lower()}.test/tariff"),
        )
        self.conn.commit()

    def _term(
        self,
        org,
        rule_type,
        excerpt,
        *,
        amount=None,
        currency=None,
        unit=None,
        effective="2026-01-01",
        version="V1",
        digest=None,
    ):
        loc = self.conn.execute(
            """SELECT tl.id FROM tariff_locations tl
               JOIN entities e ON e.id=tl.entity_id
               WHERE e.organization_no=?""",
            (org,),
        ).fetchone()[0]
        digest = digest or (org[0].lower() * 64)
        requested = (
            f"https://{org.lower()}.test/{rule_type}/{version}/"
            f"{abs(hash((excerpt, amount, unit))) % 1000000}"
        )
        self.conn.execute(
            """INSERT INTO snapshots(
                 tariff_location_id, requested_url, final_url, fetched_at, http_status,
                 content_type, byte_count, sha256, blob_relpath, parser_status,
                 source_version, effective_from
               ) VALUES (?, ?, ?, '2026-09-22T00:00:00Z', 200, 'text/html', 100,
                         ?, 'blobs/x', 'parsed:html:entity_scoped', ?, ?)""",
            (loc, requested, requested, digest, version, effective),
        )
        snap = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute(
            """INSERT INTO terms(
                 snapshot_id, entity_class, organization_no, legal_name, rule_type,
                 term_kind, amount_value, currency, unit, effective_from, source_version,
                 evidence_locator, evidence_excerpt, confidence, parser_version, created_at
               )
               SELECT ?, e.entity_class, e.organization_no, e.legal_name, ?, ?, ?, ?, ?,
                      ?, ?, 'rule:test', ?, 0.95, 'test', 'now'
               FROM entities e WHERE e.organization_no=?""",
            (
                snap,
                rule_type,
                "money" if amount is not None else "rule_text",
                amount,
                currency,
                unit,
                effective,
                version,
                excerpt,
                org,
            ),
        )
        self.conn.commit()

    def _input(self, **overrides):
        values = dict(
            invoice_line_id="L1",
            nvocc_organization_no="NVO001",
            upstream_vocc_organization_no="VOC001",
            cargo_received_date="2026-06-01",
            rule_type="terminal_handling",
            billed_amount="125",
            currency="USD",
            quantity="1",
            unit="per container",
            separately_disclosed_service_fee="0",
        )
        values.update(overrides)
        return audit.AuditInput(**values)

    def test_positive_delta_is_review_candidate_not_asserted_recovery(self):
        self._term(
            "NVO001",
            "pass_through",
            "Terminal services charges are passed through at cost without markup.",
        )
        self._term(
            "VOC001",
            "terminal_handling",
            "Terminal handling charge USD 100 per container.",
            amount="100",
            currency="USD",
            unit="per container",
        )
        result = audit.audit_one(self.conn, self._input())
        self.assertEqual(result["status"], "POTENTIAL_PASS_THROUGH_MARKUP_REVIEW")
        self.assertEqual(result["potential_markup_delta"], "25.00")
        self.assertEqual(result["asserted_recovery"], "0.00")

    def test_category_must_be_listed_in_nvocc_evidence(self):
        self._term(
            "NVO001",
            "pass_through",
            "Canal tolls are passed through at cost without markup.",
        )
        self._term(
            "VOC001",
            "terminal_handling",
            "Terminal handling USD 100 per container.",
            amount="100",
            currency="USD",
            unit="per container",
        )
        result = audit.audit_one(self.conn, self._input())
        self.assertEqual(result["status"], "CHARGE_CATEGORY_NOT_PROVEN_LISTED")

    def test_undated_nvocc_rule_abstains(self):
        self._term(
            "NVO001",
            "pass_through",
            "Terminal services are passed through without markup.",
            effective=None,
        )
        result = audit.audit_one(self.conn, self._input())
        self.assertEqual(result["status"], "UNDATED_NVOCC_PASSTHROUGH_RULE")

    def test_ambiguous_upstream_prices_abstain(self):
        self._term(
            "NVO001",
            "pass_through",
            "Terminal services charges are passed through at cost without markup.",
        )
        # Same authority snapshot identity/version can legitimately contain multiple slabs.
        self._term(
            "VOC001",
            "terminal_handling",
            "THC USD 100 per container.",
            amount="100",
            currency="USD",
            unit="per container",
            digest="b" * 64,
        )
        self._term(
            "VOC001",
            "terminal_handling",
            "THC USD 150 per container.",
            amount="150",
            currency="USD",
            unit="per container",
            digest="b" * 64,
        )
        result = audit.audit_one(self.conn, self._input())
        self.assertEqual(result["status"], "AMBIGUOUS_PRICE")
        self.assertEqual(result["asserted_recovery"], "0.00")

    def test_no_overage(self):
        self._term(
            "NVO001",
            "pass_through",
            "Terminal services charges are passed through at cost without markup.",
        )
        self._term(
            "VOC001",
            "terminal_handling",
            "Terminal handling USD 125 per container.",
            amount="125",
            currency="USD",
            unit="per container",
        )
        result = audit.audit_one(self.conn, self._input(billed_amount="120"))
        self.assertEqual(result["status"], "NO_PASS_THROUGH_OVERAGE")

    def test_separate_service_fee_is_not_netted_into_pass_through(self):
        self._term(
            "NVO001",
            "pass_through",
            "Terminal services are passed through at cost without markup. "
            "Advance payment service fees are separately stated.",
        )
        self._term(
            "VOC001",
            "terminal_handling",
            "Terminal handling USD 100 per container.",
            amount="100",
            currency="USD",
            unit="per container",
        )
        result = audit.audit_one(
            self.conn,
            self._input(
                billed_amount="120",
                separately_disclosed_service_fee="15",
            ),
        )
        self.assertEqual(result["potential_markup_delta"], "20.00")
        self.assertEqual(result["separately_disclosed_service_fee"], "15.00")


if __name__ == "__main__":
    unittest.main()
