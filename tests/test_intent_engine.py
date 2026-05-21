"""
Unit tests for the deterministic intent engine.
Tests keyword routing, service selection, and payload generation.

Run: pytest tests/test_intent_engine.py -v
"""

import pytest
from backend.intent_engine import build_execution_plan


# ─── Service routing ──────────────────────────────────────────────────────────

class TestServiceRouting:

    def test_qod_default_english(self):
        mode, steps = build_execution_plan("Boost video for +306912345678 for 10 minutes")
        assert mode == "deterministic"
        assert steps[0].service_id == "qod"

    def test_qod_default_turkish(self):
        _, steps = build_execution_plan("+905551112233 için 5 dakika QoS iyileştir")
        assert steps[0].service_id == "qod"

    def test_location_english(self):
        _, steps = build_execution_plan("Where is device +306912345678?")
        assert steps[0].service_id == "location-retrieval"

    def test_location_turkish(self):
        _, steps = build_execution_plan("+905551112233 nerede?")
        assert steps[0].service_id == "location-retrieval"

    def test_location_keyword_locate(self):
        _, steps = build_execution_plan("Locate device +34600000000")
        assert steps[0].service_id == "location-retrieval"

    def test_location_keyword_gps(self):
        _, steps = build_execution_plan("Get GPS coordinates for +12025550180")
        assert steps[0].service_id == "location-retrieval"

    def test_provisioning_permanent(self):
        _, steps = build_execution_plan("Permanently assign QOS_L to +905551112233")
        assert steps[0].service_id == "qos-provisioning"

    def test_provisioning_kalici(self):
        _, steps = build_execution_plan("+905551112233 cihazına kalıcı QOS_M ata")
        assert steps[0].service_id == "qos-provisioning"

    def test_qos_profiles_list(self):
        _, steps = build_execution_plan("List available QoS profiles for +34600000000")
        assert steps[0].service_id == "qos-profiles"

    def test_qos_profiles_turkish(self):
        _, steps = build_execution_plan("Hangi QoS profilleri mevcut?")
        assert steps[0].service_id == "qos-profiles"


# ─── Payload validation ───────────────────────────────────────────────────────

class TestQoDPayload:

    def test_phone_number_included(self):
        _, steps = build_execution_plan("QoS boost for +306912345678 for 5 minutes")
        payload = steps[0].payload
        assert payload["device"]["phoneNumber"] == "+306912345678"

    def test_duration_minutes_converted(self):
        _, steps = build_execution_plan("QoD session for +34600000000 for 10 minutes")
        payload = steps[0].payload
        assert payload["duration"] == 600  # 10 * 60

    def test_duration_seconds_kept(self):
        _, steps = build_execution_plan("QoD session for +34600000000 for 300 seconds")
        payload = steps[0].payload
        assert payload["duration"] == 300

    def test_qos_profile_set_for_streaming_hint(self):
        """Intent with 'streaming' hint should map to QOS_E_STREAMING."""
        _, steps = build_execution_plan("Boost video streaming for +905551112233 for 5 minutes")
        payload = steps[0].payload
        assert payload["qosProfile"] == "QOS_E_STREAMING"

    def test_application_server_present(self):
        _, steps = build_execution_plan("Boost network for +12025550180 for 1 hour")
        payload = steps[0].payload
        assert "applicationServer" in payload

    def test_duration_hours_converted(self):
        """'5 hours' should be parsed as 5*3600 = 18000 s (no cap at planner level)."""
        _, steps = build_execution_plan("QoD session for +34600000000 for 5 hours")
        payload = steps[0].payload
        assert payload["duration"] == 18000  # cap is enforced by validator, not planner


class TestLocationPayload:

    def test_phone_in_device(self):
        _, steps = build_execution_plan("Where is +306912345678?")
        payload = steps[0].payload
        assert payload["device"]["phoneNumber"] == "+306912345678"

    def test_max_age_field_name(self):
        """maxAge must be 'maxAge', not 'maxAgeSeconds'."""
        _, steps = build_execution_plan("Get location of +34600000000")
        payload = steps[0].payload
        assert "maxAge" in payload
        assert "maxAgeSeconds" not in payload


class TestProvisioningPayload:

    def test_phone_in_device(self):
        _, steps = build_execution_plan("Permanently set QOS_E for +905551112233")
        payload = steps[0].payload
        assert payload["device"]["phoneNumber"] == "+905551112233"

    def test_qos_profile_present(self):
        _, steps = build_execution_plan("Permanent QOS_M for +34600000000")
        payload = steps[0].payload
        assert "qosProfile" in payload


# ─── Edge cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_no_phone_uses_default(self):
        """Intent without a phone number should still return valid steps."""
        _, steps = build_execution_plan("Boost network quality")
        assert steps[0].service_id in ("qod", "location-retrieval", "qos-profiles", "qos-provisioning")
        assert len(steps) > 0

    def test_mixed_language_intent(self):
        """Mixed EN/TR intents should still route correctly."""
        _, steps = build_execution_plan("location nerede +306912345678")
        assert steps[0].service_id == "location-retrieval"

    def test_steps_not_empty(self):
        _, steps = build_execution_plan("do something with +34600000000")
        assert len(steps) >= 1

    def test_operation_id_set(self):
        _, steps = build_execution_plan("QoD for +34600000000 for 5 minutes")
        assert steps[0].operation_id is not None
        assert len(steps[0].operation_id) > 0
