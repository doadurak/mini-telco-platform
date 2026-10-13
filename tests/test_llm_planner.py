"""
Unit tests for the LLM planner's response parsing and multi-intent handling.
The LLM is replaced by canned responses — no API calls are made.

Run: pytest tests/test_llm_planner.py -v
"""

import json

import pytest

from backend import llm_planner
from backend.llm_planner import LlmPlanningError, _parse_json_response, build_llm_execution_plan

_LOCATION_PLAN = {
    "service_id": "location-retrieval",
    "operation_id": "retrieveLocation",
    "method": "POST",
    "path": "/location-retrieval/v0.5/retrieve",
    "rationale": "user asks where the device is",
}
_PROFILES_PLAN = {
    "service_id": "qos-profiles",
    "operation_id": "retrieveQoSProfiles",
    "method": "POST",
    "path": "/qos-profiles/v1/retrieve-qos-profiles",
    "rationale": "user asks which profiles exist",
}


# ─── _parse_json_response ────────────────────────────────────────────────────

def test_parse_object():
    assert _parse_json_response('{"a": 1}', "ctx") == {"a": 1}


def test_parse_strips_code_fence():
    assert _parse_json_response('```json\n{"a": 1}\n```', "ctx") == {"a": 1}


def test_parse_list_rejected_by_default():
    with pytest.raises(LlmPlanningError, match="expected JSON object, got list"):
        _parse_json_response('[{"a": 1}]', "ctx")


def test_parse_list_allowed():
    assert _parse_json_response('[{"a": 1}, {"b": 2}]', "ctx", allow_list=True) == [{"a": 1}, {"b": 2}]


@pytest.mark.parametrize("text", ["[]", "[1, 2]", '"plan"'])
def test_parse_list_must_hold_objects(text):
    with pytest.raises(LlmPlanningError):
        _parse_json_response(text, "ctx", allow_list=True)


# ─── active_llm_configured (auto-mode LLM attempt) ───────────────────────────

@pytest.mark.parametrize("provider,key_attr", [
    ("openai", "openai_api_key"), ("anthropic", "anthropic_api_key"), ("gemini", "gemini_api_key"),
])
def test_active_llm_configured_follows_active_provider(monkeypatch, provider, key_attr):
    for attr in ("openai_api_key", "anthropic_api_key", "gemini_api_key"):
        monkeypatch.setattr(llm_planner.settings, attr, "")
    monkeypatch.setattr(llm_planner, "_llm_provider_override", provider)
    assert not llm_planner.active_llm_configured()
    monkeypatch.setattr(llm_planner.settings, key_attr, "key")
    assert llm_planner.active_llm_configured()


# ─── build_llm_execution_plan ────────────────────────────────────────────────

@pytest.fixture
def fake_llm(monkeypatch):
    """Serve canned LLM texts in order; returns the list of prompts received."""
    prompts: list[str] = []

    def install(*texts: str):
        queue = list(texts)

        def _call(prompt):
            prompts.append(prompt)
            return {"text": queue.pop(0)}, "fake"

        monkeypatch.setattr(llm_planner, "_call_llm", _call)
        monkeypatch.setattr(llm_planner, "_extract_text", lambda resp, provider: resp["text"])
        monkeypatch.setattr(llm_planner, "_discovery_grounding", lambda: (False, [], None))
        return prompts

    return install


def test_single_plan_gives_one_step(fake_llm):
    prompts = fake_llm(json.dumps(_LOCATION_PLAN), json.dumps({"device": {"phoneNumber": "+81312345678"}}))
    steps, meta = build_llm_execution_plan("Where is +81312345678?")
    assert [s.service_id for s in steps] == ["location-retrieval"]
    assert len(prompts) == 2
    assert meta.raw_plan["phase2_payload"] == {"device": {"phoneNumber": "+81312345678"}}


def test_multi_intent_list_gives_ordered_steps(fake_llm):
    prompts = fake_llm(
        json.dumps([_LOCATION_PLAN, _PROFILES_PLAN]),
        json.dumps({"device": {"phoneNumber": "+81312345678"}, "maxAge": 60}),
        json.dumps({"device": {"phoneNumber": "+81312345678"}}),
    )
    steps, meta = build_llm_execution_plan(
        "Tell me where +81312345678 is and also list its available QoS profiles"
    )
    # first-mentioned request is the primary step; one Phase-2 call per step
    assert [s.service_id for s in steps] == ["location-retrieval", "qos-profiles"]
    assert steps[0].payload["maxAge"] == 60
    assert len(prompts) == 3
    assert isinstance(meta.raw_plan["phase1_plan"], list)


def test_multi_intent_rejects_unknown_service(fake_llm):
    fake_llm(json.dumps([_LOCATION_PLAN, {**_PROFILES_PLAN, "service_id": "teleport"}]))
    with pytest.raises(LlmPlanningError, match="unsupported service 'teleport'"):
        build_llm_execution_plan("Where is +81312345678 and teleport it")
