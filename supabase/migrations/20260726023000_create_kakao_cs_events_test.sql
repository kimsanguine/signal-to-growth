create table if not exists public.kakao_cs_events_test (
  event_id text primary key,
  provider text not null check (provider = 'kakao_openbuilder'),
  provider_event_id text not null,
  received_at timestamptz not null,
  canonical_event jsonb not null,
  created_at timestamptz not null default now()
);

comment on table public.kakao_cs_events_test is
  'Synthetic Kakao Open Builder events for Signal to Growth test-account verification.';

alter table public.kakao_cs_events_test enable row level security;

revoke all on table public.kakao_cs_events_test from public, anon, authenticated;
grant insert, select on table public.kakao_cs_events_test to service_role;
