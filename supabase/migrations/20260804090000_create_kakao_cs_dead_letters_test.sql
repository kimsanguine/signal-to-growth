-- Dead-letter storage for synthetic Kakao events that Supabase permanently
-- rejected. Availability failures are not stored here: those are retried by the
-- provider and recorded as structured logs instead.

create table if not exists public.kakao_cs_dead_letters_test (
  event_id text primary key,
  provider text not null check (provider = 'kakao_openbuilder'),
  provider_event_id text not null,
  received_at timestamptz not null,
  approval_ref text not null,
  failure_class text not null check (failure_class in ('contract', 'availability', 'unknown')),
  error_type text not null,
  status_code integer,
  canonical_event jsonb not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '7 days')
);

comment on table public.kakao_cs_dead_letters_test is
  'Synthetic Kakao events that failed a contract check and cannot be retried.';

comment on column public.kakao_cs_dead_letters_test.failure_class is
  'Why the event could not be stored normally. Contract failures never succeed on retry.';

comment on column public.kakao_cs_dead_letters_test.error_type is
  'Exception class name only. Exception messages are never stored, to avoid leaking payloads.';

comment on column public.kakao_cs_dead_letters_test.expires_at is
  'Deletion eligibility marker. Automated deletion is configured separately.';

alter table public.kakao_cs_dead_letters_test
  add constraint kakao_cs_dead_letters_test_approval_ref_format
  check (approval_ref ~ '^APR-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$');

alter table public.kakao_cs_dead_letters_test
  add constraint kakao_cs_dead_letters_test_expiry_after_creation
  check (expires_at > created_at);

create index if not exists kakao_cs_dead_letters_test_expires_at_idx
  on public.kakao_cs_dead_letters_test (expires_at);

create index if not exists kakao_cs_dead_letters_test_failure_class_idx
  on public.kakao_cs_dead_letters_test (failure_class, created_at);

alter table public.kakao_cs_dead_letters_test enable row level security;

revoke all on table public.kakao_cs_dead_letters_test from public, anon, authenticated;
grant insert, select on table public.kakao_cs_dead_letters_test to service_role;

create policy "deny client access to synthetic kakao dead letters"
on public.kakao_cs_dead_letters_test
for all
to anon, authenticated
using (false)
with check (false);

comment on policy "deny client access to synthetic kakao dead letters"
on public.kakao_cs_dead_letters_test is
  'Defense in depth: browser roles remain denied even if table grants change.';
