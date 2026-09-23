# RecoveryOS public site

This is the broader RecoveryOS business site. It is published as an isolated
subdirectory beside the Freight Recovery microsite, so changes here do not
alter the Freight sales experience.

The browser form prepares an email locally. It does not upload or transmit
business records. Publication fails closed unless a verified contact inbox is
provided through `RECOVERYOS_CONTACT_EMAIL` and explicitly enabled with
`RECOVERYOS_CONTACT_VERIFIED=1`.

Build from the repository root:

```text
RECOVERYOS_CONTACT_EMAIL=owner@business.test \
RECOVERYOS_CONTACT_VERIFIED=1 \
python recoveryworks/site/build.py --output /tmp/recoveryos-public
```

The original website photography was generated for RecoveryOS and optimized to
WebP. Newsreader and Familjen Grotesk are distributed under the SIL Open Font
License; their license texts are shipped with the font files.
