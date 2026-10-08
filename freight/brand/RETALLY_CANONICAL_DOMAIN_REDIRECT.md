# RETALLY | Canonical HTTPS host

At completion, the Cloudflare zone `retallyrecovery.com` has a zone-level redirect ruleset in `http_request_dynamic_redirect`, created after observing inconsistent recovery-rate content between apex and www.

- Ruleset ID: `6c6f2d2cce5d4da58ed6395e76429c94`.
- Rule ID: `2387a677fe8b4fffba293345e40efe3a`.
- Exact condition: `http.host eq "retallyrecovery.com"`.
- Action: HTTP 301 to `https://www.retallyrecovery.com` + existing path.
- Preserve original query string.
- Both domain CNAME records are proxied by Cloudflare.

Read-only checks after creation:
- `https://retallyrecovery.com/` resolved to `https://www.retallyrecovery.com/`.
- A public audit-example link with `?utm_source=retally_qa` arrived on the canonical www host with the tracking parameter preserved. Cloudflare Pages may normalize .html in its final response.
- `https://www.retallyrecovery.com/` remains the published canonical destination.

**Rollback:** disable or delete only the above redirect rule using its saved ruleset/rule identifiers; do not change Zoho DNS MX/TXT records. Keep the old GitHub Pages URL accessible unless redirect continuity is verified. DNS and site deployment are independently managed.
