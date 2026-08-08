-- Business-separated CS event tables + reply-draft approval workflow.
-- Originally written 2026-08-08 by reconstructing the live signal-to-growth-test
-- project via pg_policies/pg_constraint/pg_get_functiondef introspection, then
-- revised the same day after an adversarial review (Codex) found that anon/
-- authenticated had direct SELECT on all three tables and EXECUTE on the
-- approve RPC — meaning loop.habix.ai's Basic Auth was cosmetic; anyone with
-- the publishable key could bypass it entirely. This version closes that: no
-- permissive policy exists for anon/authenticated on any of these tables or
-- the RPC, so RLS default-deny blocks all of it. The only path in is the
-- loop-habix Worker's SUPABASE_SERVICE_KEY (service_role, bypasses RLS),
-- which is not committed anywhere and is set via `wrangler secret put`.
-- Every statement below is safe to re-run against a project that already has
-- these objects (drop-if-exists guards), which the first version lacked.

create table if not exists public.kakao_cs_events_habix_legal (
  event_id text primary key,
  provider text not null check (provider = 'kakao_openbuilder'),
  provider_event_id text not null,
  received_at timestamptz not null,
  canonical_event jsonb not null,
  created_at timestamptz not null default now(),
  approval_ref text not null check (approval_ref ~ '^APR-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$'),
  expires_at timestamptz not null default (now() + interval '7 days') check (expires_at > created_at),
  category_tag text
);

create table if not exists public.kakao_cs_events_habix_course (
  event_id text primary key,
  provider text not null check (provider = 'kakao_openbuilder'),
  provider_event_id text not null,
  received_at timestamptz not null,
  canonical_event jsonb not null,
  created_at timestamptz not null default now(),
  approval_ref text not null check (approval_ref ~ '^APR-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$'),
  expires_at timestamptz not null default (now() + interval '7 days') check (expires_at > created_at),
  category_tag text
);

alter table public.kakao_cs_events_habix_legal enable row level security;
alter table public.kakao_cs_events_habix_course enable row level security;

-- Writes stay denied for anon/authenticated (RESTRICTIVE, split per command:
-- a single restrictive "for all" policy ANDs against SELECT too and would
-- defeat any later permissive SELECT — not that one exists here anymore).
drop policy if exists "deny anon writes to habix legal kakao events" on public.kakao_cs_events_habix_legal;
create policy "deny anon writes to habix legal kakao events" on public.kakao_cs_events_habix_legal
  as restrictive for insert to anon, authenticated with check (false);
drop policy if exists "deny anon updates to habix legal kakao events" on public.kakao_cs_events_habix_legal;
create policy "deny anon updates to habix legal kakao events" on public.kakao_cs_events_habix_legal
  as restrictive for update to anon, authenticated using (false);
drop policy if exists "deny anon deletes to habix legal kakao events" on public.kakao_cs_events_habix_legal;
create policy "deny anon deletes to habix legal kakao events" on public.kakao_cs_events_habix_legal
  as restrictive for delete to anon, authenticated using (false);
-- No permissive SELECT policy for anon/authenticated: RLS default-deny blocks
-- reads too. Only the Worker's service_role key (bypasses RLS) can read this.
drop policy if exists "allow read to anon" on public.kakao_cs_events_habix_legal;

drop policy if exists "deny anon writes to habix course kakao events" on public.kakao_cs_events_habix_course;
create policy "deny anon writes to habix course kakao events" on public.kakao_cs_events_habix_course
  as restrictive for insert to anon, authenticated with check (false);
drop policy if exists "deny anon updates to habix course kakao events" on public.kakao_cs_events_habix_course;
create policy "deny anon updates to habix course kakao events" on public.kakao_cs_events_habix_course
  as restrictive for update to anon, authenticated using (false);
drop policy if exists "deny anon deletes to habix course kakao events" on public.kakao_cs_events_habix_course;
create policy "deny anon deletes to habix course kakao events" on public.kakao_cs_events_habix_course
  as restrictive for delete to anon, authenticated using (false);
drop policy if exists "allow read to anon" on public.kakao_cs_events_habix_course;

-- Reply-draft approval workflow (loop.habix.ai CS admin V1).
create table if not exists public.reply_drafts (
  draft_id text primary key,
  source_event_ids text[] not null,
  business text not null check (business in ('habix_legal', 'habix_course')),
  conversation_ref text not null,
  content text not null,
  risk_class text not null check (risk_class in ('low', 'medium', 'high', 'critical')),
  status text not null default 'draft' check (status in ('draft', 'awaiting_human_review', 'approved', 'blocked', 'expired')),
  approval_id text,
  external_write boolean not null default false check (external_write = false),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);

alter table public.reply_drafts enable row level security;

drop policy if exists "deny anon/authenticated direct writes to reply_drafts" on public.reply_drafts;
create policy "deny anon/authenticated direct writes to reply_drafts" on public.reply_drafts
  as restrictive for insert to anon, authenticated with check (false);
drop policy if exists "deny anon/authenticated deletes on reply_drafts" on public.reply_drafts;
create policy "deny anon/authenticated deletes on reply_drafts" on public.reply_drafts
  as restrictive for delete to anon, authenticated using (false);
-- No permissive SELECT policy, and no UPDATE policy of any kind: RLS
-- default-deny blocks both for anon/authenticated. The only sanctioned write
-- path is the security-definer RPC below, which runs as the function owner
-- and is not itself subject to the caller's row policies.
drop policy if exists "allow read of reply_drafts to anon" on public.reply_drafts;

-- Audit integrity: an approved row must carry its approval_id, and no other
-- status may claim one. The RPC below is the only writer, but this constraint
-- holds even if a future privileged process (migration, admin script) writes
-- to this table directly.
alter table public.reply_drafts drop constraint if exists reply_drafts_approval_id_consistency;
alter table public.reply_drafts add constraint reply_drafts_approval_id_consistency
  check (
    (status = 'approved' and approval_id is not null)
    or (status <> 'approved' and approval_id is null)
  );

-- Narrow, validated status transition: only draft/awaiting_human_review with
-- expires_at still in the future -> approved. Anything else (already
-- approved/blocked/expired, an expired-but-still-draft row, or an unknown
-- draft_id) raises so the caller can distinguish "nothing happened" from
-- "succeeded", instead of a silent no-op update.
create or replace function public.approve_reply_draft(p_draft_id text)
returns public.reply_drafts
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row public.reply_drafts;
begin
  update public.reply_drafts
  set status = 'approved',
      approval_id = 'APR-LOOP-' || to_char(now(), 'YYYYMMDD') || '-' || substr(md5(random()::text), 1, 8)
  where draft_id = p_draft_id
    and status in ('draft', 'awaiting_human_review')
    and expires_at > now()
  returning * into v_row;

  if v_row.draft_id is null then
    raise exception 'draft % is not in an approvable state', p_draft_id using errcode = '22023';
  end if;

  return v_row;
end;
$$;

-- anon/authenticated get nothing: the Worker calls this RPC with the
-- service_role key, which is not subject to function-level grants at all.
-- This revoke closes the direct hole (anyone with the publishable key could
-- previously call this RPC and approve drafts without going through
-- loop.habix.ai's Basic Auth).
revoke all on function public.approve_reply_draft(text) from public;
revoke execute on function public.approve_reply_draft(text) from anon, authenticated;
