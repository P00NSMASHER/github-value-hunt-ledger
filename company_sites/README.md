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
copies only named existing images/fonts and ships their font licenses. The
pages have no JavaScript, accounts, file uploads, analytics or payment submission.
The restrictive CSP reflects those actual capabilities.

Run the publication checks from the repository root:

    python -m unittest discover -s company_sites -p 'test_*.py'

These check output isolation, local links and anchors, canonical URLs, security
headers, source-revision attribution and refusal to overwrite source or output.

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
Links explicitly open the visitor's email app; there is no claim that the site
has sent or stored a request. email_off comments prevent Cloudflare from
injecting its email-obfuscation script into these script-free pages.

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

