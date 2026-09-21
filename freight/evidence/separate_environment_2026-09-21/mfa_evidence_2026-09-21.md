# MFA verification evidence — redacted

Observed: 2026-09-21

Evidence supplied by the environment owner:
- a Google-branded 2-Step Verification screen for the Gmail account used for the controlled pilot environment;
- the screen states: "This extra step shows it’s really you trying to sign in";
- the account identifier is visually masked except for the Gmail domain;
- the environment owner confirmed that 2-Step Verification is enabled.

Uploaded screenshot cryptographic receipt:
- SHA-256: `e4594ecd2025320220583dcc79b3d9672bf7a2a6b1518ce71e08d632ba2baea1`
- byte length: `45736`

Independent supporting account evidence already recorded:
- Google security alert dated 2026-09-17 showing a new passkey was added to the same account used for the staged Google Drive environment;
- no matching passkey-removal alert or 2-Step Verification disable alert was found in the connected Gmail history checked on 2026-09-21.

Control conclusion:
The supplied Google 2-Step Verification challenge is direct provider-generated evidence that an additional authentication step is enforced for the account sign-in flow observed. Together with the existing account-security evidence, this satisfies the controlled-environment `mfa_enforced` gate for the staged single-tenant manual pilot.

Privacy:
The screenshot itself is not committed to Hunter. Only this redacted summary and the screenshot SHA-256/byte-length receipt are retained.
