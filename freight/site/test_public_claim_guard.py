"""RETALLY / RecoveryOS Mission 36 website publication claim gate.

Tests realistic visible copy and SEO/JSON-LD/JS channels, including the
actual existing public pages. No customer data, production deployment,
contact action, credentials, payments or scheduled tasks.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight.site import public_claim_guard as gate
from freight.site import build as freight_build
from freight.site import cloudflare_build
from recoveryworks.site import build as recovery_build


FREIGHT_ROOT=Path(__file__).resolve().parent
RECOVERY_ROOT=FREIGHT_ROOT.parent.parent/"recoveryworks"/"site"


def actual_source(site="RETALLY"):
    if site=="RETALLY":
        root=FREIGHT_ROOT
        names=freight_build.TEXT_SOURCE_FILES
    else:
        root=RECOVERY_ROOT
        names=recovery_build.TEXT_FILES
    return {
        name:(root/name).read_text(encoding="utf-8")
        for name in names
        if "/" not in name and Path(name).suffix.lower() in gate.TEXT_EXTENSIONS
    }


class PublicClaimPublicationGateTests(unittest.TestCase):
    def test_actual_retally_pages_all_pass_as_currently_written(self):
        report=gate.validate_public_text_bundle(actual_source(),site="RETALLY")
        self.assertGreaterEqual(report["text_assets_checked"],27)
        self.assertEqual(report["unsupported_real_customer_claims_detected"],0)
        self.assertEqual(report["required_fictional_disclosures_checked"],10)
        self.assertFalse(report["external_publication_authority_granted"])

    def test_actual_recoveryos_public_landing_page_passes(self):
        report=gate.validate_public_text_bundle(
            actual_source("RECOVERYOS"),site="RECOVERYOS"
        )
        self.assertEqual(report["required_fictional_disclosures_checked"],1)
        self.assertEqual(report["unsupported_real_customer_claims_detected"],0)
        self.assertFalse(report["human_marketing_legal_review_replaced"])

    def test_mainline_public_rule_categories_require_all_nine_unsafe_classes(self):
        self.assertEqual(len(gate.UNSUPPORTED),9)
        self.assertEqual({x[0] for x in gate.UNSUPPORTED},gate.REQUIRED_RULE_NAMES)
        gate._frozen_policy()

    def test_missing_required_public_block_rule_fails_closed(self):
        with patch.object(gate,"UNSUPPORTED",gate.UNSUPPORTED[:-1]):
            with self.assertRaisesRegex(gate.PublicClaimViolation,
                                        "M36_STATIC_PUBLIC_CLAIM_POLICY_INCOMPLETE"):
                gate.validate_public_text_bundle(actual_source(),site="RETALLY")

    def test_unsupported_site_or_missing_index_cannot_pass(self):
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M36_PUBLIC_INDEX_MISSING"):
            gate.validate_public_text_bundle({},site="RETALLY")
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M36_UNKNOWN_OR_MISSING_PUBLICATION_SURFACE"):
            gate.validate_public_text_bundle(actual_source(),site="FAKE")
        with self.assertRaisesRegex(gate.PublicClaimViolation,"M36_PUBLIC_INDEX_MISSING"):
            gate.validate_public_text_bundle({"terms.html":"Hello"},site="RETALLY")

    def test_existing_zero_upfront_actual_recovery_pricing_is_allowed(self):
        r=actual_source()
        r["index.html"]+=(
            '<p>Our $0-upfront audit is available; a separately authorized '
            'contingency fee applies only to eligible funds actually recovered. '
            'No recovery means no recovery fee. Recovery is not guaranteed.</p>'
        )
        gate.validate_public_text_bundle(r,site="RETALLY")

    def test_existing_illustrative_dollar_calculator_is_permitted_when_labeled(self):
        r=actual_source()
        self.assertIn('$100,000',r["index.html"])
        gate.validate_public_text_bundle(r,site="RETALLY")

    def test_fictional_sample_report_must_retain_its_labels(self):
        original=actual_source()
        for filename,phrase in (
            ("index.html","Sample data"),
            ("index.html","Illustrative only. Not customer results."),
            ("index.html","Illustration only; signed engagement terms govern."),
            ("recovery-status-example.html","This report uses sample data only."),
            ("freight-audit-example.html","This scenario uses sample data only."),
        ):
            r=deepcopy(original)
            self.assertIn(phrase,r[filename])
            r[filename]=r[filename].replace(phrase,"")
            with self.subTest(filename=filename,phrase=phrase):
                with self.assertRaisesRegex(gate.PublicClaimViolation,
                                            "M36_FICTIONAL_SAMPLE_OR_FEE_ILLUSTRATION"):
                    gate.validate_public_text_bundle(r,site="RETALLY")

    def test_recoveryos_fictional_finding_cannot_lose_its_disclosure(self):
        r=actual_source("RECOVERYOS")
        r["index.html"]=r["index.html"].replace(
            "Illustrative data. A finding is not recovered cash.",""
        )
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M36_FICTIONAL_SAMPLE_OR_FEE_ILLUSTRATION"):
            gate.validate_public_text_bundle(r,site="RECOVERYOS")

    def test_fictional_demo_page_removed_causes_build_failure(self):
        r=actual_source()
        del r["recovery-status-example.html"]
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M36_REQUIRED_SYNTHETIC_EXAMPLE_PAGE_MISSING"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_high_confidence_fabricated_customer_cash_recovery_fails(self):
        for claim in (
            "RETALLY has recovered $250,000 for customers.",
            "RecoveryOS has already recovered $10,500 for businesses.",
            "Our team has successfully refunded $20,000 to clients.",
            "We have recovered $30,000 from carrier overcharges.",
        ):
            r=actual_source()
            r["index.html"]+="<h2>"+claim+"</h2>"
            with self.subTest(claim=claim):
                with self.assertRaisesRegex(gate.PublicClaimViolation,
                                            "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES"):
                    gate.validate_public_text_bundle(r,site="RETALLY")

    def test_contracted_weve_and_simple_past_marketing_recovery_claims_fail(self):
        for phrase in (
            "We've recovered $1,250,000 for customers.",
            "RETALLY recovered $250,000 for shippers.",
            "RecoveryOS refunded $10,200 for clients.",
        ):
            r=actual_source()
            r["index.html"]+="<h2>"+phrase+"</h2>"
            with self.subTest(phrase=phrase):
                with self.assertRaisesRegex(gate.PublicClaimViolation,
                                            "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES"):
                    gate.validate_public_text_bundle(r,site="RETALLY")

    def test_unverified_customer_invoice_volume_claims_fail(self):
        for claim in (
            "We have audited 12,000 real customer invoices.",
            "RETALLY has processed over 50,000 freight bills.",
            "RecoveryOS has reviewed 25 customer invoices.",
        ):
            r=actual_source("RECOVERYOS")
            r["index.html"]+="<p>"+claim+"</p>"
            with self.subTest(claim=claim):
                with self.assertRaisesRegex(gate.PublicClaimViolation,
                                            "M35-15_UNVERIFIED_PAID_INVOICE_COHORT"):
                    gate.validate_public_text_bundle(r,site="RECOVERYOS")

    def test_weve_audited_claim_is_not_allowed(self):
        r=actual_source()
        r["index.html"]+="<p>We've audited 12,000 customer invoices.</p>"
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M35-15_UNVERIFIED_PAID_INVOICE_COHORT"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_unsupported_macro_market_size_tam_fails(self):
        for phrase in (
            "Recoverable freight audit market $142.608 billion",
            "Freight recovery TAM is $142.607 billion",
        ):
            r=actual_source()
            r["index.html"]+="<div>"+phrase+"</div>"
            with self.subTest(phrase=phrase):
                with self.assertRaisesRegex(gate.PublicClaimViolation,
                                            "M35-09_UNVERIFIED_RECOVERABLE_MARKET"):
                    gate.validate_public_text_bundle(r,site="RETALLY")

    def test_bea_census_gap_misrepresented_as_unpaid_freight_fails(self):
        r=actual_source()
        r["index.html"]+=(
            '<p>$142.608 billion in unpaid freight invoices is recoverable.</p>'
        )
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M35-09_BEACENSUS_DENOMINATOR_MISTAKEN"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_fabricated_accuracy_and_unverified_invoice_error_rate_fails(self):
        for phrase in (
            "90% audit accuracy",
            "73.85% invoice accuracy",
            "100% recovery success rate",
            "Our audit accuracy is 99%",
        ):
            r=actual_source()
            r["index.html"]+="<p>"+phrase+"</p>"
            with self.subTest(phrase=phrase):
                with self.assertRaisesRegex(gate.PublicClaimViolation,"M35-10_"):
                    gate.validate_public_text_bundle(r,site="RETALLY")

    def test_unverified_promotional_accuracy_claim_fails(self):
        for phrase in ("RETALLY is 99% accurate.", "Our audits are 95% accurate."):
            r=actual_source()
            r["index.html"]+="<p>"+phrase+"</p>"
            with self.subTest(phrase=phrase):
                with self.assertRaisesRegex(gate.PublicClaimViolation,
                                            "M35-10_UNVERIFIED_PROMOTIONAL_ACCURACY"):
                    gate.validate_public_text_bundle(r,site="RETALLY")

    def test_guaranteed_recoveries_and_refunds_rejected(self):
        for claim in (
            "Guaranteed freight refunds.",
            "All recoveries are guaranteed.",
            "100% recovery guarantee.",
        ):
            r=actual_source()
            r["index.html"]+="<h2>"+claim+"</h2>"
            with self.subTest(claim=claim):
                with self.assertRaisesRegex(gate.PublicClaimViolation,
                                            "M35-12_RECOVERY_GUARANTEE"):
                    gate.validate_public_text_bundle(r,site="RETALLY")

    def test_fake_average_customer_savings_percent_rejected(self):
        r=actual_source()
        r["index.html"]+="<p>Our customers save an average of 90%</p>"
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M35-14_UNVERIFIED_CUSTOMER"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_seo_description_and_open_graph_copy_are_checked(self):
        r=actual_source()
        r["index.html"]+=(
            '<meta name="description" content="RETALLY has recovered $250,000">'
        )
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES"):
            gate.validate_public_text_bundle(r,site="RETALLY")
        r=actual_source()
        r["index.html"]+=(
            '<meta property="og:description" content="RETALLY has recovered $250,000">'
        )
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_jsonld_structured_result_is_checked(self):
        r=actual_source()
        j={"@context":"https://schema.org","@type":"Organization",
           "description":"RETALLY has recovered $250,000 for customers."}
        r["index.html"]+=(
            '<script type="application/ld+json">'+json.dumps(j)+'</script>'
        )
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_inline_js_that_writes_claim_is_also_checked(self):
        r=actual_source()
        r["index.html"]+=(
            '<script>document.body.innerHTML += '
            '"RETALLY has recovered $250,000 for clients";</script>'
        )
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_browser_js_public_copy_is_checked(self):
        r=actual_source()
        r["site.js"]+='const claimMessage = "RETALLY has recovered $250,000";'
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_html_tags_cannot_split_the_claim_out_of_detection(self):
        r=actual_source()
        r["index.html"]+='<p>RETALLY has recovered <strong>$250,000</strong> for clients.</p>'
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_html_comments_do_not_become_public_claims(self):
        r=actual_source()
        r["index.html"]+="<!-- RETALLY has recovered $250,000 for clients -->"
        gate.validate_public_text_bundle(r,site="RETALLY")

    def test_untrusted_text_never_echoed_in_failure(self):
        r=actual_source()
        injected="RETALLY has recovered $999,999 from private-person@buyer.invalid"
        r["index.html"]+="<p>"+injected+"</p>"
        with self.assertRaises(gate.PublicClaimViolation) as e:
            gate.validate_public_text_bundle(r,site="RETALLY")
        self.assertNotIn("private-person",str(e.exception))
        self.assertNotIn("999,999",str(e.exception))

    def test_direct_file_symlinks_disallowed_from_artifact_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"index.html").write_text(
                actual_source("RECOVERYOS")["index.html"],encoding="utf-8"
            )
            (root/"copied.html").symlink_to(root/"index.html")
            with self.assertRaisesRegex(gate.PublicClaimViolation,
                                        "M36_PUBLIC_ASSET_SYMLINK_NOT_ALLOWED"):
                gate.validate_public_tree(root,site="RECOVERYOS")

    def test_oversize_or_nontext_public_claim_file_blocked(self):
        r=actual_source()
        r["site.js"]="x"*(gate.MAX_TEXT_BYTES+1)
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M36_TEXT_ASSET_MISSING_OR_OVER_MAXIMUM"):
            gate.validate_public_text_bundle(r,site="RETALLY")
        r=actual_source()
        r["site.js"]=b"wrong"
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M36_TEXT_ASSET_MISSING_OR_OVER_MAXIMUM"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_unknown_root_level_file_type_not_silent_approval(self):
        r=actual_source()
        r["private.sqlite"]="not a marketing page"
        with self.assertRaisesRegex(gate.PublicClaimViolation,
                                    "M36_UNREVIEWED_OR_NONPUBLIC_TEXT_ASSET"):
            gate.validate_public_text_bundle(r,site="RETALLY")

    def test_actual_builder_freight_output_is_scanned(self):
        with tempfile.TemporaryDirectory() as temp:
            out=freight_build.build(
                Path(temp)/"public","sales@freightfixture.com",True,"0.30"
            )
            proof=gate.validate_public_tree(out,site="RETALLY")
            self.assertEqual(proof["unsupported_real_customer_claims_detected"],0)
            self.assertGreater(proof["text_assets_checked"],25)

    def test_actual_builder_recoveryos_output_is_scanned(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/"recovery"
            with patch.dict("os.environ",{
                "RECOVERYOS_CONTACT_EMAIL":"owner@recovery.test",
                "RECOVERYOS_CONTACT_VERIFIED":"1",
            },clear=True):
                recovery_build.build(out)
            proof=gate.validate_public_tree(out,site="RECOVERYOS")
            self.assertEqual(proof["unsupported_real_customer_claims_detected"],0)

    def test_cloudflare_build_blocks_claim_injected_after_url_rebase(self):
        original_rebase=cloudflare_build.rebase
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            target=base/"cf-public"
            def inject_after_rebase(bundle):
                changed=original_rebase(bundle)
                home=bundle/"index.html"
                page=home.read_text(encoding="utf-8")
                home.write_text(
                    page.replace("</body>",
                                 "<p>RETALLY has recovered $250,000 for clients</p></body>"),
                    encoding="utf-8"
                )
                return changed
            with patch.object(cloudflare_build,"REPO",base):
                with patch.object(cloudflare_build,"rebase",side_effect=inject_after_rebase):
                    with patch.dict("os.environ",{
                        "FREIGHT_CONTACT_EMAIL":"jay@retallyrecovery.com",
                        "FREIGHT_CONTACT_VERIFIED":"1",
                    },clear=True):
                        with self.assertRaisesRegex(
                            gate.PublicClaimViolation,
                            "M35-12_UNVERIFIED_ACTUAL_CUSTOMER_RECOVERIES",
                        ):
                            cloudflare_build.build(target)
            self.assertFalse(target.exists())

    def test_real_freight_builder_blocks_modified_unverified_claim_before_any_writes(self):
        original=freight_build._public_source
        with tempfile.TemporaryDirectory() as tmp:
            temp=Path(tmp)
            changed=temp/"index.html"
            changed.write_text(
                (FREIGHT_ROOT/"index.html").read_text()
                + "<p>RETALLY has recovered $250,000 for customers</p>",
                encoding="utf-8"
            )
            def malicious(name):
                return changed if name=="index.html" else original(name)
            target=temp/"public"
            with patch.object(freight_build,"_public_source",side_effect=malicious):
                with self.assertRaisesRegex(gate.PublicClaimViolation,"M35-12_"):
                    freight_build.build(target,"sales@freightfixture.com",True,"0.30")
            self.assertFalse(target.exists())

    def test_real_recoveryos_builder_blocks_modified_claim_before_any_writes(self):
        original=recovery_build._safe_source
        with tempfile.TemporaryDirectory() as tmp:
            temp=Path(tmp)
            changed=temp/"index.html"
            changed.write_text(
                (RECOVERY_ROOT/"index.html").read_text()
                + "<p>RecoveryOS has recovered $250,000 for clients</p>",
                encoding="utf-8"
            )
            def malicious(name):
                return changed if name=="index.html" else original(name)
            target=temp/"public"
            with patch.object(recovery_build,"_safe_source",side_effect=malicious):
                with patch.dict("os.environ",{
                    "RECOVERYOS_CONTACT_EMAIL":"owner@recovery.test",
                    "RECOVERYOS_CONTACT_VERIFIED":"1",
                },clear=True):
                    with self.assertRaisesRegex(gate.PublicClaimViolation,"M35-12_"):
                        recovery_build.build(target)
            self.assertFalse(target.exists())



    def test_legacy_recoveryos_redirect_rejects_unapproved_claims_or_changes(self):
        from freight.site.group import build as group_routes
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"recoveryos"
            folder.mkdir()
            destination="https://recoveryworks.retallyrecovery.com/"
            original=group_routes._notice_page(
                "RETALLY RecoveryWorks",destination,"This page has moved",
                "Visit the dedicated website for this business's current scope, availability and terms.",
                destination,"Continue to RETALLY RecoveryWorks",
            )
            page=folder/"index.html"
            page.write_text(original,encoding="utf-8")
            safe=gate.validate_recoveryos_legacy_redirect(folder)
            self.assertFalse(safe["external_publication_authority_granted"])
            self.assertEqual(safe["text_assets_checked"],1)
            for modified in (
                original.replace('noindex,follow','index,follow'),
                original.replace(destination,'https://attacker.invalid/'),
                original+"<h2>RecoveryOS has recovered $250,000 for customers</h2>",
                original+"<form><input name='customer'></form>",
            ):
                page.write_text(modified,encoding="utf-8")
                with self.assertRaises(gate.PublicClaimViolation):
                    gate.validate_recoveryos_legacy_redirect(folder)
            page.unlink()
            with self.assertRaises(gate.PublicClaimViolation):
                gate.validate_recoveryos_legacy_redirect(folder)

if __name__=="__main__":
    unittest.main()
