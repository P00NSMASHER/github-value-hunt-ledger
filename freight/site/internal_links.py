"""RETALLY first-party hyperlink checks for release bundles and live production.

Only inspect anchor destinations on the published host. No requests to third-
party sites, customer APIs, contact forms, or credentials are ever made.
"""
from __future__ import annotations

from html.parser import HTMLParser
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

CANONICAL = "https://www.retallyrecovery.com/"
HOSTS = frozenset({"www.retallyrecovery.com", "retallyrecovery.com"})
REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})

# The verified public sales inbox must not be rewritten into Cloudflare's
# /cdn-cgi/l/email-protection (a non-page returning HTTP 404).
_BUSINESS_MAILTO_ANCHOR = re.compile(
    r'<a\b[^>]*\bhref="mailto:jay@retallyrecovery\.com[^"]*"[^>]*>.*?</a>',
    re.IGNORECASE | re.DOTALL,
)


class InternalLinkError(AssertionError):
    """A published first-party hyperlink cannot reach a valid destination."""


class _Anchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            for key, value in attrs:
                if key.lower() == "href" and value is not None:
                    self.hrefs.append(value.strip())
                    break


def internal_destinations(html: str, source_url: str) -> set[str]:
    """Resolve anchors, omitting fragments and all third-party destinations."""
    parser = _Anchors()
    parser.feed(html)
    found = set()
    for href in parser.hrefs:
        if not href:
            continue
        url = urljoin(source_url, href)
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or parts.hostname not in HOSTS:
            continue
        if parts.username or parts.password or parts.port not in (None, 80, 443):
            raise InternalLinkError(f"Unsafe first-party hyperlink in {source_url}")
        found.add(urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, "")))
    return found


def _published_url(relative_html: Path) -> str:
    relative = relative_html.as_posix()
    if relative == "index.html":
        return CANONICAL
    if relative.endswith("/index.html"):
        return CANONICAL + relative[:-len("index.html")]
    return CANONICAL + relative[:-len(".html")]


def _candidate_files(root: Path, url_path: str) -> list[Path]:
    path = unquote(url_path)
    if "\\" in path or "\x00" in path or any(p in (".", "..") for p in path.split("/")):
        raise InternalLinkError(f"Unsafe first-party URL path: {url_path}")
    relative = path.lstrip("/")
    if not relative:
        return [root / "index.html"]
    file = root / relative
    if path.endswith("/"):
        return [file / "index.html"]
    if file.suffix:
        return [file]
    return [file, root / (relative + ".html"), file / "index.html"]


def validate_bundle_links(root: Path) -> dict[str, int]:
    """Fail before deployment when an anchor targets a non-published file/route.

    Cloudflare's extensionless HTML routes are backed by .html files.
    Deliberate external links and fragment identifiers are not treated as files.
    """
    root = root.resolve()
    source_pages = sorted(root.rglob("*.html"))
    destinations: set[str] = set()
    for source in source_pages:
        if source.is_symlink():
            raise InternalLinkError(f"Symlinked HTML page: {source.relative_to(root)}")
        url = _published_url(source.relative_to(root))
        html = source.read_text(encoding="utf-8")
        for match in _BUSINESS_MAILTO_ANCHOR.finditer(html):
            if (not html[:match.start()].endswith("<!--email_off-->")
                    or not html[match.end():].startswith("<!--/email_off-->")):
                raise InternalLinkError(
                    f"Unprotected business mailto creates Cloudflare 404: {url}"
                )
        for target in internal_destinations(html, url):
            parts = urlsplit(target)
            if parts.scheme != "https" or parts.netloc != "www.retallyrecovery.com":
                raise InternalLinkError(f"Noncanonical internal link: {url} -> {target}")
            candidates = _candidate_files(root, parts.path)
            if not any(p.is_file() and not p.is_symlink()
                       and p.resolve().is_relative_to(root) for p in candidates):
                raise InternalLinkError(f"Missing published internal link: {url} -> {target}")
            destinations.add(target)
    return {"pages": len(source_pages), "destinations": len(destinations)}


def validate_live_links(
    pages: dict[str, str],
    fetcher,
    known_good: set[str] | None = None,
) -> dict[str, int]:
    """GET each unique first-party href once; resolve bounded safe redirects.

    fetcher uses the production audit's no-redirect HTTP client. A 4XX/5XX,
    redirect loop, or unsafe cross-origin redirect fails the release audit.
    """
    origins: dict[str, set[str]] = {}
    for source, html in pages.items():
        for target in internal_destinations(html, source):
            origins.setdefault(target, set()).add(source)

    passed = set(known_good or ())
    redirects = set()
    for target, sources in sorted(origins.items()):
        current = target
        visited = set()
        for _ in range(4):
            if current in passed:
                break
            if current in visited:
                raise InternalLinkError(f"Redirect loop: {target} (from {sorted(sources)[0]})")
            visited.add(current)
            try:
                status, headers, _ = fetcher(current)
            except Exception as error:
                raise InternalLinkError(
                    f"Internal link request failed: {current} (from {sorted(sources)[0]}): "
                    f"{type(error).__name__}"
                ) from error
            if status in REDIRECT_CODES:
                location = headers.get("Location")
                if not location:
                    raise InternalLinkError(f"Redirect missing Location: {current}")
                next_url = urljoin(current, location)
                parsed = urlsplit(next_url)
                if parsed.scheme != "https" or parsed.netloc != "www.retallyrecovery.com":
                    raise InternalLinkError(f"Unsafe internal redirect: {current} -> {next_url}")
                current = urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/",
                                       parsed.query, ""))
                redirects.add(target)
                continue
            if status != 200:
                raise InternalLinkError(
                    f"Broken internal link: {target} (from {sorted(sources)[0]}): "
                    f"HTTP {status} at {current}"
                )
            passed.add(current)
            break
        else:
            raise InternalLinkError(f"Too many internal redirects: {target}")
        passed.add(target)
    return {"destinations": len(origins), "redirected_destinations": len(redirects)}
