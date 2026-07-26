create policy "deny client access to synthetic kakao events"
on public.kakao_cs_events_test
for all
to anon, authenticated
using (false)
with check (false);

comment on policy "deny client access to synthetic kakao events"
on public.kakao_cs_events_test is
  'Defense in depth: browser roles remain denied even if table grants change.';
