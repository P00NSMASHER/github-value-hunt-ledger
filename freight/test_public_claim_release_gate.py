"""Mission 36: adversarial public copy release boundary.

These tests are a deterministic high-risk pattern guard, NOT an AI review or
legal signoff. The site copy check is effective only in the repository-owned
GitHub Pages build; no live external website or social accounts are changed.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

from freight import public_claim_release_gate as gate

BASELINE={
    "index.html":('<html><head><meta name="description" content="$0-upfront '
                  'freight audit, followed by separately authorized recovery '
                  'work tied to eligible funds actually recovered."></head>'
                  '<body><main><h1>Find it. Prove it. Recover it.</h1>'
                  '<p>Fictional data only. This is a demonstration, not a '
                  'customer recovery result or invoice accuracy claim.</p>'
                  '<p>If eligible funds are actually recovered, a contractual '
                  'contingency fee may be charged.</p></main></body></html>'),
    "llms.txt":('RETALLY reviews potential freight billing discrepancies. '
                'Recovery is not guaranteed. No real invoices are accepted '
                'before independently approved secure customer onboarding.'),
    "commercial-config.js":('const contingencyRate = "0.30"; '
                            'const note = "Fees are charged only on eligible '
                            'funds actually recovered.";\n'),
}


def codes(data:dict[str,str])->set[str]:
    return {r.rule for r in gate.scan_public_copy(data)}


class PublicClaimReleaseGateM36Tests(unittest.TestCase):
    def test_healthy_descriptions_and_conditional_contingency_fees_pass(self):
        self.assertEqual(codes(BASELINE),set())
        gate.require_public_copy_clearance(BASELINE)

    def test_negative_statement_recovery_not_guaranteed_is_allowed(self):
        self.assertEqual(codes({"page.html":
            "<p>Recovery is not guaranteed; estimates are not money recovered.</p>"
        }),set())

    def test_fictional_sample_invoice_numbers_without_true_outcome_claims_pass(self):
        self.assertEqual(codes({"sample.html":
            "<p>Fictional Northstar Industrial Supply invoice $1,167.60; "
            "hypothetical carrier credit $230 after a made-up comparison.</p>"
        }),set())

    def test_claimed_real_customer_dollar_recoveries_rejected(self):
        for sentence in (
            "RETALLY has recovered $5,000 for clients.",
            "We have recovered over $120,000 in freight overcharges.",
            "Our team successfully recovered $85,000 for customers.",
            "RETALLY refunded $2 million last year.",
            "We've audited 12,500 invoices.",
        ):
            with self.subTest(sentence=sentence):
                self.assertIn("CLAIMED_CUSTOMER_RECOVERIES",
                    codes({"page.html":"<h1>"+sentence+"</h1>"}))

    def test_single_real_customer_success_claim_rejected(self):
        sentence="Successfully recovered $18,500 for a real customer"
        self.assertIn("CLAIMED_REAL_CUSTOMER_RESULT",
                      codes({"page.html":"<p>"+sentence+"</p>"}))

    def test_we_have_recovered_across_html_markup_is_detected(self):
        html="<p>RETALLY has <strong>recovered</strong> $12,500 for clients</p>"
        self.assertIn("CLAIMED_CUSTOMER_RECOVERIES",
                      codes({"page.html":html}))

    def test_user_claimed_customer_success_rates_are_blocked(self):
        for sentence in (
            "Our success rate is 95% across all audits.",
            "RETALLY's accuracy rate is 99%.",
            "We achieved 98% accuracy in real-world freight audits.",
            "Our verified 90% recovery results prove real performance.",
        ):
            with self.subTest(sentence=sentence):
                got=codes({"site.html":"<p>"+sentence+"</p>"})
                self.assertTrue(got & {
                    "UNVERIFIED_AUDIT_RATE","UNVERIFIED_AUDIT_ACCURACY"
                },sentence)

    def test_unbacked_guaranteed_refunds_or_savings_are_blocked(self):
        for sentence in (
            "Guaranteed refunds for freight audit clients.",
            "We guarantee 100% savings.",
            "RETALLY promises recovery of freight charges.",
        ):
            with self.subTest(sentence=sentence):
                self.assertIn("GUARANTEED_CUSTOMER_OUTCOMES",
                              codes({"site.html":"<p>"+sentence+"</p>"}))

    def test_fake_serviceable_market_claims_blocked(self):
        for sentence in (
            "Our recoverable freight audit market is $5 billion.",
            "The serviceable audit TAM is $9,000,000.",
            "Our addressable freight audit opportunity is $45 million.",
        ):
            with self.subTest(sentence=sentence):
                self.assertIn("FABRICATED_RECOVERABLE_TAM",
                              codes({"site.html":"<p>"+sentence+"</p>"}))

    def test_bea_census_denominator_gap_laundered_as_recovery_blocked(self):
        for sentence in (
            "The $142.608 billion recoverable freight market is ours.",
            "Recoverable overcharges total $142,607.754 million.",
            "We can audit the $142.608B refund opportunity.",
        ):
            got=codes({"site.html":"<p>"+sentence+"</p>"})
            self.assertTrue("PUBLISHED_M34_GAP_AS_RECOVERY" in got
                            or "FABRICATED_RECOVERABLE_TAM" in got)

    def test_hidden_comment_not_counted_as_visible_marketing(self):
        html="<html><body><!-- RETALLY has recovered $100,000 for clients. -->"\
             "<p>Potential claims require customer evidence.</p></body></html>"
        self.assertEqual(codes({"index.html":html}),set())

    def test_html_meta_description_triggers_guard(self):
        html='<meta name="description" content="RETALLY has recovered $100,000 for clients.">'
        hit=gate.scan_public_copy({"index.html":html})
        self.assertTrue(any(x.rule=="CLAIMED_CUSTOMER_RECOVERIES"
                            and x.channel=="metadata" for x in hit))

    def test_open_graph_social_metadata_triggers_guard(self):
        html='<meta property="og:description" content="Guaranteed recovery for every customer.">'
        got=gate.scan_public_copy({"index.html":html})
        self.assertTrue(any(x.channel=="metadata" and
                            x.rule=="GUARANTEED_CUSTOMER_OUTCOMES" for x in got))

    def test_twitter_social_metadata_triggers_guard(self):
        html='<meta name="twitter:description" content="RETALLY has recovered $120,000 for clients.">'
        got=gate.scan_public_copy({"index.html":html})
        self.assertTrue(any(x.channel=="metadata"
                            and x.rule=="CLAIMED_CUSTOMER_RECOVERIES" for x in got))

    def test_jsonld_semantic_description_triggers_guard(self):
        html=('<html><script type="application/ld+json">'
              '{"@type":"Service","name":"RETALLY",'
              '"description":"RETALLY has recovered $250000 for clients"}'
              '</script><p>Authorized recovery is conditional.</p></html>')
        got=gate.scan_public_copy({"index.html":html})
        self.assertTrue(any(x.channel=="jsonld"
                            and x.rule=="CLAIMED_CUSTOMER_RECOVERIES" for x in got))

    def test_nested_jsonld_graph_descriptions_are_scanned(self):
        html=('<script type="application/ld+json">'
              '{"@graph":[{"@type":"Organization","name":"RETALLY"},'
              '{"@type":"Service","description":"Our accuracy rate is 98%"}]}'
              '</script>')
        got=gate.scan_public_copy({"index.html":html})
        self.assertTrue(any(x.channel=="jsonld"
                            and x.rule=="UNVERIFIED_AUDIT_RATE" for x in got))

    def test_invalid_jsonld_fails_before_publication(self):
        with self.assertRaisesRegex(ValueError,"PUBLIC_CLAIM_GATE_JSONLD_INVALID"):
            gate.scan_public_copy({"index.html":
                '<script type="application/ld+json">{bad}</script>'
            })

    def test_scripts_code_alone_is_not_treated_as_visible_html(self):
        html=('<html><body><script>const fictionalDebug="RETALLY has '
              'recovered $1,000,000 for customers";</script>'
              '<p>Free audit, no guarantees.</p></body></html>')
        self.assertEqual(codes({"index.html":html}),set())

    def test_static_javascript_string_content_is_scanned(self):
        js='const headline = "RETALLY has recovered $2 million for clients";'
        self.assertIn("CLAIMED_CUSTOMER_RECOVERIES",
                      codes({"site.js":js}))

    def test_llms_txt_and_public_csv_copy_are_scanned(self):
        self.assertIn("CLAIMED_CUSTOMER_RECOVERIES",
                      codes({"llms.txt":"RETALLY has recovered $1 million for clients."}))
        self.assertIn("UNVERIFIED_AUDIT_RATE",
                      codes({"provider.csv":"name,claim\nRETALLY,Our recovery rate is 95%"}))

    def test_css_generated_content_is_scanned(self):
        self.assertIn("CLAIMED_CUSTOMER_RECOVERIES",
                      codes({"site.css":'.badge::after {content:"RETALLY has recovered $2 million for clients";}'}))

    def test_unrelated_lines_are_not_spliced_into_fabricated_claims(self):
        self.assertEqual(codes({"copy.txt":
            "RETALLY is a freight audit company.\n"
            "$500,000 is an illustrative annual budget.\n"
            "Recovered funds require independent original evidence.\n"
        }),set())

    def test_untrusted_asset_paths_and_text_types_rejected(self):
        for value in (
            {"../outside.txt":"RETALLY service copy"},
            {"/etc/passwd":"content"},
            {"index.html":None},
            ["not a mapping"],
        ):
            with self.assertRaisesRegex(ValueError,
                                        "PUBLIC_CLAIM_GATE_INVALID_ASSET_PATH_OR_COPY|PUBLIC_CLAIM_GATE_ASSET_MAP_REQUIRED"):
                gate.scan_public_copy(value)

    def test_nonpublic_assets_are_not_marketing_copy(self):
        self.assertEqual(codes({"assets/image.webp":"RETALLY has recovered $10 million",
                                "assets/fonts/foo.woff2":"RETALLY has recovered $10 million"}),set())

    def test_policy_requires_M35_frozen_source_claim_register(self):
        gate._check_authority()
        with patch.object(gate.m35,"validate_policy",return_value=["forged publication authority"]):
            with self.assertRaisesRegex(ValueError,"PUBLIC_CLAIM_GATE_M35_SOURCE_POLICY_INVALID"):
                gate.require_public_copy_clearance(BASELINE)

    def test_forged_real_customer_pilot_human_signoff_blocks_even_safe_copy(self):
        from freight import research_pilot_preflight
        real=research_pilot_preflight.build_preflight(as_of=date(2026,10,12))
        fake=deepcopy(real)
        fake["unmet_requirements"]=17
        fake["controls_with_independently_verified_external_evidence"]=1
        with patch.object(research_pilot_preflight,"build_preflight",return_value=fake):
            with self.assertRaisesRegex(ValueError,"PUBLIC_CLAIM_GATE_HUMAN_APPROVAL_SOURCE_CHANGED"):
                gate.require_public_copy_clearance(BASELINE)

    def test_forged_M35_research_claim_approval_blocks_build(self):
        original=gate.m35._policy
        modified=deepcopy(original())
        modified["external_claims_approved"]=1
        with patch.object(gate.m35,"_policy",return_value=modified):
            with self.assertRaisesRegex(ValueError,"PUBLIC_CLAIM_GATE_M35_SOURCE_POLICY_INVALID|PUBLIC_CLAIM_GATE_FALSE_APPROVAL"):
                gate.require_public_copy_clearance(BASELINE)

    def test_release_boundary_fails_without_creating_a_source_approved_claim(self):
        copy={"index.html":"<h1>Our recovery rate is 99%.</h1>"}
        with self.assertRaisesRegex(ValueError,
                                    "PUBLIC_CLAIM_GATE_UNSUPPORTED_ASSERTION"):
            gate.require_public_copy_clearance(copy)

    def test_rule_results_are_typed_and_include_file_and_channel(self):
        v=gate.scan_public_copy({"index.html":"<p>Our recovery rate is 97%</p>"})[0]
        self.assertEqual(v.file,"index.html")
        self.assertEqual(v.channel,"visible")
        self.assertIn(v.rule,{"UNVERIFIED_AUDIT_RATE","UNVERIFIED_AUDIT_ACCURACY"})
        self.assertIn("97%",v.excerpt)

    def test_html_title_and_alt_aria_labels_cannot_hide_unsupported_copy(self):
        cases={
            "title":"<title>RETALLY has recovered $5 million for clients</title>",
            "alt":'<img alt="RETALLY has recovered $5 million for clients" src="asset.png">',
            "aria":'<a aria-label="RETALLY has recovered $5 million for clients">Visit</a>',
        }
        for label,html in cases.items():
            with self.subTest(label=label):
                self.assertIn("CLAIMED_CUSTOMER_RECOVERIES",
                              codes({"index.html":html}))

    def test_existing_fictional_illustrations_and_no_fee_disclaimers_not_blocked(self):
        html=('<p>Northstar Industrial Supply, fictional carrier Blue River Freight, '
              'invoice $1,167.60, expected $1,042.60.</p>'
              '<p>No recovery, no recovery fee. A contingency fee applies '
              'only to eligible funds actually recovered.</p>')
        self.assertEqual(codes({"sample.html":html}),set())


if __name__=="__main__":
    unittest.main()
