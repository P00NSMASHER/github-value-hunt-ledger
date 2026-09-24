# business_os — archived legacy implementation

**Status: FROZEN LEGACY REFERENCE**

The canonical implementation is now `ai_business_os/`.

This package remains temporarily for provenance and comparison. New features, bug fixes,
production adapters, governance changes, and database work must land in `ai_business_os/`.

`ARCHIVED_SOURCE_MANIFEST.json` pins every Python source/test file by Git blob identity.
Canonical CI also rejects Python outside this directory that imports `business_os`.

Phase 2 can remove or relocate this package after confirming that any genuinely unique behavior
has been ported and no compatibility consumer remains.
