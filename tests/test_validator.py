"""
Unit tests for the three-layer validator.
Tests L1 (schema), L2 (telecom semantic), and registry skip behavior.

Run: pytest tests/test_validator.py -v
"""

import pytest
from backend.validator import validate_step


def _validate(service_id, payload, operation_id=None, method="POST", skip_registry=True):
    return validate_step(
        service_id=service_id,
        payload=payload,
        operation_id=operation_id,
        method=method,
        skip_registry=skip_registry,
    )


# ─── QoD Session ─────────────────────────────────────────────────────────────

class TestQoDValidation:

    VALID_PAYLOAD = {
        "device": {"phoneNumber": "+306912345678"},
        "applicationServer": {"ipv4Address": "198.51.100.10"},
        "qosProfile": "QOS_E",
        "duration": 600,
    }

    def test_valid_qod_passes_all_layers(self):
        r = _validate("qod", self.VALID_PAYLOAD, operation_id="createSession")
        assert r.valid is True
        assert r.layer1_schema.passed
        assert r.layer2_semantic.passed

    def test_missing_device_fails_l1(self):
        payload = {k: v for k, v in self.VALID_PAYLOAD.items() if k != "device"}
        r = _validate("qod", payload, operation_id="createSession")
        assert r.valid is False
        assert not r.layer1_schema.passed

    def test_invalid_phone_fails_l2(self):
        payload = {**self.VALID_PAYLOAD, "device": {"phoneNumber": "06551234"}}
        r = _validate("qod", payload, operation_id="createSession")
        assert r.valid is False
        assert not r.layer2_semantic.passed

    def test_invalid_qos_profile_fails_l2(self):
        payload = {**self.VALID_PAYLOAD, "qosProfile": "QOS_INVALID"}
        r = _validate("qod", payload, operation_id="createSession")
        assert r.valid is False
        assert not r.layer2_semantic.passed

    def test_duration_zero_fails_l2(self):
        payload = {**self.VALID_PAYLOAD, "duration": 0}
        r = _validate("qod", payload, operation_id="createSession")
        assert r.valid is False

    def test_duration_over_7200_fails_l2(self):
        payload = {**self.VALID_PAYLOAD, "duration": 7201}
        r = _validate("qod", payload, operation_id="createSession")
        assert r.valid is False

    def test_duration_7200_passes(self):
        payload = {**self.VALID_PAYLOAD, "duration": 7200}
        r = _validate("qod", payload, operation_id="createSession")
        assert r.valid is True

    def test_all_valid_qos_profiles(self):
        valid_profiles = [
            "QOS_E", "QOS_S", "QOS_M", "QOS_L",
            "QOS_E_STREAMING", "QOS_GAMING", "QOS_LOW_LATENCY", "QOS_CRITICAL_COMMS",
        ]
        for profile in valid_profiles:
            payload = {**self.VALID_PAYLOAD, "qosProfile": profile}
            r = _validate("qod", payload, operation_id="createSession")
            assert r.valid is True, f"Profile {profile} should be valid"

    def test_ipv6_device_valid(self):
        payload = {
            **self.VALID_PAYLOAD,
            "device": {"ipv6Address": "2001:db8::1"},
        }
        r = _validate("qod", payload, operation_id="createSession")
        assert r.valid is True


# ─── Location Retrieval ───────────────────────────────────────────────────────

