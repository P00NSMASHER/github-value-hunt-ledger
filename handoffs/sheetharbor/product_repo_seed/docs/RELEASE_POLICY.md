# Release Policy

## Freeze rule

A SheetHarbor release can be frozen only when all P0 gates are supported by reproducible evidence tied to exact artifact hashes.

For `v0.2.0`, required evidence is:

1. exact SHA-256 identity of the four vertical XLSX artifacts;
2. independent arithmetic regression results;
3. Google Sheets import/recalc/export results;
4. Microsoft Excel open/recalculate/save/reopen results on a named Excel version/build.

A parser-only or LibreOffice-only test must never be labeled as Microsoft Excel compatibility.

## Artifact immutability

If any canonical workbook bytes change after a compatibility test, the previous compatibility result is invalid for the new bytes. Update the manifest hash and rerun all compatibility gates.

## Claims

Compatibility claims must state the tested application and version/build when known. Customer outcome claims require separate pilot evidence.
