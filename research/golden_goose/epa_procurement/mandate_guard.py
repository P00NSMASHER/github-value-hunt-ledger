"""Conservative, offline mandate-change risk screen. No sourcing or legal verification.

A dated public regulatory signal is not proof a procurement will occur. This
module finds evidence that should stop a sales lead from being called actionable,
especially when a later court *proposal* would replace its project scope.
It never returns an affirmative award, purchasable lead, or dollar value.
"""
from datetime import date
from urllib.parse import urlparse
import re

_FR_PATH = re.compile(r"/content/pkg/FR-\d{4}-\d{2}-\d{2}/html/\d{4}-\d+\.htm\Z")
_GOV_HOSTS = {"www.govinfo.gov", "govinfo.gov"}
_KINDS = {"proposed_replacement", "reported_final_replacement", "reported_completion", "reinstatement"}
_TERMINAL_BIDS = {"CLOSED", "AWARDED", "CANCELLED", "WITHDRAWN", "EXPIRED"}


def _iso(s):
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _official_receipt(event, project_id, as_of):
    """Only a syntactic provenance gate, never authentication of source text."""
    if not isinstance(event, dict) or event.get("project_id") != project_id:
        return False
    if event.get("source_kind") != "federal_register_notice":
        return False
    if event.get("kind") not in _KINDS:
        return False
    published, observed = _iso(event.get("published_on")), _iso(event.get("observed_on"))
    if not published or not observed or published > observed or observed > as_of:
        return False
    try:
        p = urlparse(event.get("source_url"))
        if p.scheme != "https" or p.hostname not in _GOV_HOSTS or p.username or p.password:
            return False
        if p.query or p.fragment or p.params or not _FR_PATH.fullmatch(p.path):
            return False
        # The claimed notice date must appear in the exact Federal Register package path.
        return f"/FR-{published.isoformat()}/" in p.path
    except (ValueError, TypeError):
        return False


def review(project_id, as_of, events, *, bid_status=None, bid_due=None):
    """Return (screen_status, reason). Unknown/no evidence is NOT a green lead.

    Events must be tied to the *same project*, not merely the same town or utility.
    Later-known evidence cannot leak backwards into a historical as_of replay.
    Human verification of the actual official page is a separate required gate.
    """
    as_date = _iso(as_of)
    if not isinstance(project_id, str) or not project_id.strip() or not as_date or not isinstance(events, list):
        return ("REVIEW", "bad_review_input")
    matched = []
    for event in events:
        if not isinstance(event, dict):
            return ("REVIEW", "malformed_event")
        if event.get("project_id") != project_id:
            continue
        observed = _iso(event.get("observed_on"))
        published = _iso(event.get("published_on"))
        if not observed or not published:
            return ("REVIEW", "undated_project_event")
        if observed > as_date:
            continue  # Proper out-of-time evaluation; never use knowledge from the future.
        if not _official_receipt(event, project_id, as_date):
            return ("REVIEW", "unverified_project_change")
        matched.append(event)

    # Every later project change needs independent verification. The *presence*
    # of a credible pending change blocks confident future-spend assertions.
    if matched:
        newest_date = max(_iso(x["published_on"]) for x in matched)
        newest = [x for x in matched if _iso(x["published_on"]) == newest_date]
        if len({x["kind"] for x in newest}) > 1:
            return ("REVIEW", "conflicting_project_changes")
        latest_kind = newest[0]["kind"]
        if latest_kind == "proposed_replacement":
            return ("REVIEW", "pending_scope_replacement_not_court_final")
        if latest_kind == "reported_final_replacement":
            return ("REVIEW", "finality_must_be_verified_from_court_order")
        if latest_kind == "reported_completion":
            return ("REVIEW", "completion_must_be_independently_verified")
        return ("REVIEW", "reinstatement_requires_new_authority")

    if bid_status is not None:
        if not isinstance(bid_status, str) or bid_status not in (_TERMINAL_BIDS | {"OPEN", "UNKNOWN"}):
            return ("REVIEW", "bid_status_unknown")
        if bid_status in _TERMINAL_BIDS:
            return ("NOT_ACTIONABLE", "tender_not_open")
        if bid_status == "OPEN":
            due = _iso(bid_due)
            if not due:
                return ("REVIEW", "missing_issuer_verified_deadline")
            if due <= as_date:
                return ("NOT_ACTIONABLE", "bid_deadline_passed")
    return ("REVIEW", "no_complete_current_mandate_and_bid_authority")
