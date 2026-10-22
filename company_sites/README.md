# Independent RETALLY company sites

These are separate static marketing sites. The group directory lists exactly four
businesses. RecoveryWorks accepts enquiries for a narrow managed pilot; it does
not inherit Freight's fee or make a broad 18-lane commercial claim.

## Build

From the repository root:

    python company_sites/build.py group --output dist-group
    python company_sites/build.py recoveryworks --output dist-recoveryworks

From company_sites (the Cloudflare Pages project root):

    python build.py group --output dist-group
    python build.py recoveryworks --output dist-recoveryworks

Configure distinct Pages projects with root directory company_sites and output
directories dist-group and dist-recoveryworks respectively. Do not use the
repository root as a new project's Pages root: the existing freight Functions
remain separate. No functions, worker, customer data or operational system enters
either company's explicit publication allowlist.

The builder refuses nonempty outputs, unsafe sources and unresolved tokens. It
copies only named existing images/fonts and ships their font licenses. The Group
homepage includes one allowlisted, content-versioned enquiry client; RecoveryWorks
remains script-free. Neither site provides accounts, file uploads, analytics or
payment submission. Each site's restrictive CSP reflects its actual capabilities.

Run the publication checks from the repository root:

    python -m unittest discover -s company_sites -p 'test_*.py'
    node --test company_sites/test_group_client.mjs

These check output isolation, local links and anchors, canonical URLs, security
headers, source-revision attribution and refusal to overwrite source or output.
The isolated client tests use a minimal DOM and mocked transport. They verify
explicit submission, consent, security expiry, saved receipts, uncertain-response
retries, fallback copying and active/legacy business query selection without any
browser network, provider call or production submission.

## Production map and restoration

| Business | Production URL | Publication owner |
| --- | --- | --- |
| RETALLY Group | https://group.retallyrecovery.com/ | `company_sites/group` |
| RETALLY Freight Recovery | https://www.retallyrecovery.com/ | Existing standalone `freight/site` |
| RETALLY RecoveryWorks | https://recoveryworks.retallyrecovery.com/ | `company_sites/recoveryworks` |
| PermitPlate | https://permitplate.retallyrecovery.com/ | Separate PermitPlate project |
| CaptureBrief | https://capturebrief.retallyrecovery.com/ | Separate CaptureBrief project |

The apex https://retallyrecovery.com/ remains the Freight entry point and resolves
to the existing canonical www host. The restoration uses the standalone Freight
homepage at `freight/site/index.html` and its existing assets. Keep that source
and its recovery/intake logic in place; the group directory must never replace
the Freight root page. These company builds only read their listed shared assets
and do not move or rewrite the original Freight files.

Set `root_dir=company_sites` for **both** new Group and RecoveryWorks Cloudflare
Pages projects. Their output directories are `dist-group` and
`dist-recoveryworks`. This root excludes the repository-root Freight `functions/`
directory from those static projects. Product projects have their own deployment
configuration and are not folded into either output.

Release the independent company sites first. Verify each production hostname,
canonical URL, contact/support links, security headers and deployed source
revision; then verify the Group links resolve to the intended company. Release
the restored Freight root and the legacy-route redirects only after the new
destinations are live. Preserve the original source and research assets in the
repository even when experiments leave the primary navigation.

The existing `freight-site-pages.yml` workflow includes `company_sites/**` in
pull-request and main-branch triggers. Its company step tests both publication
allowlists, builds from the Pages root directory and verifies that both build
fingerprints identify the workflow's Git revision. All existing Freight gates
remain in the same verification job; the company step does not deploy a site.

## Destinations and contact

Default canonical hosts are group.retallyrecovery.com and
recoveryworks.retallyrecovery.com. Product links point to the separately planned
PermitPlate and CaptureBrief subdomains; Freight remains www.retallyrecovery.com.
Deploy and verify a destination before sending public traffic to it.

The following HTTPS URL overrides support a staged migration without introducing
unknown links: RETALLY_GROUP_URL, RETALLY_FREIGHT_URL,
RETALLY_RECOVERYWORKS_URL, RETALLY_PERMITPLATE_URL,
RETALLY_CAPTUREBRIEF_URL. A per-build --public-url overrides that company's
canonical base. Product privacy URLs retain their established privacy.html path.

The public inbox is the existing published jay@retallyrecovery.com address.
Brand-specific mail subjects route each enquiry without inventing new mailboxes.
Email links explicitly open the visitor's email app, and copying is never
described as sending. email_off comments prevent Cloudflare from injecting an
email-obfuscation script outside the explicit publication allowlist.

### Group secure enquiry

`group/enquiry.js` adapts the receipt flow from source revision
`c46b7405d8f766334b16aede807acdbf3f2604ff`. It loads only on the Group homepage.
GET checks availability at `https://www.retallyrecovery.com/api/group-inquiry`;
only an explicit, valid form submission sends a POST to that same endpoint.
Both requests use `credentials: "omit"`, CORS mode, no-store caching and no
redirect following. The backend must admit only the verified Group origin for
cross-origin requests and validate the matching Turnstile hostname/action.

The form selects only `general`, `recovery`, `recoveryworks`, `permitplate` or
`capturebrief`. Old display names `RETALLY Recovery` and `PermitPlate NYC` map
to their active businesses; retired experiment values default to `general`.
The client receives the public Turnstile site key from availability configuration
and renders the compact widget. No secret is embedded in the public output.

A success state requires HTTP 202 plus a valid saved reference and explicit
`ok`/`received` flags. A pending notification remains a successful save without
claiming email delivery. Uncertain responses keep the details on the page; an
unchanged retry keeps its idempotency key while a changed enquiry gets a new key.
This retry identity lasts for the current page session and is not browser storage.
Email draft and copy alternatives remain available, including when secure intake
or the security widget is unavailable. Without JavaScript, direct email remains
visible and the nonfunctional form stays hidden.

The Group CSP admits local scripts and `challenges.cloudflare.com` for Turnstile,
and permits connections only to the site itself, the fixed Freight-hosted intake
origin and Turnstile. Native form navigation remains blocked. The Group project
still publishes no Functions; deploy the matching backend/CORS change with the
frontend before enabling this flow in production. RecoveryWorks retains
`script-src 'none'` and `connect-src 'none'`.

Each output exposes build-info.json containing the target, canonical URL and
CF_PAGES_COMMIT_SHA (or GITHUB_SHA). A build with neither variable says local /
local_unattributed; it must not be cited as a verified production source revision.

## Content and ownership

- group/: homepage and group-specific privacy notice.
- recoveryworks/: homepage, engagement framework and pilot-specific privacy.
- Existing supporting software remains named RecoveryOS internally.
- Transportation and parcel billing stays with Freight Recovery.
- RecoveryWorks' initial public offer covers vendor overpayment review and
  missed-credit reconciliation. Other categories require separate acceptance.
- All illustrative calculations are labeled and report zero confirmed recovery.
- No corporation name, legal status, registered office or universal fee is
  invented. A pilot's operator and terms are identified before acceptance.
- Experiments are absent from the group and company commercial navigation.

