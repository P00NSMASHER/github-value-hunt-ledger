# FreightLeak marketing source

This is a repaired, reviewable **public marketing page**, recovered from the historical `freightleak-v0.zip` artifact. It is not a copy of a verified current production deployment. At the time of this audit, `https://freightleak-audit.netlify.app/` returned **Site not found**, and the available provider connector could not resolve a deploy. This change does not restore provider access or deploy the site.

The teal/slate visual style and clearly synthetic sample have been retained. The historical page's empty `mailto:` recipient and unconditional free-audit/20%-of-savings offer have been replaced with a fit-and-readiness inquiry. Scope and fees are agreed in writing; previously agreed offers retain their own terms. Internal pricing hypotheses remain in the commercial documentation, not in this public bundle.

## One missing business configuration

A **verified business contact email** is required before launch. No inbox has been invented. An operator must confirm control of the inbox and independently check that it can receive and reply to a message, then configure it as below. The build checks syntax and requires that attestation; it does not prove mailbox ownership or delivery.

The unbuilt `index.html` is safe to review locally: it visibly says the contact channel is pending. Its inquiry tool prepares text locally, with copy and text-download fallbacks. When built with an approved inbox, it also offers an email draft. No button claims a lead was submitted or an email delivered. No analytics, upload form, backend request, local storage, or raw Hunter information is included.

## Prepare the public bundle

From the repository root, after replacing the email value with the real verified address:

```bash
export FREIGHT_CONTACT_EMAIL='REPLACE_WITH_VERIFIED_BUSINESS_EMAIL'
export FREIGHT_CONTACT_VERIFIED=1
python freight/site/build.py --output /tmp/freightleak-public
```

The output directory must be new or empty, outside the private repository, and not one of its parents. The build fails without the contact configuration. It reads an explicit allowlist and emits only `index.html`, `site.css`, `site.js`, and `_headers`. It does not recurse through the repository, copy customer data, or follow source symlinks. A later rebuild should use a new empty directory.

**Only the generated public output directory may be passed to a deployment tool. Never deploy the repository root, `freight/`, or this source directory.** The source directory also contains non-public build documentation and tests. There is intentionally no automatic deployment workflow or repository-wide publish configuration.

Once provider access is restored, first publish this output as a reviewable provider preview. Check the visible contact address, mobile layout, keyboard navigation, synthetic labels, and all inquiry actions. Check the provider's public access settings and applied `_headers`. Production publication and a working public URL must be confirmed separately; generating this bundle proves neither. No confidential intake route is enabled by this page.

## Verify locally

```bash
python -m unittest discover -s freight/site -p 'test_*.py'
node --check freight/site/site.js
python -m http.server 8000 --directory freight/site
```

Open `http://localhost:8000` to inspect the unconfigured source preview. Use only fictional details. Preparing, copying, or downloading an inquiry must never claim that it was sent. The browser page has no form submission endpoint. The proposed response headers restrict network requests and framing when served by a host that honors `_headers`; a plain local HTTP server does not apply those provider headers.

This publication work does not authorize sensitive document collection or validate the separate customer-processing environment. Those gates remain in the freight launch and security evidence.
