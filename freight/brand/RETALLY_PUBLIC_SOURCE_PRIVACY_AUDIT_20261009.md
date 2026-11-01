# RETALLY public-source privacy audit — October 9, 2026

## Confirmed P1 defect

The current repository is publicly readable. Historical marketing and
commercial documents, plus a regression test, contained a complete
residential business mailing address and a historical personal contact
mailbox. Website deployment privacy checks missed the exposure because
they only inspected the allowlisted public *website build*, not every
publicly accessible GitHub source file.

No sensitive values are reproduced in this report.

## Remediation in this pull request

- Redact historical residence/contact strings from six public source files,
  preserving the intended historical workflow and the business-contact
  migration context.
- Keep website/public-build checks that reject known personal contact strings.
- Add a fail-closed regression test checking all Git-tracked nonbinary source
  for the identified full-address and old-inbox patterns, reporting only
  filenames and finding types.
- Run the source privacy check on every PR and main push through the global
  repository release gate, and again before the public-site deployment lane.
- Assert through synthetic (not actual) contact fixtures that violations are
  detected.

## Important residual exposure

Redaction on main does **not** erase copies in historical Git commits, pull
request diffs, third-party mirrors, local clones, search caches, or earlier
site versions. Any decision to purge history or rotate public contact
identifiers requires a separately authorized, carefully coordinated process.
Do not force-push a history rewrite as part of this bounded fix.

## Scope exclusions

This gate covers Git-tracked readable text. Opaque binary attachments and
off-platform exports require separate asset/privacy review. This fix neither
changes current published contact details nor enables online inquiry
submissions. No email sending or customer submission is performed.
