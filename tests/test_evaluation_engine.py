"""
Evaluation bookkeeping: errors, provenance and --resume. No API calls are made.

Run: pytest tests/test_evaluation_engine.py -v
"""

import json

import pytest

from backend import evaluation_engine as ev
from backend import llm_planner


def _entry(i, ok, difficulty="hard", error=None):
    return ev.EntryResult(entry_id=f"e{i}", intent="x", language="en", difficulty=difficulty, category="c",
                          mode="llm-assisted", expected_service_id="qod", expected_operation_id="createSession",
                          service_correct=ok, l1_passed=ok, l2_passed=ok, iwsr=ok, error=error)


def test_errors_count_as_failures_per_difficulty():
    r = ev.EvaluationReport(mode="llm-assisted")
    r.add(_entry(1, True))
    r.add(_entry(2, False, error="LlmPlanningError: 429"))
    s = r.summary()
    assert s["errors"] == 1
    assert s["metrics"]["IWSR"] == 0.5
    assert s["stratified_iwsr"]["hard"] == 0.5   # used to report 1.0


def test_unknown_provider_is_not_labelled_as_gemini(monkeypatch):
    monkeypatch.setattr(llm_planner, "_llm_provider_override", "gpt")
    assert ev.planner_identity("llm-assisted") == ("gpt", "unknown-provider:gpt")
    assert ev.planner_identity("deterministic") == ("keyword", "keyword-planner")


@pytest.mark.parametrize("prev_model", [None, "gemini-2.5-flash"])
def test_resume_refuses_other_model(tmp_path, monkeypatch, prev_model):
    monkeypatch.setattr(llm_planner, "_llm_provider_override", "openai")
    monkeypatch.setattr(llm_planner.settings, "openai_model", "gpt-4o-mini")
    prev = tmp_path / "prev.json"
    prev.write_text(json.dumps({"summary": {"model": prev_model}, "results": []}))
    with pytest.raises(ValueError, match="--resume file was produced by model"):
        ev.run_evaluation(mode="llm-assisted", resume_from=prev, max_entries=1)
