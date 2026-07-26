from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"


class SupabaseMigrationTests(unittest.TestCase):
    def test_test_table_is_private_and_service_role_only(self) -> None:
        migration = (
            MIGRATIONS / "20260726023000_create_kakao_cs_events_test.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("enable row level security", migration)
        self.assertIn(
            "revoke all on table public.kakao_cs_events_test "
            "from public, anon, authenticated",
            migration,
        )
        self.assertIn(
            "grant insert, select on table public.kakao_cs_events_test "
            "to service_role",
            migration,
        )

    def test_governance_migration_records_approval_and_expiry(self) -> None:
        migration = (
            MIGRATIONS / "20260726023030_add_kakao_event_governance.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("approval_ref text", migration)
        self.assertIn("expires_at timestamptz", migration)
        self.assertIn("interval '7 days'", migration)
        self.assertIn("kakao_cs_events_test_approval_ref_format", migration)
        self.assertIn("kakao_cs_events_test_expires_at_idx", migration)
        self.assertNotIn("cron.schedule", migration)

    def test_client_roles_have_an_explicit_deny_policy(self) -> None:
        migration = (
            MIGRATIONS / "20260726024618_deny_client_kakao_event_access.sql"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'create policy "deny client access to synthetic kakao events"',
            migration,
        )
        self.assertIn("to anon, authenticated", migration)
        self.assertIn("using (false)", migration)
        self.assertIn("with check (false)", migration)


if __name__ == "__main__":
    unittest.main()
