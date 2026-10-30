"""Offline adversarial checks for the September 2026 FMC procedural evidence pack.

These tests validate a secondary authored digest and pinned public regulatory
facts, NOT an original publisher PDF hash or commercial freight-accuracy labels.
"""
import hashlib
import json
from pathlib import Path
import unittest

FIXTURE = Path(__file__).with_name('fixtures') / 'fmc_charge_complaint_procedural_v1.json'
EXPECTED_SOURCE = {
    'document_number': '2026-17876',
    'federal_register_citation': '91 FR 56053-56056',
    'official_landing_url': 'https://www.govinfo.gov/app/details/FR-2026-09-01/2026-17876',
    'official_document_url': 'https://www.govinfo.gov/content/pkg/FR-2026-09-01/pdf/2026-17876.pdf',
    'publication_date': '2026-09-01',
    'procedural_amendment_effective_date': '2026-09-01',
    'OSRA_2022_effective_date': '2022-06-16',
    'original_pdf_bytes_held': False,
    'original_pdf_sha256': None,
    'commercial_reuse_of_third_party_customer_records_verified': False,
}
EXPECTED_CONTROLS = {
    'charge_complaints_under_41310_cover_on_or_after': '2022-06-16',
    '41310_statute_of_limitations': 'NONE_STATED_FOR_CHARGE_COMPLAINTS',
    '41301_reparations_filing_limit': 'THREE_YEARS_AFTER_CLAIM_ACCRUES',
    'traditional_charge_complaint_required_identifiers': ['applicable_bill_of_lading_numbers', 'invoices'],
    'interim_and_traditional_tracks_simultaneous': False,
    'duplicative_claim_after_merits_decision_permitted': False,
    'small_claims_both_parties_consent_required': True,
    'small_claims_dollar_ceiling_cents': 5000000,
    'small_claims_without_both_consent': 'SUBPART_T_NOT_SUBPART_S',
    'civil_penalties_payable_to': 'US_TREASURY_NOT_CUSTOMER',
    'demurrage_detention_carrier_reasonableness_burden_in_charge_complaint': True,
    'burden_shift_is_general_proof_of_overcharge': False,
    'interim_process_fee_as_reported_2026_09_01_cents': 0,
    'interim_process_fee_future_is_known': False,
    'traditional_formal_fee_as_reported_2026_09_01_cents': 38700,
    'traditional_small_claims_fee_as_reported_2026_09_01_cents': 17600,
    'procedural_rule_changes_substantive_carrier_billing_standards': False,
}
EXPECTED_CASES = {
    'SYN_HOLDOUT_001': 'PROCESS_ELIGIBLE_FOR_REVIEW_NOT_MERITS_WIN',
    'SYN_NEG_002': 'NOT_IN_OSRA_2022_CHARGE_COMPLAINT_COHORT',
    'SYN_NEG_003': 'INSUFFICIENT_DOCUMENT_IDENTIFIERS_NOT_AUTOMATIC_VIOLATION',
    'SYN_NEG_004': 'PROHIBITED_CONCURRENT_TRACKS',
    'SYN_NEG_005': 'PROHIBITED_DUPLICATE_MERITS_CLAIM',
    'SYN_NEG_006': 'NO_AUTOMATIC_DEMURRAGE_BURDEN_SHIFT_OR_WIN',
    'SYN_NEG_007': '41301_THREE_YEAR_BAR_NOT_41310_CLOCK',
    'SYN_NEG_008': 'SUBPART_T_NOT_AUTOMATIC_SMALL_CLAIMS',
    'SYN_NEG_009': 'TREASURY_PENALTY_NOT_CUSTOMER_CASH_RECOVERY',
    'SYN_NEG_010': 'FUTURE_FEE_UNKNOWN_AS_OF_REVIEW',
}


