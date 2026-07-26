# Kakao synthetic-event retention

## Scope

This runbook applies only to `public.kakao_cs_events_test`. The table must
contain synthetic test messages, redacted canonical events, and non-secret
approval references. It is not approved for production customer conversations.

## Retention contract

- Each new row receives `expires_at = now() + interval '7 days'`.
- `expires_at` marks when a row becomes eligible for deletion.
- The migration does not schedule automatic deletion.
- Deletion remains an explicit operator action until a reviewed Supabase Cron
  policy is approved.

This distinction prevents a schema default from being reported as an operating
cleanup job.

## Preflight

Before deletion:

1. Confirm the target project and table are the isolated test environment.
2. Confirm the rows contain only synthetic events.
3. Record the approval reference, operator, timestamp, and expected row count.
4. Preview the eligible rows without selecting `canonical_event`.

```sql
select event_id, approval_ref, created_at, expires_at
from public.kakao_cs_events_test
where expires_at <= now()
order by expires_at;
```

## Approved cleanup

Run only after the deletion target and count are approved.

```sql
delete from public.kakao_cs_events_test
where expires_at <= now();
```

Record the deleted row count. Do not add `pg_cron` or another automatic cleanup
job until its schedule, credentials, alerting, and rollback behavior have been
reviewed.
