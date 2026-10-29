"""Conservative offline CMS-versus-PA nursing-home notice coverage audit.

No website access, CHOW inference, personal data, or event-level matches.
The CMS catalogue update date is not the first-seen date of any CMS event.
"""
import argparse
import json
from datetime import date
from pathlib import Path

PA_SOURCE = 'https://sais.health.pa.gov/CommonPOC/Licensing/IPA-NCF/PublicReviewFacList.aspx'
CMS_SOURCE = 'https://catalog.data.gov/dataset/skilled-nursing-facility-change-of-ownership-2026-06-01'
CMS_DATASET_ID = 'f557a6ed-95b3-4a22-8433-4175db2dec1c'
REVIEW = 'INITIAL_PROVIDER_APPLICATION_REVIEW'
MIXED = 'INITIAL_OR_CHOW_DECISION'


class EvidenceError(ValueError):
    """Input/provenance insufficient for a timing or ownership assertion."""


def _day(value, field):
    if not isinstance(value, str) or len(value) != 10:
        raise EvidenceError(f'{field}: expected YYYY-MM-DD')
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceError(f'{field}: invalid date') from exc
    if parsed.isoformat() != value:
        raise EvidenceError(f'{field}: noncanonical date')
    return parsed


def audit(snapshot, metadata):
    """Conservative screen for whether a meaningful paired-event study is possible.

    The screen does NOT claim that no historical CMS event shares a facility.
    It only counts state posting dates relative to the catalogued CMS horizon.
    Without independent same-event linkage and *first observation* archives,
    matched-event count is zero and measured lead-time remains unknown.
    """
    if not isinstance(snapshot, dict) or snapshot.get('source_url') != PA_SOURCE:
        raise EvidenceError('Missing exact PA portal source')
    observed = _day(snapshot.get('observed_on'), 'observed_on')
    if not isinstance(metadata, dict) or metadata.get('source_url') != CMS_SOURCE:
        raise EvidenceError('Missing exact official CMS catalogue source')
    if metadata.get('dataset_id') != CMS_DATASET_ID:
        raise EvidenceError('Unexpected CMS dataset identity')
    coverage_end = _day(metadata.get('coverage_end'), 'coverage_end')
    updated = _day(metadata.get('catalog_last_updated_on'), 'catalog_last_updated_on')
    if coverage_end > updated:
        raise EvidenceError('CMS update cannot predate its stated quarter end')
    if not isinstance(snapshot.get('rows'), list):
        raise EvidenceError('Missing PA rows array')
    counts = {REVIEW: 0, MIXED: 0}
    after = before_or_on = 0
    seen = set()
    for i, row in enumerate(snapshot['rows']):
        if not isinstance(row, dict):
            raise EvidenceError(f'Row {i} must be an object')
        if row.get('category') not in counts:
            raise EvidenceError(f'Row {i}: unsupported category')
        if row['category'] == REVIEW and row.get('status') != 'PENDING_REVIEW':
            raise EvidenceError(f'Row {i}: invalid initial category/status')
        if row['category'] == MIXED and row.get('status') not in ('APPROVED', 'DENIED'):
            raise EvidenceError(f'Row {i}: invalid mixed category/status')
        if 'chow_verified' in row or 'matched_cms_event' in row:
            raise EvidenceError(f'Row {i}: unsupported ownership/match assertion')
        if not all(isinstance(row.get(k), str) and row[k].strip()
                   for k in ('name', 'address', 'county')):
            raise EvidenceError(f'Row {i}: missing facility identity')
        posted = _day(row.get('posted'), f'row[{i}].posted')
        if posted > observed:
            raise EvidenceError(f'Row {i}: future posting')
        key = tuple(' '.join(row[k].casefold().split())
                    for k in ('name', 'address', 'county')) + (row['category'],)
        if key in seen:
            raise EvidenceError(f'Row {i}: duplicate source identity')
        seen.add(key)
        counts[row['category']] += 1
        if posted > coverage_end:
            after += 1
        else:
            before_or_on += 1
    return {
        'pa_observed_on': observed.isoformat(),
        'cms_dataset_catalog_last_updated_on': updated.isoformat(),
        'cms_coverage_end': coverage_end.isoformat(),
        'pa_rows_observed': len(snapshot['rows']),
        'initial_review_count': counts[REVIEW],
        'mixed_initial_or_chow_decision_count': counts[MIXED],
        'pa_postings_after_cms_coverage_end': after,
        'pa_postings_on_or_before_cms_coverage_end': before_or_on,
        'independently_confirmed_chow_count': 0,
        'independently_confirmed_same_event_matches': 0,
        'measured_first_observation_lead_days': None,
        'claimable_revenue_usd': 0,
        'commercial_status': 'UNVALIDATED',
        'study_status': 'INSUFFICIENT_PAIRED_EVENT_EVIDENCE',
        'notes': [
            'PA mixed Initial-or-CHOW list is not a verified CHOW label.',
            'Coverage quarter-end is not an event-level match or timing advantage.',
            'CMS catalogue update date is NOT event first-publication time.',
            'Historical first-seen PA and CMS archives and independent same-event proof are absent.',
            'Unmeasured lead-time and precision remain null, not zero.'
        ]
    }


def main():
    p = argparse.ArgumentParser(description='Offline PA/CMS timing-evidence gate')
    p.add_argument('pa_snapshot', type=Path)
    p.add_argument('cms_metadata', type=Path)
    args = p.parse_args()
    pa = json.loads(args.pa_snapshot.read_text(encoding='utf-8'))
    cms = json.loads(args.cms_metadata.read_text(encoding='utf-8'))
    print(json.dumps(audit(pa, cms), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
