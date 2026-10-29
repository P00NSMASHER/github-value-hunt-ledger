"""Offline, project-specific stop-signal for obsolete municipal procurement leads.

This is a manually pinned public-source receipt, NOT a crawler, court docket
verifier, legal determination, or positive procurement/financial signal.
"""
from datetime import date
import re

PORT_CLINTON_PROJECT = 'port_clinton_1999_cso_ltcp'
PINNED_RECEIPTS = {
    'epa_port_clinton_completion_2026_06_01': {
        'project_id': PORT_CLINTON_PROJECT,
        'source_kind': 'epa_newsrelease',
        'source_url': 'https://www.epa.gov/newsreleases/epa-and-ohio-epa-terminate-settlement-after-port-clinton-ohio-completed-required',
        'published_on': '2026-06-01',
        'reported_state': 'agency_reports_required_work_complete_and_agreed_termination',
    }
}


def _iso(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def screen(project_id, as_of, events):
    """Return (PAUSE_PRE_RFP|REVIEW, reason), never an affirmative lead.

    The manually inspected EPA receipt only suppresses *the identified original*
    consent-decree construction lead. It cannot establish a court dismissal,
    disprove new projects or authenticate live website contents.
    """
    as_date = _iso(as_of)
    if (not isinstance(project_id, str) or not project_id.strip() or
            not as_date or not isinstance(events, list)):
        return 'REVIEW', 'bad_input'
    matched = []
    for event in events:
        if not isinstance(event, dict):
            return 'REVIEW', 'malformed_event'
        if event.get('project_id') != project_id:
            continue
        observed = _iso(event.get('observed_on'))
        published = _iso(event.get('published_on'))
        if not observed or not published:
            return 'REVIEW', 'undated_project_event'
        if observed > as_date:
            continue  # Future knowledge must never alter historical backtests.
        if published > observed:
            return 'REVIEW', 'publication_after_observation'
        expected = PINNED_RECEIPTS.get(event.get('receipt_id'))
        if expected is None or any(event.get(k) != v for k, v in expected.items()):
            return 'REVIEW', 'unsupported_lifecycle_evidence'
        matched.append(event)
    if len(matched) > 1:
        return 'REVIEW', 'duplicate_or_conflicting_lifecycle_evidence'
    if matched:
        return 'PAUSE_PRE_RFP', 'agency_reports_original_required_work_complete'
    return 'REVIEW', 'no_verified_current_lifecycle_evidence'
