-- Exact live migration statement. Contains no customer/provider identifiers.

alter table ai_business_os_prod.opportunities
  add column if not exists first_contact_at timestamptz;

create index if not exists idx_opportunities_first_contact
  on ai_business_os_prod.opportunities(first_contact_at)
  where first_contact_at is not null;

