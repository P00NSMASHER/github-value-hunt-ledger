-- Exact live migration statement. Contains no customer/provider identifiers.

alter table ai_business_os_prod.rights_evidence_objects
  add constraint rights_executed_permission_requires_verified_sha
  check (
    evidence_class <> 'EXECUTED_PERMISSION_VERIFIED'
    or (
      verification_status='VERIFIED'
      and evidence_sha256 is not null
      and evidence_sha256 ~ '^[0-9a-f]{64}$'
    )
  );

alter table ai_business_os_prod.rights_global_assertions
  add constraint rights_global_assertions_never_auto_scope
  check (automatic_scope_effect=false);

