-- Split operational completion from discovery completion on reply_drafts, and
-- require an owner + deadline before a high/critical-risk draft can be
-- approved. Reflects P6-C02-Clip01's own distinction: 운영 라우팅(완료 기준=
-- 고객에게 응답함, 담당=CS) vs discovery 증거(완료 기준=사람이 신호로 승인함,
-- 담당=PM), and its risk-routing rule that severity high/critical goes to a
-- human owner queue with an explicit owner and deadline, never auto-routed.

alter table public.reply_drafts
  add column if not exists ops_status text not null default 'unresponded'
    check (ops_status in ('unresponded', 'responded')),
  add column if not exists owner text,
  add column if not exists deadline timestamptz;

-- Drop the old single-argument overload explicitly: `create or replace`
-- only replaces a function with the exact same parameter signature, so
-- adding parameters here would otherwise leave the old (text) version
-- callable and able to bypass the new owner/deadline gate entirely.
drop function if exists public.approve_reply_draft(text);

-- Narrow, validated status transition, extended to require an owner and
-- deadline for high/critical risk before approval. Low/medium risk keeps the
-- original no-extra-input path.
create or replace function public.approve_reply_draft(
  p_draft_id text,
  p_owner text default null,
  p_deadline timestamptz default null
)
returns public.reply_drafts
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row public.reply_drafts;
  v_risk text;
begin
  select risk_class into v_risk from public.reply_drafts where draft_id = p_draft_id;

  if v_risk in ('high', 'critical') and (p_owner is null or btrim(p_owner) = '' or p_deadline is null) then
    raise exception 'draft % is high/critical risk and requires an owner and deadline before approval', p_draft_id
      using errcode = 'P0002';
  end if;

  update public.reply_drafts
  set status = 'approved',
      approval_id = 'APR-LOOP-' || to_char(now(), 'YYYYMMDD') || '-' || substr(md5(random()::text), 1, 8),
      owner = coalesce(nullif(btrim(p_owner), ''), owner),
      deadline = coalesce(p_deadline, deadline)
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

revoke all on function public.approve_reply_draft(text, text, timestamptz) from public;
revoke execute on function public.approve_reply_draft(text, text, timestamptz) from anon, authenticated;

-- Operational completion is independent of discovery approval and carries no
-- risk gate: any draft can be marked responded regardless of its approval
-- state, and re-marking is a no-op rather than an error.
create or replace function public.mark_customer_responded(p_draft_id text)
returns public.reply_drafts
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row public.reply_drafts;
begin
  update public.reply_drafts
  set ops_status = 'responded'
  where draft_id = p_draft_id
  returning * into v_row;

  if v_row.draft_id is null then
    raise exception 'draft % does not exist', p_draft_id using errcode = '22023';
  end if;

  return v_row;
end;
$$;

revoke all on function public.mark_customer_responded(text) from public;
revoke execute on function public.mark_customer_responded(text) from anon, authenticated;
