import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.channel_contracts import (  # noqa: E402
    CanonicalDeliveryEvent,
    CanonicalStatus,
    VerificationAssurance,
)
from signal_growth.connector_state import DeliveryStateProjector  # noqa: E402


def delivery_event(
    delivery_event_id: str,
    status: CanonicalStatus,
    observed_at: str,
    *,
    attempt_id: str = "ATT-PUBLIC-DUMMY-001",
    transport: str = "kakao",
    attempt_kind: str = "primary",
    parent_attempt_ref: str | None = None,
    fallback_applied: bool = False,
) -> CanonicalDeliveryEvent:
    return CanonicalDeliveryEvent(
        delivery_event_id=delivery_event_id,
        attempt_id=attempt_id,
        provider="public_dummy_dealer",
        product="alimtalk" if transport == "kakao" else "sms",
        channel=transport,
        occurred_at=observed_at,
        received_at=observed_at,
        status_observed_at=observed_at,
        provider_message_ref="ref:public_dummy_message",
        provider_status=status.value.upper(),
        canonical_status=status,
        attempt_kind=attempt_kind,
        parent_attempt_ref=parent_attempt_ref,
        transport=transport,
        fallback_applied=fallback_applied,
        idempotency_key=f"{delivery_event_id}:public-dummy",
        raw_payload_ref=None,
        auth_verified=False,
        verification_assurance=VerificationAssurance.NONE,
    )


class ConnectorRecoveryTests(unittest.TestCase):
    def test_acceptance_can_advance_to_delivery_but_not_regress(self):
        projector = DeliveryStateProjector()
        accepted = projector.project(
            delivery_event(
                "DLE-PUBLIC-DUMMY-001",
                CanonicalStatus.ACCEPTED,
                "2026-07-26T03:00:00Z",
            )
        )
        self.assertEqual(CanonicalStatus.ACCEPTED, accepted.state.current_status)
        delivered = projector.project(
            delivery_event(
                "DLE-PUBLIC-DUMMY-002",
                CanonicalStatus.DELIVERED,
                "2026-07-26T03:01:00Z",
            )
        )
        regressed = projector.project(
            delivery_event(
                "DLE-PUBLIC-DUMMY-003",
                CanonicalStatus.SENT,
                "2026-07-26T03:02:00Z",
            )
        )

        self.assertTrue(delivered.applied)
        self.assertEqual(CanonicalStatus.DELIVERED, delivered.state.current_status)
        self.assertFalse(regressed.applied)
        self.assertEqual("non_regressing_transition", regressed.reason)
        self.assertEqual(CanonicalStatus.DELIVERED, regressed.state.current_status)

    def test_duplicate_delivery_event_is_idempotent(self):
        projector = DeliveryStateProjector()
        event = delivery_event(
            "DLE-PUBLIC-DUMMY-004",
            CanonicalStatus.ACCEPTED,
            "2026-07-26T03:00:00Z",
        )

        first = projector.project(event)
        duplicate = projector.project(event)

        self.assertTrue(first.applied)
        self.assertFalse(duplicate.applied)
        self.assertEqual("duplicate_event", duplicate.reason)
        self.assertEqual(1, len(duplicate.state.applied_delivery_event_ids))

    def test_fallback_is_projected_as_a_separate_attempt(self):
        projector = DeliveryStateProjector()
        primary = delivery_event(
            "DLE-PUBLIC-DUMMY-005",
            CanonicalStatus.FAILED,
            "2026-07-26T03:00:00Z",
        )
        fallback = delivery_event(
            "DLE-PUBLIC-DUMMY-006",
            CanonicalStatus.QUEUED,
            "2026-07-26T03:01:00Z",
            attempt_id="ATT-PUBLIC-DUMMY-002",
            transport="sms",
            attempt_kind="fallback",
            parent_attempt_ref="ATT-PUBLIC-DUMMY-001",
            fallback_applied=True,
        )

        projector.project(primary)
        projector.project(fallback)

        attempts = projector.attempts()
        self.assertEqual(2, len(attempts))
        self.assertEqual(
            CanonicalStatus.FAILED,
            projector.get("ATT-PUBLIC-DUMMY-001", "kakao").current_status,
        )
        self.assertEqual(
            CanonicalStatus.QUEUED,
            projector.get("ATT-PUBLIC-DUMMY-002", "sms").current_status,
        )


if __name__ == "__main__":
    unittest.main()
