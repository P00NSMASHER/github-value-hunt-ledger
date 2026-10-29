"""Fail-closed, offline comparison of human-reviewed PA nursing-home licensing notices.

This intentionally does NOT scrape websites or infer ownership transfers.
Inputs are manually reviewed public-source snapshots. No patient or employee data.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

SOURCE_URL = 'https://sais.health.pa.gov/CommonPOC/Licensing/IPA-NCF/PublicReviewFacList.aspx'
REVIEW = 'INITIAL_PROVIDER_APPLICATION_REVIEW'
DECISION = 'INITIAL_OR_CHOW_DECISION'
ALLOWED_STATUS = {REVIEW: {'PENDING_REVIEW'}, DECISION: {'APPROVED', 'DENIED'}}
REQUIRED = ('name', 'address', 'county', 'posted', 'category', 'status')


class SnapshotError(ValueError):
    """Untrustworthy or internally inconsistent observations."""


def _norm(value: str) -> str:
    return re.sub(r'\s+', ' ', value.strip()).casefold()


def _valid_date(value: str) -> str:
    if not isinstance(value, str):
        raise SnapshotError('Date must be ISO-8601 string')
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise SnapshotError(f'Invalid date: {value!r}') from exc


def validate(snapshot: dict) -> dict:
    """Validate a reviewer-attested snapshot and return keyed, normalized rows.

    Never infer precise license status or CHOW from a mixed-category board.
    """
    if not isinstance(snapshot, dict):
        raise SnapshotError('Snapshot must be a JSON object')
    if snapshot.get('source_url') != SOURCE_URL:
        raise SnapshotError('Source must be exact PA government public-review URL')
    observed_on = _valid_date(snapshot.get('observed_on'))
    if not isinstance(snapshot.get('rows'), list):
        raise SnapshotError('rows must be a list')
    records = {}
    for i, row in enumerate(snapshot['rows']):
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip() for k in REQUIRED):
            raise SnapshotError(f'Row {i} missing required nonempty strings')
        if row['category'] not in ALLOWED_STATUS or row['status'] not in ALLOWED_STATUS[row['category']]:
            raise SnapshotError(f'Row {i} illegal category/status combination')
        posted = _valid_date(row['posted'])
        if posted > observed_on:
            raise SnapshotError(f'Row {i} posted after observation date')
        # The source page contains mixed initial-or-CHOW decision records; never infer CHOW.
        if row.get('chow_verified') is not None:
            raise SnapshotError('CHOW verification cannot be asserted by this portal alone')
        key = '|'.join((_norm(row['name']), _norm(row['address']), _norm(row['county']), row['category']))
        if key in records:
            raise SnapshotError(f'Duplicate source identity at row {i}')
        records[key] = dict(row, posted=posted)
    return records


def diff_snapshots(previous: dict, current: dict) -> dict:
    if _valid_date(previous.get('observed_on')) >= _valid_date(current.get('observed_on')):
        raise SnapshotError('Newer snapshot must have a later observation date')
    old, new = validate(previous), validate(current)
    events = []
    for key in sorted(set(old) | set(new)):
        if key not in old:
            events.append({'type': 'ADDED', 'record': new[key], 'chow_claim': 'UNVERIFIED'})
        elif key not in new:
            events.append({'type': 'NOT_ON_CURRENT_PAGE', 'record': old[key], 'chow_claim': 'UNVERIFIED'})
        elif new[key] != old[key]:
            events.append({'type': 'CHANGED', 'record': new[key], 'previous': old[key], 'chow_claim': 'UNVERIFIED'})
    return {'previous_observed_on': previous['observed_on'],
            'current_observed_on': current['observed_on'],
            'changes': events,
            'confirmed_chow_count': 0,
            'warning': 'Absence from a current listing is not a denial, closure, or ownership transfer. All CHOW statuses are unverified.'}


def summarize(snapshot: dict) -> dict:
    rows = list(validate(snapshot).values())
    return {'observed_on': snapshot['observed_on'], 'source_url': SOURCE_URL,
            'total_public_rows': len(rows),
            'initial_application_reviews': sum(r['category'] == REVIEW for r in rows),
            'ambiguous_initial_or_chow_decisions': sum(r['category'] == DECISION for r in rows),
            'confirmed_pending_chow': 0,
            'confirmed_completed_chow': 0,
            'note': 'Cannot infer CHOW from the mixed decision list. Not a complete census of license actions.'}


def main() -> None:
    p = argparse.ArgumentParser(description='Offline, fail-closed PA licensure notice checker')
    p.add_argument('current', type=Path)
    p.add_argument('--previous', type=Path)
    args = p.parse_args()
    current = json.loads(args.current.read_text(encoding='utf-8'))
    result = diff_snapshots(json.loads(args.previous.read_text(encoding='utf-8')), current) if args.previous else summarize(current)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
