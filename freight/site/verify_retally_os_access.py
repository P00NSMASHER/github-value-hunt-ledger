"""Anonymous RETALLY OS HTTP boundary check.

No credentials, login submissions, customer data, or state-changing requests.
Run as an explicit CI smoke check, not as a scheduled crawler.
"""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _anonymous_get(url: str) -> tuple[int, str, bytes]:
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "RETALLY-OS-anonymous-access-smoke/1.0",
    })
    try:
        response = urllib.request.build_opener(_NoRedirect).open(request, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.headers.get("Location", ""), response.read(2048)


def _require_denial(url: str, *, is_production: bool) -> None:
    status, redirect, body = _anonymous_get(url)
    if status == 200:
        raise AssertionError("owner-only route returned anonymous HTTP 200")
    if body.startswith(b'{"observedAt":') or b'"cases":' in body or b"<title>RETALLY OS" in body:
        raise AssertionError("owner-only response included protected dashboard content")
    if status in {301, 302, 303, 307, 308}:
        target = urllib.parse.urlparse(redirect)
        print(f"Anonymous redirect: HTTP {status}, host={target.hostname}, path={target.path[:80]}")
        if target.scheme != "https" or not (
            "cloudflareaccess.com" in target.hostname if target.hostname else False
        ) and "/cdn-cgi/access/" not in target.path:
            raise AssertionError("anonymous redirect did not point to Cloudflare Access")
    elif status not in ({401, 403} if is_production else {401, 403, 404}):
        raise AssertionError(f"unexpected anonymous response status: {status}")
    print(f"{'production' if is_production else 'preview'} anonymous request denied: HTTP {status}")


def _require_access_callback_keeps_apex() -> None:
    """Cloudflare-managed login/callback paths must not be rewritten to www.

    A 301 across application hostnames invalidates the Access login nonce.
    Neither request attempts to log in or supplies a session credential.
    """
    for path in ("/cdn-cgi/access/callback", "/cdn-cgi/access/certs"):
        status, redirect, _ = _anonymous_get("https://retallyrecovery.com" + path)
        if status in {301, 302, 303, 307, 308} and (
            urllib.parse.urlparse(redirect).hostname == "www.retallyrecovery.com"
        ):
            raise AssertionError("Cloudflare Access callback path was canonicalized to www")
        print(f"Access reserved path stays on apex: {path}, HTTP {status}")


def main() -> None:
    _require_denial("https://retallyrecovery.com/api/internal/retally-os?view=data", is_production=True)
    _require_denial("https://retally-web.pages.dev/api/internal/retally-os?view=data", is_production=False)
    _require_access_callback_keeps_apex()


if __name__ == "__main__":
    main()
