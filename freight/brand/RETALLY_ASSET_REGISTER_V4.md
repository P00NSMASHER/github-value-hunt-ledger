# RETALLY | Asset register, production status

The independently delivered RETALLY Brand Finishing v4 bundle contains source originals, candidate pixel-perfect matte derivatives, single-color SVG tracing candidates, avatar/favicons, PDF/DOCX customer collateral, and a CSV registering each asset SHA-256.

Approved original master hashes:
- Wordmark PNG, 1619×257: `08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd`
- Emblem PNG, 805×776: `bb02ab4a468762f597c241199baeff61b485dd793f8fb746140ad33670b68043`

**Classes and gates**
| Class | State | Approved deployment |
|---|---|---|
| Original glossy PNG assets | SOURCE APPROVED | Existing approved placement |
| New white-plate PNG/WebP composites | SOURCE-PIXEL COMPOSITE | QA before use; letterforms unaltered |
| Transparent PNG/WebP matte extraction | DERIVATIVE CANDIDATE | Human inspect alpha/halos and contrast; no public release before acceptance |
| One-color SVG traces | VECTOR CANDIDATE | Inspect counters/silhouette at size; do not label official vector master |
| 16/32/48/64/128/256/512 favicon images | ICON CANDIDATE | Browser reduction and dark/light theme tests required |
| 1024px avatar, banner and social preview | SOCIAL CANDIDATE | Verify crop and branded customer URLs prior to posting |
| Editable DOCX/PDF documents | DRAFT CUSTOMER COLLATERAL | Verify actual legal entity, data and sender details before sending |

All logo files are excluded from the public Cloudflare artifact until added deliberately to its explicit allowlist and re-tested. Do not silently change original live logos or deploy an unverified matte.
