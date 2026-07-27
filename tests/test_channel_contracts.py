import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / "contracts"
POLICY_PATH = ROOT / "policies" / "providers-kr.example.json"

SCHEMA_NAMES = (
    "cs-event.schema.json",
    "channel-connection.schema.json",
    "reply-draft.schema.json",
    "delivery-event.schema.json",
    "connector-state.schema.json",
)

PROHIBITED_RAW_FIELDS = {
    "secret",
    "secret_key",
    "callback_secret",
    "password",
    "api_key",
    "access_token",
    "refresh_token",
    "phone",
    "phone_number",
    "recipient_no",
    "recipient_phone",
    "email",
    "email_address",
}


def load_json(path: Path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def assert_valid(test_case: unittest.TestCase, schema, instance):
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(instance),
        key=lambda error: list(error.path),
    )
    test_case.assertEqual([], errors, "\n".join(error.message for error in errors))


def assert_invalid(test_case: unittest.TestCase, schema, instance):
    errors = list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(instance)
    )
    test_case.assertTrue(errors, "Instance unexpectedly satisfied the schema")


def walk_object_schemas(node):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for value in node.values():
            yield from walk_object_schemas(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_object_schemas(value)


def walk_property_names(node):
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            yield from properties
        for value in node.values():
            yield from walk_property_names(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_property_names(value)


class ChannelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {
            name: load_json(CONTRACT_DIR / name)
            for name in SCHEMA_NAMES
        }
        cls.policy = load_json(POLICY_PATH)

    def test_schemas_are_draft_2020_12_and_closed_objects(self):
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(schema)
                self.assertEqual(
                    "https://json-schema.org/draft/2020-12/schema",
                    schema["$schema"],
                )
                for object_schema in walk_object_schemas(schema):
                    self.assertIs(
                        False,
                        object_schema.get("additionalProperties"),
                        f"{name} has an open object schema",
                    )

    def test_schemas_do_not_define_raw_secret_or_contact_fields(self):
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                present = set(walk_property_names(schema))
                self.assertFalse(
                    present & PROHIBITED_RAW_FIELDS,
                    f"{name} defines prohibited fields: "
                    f"{sorted(present & PROHIBITED_RAW_FIELDS)}",
                )

    def test_cs_event_accepts_redacted_event_and_rejects_raw_fields(self):
        schema = self.schemas["cs-event.schema.json"]
        event = {
            "event_id": "CSE-20260726-0001",
            "provider": "channel_talk",
            "provider_event_id": "provider-event-001",
            "channel": "channel_talk",
            "direction": "inbound",
            "event_type": "message_received",
            "occurred_at": "2026-07-26T01:00:00Z",
            "received_at": "2026-07-26T01:00:01Z",
            "conversation_ref": "hmac:conversation_0001",
            "message_ref": "hmac:message_ref_0001",
            "customer_ref_hmac": "hmac:customer_ref_0001",
            "content_redacted": "[customer] requested an order-status check",
            "attachment_metadata": [],
            "raw_payload_ref": "restricted://cs/channel-talk/event-001",
            "privacy": {
                "classification": "restricted",
                "redaction_status": "redacted",
                "pii_types_removed": [
                    "name",
                    "phone",
                    "email",
                ],
            },
            "consent_or_processing_basis_ref": "POL-CS-001",
            "idempotency_key": "channel-talk:event-001",
            "auth_verified": False,
            "verification_assurance": "none",
            "provider_status": None,
            "canonical_status": "received",
            "source_evidence_ids": [
                "EV-FIXTURE-001",
            ],
        }
        assert_valid(self, schema, event)

        for raw_field, value in (
            ("phone", "01000000000"),
            ("email", "customer@example.invalid"),
            ("access_token", "not-a-real-token"),
            ("secret", "not-a-real-secret"),
        ):
            with self.subTest(raw_field=raw_field):
                unsafe = copy.deepcopy(event)
                unsafe[raw_field] = value
                assert_invalid(self, schema, unsafe)

        wrong_kakao_product = copy.deepcopy(event)
        wrong_kakao_product["provider"] = "kakao_openbuilder"
        wrong_kakao_product["channel"] = "kakao_consulttalk"
        assert_invalid(self, schema, wrong_kakao_product)

    def test_connections_default_safe_and_enforce_write_boundary(self):
        schema = self.schemas["channel-connection.schema.json"]
        self.assertEqual("read_only", schema["properties"]["mode"]["default"])
        self.assertIs(
            False,
            schema["properties"]["external_write_enabled"]["default"],
        )

        connection = {
            "connection_id": "CONN-20260726-001",
            "provider": "channel_talk",
            "region": "kr",
            "environment": "test",
            "mode": "read_only",
            "credential_ref": "secret://channel-talk/test",
            "capabilities": [
                {
                    "name": "webhook_ingest",
                    "support": "supported",
                    "access_mode": "read_only",
                    "source_ref": "providers-kr:channel_talk",
                }
            ],
            "retention_policy_ref": "POL-RET-001",
            "approved_by": None,
            "verified_at": None,
            "external_write_enabled": False,
        }
        assert_valid(self, schema, connection)

        unsafe = copy.deepcopy(connection)
        unsafe["external_write_enabled"] = True
        assert_invalid(self, schema, unsafe)

        approved = copy.deepcopy(connection)
        approved["mode"] = "approved_write"
        approved["approved_by"] = "APR-CONNECTION-001"
        approved["external_write_enabled"] = True
        assert_valid(self, schema, approved)

        missing_approval = copy.deepcopy(approved)
        missing_approval["approved_by"] = None
        assert_invalid(self, schema, missing_approval)

    def test_reply_draft_is_draft_only_even_after_approval(self):
        schema = self.schemas["reply-draft.schema.json"]
        self.assertEqual("draft", schema["properties"]["status"]["default"])
        self.assertIs(False, schema["properties"]["external_write"]["default"])

        draft = {
            "draft_id": "DRAFT-20260726-001",
            "source_event_ids": [
                "CSE-20260726-0001",
            ],
            "conversation_ref": "hmac:conversation_0001",
            "provider": "channel_talk",
            "product": "channel_talk",
            "session_state": "active",
            "content": "확인 후 안내드리겠습니다.",
            "template_ref": None,
            "template_variables": [],
            "risk_class": "low",
            "status": "draft",
            "approval_id": None,
            "expires_at": "2026-07-27T01:00:00Z",
            "external_write": False,
        }
        assert_valid(self, schema, draft)

        unsafe = copy.deepcopy(draft)
        unsafe["external_write"] = True
        assert_invalid(self, schema, unsafe)

        approved = copy.deepcopy(draft)
        approved["status"] = "approved"
        approved["approval_id"] = "APR-REVIEW-001"
        assert_valid(self, schema, approved)
        approved["external_write"] = True
        assert_invalid(self, schema, approved)

    def test_delivery_acceptance_is_not_delivery(self):
        schema = self.schemas["delivery-event.schema.json"]
        statuses = schema["properties"]["canonical_status"]["enum"]
        self.assertIn("accepted", statuses)
        self.assertIn("delivered", statuses)
        self.assertNotEqual(statuses.index("accepted"), statuses.index("delivered"))

        accepted = {
            "delivery_event_id": "DLE-20260726-001",
            "attempt_id": "ATT-20260726-001",
            "provider": "nhn_cloud",
            "product": "alimtalk",
            "channel": "kakao",
            "occurred_at": "2026-07-26T02:00:00Z",
            "received_at": "2026-07-26T02:00:01Z",
            "status_observed_at": "2026-07-26T02:00:00Z",
            "provider_message_ref": "hmac:provider_message_001",
            "provider_status": "REQUEST_ACCEPTED",
            "canonical_status": "accepted",
            "attempt_kind": "primary",
            "parent_attempt_ref": None,
            "transport": "kakao",
            "fallback_applied": False,
            "idempotency_key": "nhn-cloud:attempt-001",
            "raw_payload_ref": "restricted://delivery/nhn/event-001",
            "auth_verified": True,
            "verification_assurance": "medium",
            "source_evidence_ids": [
                "EV-FIXTURE-DELIVERY-001",
            ],
        }
        assert_valid(self, schema, accepted)
        self.assertEqual("accepted", accepted["canonical_status"])
        self.assertNotEqual("delivered", accepted["canonical_status"])

        false_delivery = copy.deepcopy(accepted)
        false_delivery["canonical_status"] = "delivered"
        assert_invalid(self, schema, false_delivery)

        delivered = copy.deepcopy(accepted)
        delivered["delivery_event_id"] = "DLE-20260726-002"
        delivered["provider_status"] = "DELIVERED"
        delivered["canonical_status"] = "delivered"
        assert_valid(self, schema, delivered)

        ambiguous = copy.deepcopy(accepted)
        ambiguous["canonical_status"] = "success"
        assert_invalid(self, schema, ambiguous)

    def test_fallback_is_a_separate_linked_attempt(self):
        schema = self.schemas["delivery-event.schema.json"]
        fallback = {
            "delivery_event_id": "DLE-20260726-003",
            "attempt_id": "ATT-20260726-002",
            "provider": "solapi",
            "product": "sms",
            "channel": "sms",
            "occurred_at": "2026-07-26T02:05:00Z",
            "received_at": "2026-07-26T02:05:01Z",
            "status_observed_at": "2026-07-26T02:05:00Z",
            "provider_message_ref": "hmac:provider_message_002",
            "provider_status": "QUEUED",
            "canonical_status": "queued",
            "attempt_kind": "fallback",
            "parent_attempt_ref": "ATT-20260726-001",
            "transport": "sms",
            "fallback_applied": True,
            "idempotency_key": "solapi:fallback-attempt-002",
            "raw_payload_ref": "restricted://delivery/solapi/event-002",
            "auth_verified": True,
            "verification_assurance": "medium",
            "source_evidence_ids": [
                "EV-FIXTURE-DELIVERY-002",
            ],
        }
        assert_valid(self, schema, fallback)

        unlinked = copy.deepcopy(fallback)
        unlinked["parent_attempt_ref"] = None
        assert_invalid(self, schema, unlinked)

    def test_connector_state_defaults_safe(self):
        schema = self.schemas["connector-state.schema.json"]
        self.assertEqual("read_only", schema["properties"]["mode"]["default"])
        self.assertIs(
            False,
            schema["properties"]["external_write_enabled"]["default"],
        )

        state = {
            "connection_id": "CONN-20260726-001",
            "provider": "channel_talk",
            "mode": "read_only",
            "external_write_enabled": False,
            "cursor": None,
            "last_webhook_at": None,
            "last_backfill_at": None,
            "last_reconciled_at": None,
            "ingested_count": 0,
            "duplicate_count": 0,
            "dead_letter_count": 0,
            "blocked_reasons": [],
            "health": "unknown",
            "verification_level": "none",
        }
        assert_valid(self, schema, state)

        unsafe = copy.deepcopy(state)
        unsafe["external_write_enabled"] = True
        assert_invalid(self, schema, unsafe)

    def test_provider_registry_is_safe_by_default_and_source_backed(self):
        defaults = self.policy["defaults"]
        self.assertEqual("read_only", defaults["connection_mode"])
        self.assertEqual("draft_only", defaults["reply_mode"])
        self.assertIs(False, defaults["external_write_enabled"])
        self.assertIs(False, defaults["fallback_enabled"])
        self.assertIs(False, defaults["marketing_enabled"])
        self.assertIs(False, defaults["accepted_is_terminal"])

        providers = self.policy["providers"]
        self.assertGreaterEqual(len(providers), 6)
        for provider in providers:
            with self.subTest(provider=provider["provider_id"]):
                self.assertIn(
                    provider["connection_mode"],
                    {"read_only", "draft_only"},
                )
                self.assertIs(
                    False,
                    provider["status_semantics"]["accepted_is_terminal"],
                )
                self.assertEqual(
                    "accepted",
                    provider["status_semantics"]["request_acceptance"],
                )
                self.assertEqual(
                    "delivered",
                    provider["status_semantics"]["terminal_success"],
                )
                self.assertTrue(
                    provider["source"]["document_url"].startswith("https://")
                )
                self.assertEqual("2026-07-26", provider["source"]["checked_at"])
                self.assertIs(False, provider["source"]["live_account_verified"])
                for capability in provider["capabilities"]:
                    if capability["name"].endswith("_send"):
                        self.assertEqual(
                            "disabled_by_policy",
                            capability["status"],
                        )


if __name__ == "__main__":
    unittest.main()
