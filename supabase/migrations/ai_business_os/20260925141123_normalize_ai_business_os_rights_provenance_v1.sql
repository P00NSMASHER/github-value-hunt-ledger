-- Exact live migration statement. Contains no customer/provider identifiers.

create table if not exists ai_business_os_prod.rights_subjects (
  id uuid primary key default gen_random_uuid(),
  subject_key text not null unique,
  subject_type text not null check (subject_type in (
    'REPOSITORY_CODE','DATASET','MODEL_WEIGHTS','STANDARD_SPEC','BUNDLED_ASSET',
    'TRADEMARK_PATENT','API_SERVICE','OTHER'
  )),
  source_locator text not null,
  revision text,
  public_license text,
  origin_subsystem text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.rights_evidence_objects (
  id uuid primary key default gen_random_uuid(),
  evidence_key text not null unique,
  evidence_class text not null check (evidence_class in (
    'PUBLIC_LICENSE_VERIFIED',
    'OWNER_ATTESTED',
    'EXECUTED_PERMISSION_VERIFIED',
    'UNKNOWN_REVIEW',
    'DENIED'
  )),
  evidence_location text,
  evidence_sha256 text check (
    evidence_sha256 is null or evidence_sha256 ~ '^[0-9a-f]{64}$'
  ),
  verification_status text not null check (
    verification_status in ('VERIFIED','UNVERIFIED','REJECTED')
  ),
  verifier_kind text not null check (
    verifier_kind in ('PUBLIC_SOURCE','OWNER','INDEPENDENT','SYSTEM','UNKNOWN')
  ),
  observed_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.rights_scope_state (
  subject_id uuid not null references ai_business_os_prod.rights_subjects(id),
  scope_key text not null check (scope_key in (
    'commercial_use','hosted_saas','redistribution','assignment','sublicensing',
    'change_of_control','datasets','model_weights','bundled_assets','trademarks_patents'
  )),
  scope_status text not null check (scope_status in (
    'ALLOWED','ALLOWED_WITH_CONDITIONS','DENIED','UNKNOWN_REVIEW','NOT_APPLICABLE'
  )),
  evidence_id uuid references ai_business_os_prod.rights_evidence_objects(id),
  conditions jsonb not null default '[]'::jsonb,
  rationale text not null,
  updated_at timestamptz not null default now(),
  primary key(subject_id,scope_key),
  check (
    scope_status='UNKNOWN_REVIEW'
    or evidence_id is not null
  )
);

create table if not exists ai_business_os_prod.rights_global_assertions (
  assertion_key text primary key,
  evidence_class text not null check (evidence_class in (
    'OWNER_ATTESTED','EXECUTED_PERMISSION_VERIFIED','UNKNOWN_REVIEW','DENIED'
  )),
  subject_selector text not null,
  statement text not null,
  automatic_scope_effect boolean not null default false,
  evidence_location text,
  evidence_sha256 text check (
    evidence_sha256 is null or evidence_sha256 ~ '^[0-9a-f]{64}$'
  ),
  created_at timestamptz not null default now()
);

create table if not exists ai_business_os_prod.rights_subsystem_policy (
  subsystem_key text primary key,
  canonical_registry_required boolean not null default true,
  default_stage text not null check (default_stage in (
    'ANALYSIS','CONTROLLED_PILOT','HOSTED_SAAS','ACQUIRER_DILIGENCE'
  )),
  allow_global_assertion_auto_effect boolean not null default false,
  notes text not null,
  updated_at timestamptz not null default now()
);

alter table ai_business_os_prod.rights_subjects enable row level security;
alter table ai_business_os_prod.rights_evidence_objects enable row level security;
alter table ai_business_os_prod.rights_scope_state enable row level security;
alter table ai_business_os_prod.rights_global_assertions enable row level security;
alter table ai_business_os_prod.rights_subsystem_policy enable row level security;

revoke all on ai_business_os_prod.rights_subjects,
  ai_business_os_prod.rights_evidence_objects,
  ai_business_os_prod.rights_scope_state,
  ai_business_os_prod.rights_global_assertions,
  ai_business_os_prod.rights_subsystem_policy
from public,anon,authenticated;

create index if not exists idx_rights_subjects_origin
  on ai_business_os_prod.rights_subjects(origin_subsystem,subject_type);
create index if not exists idx_rights_scope_evidence
  on ai_business_os_prod.rights_scope_state(evidence_id);
create index if not exists idx_rights_evidence_class
  on ai_business_os_prod.rights_evidence_objects(evidence_class,verification_status);

insert into ai_business_os_prod.rights_subsystem_policy(
  subsystem_key,canonical_registry_required,default_stage,
  allow_global_assertion_auto_effect,notes
) values
('hunter',true,'ANALYSIS',false,'Standing owner assertion is recorded as provenance only and never auto-promotes repository scopes.'),
('freight',true,'CONTROLLED_PILOT',false,'Controlled-pilot runtime use requires scope-specific canonical rights readiness.'),
('recoveryworks',true,'ANALYSIS',false,'New runtime/imported components must resolve through canonical rights state before pilot promotion.'),
('ai_business_os',true,'ANALYSIS',false,'Production tools/components must not derive rights from graph presence or generic assertions.')
on conflict(subsystem_key) do update set
  canonical_registry_required=excluded.canonical_registry_required,
  default_stage=excluded.default_stage,
  allow_global_assertion_auto_effect=excluded.allow_global_assertion_auto_effect,
  notes=excluded.notes,
  updated_at=now();

insert into ai_business_os_prod.rights_global_assertions(
  assertion_key,evidence_class,subject_selector,statement,
  automatic_scope_effect,evidence_location,evidence_sha256
) values (
  'hunter-standing-owner-attestation-2026-09-19',
  'OWNER_ATTESTED',
  'repository_owned_public_code',
  'Owner states separate commercial permission exists for repository-owned public GitHub code/content used in the hunt.',
  false,
  'MASTER.md',
  null
)
on conflict(assertion_key) do update set
  evidence_class=excluded.evidence_class,
  subject_selector=excluded.subject_selector,
  statement=excluded.statement,
  automatic_scope_effect=false,
  evidence_location=excluded.evidence_location,
  evidence_sha256=excluded.evidence_sha256;

with seed as (
  select * from jsonb_to_recordset('[{"subject_key":"emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","repository":"emoss08/Trenova","revision":"95fcf816562025ad9af864ded4a5fce8a555bd65","public_license":"FSL-1.1-ALv2","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE_EXACT_REVISION","evidence_key":"owner-attestation:emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","repository":"kodekinetics79/opstrax-enterprise-build","revision":"fec2ba1432d6f8b4ba4c48be3d58e7e096819045","public_license":"NO_PUBLIC_LICENSE_RECORDED","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_PERMISSION","evidence_key":"owner-attestation:kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","repository":"sengtha/Kareya-Silo","revision":"a43eedea03add0728eadfc1f8ea35cc3ca6867cc","public_license":"Apache-2.0","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","repository":"vidyesh95/qatoto-backend","revision":"4f5f270f6ba5ef3ed4b230716997ccea049ce408","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","repository":"A-Jatin/freight-ratecon-extraction","revision":"a3dbbfec7f6b042176880d06c5114f81f29e57eb","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","repository":"OmarFaig/Assay","revision":"821303935ef2855908a9a9bd1efd4c33f9cd39d2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","repository":"srthck/trustmesh","revision":"5a93d70b37aafecaf61a5bc0296eaf831e5504ac","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_AND_USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE","evidence_key":"public-license:srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","repository":"mgilbir/formalis","revision":"2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","repository":"DominicFinn/open_tms","revision":"93d8c2b8ff78373ff69bb7ea546743e4703628b1","public_license":"MIT","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","repository":"justicebajaj161/Freight-Audit-Console","revision":"c2d4c07310a77e20ee21a74fc96d49df783c2e3a","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","repository":"WRBriska/InvoiceAudit","revision":"bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","repository":"AnsonLai/docx-redline-js","revision":"e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","repository":"kingsleyonoh/sla-penalty-settlement-engine","revision":"ea66727de51df7ee67a9f03f2549845fa6247b3d","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","repository":"yaogdu/AgentLedger","revision":"dd966e3b3d9eb54032c51701d30efcfbaa2379b0","public_license":"Apache-2.0","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","repository":"microsoft/duroxide-python","revision":"0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","repository":"fleetbase/fleetbase","revision":"4ff6980c6db6f3e8103b3ec425a089aa6d251af4","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","repository":"Budget-Lab-Yale/tariff-rate-tracker","revision":"5a977726af0ead299e7db9cbca018b04dc2cc2e6","public_license":"MIT","runtime_status":"PINNED_SOURCE_DATA_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"}]'::jsonb) as x(
    subject_key text,
    repository text,
    revision text,
    public_license text,
    runtime_status text,
    legacy_basis text,
    evidence_key text,
    evidence_class text,
    evidence_location text,
    evidence_sha text,
    commercial_status text,
    hosted_saas text,
    assignment text,
    sublicensing text,
    change_of_control text
  )
)
insert into ai_business_os_prod.rights_subjects(
  subject_key,subject_type,source_locator,revision,public_license,origin_subsystem,metadata
)
select
  s.subject_key,'REPOSITORY_CODE',s.repository,s.revision,s.public_license,'freight',
  jsonb_build_object(
    'runtime_status',s.runtime_status,
    'legacy_commercial_use_basis',s.legacy_basis,
    'imported_from','freight/COMPONENT_RIGHTS_REGISTRY.json'
  )
from seed s
on conflict(subject_key) do update set
  source_locator=excluded.source_locator,
  revision=excluded.revision,
  public_license=excluded.public_license,
  metadata=excluded.metadata,
  updated_at=now();

with seed as (
  select * from jsonb_to_recordset('[{"subject_key":"emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","repository":"emoss08/Trenova","revision":"95fcf816562025ad9af864ded4a5fce8a555bd65","public_license":"FSL-1.1-ALv2","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE_EXACT_REVISION","evidence_key":"owner-attestation:emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","repository":"kodekinetics79/opstrax-enterprise-build","revision":"fec2ba1432d6f8b4ba4c48be3d58e7e096819045","public_license":"NO_PUBLIC_LICENSE_RECORDED","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_PERMISSION","evidence_key":"owner-attestation:kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","repository":"sengtha/Kareya-Silo","revision":"a43eedea03add0728eadfc1f8ea35cc3ca6867cc","public_license":"Apache-2.0","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","repository":"vidyesh95/qatoto-backend","revision":"4f5f270f6ba5ef3ed4b230716997ccea049ce408","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","repository":"A-Jatin/freight-ratecon-extraction","revision":"a3dbbfec7f6b042176880d06c5114f81f29e57eb","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","repository":"OmarFaig/Assay","revision":"821303935ef2855908a9a9bd1efd4c33f9cd39d2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","repository":"srthck/trustmesh","revision":"5a93d70b37aafecaf61a5bc0296eaf831e5504ac","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_AND_USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE","evidence_key":"public-license:srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","repository":"mgilbir/formalis","revision":"2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","repository":"DominicFinn/open_tms","revision":"93d8c2b8ff78373ff69bb7ea546743e4703628b1","public_license":"MIT","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","repository":"justicebajaj161/Freight-Audit-Console","revision":"c2d4c07310a77e20ee21a74fc96d49df783c2e3a","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","repository":"WRBriska/InvoiceAudit","revision":"bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","repository":"AnsonLai/docx-redline-js","revision":"e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","repository":"kingsleyonoh/sla-penalty-settlement-engine","revision":"ea66727de51df7ee67a9f03f2549845fa6247b3d","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","repository":"yaogdu/AgentLedger","revision":"dd966e3b3d9eb54032c51701d30efcfbaa2379b0","public_license":"Apache-2.0","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","repository":"microsoft/duroxide-python","revision":"0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","repository":"fleetbase/fleetbase","revision":"4ff6980c6db6f3e8103b3ec425a089aa6d251af4","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","repository":"Budget-Lab-Yale/tariff-rate-tracker","revision":"5a977726af0ead299e7db9cbca018b04dc2cc2e6","public_license":"MIT","runtime_status":"PINNED_SOURCE_DATA_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"}]'::jsonb) as x(
    subject_key text,
    repository text,
    revision text,
    public_license text,
    runtime_status text,
    legacy_basis text,
    evidence_key text,
    evidence_class text,
    evidence_location text,
    evidence_sha text,
    commercial_status text,
    hosted_saas text,
    assignment text,
    sublicensing text,
    change_of_control text
  )
)
insert into ai_business_os_prod.rights_evidence_objects(
  evidence_key,evidence_class,evidence_location,evidence_sha256,
  verification_status,verifier_kind,observed_at,metadata
)
select
  s.evidence_key,
  s.evidence_class,
  s.evidence_location,
  nullif(s.evidence_sha,''),
  case when s.evidence_class='UNKNOWN_REVIEW' then 'UNVERIFIED' else 'VERIFIED' end,
  case
    when s.evidence_class='OWNER_ATTESTED' then 'OWNER'
    when s.evidence_class='PUBLIC_LICENSE_VERIFIED' then 'PUBLIC_SOURCE'
    else 'UNKNOWN'
  end,
  now(),
  jsonb_build_object(
    'subject_key',s.subject_key,
    'legacy_basis',s.legacy_basis,
    'imported_from','freight rights registries'
  )
from seed s
on conflict(evidence_key) do update set
  evidence_class=excluded.evidence_class,
  evidence_location=excluded.evidence_location,
  evidence_sha256=excluded.evidence_sha256,
  verification_status=excluded.verification_status,
  verifier_kind=excluded.verifier_kind,
  observed_at=excluded.observed_at,
  metadata=excluded.metadata;

with seed as (
  select * from jsonb_to_recordset('[{"subject_key":"emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","repository":"emoss08/Trenova","revision":"95fcf816562025ad9af864ded4a5fce8a555bd65","public_license":"FSL-1.1-ALv2","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE_EXACT_REVISION","evidence_key":"owner-attestation:emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","repository":"kodekinetics79/opstrax-enterprise-build","revision":"fec2ba1432d6f8b4ba4c48be3d58e7e096819045","public_license":"NO_PUBLIC_LICENSE_RECORDED","runtime_status":null,"legacy_basis":"USER_ASSERTED_SEPARATE_PERMISSION","evidence_key":"owner-attestation:kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045","evidence_class":"OWNER_ATTESTED","evidence_location":"freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md","evidence_sha":"ef93b40812bf68f027347cd95fa41550d58c06387c615272dd786fe8fbe57d71","commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","repository":"sengtha/Kareya-Silo","revision":"a43eedea03add0728eadfc1f8ea35cc3ca6867cc","public_license":"Apache-2.0","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","repository":"vidyesh95/qatoto-backend","revision":"4f5f270f6ba5ef3ed4b230716997ccea049ce408","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","repository":"A-Jatin/freight-ratecon-extraction","revision":"a3dbbfec7f6b042176880d06c5114f81f29e57eb","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","repository":"OmarFaig/Assay","revision":"821303935ef2855908a9a9bd1efd4c33f9cd39d2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","repository":"srthck/trustmesh","revision":"5a93d70b37aafecaf61a5bc0296eaf831e5504ac","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_AND_USER_ASSERTED_SEPARATE_COMMERCIAL_LICENSE","evidence_key":"public-license:srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","repository":"mgilbir/formalis","revision":"2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","public_license":"MIT","runtime_status":null,"legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","repository":"DominicFinn/open_tms","revision":"93d8c2b8ff78373ff69bb7ea546743e4703628b1","public_license":"MIT","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_LICENSE_PLUS_USER_STANDING_PERMISSION","evidence_key":"public-license:DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","repository":"justicebajaj161/Freight-Audit-Console","revision":"c2d4c07310a77e20ee21a74fc96d49df783c2e3a","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:justicebajaj161/Freight-Audit-Console@c2d4c07310a77e20ee21a74fc96d49df783c2e3a","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","repository":"WRBriska/InvoiceAudit","revision":"bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","public_license":"REVIEW_LEDGER_BEFORE_RUNTIME_USE","runtime_status":"KEEP_INDEPENDENT","legacy_basis":"BENCHMARK_OR_INDEPENDENT_FALSIFIER","evidence_key":"legacy-review:WRBriska/InvoiceAudit@bd3c0550f7a7f4a7ab9df8a5efc4b7a370c8253c","evidence_class":"UNKNOWN_REVIEW","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json","evidence_sha":null,"commercial_status":"UNKNOWN_REVIEW","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","repository":"AnsonLai/docx-redline-js","revision":"e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#AnsonLai/docx-redline-js@e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","repository":"kingsleyonoh/sla-penalty-settlement-engine","revision":"ea66727de51df7ee67a9f03f2549845fa6247b3d","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#kingsleyonoh/sla-penalty-settlement-engine@ea66727de51df7ee67a9f03f2549845fa6247b3d","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","repository":"yaogdu/AgentLedger","revision":"dd966e3b3d9eb54032c51701d30efcfbaa2379b0","public_license":"Apache-2.0","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#yaogdu/AgentLedger@dd966e3b3d9eb54032c51701d30efcfbaa2379b0","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","repository":"microsoft/duroxide-python","revision":"0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","public_license":"MIT","runtime_status":"PINNED_ISOLATED_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#microsoft/duroxide-python@0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","repository":"fleetbase/fleetbase","revision":"4ff6980c6db6f3e8103b3ec425a089aa6d251af4","public_license":"AGPL-3.0","runtime_status":"COMPARATOR_NOT_PRIMARY_RUNTIME","legacy_basis":"PUBLIC_AGPL_LICENSE_WITH_COMPLIANCE_REQUIRED","evidence_key":"public-license:fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4","evidence_sha":null,"commercial_status":"ALLOWED_WITH_CONDITIONS","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"},{"subject_key":"Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","repository":"Budget-Lab-Yale/tariff-rate-tracker","revision":"5a977726af0ead299e7db9cbca018b04dc2cc2e6","public_license":"MIT","runtime_status":"PINNED_SOURCE_DATA_ADAPTER","legacy_basis":"PUBLIC_LICENSE","evidence_key":"public-license:Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_class":"PUBLIC_LICENSE_VERIFIED","evidence_location":"freight/COMPONENT_RIGHTS_REGISTRY.json#Budget-Lab-Yale/tariff-rate-tracker@5a977726af0ead299e7db9cbca018b04dc2cc2e6","evidence_sha":null,"commercial_status":"ALLOWED","hosted_saas":"UNKNOWN_REVIEW","assignment":"UNKNOWN_REVIEW","sublicensing":"UNKNOWN_REVIEW","change_of_control":"UNKNOWN_REVIEW"}]'::jsonb) as x(
    subject_key text,
    repository text,
    revision text,
    public_license text,
    runtime_status text,
    legacy_basis text,
    evidence_key text,
    evidence_class text,
    evidence_location text,
    evidence_sha text,
    commercial_status text,
    hosted_saas text,
    assignment text,
    sublicensing text,
    change_of_control text
  )
), expanded as (
  select s.subject_key,s.evidence_key,'commercial_use'::text as scope_key,s.commercial_status as scope_status
  from seed s
  union all select s.subject_key,s.evidence_key,'hosted_saas',s.hosted_saas from seed s
  union all select s.subject_key,s.evidence_key,'assignment',s.assignment from seed s
  union all select s.subject_key,s.evidence_key,'sublicensing',s.sublicensing from seed s
  union all select s.subject_key,s.evidence_key,'change_of_control',s.change_of_control from seed s
  union all select s.subject_key,null,'redistribution','UNKNOWN_REVIEW' from seed s
  union all select s.subject_key,null,'datasets','UNKNOWN_REVIEW' from seed s
  union all select s.subject_key,null,'model_weights','UNKNOWN_REVIEW' from seed s
  union all select s.subject_key,null,'bundled_assets','UNKNOWN_REVIEW' from seed s
  union all select s.subject_key,null,'trademarks_patents','UNKNOWN_REVIEW' from seed s
)
insert into ai_business_os_prod.rights_scope_state(
  subject_id,scope_key,scope_status,evidence_id,conditions,rationale
)
select
  rs.id,
  e.scope_key,
  e.scope_status,
  case when e.scope_status='UNKNOWN_REVIEW' then null else reo.id end,
  case
    when e.scope_status='ALLOWED_WITH_CONDITIONS'
      then '["license/compliance obligations must be satisfied before runtime use"]'::jsonb
    else '[]'::jsonb
  end,
  case
    when e.scope_status='UNKNOWN_REVIEW' then 'No scope-specific evidence currently resolves this right.'
    when reo.evidence_class='OWNER_ATTESTED' then 'Scope resolved only to the extent stated by the owner attestation; no stronger evidence class is inferred.'
    when reo.evidence_class='PUBLIC_LICENSE_VERIFIED' then 'Scope reflects recorded public-license evidence; independently owned dependencies/data/assets remain separate.'
    else 'Canonical imported rights state.'
  end
from expanded e
join ai_business_os_prod.rights_subjects rs on rs.subject_key=e.subject_key
left join ai_business_os_prod.rights_evidence_objects reo on reo.evidence_key=e.evidence_key
on conflict(subject_id,scope_key) do update set
  scope_status=excluded.scope_status,
  evidence_id=excluded.evidence_id,
  conditions=excluded.conditions,
  rationale=excluded.rationale,
  updated_at=now();

create or replace view ai_business_os_prod.rights_canonical_status_v1
with (security_invoker=true)
as
select
  s.subject_key,
  s.subject_type,
  s.source_locator,
  s.revision,
  s.public_license,
  s.origin_subsystem,
  sc.scope_key,
  sc.scope_status,
  e.evidence_class,
  e.verification_status,
  e.evidence_location,
  e.evidence_sha256,
  sc.conditions,
  sc.rationale
from ai_business_os_prod.rights_subjects s
join ai_business_os_prod.rights_scope_state sc on sc.subject_id=s.id
left join ai_business_os_prod.rights_evidence_objects e on e.id=sc.evidence_id
order by s.subject_key,sc.scope_key;

create or replace function ai_business_os_prod.rights_stage_readiness_v1(
  p_subject_key text,
  p_stage text
) returns jsonb
language plpgsql
stable
security invoker
set search_path = ai_business_os_prod, pg_temp
as $$
declare
  v_subject uuid;
  v_required text[];
  v_missing text[] := '{}';
  v_denied text[] := '{}';
  v_conditional text[] := '{}';
  v_scope text;
  v_status text;
  v_evidence_class text;
  v_state text;
begin
  if p_stage not in ('ANALYSIS','CONTROLLED_PILOT','HOSTED_SAAS','ACQUIRER_DILIGENCE') then
    raise exception 'unsupported rights stage';
  end if;

  select id into v_subject
  from ai_business_os_prod.rights_subjects
  where subject_key=p_subject_key;

  if v_subject is null then
    return jsonb_build_object(
      'subject_key',p_subject_key,
      'stage',p_stage,
      'state','BLOCKED',
      'reason','SUBJECT_NOT_REGISTERED'
    );
  end if;

  if p_stage='ANALYSIS' then
    return jsonb_build_object(
      'subject_key',p_subject_key,
      'stage',p_stage,
      'state','ANALYSIS_ONLY',
      'reason','Analysis/provenance may proceed without implying runtime permission.'
    );
  elsif p_stage='CONTROLLED_PILOT' then
    v_required:=array['commercial_use'];
  elsif p_stage='HOSTED_SAAS' then
    v_required:=array['commercial_use','hosted_saas'];
  else
    v_required:=array[
      'commercial_use','hosted_saas','redistribution',
      'assignment','sublicensing','change_of_control'
    ];
  end if;

  foreach v_scope in array v_required
  loop
    select sc.scope_status,e.evidence_class
    into v_status,v_evidence_class
    from ai_business_os_prod.rights_scope_state sc
    left join ai_business_os_prod.rights_evidence_objects e on e.id=sc.evidence_id
    where sc.subject_id=v_subject and sc.scope_key=v_scope;

    if v_status is null or v_status='UNKNOWN_REVIEW' then
      v_missing:=array_append(v_missing,v_scope);
    elsif v_status='DENIED' then
      v_denied:=array_append(v_denied,v_scope);
    elsif v_status='ALLOWED_WITH_CONDITIONS' then
      v_conditional:=array_append(v_conditional,v_scope);
    elsif v_status='ALLOWED' and v_evidence_class not in (
      'PUBLIC_LICENSE_VERIFIED','OWNER_ATTESTED','EXECUTED_PERMISSION_VERIFIED'
    ) then
      v_missing:=array_append(v_missing,v_scope);
    end if;
  end loop;

  v_state:=case
    when cardinality(v_denied)>0 then 'BLOCKED'
    when cardinality(v_missing)>0 then 'BLOCKED'
    when cardinality(v_conditional)>0 then 'CONDITIONAL'
    else 'READY'
  end;

  return jsonb_build_object(
    'subject_key',p_subject_key,
    'stage',p_stage,
    'state',v_state,
    'missing_scopes',to_jsonb(v_missing),
    'denied_scopes',to_jsonb(v_denied),
    'conditional_scopes',to_jsonb(v_conditional),
    'global_assertions_auto_effect',false
  );
end;
$$;

revoke execute on function ai_business_os_prod.rights_stage_readiness_v1(text,text)
from public,anon,authenticated;

