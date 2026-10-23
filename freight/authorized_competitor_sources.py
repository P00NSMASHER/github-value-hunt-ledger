"""Permission-scoped GitHub inventory for RETALLY competitor research.

Lists only repos already visible to the authenticated GitHub principal. This
never discovers hidden names, reads file contents, exports private paths, or
grants commercial reuse rights. Safe for the PUBLIC RETALLY repository.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

_API = "https://api.github.com/user/repos"
_OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_PER_PAGE = 100
_MAX_PAGES = 10
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class CatalogError(ValueError):
    """Expected lack of access, malformed API data, or incomplete pagination."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _normalize_owners(owners: Sequence[str]) -> tuple[str, ...]:
    if not owners:
        raise CatalogError("explicit competitor organization allowlist required")
    by_lower: dict[str, str] = {}
    for owner in owners:
        if not isinstance(owner, str) or not _OWNER.fullmatch(owner):
            raise CatalogError("invalid GitHub organization identifier")
        lower = owner.lower()
        if lower in by_lower:
            raise CatalogError("duplicate competitor organization identifier")
        by_lower[lower] = owner
    if len(by_lower) > 50:
        raise CatalogError("competitor organization allowlist exceeds 50")
    return tuple(by_lower.values())


def _fetch_visible_page(page: int, token: str) -> list[dict]:
    if not token:
        raise CatalogError("authorized GitHub token unavailable")
    query = urlencode({
        "visibility": "all", "affiliation": "owner,collaborator,organization_member",
        "per_page": _PER_PAGE, "page": page,
    })
    request = Request(
        _API + "?" + query,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RETALLY-private-visibility-inventory/1.0",
        },
    )
    try:
        with build_opener(_NoRedirect()).open(request, timeout=15) as response:
            if response.status != 200:
                raise CatalogError("GitHub authorized catalog unavailable")
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, OSError) as exc:
        # Never include HTTP response bodies, URLs or header/token values.
        raise CatalogError("GitHub authorization, catalog access or transport unavailable") from None
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise CatalogError("GitHub catalog response exceeded size limit")
    try:
        rows = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise CatalogError("GitHub catalog response was invalid JSON") from None
    if not isinstance(rows, list) or len(rows) > _PER_PAGE:
        raise CatalogError("GitHub catalog response violated page contract")
    return rows


def summarize_visible_repositories(rows: Iterable[Mapping], owners: Sequence[str]) -> dict:
    """Privacy-safe aggregate. Never serialize private repository names or paths."""
    labels = _normalize_owners(owners)
    counters = {
        owner.lower(): {
            "organization": owner,
            "visible_public": 0,
            "visible_private": 0,
            "visible_internal": 0,
            "restricted_read_permission_confirmed": 0,
            "restricted_read_permission_unverified": 0,
        }
        for owner in labels
    }
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise CatalogError("GitHub repository metadata was not an object")
        identity = row.get("full_name")
        owner_record = row.get("owner")
        if not isinstance(identity, str) or not isinstance(owner_record, Mapping):
            raise CatalogError("GitHub repository metadata missing identity")
        login = owner_record.get("login")
        if not isinstance(login, str) or not identity.lower().startswith(login.lower() + "/"):
            raise CatalogError("GitHub repository owner metadata disagrees with identity")
        if identity.lower() in seen:
            raise CatalogError("duplicate GitHub repository across catalog pages")
        seen.add(identity.lower())
        counter = counters.get(login.lower())
        if counter is None:
            continue
        visibility = row.get("visibility")
        private = row.get("private")
        if type(private) is not bool or visibility not in ("public", "private", "internal"):
            raise CatalogError("GitHub repository visibility metadata incomplete")
        if (visibility == "public" and private) or (visibility == "private" and not private):
            raise CatalogError("GitHub private/visibility metadata conflict")
        if visibility == "public":
            counter["visible_public"] += 1
        else:
            counter["visible_" + visibility] += 1
            permissions = row.get("permissions")
            if isinstance(permissions, Mapping) and permissions.get("pull") is True:
                counter["restricted_read_permission_confirmed"] += 1
            else:
                counter["restricted_read_permission_unverified"] += 1
    result = list(counters.values())
    for count in result:
        if count["restricted_read_permission_confirmed"]:
            state = "RESTRICTED_REPOSITORIES_VISIBLE_WITH_READ_ACCESS_REUSE_NOT_AUTHORIZED"
        elif count["visible_private"] or count["visible_internal"]:
            state = "RESTRICTED_METADATA_VISIBLE_READ_ACCESS_UNVERIFIED"
        else:
            state = "NO_RESTRICTED_REPOSITORIES_VISIBLE_NOT_PROOF_NONE_EXIST"
        count["restricted_source_status"] = state
    return {
        "schema_version": 1,
        "scope": "AUTHENTICATED_USER_VISIBLE_REPOSITORIES_ONLY",
        "visibility_limit": "Hidden company repositories and undisclosed names cannot be inferred",
        "reuse_rights": "READ_ACCESS_DOES_NOT_AUTHORIZE_SOURCE_REUSE_OR_COPYING",
        "source_code_exported": False,
        "private_repository_identifiers_exported": False,
        "organizations": result,
    }


def inventory_competitors(
    owners: Sequence[str], *, token: str = "",
    fetch_page: Callable[[int], list[dict]] | None = None,
    max_pages: int = _MAX_PAGES,
) -> dict:
    """Fetch bounded accessible metadata only. Stop rather than truncate results."""
    _normalize_owners(owners)
    if type(max_pages) is not int or not 1 <= max_pages <= _MAX_PAGES:
        raise CatalogError("invalid catalog pagination bound")
    if fetch_page is None:
        if not token:
            raise CatalogError("authorized GitHub token unavailable")
        fetch_page = lambda page: _fetch_visible_page(page, token)
    rows: list[dict] = []
    exhausted = False
    for page in range(1, max_pages + 1):
        response = fetch_page(page)
        if not isinstance(response, list) or len(response) > _PER_PAGE:
            raise CatalogError("GitHub catalog page invalid or oversized")
        rows.extend(response)
        if len(response) < _PER_PAGE:
            exhausted = True
            break
    if not exhausted:
        raise CatalogError("GitHub catalog pagination incomplete; no partial output published")
    return summarize_visible_repositories(rows, owners)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate accessible competitor GitHub visibility safely.")
    parser.add_argument("--owner", action="append", required=True,
                        help="Competitor GitHub organization login; repeat for each owner")
    args = parser.parse_args(argv)
    # OAuth/GitHub App access must be provided independently by its owner, then
    # made available only inside a protected execution environment.
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        report = inventory_competitors(args.owner, token=token)
    except CatalogError as exc:
        parser.exit(2, "Access-scoped inventory unavailable: " + str(exc) + "\n")
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