def digest_without_authored_hash(data):
    payload = {k: v for k, v in data.items() if k != 'authored_fixture_sha256'}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def validate(data):
    if data['schema_version'] != '1.0.0':
        raise ValueError('SCHEMA_VERSION')
    if data['authored_fixture_sha256'] != digest_without_authored_hash(data):
        raise ValueError('AUTHOR_FIXTURE_TAMPER')
    if data['fixture_id'] != 'RETALLY_FMC_2026_17876_CHARGE_COMPLAINT_PROCESS_NEGATIVE_CONTROLS_V1':
        raise ValueError('FIXTURE_ID')
    if data['evaluation_lane'] != 'FREIGHT_PROCESS_TRIAGE_SEPARATE_FROM_FREIGHT_ERROR_ACCURACY_AND_ACCOUNTING_RECONCILIATION':
        raise ValueError('EVALUATION_LANE')
    if data['cohort'] != 'FMC_FEDERAL_REGISTER_2026_09_01':
        raise ValueError('COHORT')
    source = data['source']
    if any(source.get(k) != v for k, v in EXPECTED_SOURCE.items()):
        raise ValueError('OFFICIAL_SOURCE_OR_CUSTODY_MISLABELED')
    if source['review_date'] != '2026-10-30' or source['original_document_page_images_inspected'] != [56055, 56056]:
        raise ValueError('UNVERIFIED_SOURCE_REVIEW')
    if not source['rights'].startswith('U.S._federal_government_authored_rule_text_generally_public_domain_17_USC_105'):
        raise ValueError('RIGHTS_PROMOTION')
    if data['source_bound_procedural_controls'] != EXPECTED_CONTROLS:
        raise ValueError('PROCEDURAL_FACTS_UNSUPPORTED')
    cases = data['challenge_cases']
    if len(cases) != len(EXPECTED_CASES) or len({c['case_id'] for c in cases}) != len(cases):
        raise ValueError('CASE_POPULATION_OR_DUPLICATES')
    if {c['case_id']: c['expected'] for c in cases} != EXPECTED_CASES:
        raise ValueError('PROCEDURAL_CASE_LABEL_DRIFT')
    if any(c['synthetic'] is not True or c['held_out_from_engine_training'] is not True
           or c['independently_adjudicated_invoice_outcome'] != 'UNKNOWN'
           for c in cases):
        raise ValueError('SYNTHETIC_CASE_PROMOTED_TO_REAL_TRUTH')
    if data['case_label_authority'] != 'LAB_AUTHORED_SYNTHETIC_PROCEDURAL_CONTROLS_NOT_THIRD_PARTY_OUTCOMES':
        raise ValueError('AUTHORITY_MISREPRESENTED')
    if any(data[k] != v for k, v in {
        'source_content_sha256': None,
        'independently_labeled_real_freight_error_cases': 0,
        'independently_labeled_real_clean_invoice_cases': 0,
        'actual_freight_recovery_cash_cents': 0,
        'compliant_engine_or_release_authorized': False,
    }.items()):
        raise ValueError('ORIGINAL_SOURCE_OR_COMMERCIAL_TRUTH_PROMOTION')
    return {
        'original_procedural_publisher_reference_count': 1,
        'synthetic_frozen_process_controls': len(cases),
        'independent_real_freight_accuracy_labels': 0,
        'verified_retally_cash_cents': 0,
        'commercial_release_allowed': False,
    }


class FMC2026SourceBoundEvaluation(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def test_green_exact_source_bound_and_unknown_traps(self):
        self.assertEqual(validate(self.data)['synthetic_frozen_process_controls'], 10)

    def test_red_authored_hash_tamper(self):
        self.data['source_bound_procedural_controls']['41301_reparations_filing_limit'] = 'ONE_YEAR'
        with self.assertRaisesRegex(ValueError, 'AUTHOR_FIXTURE_TAMPER'):
            validate(self.data)

    def test_red_rehashed_wrong_three_year_vs_no_time_limit(self):
        self.data['source_bound_procedural_controls']['41310_statute_of_limitations'] = 'THREE_YEARS'
        self.data['authored_fixture_sha256'] = digest_without_authored_hash(self.data)
        with self.assertRaisesRegex(ValueError, 'PROCEDURAL_FACTS_UNSUPPORTED'):
            validate(self.data)

    def test_red_synthetic_holdout_falsely_promoted_real(self):
        self.data['challenge_cases'][0]['synthetic'] = False
        self.data['authored_fixture_sha256'] = digest_without_authored_hash(self.data)
        with self.assertRaisesRegex(ValueError, 'SYNTHETIC_CASE_PROMOTED_TO_REAL_TRUTH'):
            validate(self.data)

    def test_red_duplicate_case_and_wrong_control(self):
        self.data['challenge_cases'][-1]['case_id'] = self.data['challenge_cases'][0]['case_id']
        self.data['authored_fixture_sha256'] = digest_without_authored_hash(self.data)
        with self.assertRaisesRegex(ValueError, 'CASE_POPULATION_OR_DUPLICATES'):
            validate(self.data)

    def test_red_unacquired_original_pdf_hash_claim(self):
        self.data['source']['original_pdf_sha256'] = '0' * 64
        self.data['authored_fixture_sha256'] = digest_without_authored_hash(self.data)
        with self.assertRaisesRegex(ValueError, 'OFFICIAL_SOURCE_OR_CUSTODY_MISLABELED'):
            validate(self.data)

    def test_red_civil_penalty_counted_as_retally_cash(self):
        self.data['actual_freight_recovery_cash_cents'] = 10000
        self.data['authored_fixture_sha256'] = digest_without_authored_hash(self.data)
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_SOURCE_OR_COMMERCIAL_TRUTH_PROMOTION'):
            validate(self.data)


if __name__ == '__main__':
    unittest.main()
