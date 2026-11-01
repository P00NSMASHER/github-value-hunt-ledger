"""Mission 36: adversarial checks for the actual RETALLY publication boundary.

All mutations are synthetic in-memory or within temp directories. Neither
site build nor these tests deploys, contacts buyers or authorizes a real pilot.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight.site import public_claim_gate as gate
from freight.site import build as builder


class PublicClaimGateM36Tests(unittest.TestCase):
    def test_frozen_research_policy_source_receipt_and_no_approval(self):
        self.assertEqual(
            gate._git_blob(gate.CLAIM_POLICY.read_bytes()),
            gate.POLICY_GIT_BLOB_SHA1,
        )
        p=gate.read_frozen_claim_policy()
        self.assertEqual(p["lab_number"],14)
        self.assertEqual(p["claim_count"],16)
        self.assertEqual(p["qualified_internal_claim_count"],8)
        self.assertEqual(p["blocked_inference_claim_count"],8)
        self.assertEqual(p["required_pilot_gate_count"],18)
        self.assertEqual(p["external_claims_approved"],0)
        self.assertFalse(any(c["public_publication_authorized"] for c in
                             p["claim_registry"]))

    def test_source_registry_modification_requires_explicit_review(self):
        raw=gate.CLAIM_POLICY.read_text()
        with tempfile.TemporaryDirectory() as folder:
            fake=Path(folder)/"CLAIM_CLEARANCE_M35.json"
            fake.write_text(raw.replace('"external_claims_approved": 0',
                                        '"external_claims_approved": 1'))
            with patch.object(gate,"CLAIM_POLICY",fake):
                with self.assertRaisesRegex(
                    ValueError,"PUBLIC_CLAIM_GATE_POLICY_BLOB_CHANGED"
                ):
                    gate.read_frozen_claim_policy()

    def test_existing_source_allowlist_passes_static_claim_gate(self):
        files={
            name:(builder.SOURCE/name).read_text(encoding="utf-8")
            for name in builder.TEXT_SOURCE_FILES
        }
        r=gate.audit_public_bundle(files)
        self.assertEqual(r["scope"],
                         "BUILD_TIME_PUBLICATION_NEGATIVE_CHECK_NOT_MARKETING_APPROVAL")
        self.assertEqual(r["registered_source_and_claim_cases"],16)
        self.assertEqual(r["independent_real_customer_pilot_requirements_unmet"],18)
        self.assertEqual(r["flagged_unsupported_claims"],0)
        self.assertFalse(r["legal_or_external_marketing_publication_approved"])
        self.assertGreaterEqual(r["files_scanned"],30)
        self.assertEqual(len(r["scan_fingerprint_sha256"]),64)

    def test_exact_transformed_public_build_passes_without_changing_pricing(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=builder.build(Path(folder)/"site","sales@freightfixture.com",
                               True,"0.30")
            self.assertIn('contingencyRecoveryRate: "0.3"',
                          (dest/"commercial-config.js").read_text())
            html=(dest/"index.html").read_text()
            self.assertIn('id="actualRecoveredDisplay">$100,000',html)
            self.assertIn("Fictional data only",html)
            r=gate.audit_public_bundle({
                name:(dest/name).read_text() for name in builder.TEXT_SOURCE_FILES
            })
            self.assertEqual(r["flagged_unsupported_claims"],0)

    def test_original_macro_industry_values_all_external_unapproved(self):
        samples={
            "M35-01":"2024 BEA trucking industry gross output $545,435 million.",
            "M35-02":"Census trucking employer revenue was $402,827.246 million.",
            "M35-03":"RETALLY can recover $142,607.754 million.",
            "M35-04":"Census covers 73.85% of trucking freight invoices.",
            "M35-05":"BEA trucking real output rose 8.05%.",
            "M35-06":"BLS trucking real sectoral output increased 4.02%.",
            "M35-07":"Census-PPI trucking proxy grew 1.18%.",
            "M35-08":"BEA less BLS producer price change was 0.45 percentage points.",
        }
        for identifier,body in samples.items():
            with self.subTest(identifier=identifier):
                violations=gate.inspect_public_text("about.html",
                                                    "<h1>"+body+"</h1>")
                self.assertIn(
                    "RESEARCH_ONLY_NUMBER_IN_PUBLIC_COPY_"+identifier,violations
                )

    def test_rounded_billion_gap_not_laundered_into_recoverable_tam(self):
        for body in (
            "We identified $142.6 billion in recoverable freight overcharges.",
            "RETALLY uncovered $142.608 billion in freight bill errors.",
            "RETALLY $142.6bn addressable carrier overcharges.",
        ):
            self.assertIn(
                "RESEARCH_ONLY_NUMBER_IN_PUBLIC_COPY_M35-03",
                gate.inspect_public_text("freight-overcharge-recovery.html",body),
                body,
            )

    def test_fake_company_recovered_cash_claim_rejected_in_visible_html(self):
        for body in (
            "We have recovered $120,000 from shippers.",
            "RETALLY recovered $250,000 in freight bills.",
            "Our team already saved $50,000 for customers.",
            "We've refunded $100,000 to freight clients.",
        ):
            self.assertIn(
                "UNVERIFIED_OWN_RECOVERED_MONEY",
                gate.inspect_public_text("about.html",
                                         "<section><p>"+body+"</p></section>"),
                body,
            )

    def test_fake_real_customer_audit_volume_rejected(self):
        for body in (
            "We've audited 1,284 customer invoices.",
            "RETALLY has processed 1000 shipments.",
            "Our team reviewed over 400 freight invoices.",
        ):
            self.assertIn(
                "UNVERIFIED_OWN_AUDIT_VOLUME",
                gate.inspect_public_text("trust.html",body),
                body,
            )

    def test_fake_recovery_success_rate_and_security_certification(self):
        blocked={
            "Our recovery rate is 98.5%.":"UNVERIFIED_OWN_RECOVERY_RATE",
            "RETALLY's invoice error rate: 22%.":"UNVERIFIED_OWN_RECOVERY_RATE",
            "RETALLY is SOC 2 certified.":"UNVERIFIED_OWN_SECURITY_CERTIFICATION",
            "Our platform is ISO 27001 compliant.":"UNVERIFIED_OWN_SECURITY_CERTIFICATION",
            "RETALLY guarantees savings.":"UNVERIFIED_GUARANTEED_REFUNDS",
            "Guaranteed recovery.":"UNVERIFIED_GUARANTEED_REFUNDS",
        }
        for text,rule in blocked.items():
            self.assertIn(rule,gate.inspect_public_text("trust.html",text),text)

    def test_plain_legitimate_service_offer_and_fee_terms_not_blocked(self):
        samples=(
            "The initial recovery audit is $0 upfront. Recovery work requires written authorization.",
            "Our fee is 30% of eligible funds actually recovered after reconciliation.",
            "No recovery, no recovery fee. A candidate is not recovered cash.",
            "A future verified claim may be pursued only with customer permission.",
            "An approved carrier credit is not cash until the realized benefit posts.",
            "The company does not guarantee recovery.",
        )
        for text in samples:
            self.assertEqual(
                gate.inspect_public_text("freight-audit-services.html",text),[],
                text,
            )

    def test_worked_example_missing_fictional_label_is_blocked(self):
        text="<h1>Worked freight audit example</h1><p>$125 was recovered for a customer.</p><p>Not a customer result.</p>"
        violations=gate.inspect_public_text("freight-audit-example.html",text)
        self.assertIn("SYNTHETIC_EXAMPLE_MISSING_FICTIONAL_LABEL",violations)

    def test_status_dashboard_missing_not_real_result_label_is_blocked(self):
        text="<h1>Fictional recovery status report</h1><p>Recoveries posted $13,450.</p>"
        violations=gate.inspect_public_text("recovery-status-example.html",text)
        self.assertIn("SYNTHETIC_EXAMPLE_MISSING_NOT_REAL_CUSTOMER_RESULT",
                      violations)

    def test_home_sample_metrics_require_both_fictional_disclaimers(self):
        text="<h1>RETALLY</h1><section>Sample audit: invoices reviewed 1,284 and recoveries posted 6</section>"
        failures=gate.inspect_public_text("index.html",text)
        self.assertIn("HOME_SAMPLE_METRICS_MISSING_FICTIONAL_LABEL",failures)
        self.assertIn("HOME_SAMPLE_METRICS_MISSING_NO_REAL_CUSTOMER_DISCLAIMER",failures)
        good=text+"<p>Fictional data. Illustrative only. Not customer results.</p>"
        self.assertEqual(gate.inspect_public_text("index.html",good),[])

    def test_nonexample_page_no_presumption_that_samples_are_real(self):
        text="Sample recovery status: fictional data, not actual customer results."
        self.assertEqual(gate.inspect_public_text("trust.html",text),[])
        self.assertTrue(any("SYNTHETIC" in x
                            for x in gate.inspect_public_text(
                                "freight-audit-example.html",text.replace("fictional","")
                            )))

    def test_keyword_inside_metadata_and_open_graph_is_inspected(self):
        for attrib in (
            'name="description"',
            'property="og:description"',
            'name="twitter:description"',
        ):
            text='<meta '+attrib+' content="RETALLY has recovered $12,000 in cash.">'
            self.assertIn(
                "UNVERIFIED_OWN_RECOVERED_MONEY",
                gate.inspect_public_text("about.html",text),
                text,
            )

    def test_search_jsonld_is_inspected_not_skipped(self):
        text='<script type="application/ld+json">{"description":"Our recovery rate is 95%."}</script>'
        self.assertIn(
            "UNVERIFIED_OWN_RECOVERY_RATE",
            gate.inspect_public_text("index.html",text),
        )

    def test_alt_text_and_accessibility_labels_are_inspected(self):
        text='<img alt="RETALLY recovered $50,000 for clients."><span aria-label="RETALLY is SOC 2 certified"></span>'
        violations=gate.inspect_public_text("about.html",text)
        self.assertIn("UNVERIFIED_OWN_RECOVERED_MONEY",violations)
        self.assertIn("UNVERIFIED_OWN_SECURITY_CERTIFICATION",violations)

    def test_inline_dynamic_claims_are_scanned_and_css_not_treated_as_copy(self):
        html='<script>const value="RETALLY recovered $500,000";</script><style>.foo{content:"We recovered $1";}</style><p>Welcome to RETALLY</p>'
        self.assertIn("UNVERIFIED_OWN_RECOVERED_MONEY",
                      gate.inspect_public_text("about.html",html))
        self.assertEqual(gate.inspect_public_text("about.html",
            '<style>.foo{content:"We recovered $1";}</style><p>Welcome to RETALLY</p>'),[])
        self.assertIn("UNVERIFIED_OWN_RECOVERED_MONEY",
                      gate.inspect_public_text("site.js",
                          'const copy="RETALLY recovered $500,000";'))

    def test_client_rendered_data_claim_attribute_cannot_hide_recovery(self):
        html='<div data-copy="RETALLY recovered $12,000" data-track="banner"></div>'
        self.assertIn("UNVERIFIED_OWN_RECOVERED_MONEY",
                      gate.inspect_public_text("index.html",html))

    def test_unapproved_claim_in_llms_txt_or_csv_is_blocked(self):
        self.assertIn(
            "RESEARCH_ONLY_NUMBER_IN_PUBLIC_COPY_M35-03",
            gate.inspect_public_text("llms.txt","RETALLY can audit $142,607.754m"),
        )
        self.assertIn(
            "UNVERIFIED_OWN_RECOVERED_MONEY",
            gate.inspect_public_text("provider-scorecard.csv",
                                     'RETALLY,"We recovered $1,000",2026'),
        )

    def test_rejects_arbitrary_unverified_guarantee_but_allows_denial(self):
        self.assertIn(
            "UNVERIFIED_GUARANTEED_REFUNDS",
            gate.inspect_public_text("pricing.html","We guarantee savings."),
        )
        self.assertEqual(gate.inspect_public_text("pricing.html",
                                                  "No guaranteed recovery."),[])

    def test_complete_public_bundle_missing_protected_example_fails_closed(self):
        with self.assertRaisesRegex(
            ValueError,"PUBLIC_CLAIM_GATE_MISSING_QUALIFIED_SYNTHETIC_EXAMPLE_PAGE"
        ):
            gate.audit_public_bundle({"index.html":"RETALLY"},require_examples=True)

    def test_cross_page_claim_injection_cannot_be_hidden_by_fictional_label_elsewhere(self):
        pages={
            "freight-audit-example.html":
                "<p>Fictional source example. Not a customer result.</p>",
            "recovery-status-example.html":
                "<p>Fictional source report. Not a customer result.</p>",
            "index.html":"<p>Fictional data. Illustrative only. Not customer results.</p>",
            "about.html":"RETALLY recovered $5,000.",
        }
        with self.assertRaisesRegex(ValueError,
                                    "PUBLIC_CLAIM_GATE_REJECTED:about.html:UNVERIFIED_OWN_RECOVERED_MONEY"):
            gate.audit_public_bundle(pages)

    def test_build_gates_claim_before_publishing_any_files(self):
        old=builder._public_source
        with tempfile.TemporaryDirectory() as root:
            injection=Path(root)/"index.html"
            injection.write_text(
                (builder.SOURCE/"index.html").read_text()+
                '<section>RETALLY has recovered $500,000 for customers.</section>'
            )
            def changed_source(name):
                return injection if name=="index.html" else old(name)
            output=Path(root)/"not-published"
            with patch.object(builder,"_public_source",side_effect=changed_source):
                with self.assertRaisesRegex(
                    ValueError,"PUBLIC_CLAIM_GATE_REJECTED:index.html:UNVERIFIED_OWN_RECOVERED_MONEY"
                ):
                    builder.build(output,"sales@freightfixture.com",True)
            self.assertFalse(output.exists(),"A rejected public bundle must not be written")

    def test_valid_marketing_brand_templates_checked_without_deploying(self):
        names=(
            "RETALLY_PROPOSAL_TEMPLATE.md",
            "RETALLY_CUSTOMER_APPLICATION.md",
            "RETALLY_EMAIL_SIGNATURE.html",
        )
        content={
            name:(builder.SOURCE.parent/"brand"/name).read_text(encoding="utf-8")
            for name in names
        }
        result=gate.audit_public_bundle(content,require_examples=False)
        self.assertEqual(result["files_scanned"],3)
        self.assertEqual(result["flagged_unsupported_claims"],0)
        self.assertFalse(result["legal_or_external_marketing_publication_approved"])

    def test_external_publication_authority_cannot_be_claimed_from_a_clean_scan(self):
        r=gate.audit_public_bundle({"foo.html":"A page about evidence quality."},
                                  require_examples=False)
        self.assertEqual(r["registered_source_and_claim_cases"],16)
        self.assertFalse(r["legal_or_external_marketing_publication_approved"])
        self.assertEqual(r["independent_real_customer_pilot_approvals_verified"],0)
        self.assertEqual(r["independent_real_customer_pilot_requirements_unmet"],18)

    def test_hostile_policy_file_or_missing_policy_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            bad=Path(root)/"policy.json"
            bad.write_text('{"external_claims_approved": 18}')
            with patch.object(gate,"CLAIM_POLICY",bad):
                with self.assertRaisesRegex(ValueError,
                                            "PUBLIC_CLAIM_GATE_POLICY_BLOB_CHANGED"):
                    gate.audit_public_bundle({"index.html":"RETALLY"},
                                             require_examples=False)

    def test_input_rejects_binary_content_or_unexpected_types(self):
        for value in (b"RETALLY",None,42,{},[]):
            with self.assertRaises(ValueError):
                gate.audit_public_bundle({"foo.html":value},require_examples=False)

    def test_complete_output_checks_include_generated_demo_link_in_home(self):
        with tempfile.TemporaryDirectory() as root:
            out=builder.build(Path(root)/"export","sales@freightfixture.com",True)
            home=(out/"index.html").read_text()
            self.assertIn("Fictional data only",home)
            self.assertIn("not a customer result or recovery claim",home)
            self.assertIn('href="synthetic-pilot-demo.zip"',home)
            self.assertIn('value="100000"',home)

    def test_claim_gate_does_not_emit_sensitive_private_copy_in_errors(self):
        with self.assertRaises(ValueError) as err:
            gate.audit_public_bundle({"service.html":"RETALLY recovered $4,000 for Jane Roe."},
                                     require_examples=False)
        self.assertIn("UNVERIFIED_OWN_RECOVERED_MONEY",str(err.exception))
        self.assertNotIn("Jane Roe",str(err.exception))
        self.assertNotIn("4,000",str(err.exception))


if __name__=="__main__":
    unittest.main()
