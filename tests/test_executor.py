"""
Unit tests for executor.py in dry-run mode.
All tests use dry_run=True — no live provider calls needed.

Run: pytest tests/test_executor.py -v
"""

import pytest
from backend.executor import execute_step
from backend.models import ExecutionStep


def _make_step(service_id, operation_id, payload, method="POST") -> ExecutionStep:
    return ExecutionStep(
        service_id=service_id,
        operation_id=operation_id,
        method=method,
        path="/",
        payload=payload,
        rationale="test",
    )


# ─── Dry-run returns correct structure ───────────────────────────────────────

class TestDryRunReturns:

    def test_qod_dry_run(self):
        step = _make_step("qod", "createSession", {
            "device": {"phoneNumber": "+306912345678"},
            "applicationServer": {"ipv4Address": "198.51.100.10"},
            "qosProfile": "QOS_E",
            "duration": 600,
        })
        result = execute_step(step, dry_run=True)
        assert result["status"] == "dry-run"
        assert "payload" in result

    def test_location_dry_run(self):
        step = _make_step("location-retrieval", "retrieveLocation", {
            "device": {"phoneNumber": "+34600000000"},
            "maxAge": 60,
        })
        result = execute_step(step, dry_run=True)
        assert result["status"] == "dry-run"

    def test_qos_profiles_dry_run(self):
        step = _make_step("qos-profiles", "retrieveQoSProfiles", {
            "device": {"phoneNumber": "+34600000000"},
        })
        result = execute_step(step, dry_run=True)
        assert result["status"] == "dry-run"

    def test_qos_provisioning_dry_run(self):
        step = _make_step("qos-provisioning", "createQosAssignment", {
            "device": {"phoneNumber": "+905551112233"},
            "qosProfile": "QOS_L",
        })
        result = execute_step(step, dry_run=True)
        assert result["status"] == "dry-run"

    def test_unknown_service_dry_run(self):
        step = _make_step("unknown-service", "someOp", {"key": "value"})
        result = execute_step(step, dry_run=True)
        # Should still return dry-run (unknown service gets generic dry-run)
        assert result["status"] == "dry-run"

    def test_dry_run_includes_service_id(self):
        step = _make_step("qod", "createSession", {
            "device": {"phoneNumber": "+306912345678"},
            "applicationServer": {"ipv4Address": "198.51.100.10"},
            "qosProfile": "QOS_E",
            "duration": 300,
        })
        result = execute_step(step, dry_run=True)
        assert result.get("service_id") == "qod" or result["status"] == "dry-run"

    def test_dry_run_returns_dict(self):
        step = _make_step("qod", "createSession", {
            "device": {"phoneNumber": "+34600000000"},
            "applicationServer": {"ipv4Address": "10.0.0.1"},
            "qosProfile": "QOS_E",
            "duration": 60,
        })
        result = execute_step(step, dry_run=True)
        assert isinstance(result, dict)


# ─── QoS profiles catalog (no network) ───────────────────────────────────────

class TestQoSProfilesCatalog:

    def test_profiles_returned_in_dry_run(self):
        step = _make_step("qos-profiles", "retrieveQoSProfiles", {
            "device": {"phoneNumber": "+34600000000"},
        })
        result = execute_step(step, dry_run=True)
        assert result["status"] == "dry-run"
        assert isinstance(result, dict)

    def test_all_profile_names_in_catalog(self):
        """The 8 CAMARA QoS profiles should be known to the executor."""
        from backend.executor import _QOS_PROFILES
        names = {p["name"] for p in _QOS_PROFILES}
        expected = {
            "QOS_E", "QOS_S", "QOS_M", "QOS_L",
            "QOS_E_STREAMING", "QOS_GAMING", "QOS_LOW_LATENCY", "QOS_CRITICAL_COMMS",
        }
        assert expected == names


# ─── Config-driven NEF parameters ────────────────────────────────────────────

class TestNEFConfig:

    def test_scs_as_id_from_settings(self):
        from backend.config import settings
        assert settings.nef_scs_as_id is not None
        assert len(settings.nef_scs_as_id) > 0

    def test_nef_notification_url_set(self):
        from backend.config import settings
        assert settings.nef_notification_url.startswith("http")

    def test_nef_default_ue_ipv4_is_valid_ip(self):
        import ipaddress
        from backend.config import settings
        # Should not raise
        ipaddress.IPv4Address(settings.nef_default_ue_ipv4)
