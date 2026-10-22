# RETALLY OCI remote execution — 22 October 2026

The original Oracle command receipt was rechecked using the authenticated owner Cloud Shell. The exact E2 Micro VM's agent reported a completed command with lifecycle `SUCCEEDED`, delivery `ACKED`, exit code 0, and the expected synthetic text marker. This was a *Cloud Shell-originated* manual probe, not a GitHub Actions deployment.

The GitHub-hosted workflow `.github/workflows/retally-oci-runcommand-canary.yml` has **not** produced independently verified manual execution success. Keep `RETALLY_OCI_RUN_COMMAND_ENABLED` disabled until GitHub account-owner verification, separate OAuth identity and OIDC trust, and exact-source approval pass.

Keep private synthetic staging separate from production: no customer data, billable resources, public SSH or DNS/Tunnel/Access-Allow changes. Never resubmit an uncertain OCI command without first reconciling its existing command ID in Oracle Audit and execution records.
