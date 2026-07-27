alter table public.kakao_cs_events_test
  add column if not exists approval_ref text,
  add column if not exists expires_at timestamptz;

update public.kakao_cs_events_test
set
  approval_ref = coalesce(approval_ref, 'APR-LEGACY-MIGRATION-001'),
  expires_at = coalesce(expires_at, created_at + interval '7 days')
where approval_ref is null or expires_at is null;

alter table public.kakao_cs_events_test
  alter column approval_ref set not null,
  alter column expires_at set default (now() + interval '7 days'),
  alter column expires_at set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'kakao_cs_events_test_approval_ref_format'
      and conrelid = 'public.kakao_cs_events_test'::regclass
  ) then
    alter table public.kakao_cs_events_test
      add constraint kakao_cs_events_test_approval_ref_format
      check (approval_ref ~ '^APR-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$');
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conname = 'kakao_cs_events_test_expiry_after_creation'
      and conrelid = 'public.kakao_cs_events_test'::regclass
  ) then
    alter table public.kakao_cs_events_test
      add constraint kakao_cs_events_test_expiry_after_creation
      check (expires_at > created_at);
  end if;
end
$$;

create index if not exists kakao_cs_events_test_expires_at_idx
  on public.kakao_cs_events_test (expires_at);

comment on column public.kakao_cs_events_test.approval_ref is
  'Non-secret reference to the human-approved synthetic test run.';

comment on column public.kakao_cs_events_test.expires_at is
  'Deletion eligibility marker. Automated deletion is configured separately.';
