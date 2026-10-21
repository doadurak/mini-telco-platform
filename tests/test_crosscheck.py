"""
The service cross-check in POST /orchestrate: a live LLM plan whose service differs from the
keyword planner's is held until the operator confirms it. The LLM and the provider are faked.

Run: pytest tests/test_crosscheck.py -v
"""

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.models import ExecutionStep, PlannerMetadata

_INTENT = "Provide network quality improvement for device +905551112233 for a long time"
_PROVISIONING = ExecutionStep(service_id="qos-provisioning", operation_id="createQosAssignment", method="POST",
                              path="/qos-assignments", rationale="long-lived QoS",
                              payload={"device": {"phoneNumber": "+905551112233"}, "qosProfile": "QOS_E"})


@pytest.fixture
def client(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "build_llm_execution_plan",
                        lambda intent: ([_PROVISIONING], PlannerMetadata(strategy="llm-assisted")))
    monkeypatch.setattr(main, "execute_step", lambda step, dry_run: calls.append(dry_run) or {"status": "created"})
    return TestClient(main.app), calls


def _post(c, **kw):
    body = {"intent": _INTENT, "check_registry": False, "orchestration_mode": "llm-assisted", **kw}
    return c.post("/orchestrate", json=body).json()


def test_disagreement_holds_live_call(client):
    c, calls = client
    d = _post(c, dry_run=False)
    assert d["service_crosscheck"] == {"keyword_planner_service": "qod", "agrees": False, "held": True}
    assert d["execution_result"]["status"] == "held-for-confirmation"
    assert calls == []


def test_confirmation_releases_live_call(client):
    c, calls = client
    d = _post(c, dry_run=False, confirm_service=True)
    assert d["service_crosscheck"]["held"] is False
    assert calls == [False]


def test_dry_run_is_never_held(client):
    c, calls = client
    d = _post(c, dry_run=True)
    assert d["service_crosscheck"]["agrees"] is False and d["service_crosscheck"]["held"] is False
    assert calls == [True]