class TestLocationValidation:

    VALID_PAYLOAD = {
        "device": {"phoneNumber": "+34600000000"},
        "maxAge": 60,
    }

    def test_valid_location_passes(self):
        r = _validate("location-retrieval", self.VALID_PAYLOAD, operation_id="retrieveLocation")
        assert r.valid is True

    def test_missing_device_fails(self):
        r = _validate("location-retrieval", {"maxAge": 60}, operation_id="retrieveLocation")
        assert r.valid is False

    def test_max_age_field_name_correct(self):
        """If maxAge is present with correct name it passes; maxAgeSeconds is ignored (extra field)."""
        # Correct field name passes
        payload = {"device": {"phoneNumber": "+34600000000"}, "maxAge": 60}
        r = _validate("location-retrieval", payload, operation_id="retrieveLocation")
        assert r.valid is True
        # Wrong field name only: validator skips maxAge check since field absent → passes (no hard schema)
        payload2 = {"device": {"phoneNumber": "+34600000000"}, "maxAgeSeconds": 60}
        r2 = _validate("location-retrieval", payload2, operation_id="retrieveLocation")
        # L1 passes (no strict schema), L2 skips maxAge check — result is valid
        assert r2.layer1_schema.passed is True

    def test_max_age_out_of_range_fails(self):
        payload = {**self.VALID_PAYLOAD, "maxAge": 0}
        r = _validate("location-retrieval", payload, operation_id="retrieveLocation")
        assert r.valid is False

    def test_max_age_3600_passes(self):
        payload = {**self.VALID_PAYLOAD, "maxAge": 3600}
        r = _validate("location-retrieval", payload, operation_id="retrieveLocation")
        assert r.valid is True


# ─── QoS Profiles ─────────────────────────────────────────────────────────────

class TestQoSProfilesValidation:

    def test_valid_profiles_list_request(self):
        payload = {"device": {"phoneNumber": "+34600000000"}}
        r = _validate("qos-profiles", payload, operation_id="retrieveQoSProfiles")
        assert r.valid is True

    def test_single_profile_request_get(self):
        """getQosProfile operation requires GET method per service catalog."""
        payload = {"device": {"phoneNumber": "+34600000000"}, "qosProfile": "QOS_E"}
        r = _validate("qos-profiles", payload, operation_id="getQosProfile", method="GET")
        assert r.valid is True

    def test_single_profile_request_post_fails(self):
        """getQosProfile with POST method should fail L2 method check."""
        payload = {"device": {"phoneNumber": "+34600000000"}, "qosProfile": "QOS_E"}
        r = _validate("qos-profiles", payload, operation_id="getQosProfile", method="POST")
        assert r.valid is False


# ─── QoS Provisioning ─────────────────────────────────────────────────────────

class TestQoSProvisioningValidation:

    VALID_PAYLOAD = {
        "device": {"phoneNumber": "+905551112233"},
        "qosProfile": "QOS_L",
    }

    def test_valid_provisioning_passes(self):
        r = _validate("qos-provisioning", self.VALID_PAYLOAD, operation_id="createQosAssignment")
        assert r.valid is True

    def test_invalid_profile_fails(self):
        payload = {**self.VALID_PAYLOAD, "qosProfile": "NONEXISTENT"}
        r = _validate("qos-provisioning", payload, operation_id="createQosAssignment")
        assert r.valid is False


# ─── Unknown service ─────────────────────────────────────────────────────────

class TestUnknownService:

    def test_nonexistent_service_fails(self):
        r = _validate("nonexistent-service", {"device": {"phoneNumber": "+34600000000"}})
        assert r.valid is False

    def test_wrong_operation_id_fails_l2(self):
        payload = {
            "device": {"phoneNumber": "+34600000000"},
            "applicationServer": {"ipv4Address": "198.51.100.10"},
            "qosProfile": "QOS_E",
            "duration": 300,
        }
        r = _validate("qod", payload, operation_id="nonExistentOp")
        assert r.valid is False


# ─── Phone number format ──────────────────────────────────────────────────────

class TestPhoneNumberFormats:

    @pytest.mark.parametrize("phone,expected_valid", [
        ("+306912345678", True),
        ("+905551112233", True),
        ("+34600000000",  True),
        ("+12025550180",  True),
        ("00306912345678", False),  # no leading +
        ("306912345678",   False),  # no +
        ("+1234",          False),  # too short
        ("+0306912345678", False),  # starts with +0
    ])
    def test_phone_number_format(self, phone, expected_valid):
        payload = {
            "device": {"phoneNumber": phone},
            "applicationServer": {"ipv4Address": "198.51.100.10"},
            "qosProfile": "QOS_E",
            "duration": 300,
        }
        r = _validate("qod", payload, operation_id="createSession")
        if expected_valid:
            assert r.valid is True, f"Phone {phone} should be valid"
        else:
            assert r.valid is False, f"Phone {phone} should be invalid"
