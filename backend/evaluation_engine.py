"""
Reliability Evaluation Engine

Computes the six reliability metrics defined in the thesis architecture:

  IWSR  — Intent-to-Workflow Success Rate
          % of intents that produce a valid, schema-compliant execution plan

  SCR   — Schema Compliance Rate
          % where the payload passes Layer 1 (JSON schema) validation

  SVR   — Semantic Validity Rate
          % where the payload passes Layer 2 (telecom semantic policy) validation

  HR    — Hallucination Rate
          % where the selected service does NOT match the ground truth

  SS    — Stability Score
          1 - normalised std-dev of IWSR across difficulty strata
          (measures whether reliability degrades for harder intents)

  RRF   — Recovery Rate after Feedback
          % of initially-invalid plans that became valid after feedback loop

Dataset format: datasets/ground_truth.json
"""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config import ROOT_DIR

DATASET_PATH = ROOT_DIR / "datasets" / "ground_truth.json"

VALID_QOS_PROFILES = {
    "QOS_E", "QOS_S", "QOS_M", "QOS_L",
    "QOS_E_STREAMING", "QOS_GAMING", "QOS_LOW_LATENCY", "QOS_CRITICAL_COMMS",
}


# ─── Result objects ──────────────────────────────────────────────────────────

@dataclass
class EntryResult:
    entry_id: str
    intent: str
    language: str
    difficulty: str
    category: str
    mode: str

    # Ground truth
    expected_service_id: str
    expected_operation_id: str

    # Actual output
    actual_service_id: str | None = None
    actual_operation_id: str | None = None
    actual_payload: dict[str, Any] | None = None

    # Metric flags
    service_correct: bool = False    # HR: service_id matches expected
    l1_passed: bool = False          # SCR: schema layer passed
    l2_passed: bool = False          # SVR: semantic layer passed
    l3_passed: bool = False          # registry layer passed
    iwsr: bool = False               # IWSR: overall valid plan

    # Feedback
    feedback_attempted: bool = False
    feedback_recovered: bool = False
    feedback_iterations: int = 0

    # Execution
    error: str | None = None
    latency_ms: float = 0.0


@dataclass
class EvaluationReport:
    mode: str
    total: int = 0

    # Core metric accumulators
    _iwsr_passes: int = 0
    _scr_passes: int = 0
    _svr_passes: int = 0
    _hallucinations: int = 0          # service_id mismatch

    # Feedback
    _feedback_attempted: int = 0
    _feedback_recovered: int = 0

    # Stratified for SS
    _iwsr_by_difficulty: dict[str, list[bool]] = field(default_factory=dict)

    results: list[EntryResult] = field(default_factory=list)

    def add(self, r: EntryResult) -> None:
        self.total += 1
        self.results.append(r)

        if r.error is None:
            if r.iwsr:
                self._iwsr_passes += 1
            if r.l1_passed:
                self._scr_passes += 1
            if r.l2_passed:
                self._svr_passes += 1
            if not r.service_correct:
                self._hallucinations += 1

            diff = r.difficulty or "unknown"
            self._iwsr_by_difficulty.setdefault(diff, []).append(r.iwsr)

        if r.feedback_attempted:
            self._feedback_attempted += 1
            if r.feedback_recovered:
                self._feedback_recovered += 1

    @property
    def iwsr(self) -> float:
        return self._iwsr_passes / self.total if self.total else 0.0

    @property
    def scr(self) -> float:
        return self._scr_passes / self.total if self.total else 0.0

    @property
    def svr(self) -> float:
        return self._svr_passes / self.total if self.total else 0.0

    @property
    def hr(self) -> float:
        return self._hallucinations / self.total if self.total else 0.0

    @property
    def rrf(self) -> float:
        return self._feedback_recovered / self._feedback_attempted if self._feedback_attempted else 0.0

    @property
    def ss(self) -> float:
        """
        Stability Score = 1 - normalised std-dev of IWSR across difficulty strata.
        If all difficulties have the same pass rate → SS = 1.0 (perfectly stable).
        """
        stratum_rates = []
        for passes in self._iwsr_by_difficulty.values():
            rate = sum(passes) / len(passes) if passes else 0.0
            stratum_rates.append(rate)

        if len(stratum_rates) < 2:
            return 1.0

        std = statistics.stdev(stratum_rates)
        return round(1.0 - std, 4)

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "total_entries": self.total,
            "metrics": {
                "IWSR": round(self.iwsr, 4),
                "SCR": round(self.scr, 4),
                "SVR": round(self.svr, 4),
                "HR": round(self.hr, 4),
                "SS": round(self.ss, 4),
                "RRF": round(self.rrf, 4),
            },
            "raw_counts": {
                "iwsr_pass": self._iwsr_passes,
                "scr_pass": self._scr_passes,
                "svr_pass": self._svr_passes,
                "hallucinations": self._hallucinations,
                "feedback_attempted": self._feedback_attempted,
                "feedback_recovered": self._feedback_recovered,
            },
            "stratified_iwsr": {
                diff: round(sum(passes) / len(passes), 4)
                for diff, passes in self._iwsr_by_difficulty.items()
            },
        }


# ─── Payload checking ────────────────────────────────────────────────────────

def _get_nested(obj: dict[str, Any], dotted_key: str) -> Any:
    """Access 'device.phoneNumber' style keys."""
    parts = dotted_key.split(".")
    node: Any = obj
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def check_payload_against_ground_truth(
    payload: dict[str, Any],
    checks: dict[str, Any],
) -> list[str]:
    """
    Validate payload against ground_truth payload_checks.
    Returns list of failed check descriptions (empty = all pass).
    """
    failures: list[str] = []

    for field_key in checks.get("required_fields", []):
        if _get_nested(payload, field_key) is None:
            failures.append(f"Missing required field: {field_key}")

    if "device.phoneNumber" in checks:
        expected_phone = checks["device.phoneNumber"]
        actual_phone = _get_nested(payload, "device.phoneNumber")
        if actual_phone != expected_phone:
            failures.append(
                f"device.phoneNumber mismatch: expected '{expected_phone}', got '{actual_phone}'"
            )

    if "qosProfile_valid" in checks:
        profile = payload.get("qosProfile")
        if profile and profile not in checks["qosProfile_valid"]:
            failures.append(
                f"qosProfile '{profile}' not in expected set {checks['qosProfile_valid']}"
            )

    if "duration_min" in checks or "duration_max" in checks:
        duration = payload.get("duration")
        if duration is not None:
            mn = checks.get("duration_min", 1)
            mx = checks.get("duration_max", 86400)
            if not (mn <= duration <= mx):
                failures.append(
                    f"duration {duration}s out of expected range [{mn}, {mx}]"
                )

    # Support both "maxAge_min/max" (current CAMARA spec) and legacy "maxAgeSeconds_min/max"
    _ma_min_key = "maxAge_min" if "maxAge_min" in checks else "maxAgeSeconds_min"
    _ma_max_key = "maxAge_max" if "maxAge_max" in checks else "maxAgeSeconds_max"
    if _ma_min_key in checks or _ma_max_key in checks:
        # Accept either field name in the payload (graceful migration)
        max_age = payload.get("maxAge") if payload.get("maxAge") is not None else payload.get("maxAgeSeconds")
        if max_age is not None:
            mn = checks.get(_ma_min_key, 1)
            mx = checks.get(_ma_max_key, 3600)
            if not (mn <= max_age <= mx):
                failures.append(
                    f"maxAge {max_age} out of expected range [{mn}, {mx}]"
                )

    return failures


# ─── Single-entry evaluation ─────────────────────────────────────────────────

def evaluate_entry(
    entry: dict[str, Any],
    mode: str,
    dry_run: bool = True,
    use_feedback: bool = True,
) -> EntryResult:
    """Run a single ground truth entry through the orchestration pipeline."""
    from backend.executor import execute_step
    from backend.feedback_engine import run_correction_loop
    from backend.intent_engine import build_execution_plan
    from backend.llm_planner import LlmPlanningError, build_llm_execution_plan, correct_payload_with_feedback
    from backend.rag_context import get_payload_schema_prompt
    from backend.validator import validate_step

    expected = entry["expected"]
    result = EntryResult(
        entry_id=entry["id"],
        intent=entry["intent"],
        language=entry.get("language", "en"),
        difficulty=entry.get("difficulty", "medium"),
        category=entry.get("category", "unknown"),
        mode=mode,
        expected_service_id=expected["service_id"],
        expected_operation_id=expected["operation_id"],
    )

    t_start = time.monotonic()

    try:
        if mode == "deterministic":
            plan_mode, steps = build_execution_plan(entry["intent"])
            step = steps[0]
            feedback_meta = None
        elif mode in ("llm-assisted", "llm-single"):
            if mode == "llm-single":
                from backend.llm_planner import build_llm_execution_plan_single_call
                steps, planner_meta = build_llm_execution_plan_single_call(entry["intent"])
            else:
                steps, planner_meta = build_llm_execution_plan(entry["intent"])
            step = steps[0]
            feedback_meta = None
        else:
            raise ValueError(f"Unknown mode: {mode}")

        result.actual_service_id = step.service_id
        result.actual_operation_id = step.operation_id
        result.actual_payload = step.payload

        # Service selection correctness (HR)
        result.service_correct = (step.service_id == expected["service_id"])

        # Run validation
        validation = validate_step(
            service_id=step.service_id,
            payload=step.payload,
            operation_id=step.operation_id,
            method=step.method,
            skip_registry=dry_run,
        )

        # Feedback loop (only for LLM-assisted mode)
        if not validation.valid and mode == "llm-assisted" and use_feedback:
            schema_ctx = get_payload_schema_prompt(step.service_id, step.operation_id)

            def _revalidate(s, skip):
                return validate_step(
                    service_id=s.service_id,
                    payload=s.payload,
                    operation_id=s.operation_id,
                    method=s.method,
                    skip_registry=skip,
                )

            step, validation, fb = run_correction_loop(
                intent=entry["intent"],
                step=step,
                initial_validation=validation,
                schema_context=schema_ctx,
                correct_fn=correct_payload_with_feedback,
                revalidate_fn=_revalidate,
                skip_registry=dry_run,
            )
            result.feedback_attempted = fb.attempted
            result.feedback_recovered = fb.recovered
            result.feedback_iterations = fb.iterations
            result.actual_payload = step.payload

        result.l1_passed = validation.layer1_schema.passed
        result.l2_passed = validation.layer2_semantic.passed
        result.l3_passed = validation.layer3_registry.passed
        result.iwsr = validation.valid and result.service_correct

    except LlmPlanningError as exc:
        result.error = f"LlmPlanningError: {exc}"
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"

    result.latency_ms = (time.monotonic() - t_start) * 1000
    return result


# ─── Full dataset evaluation ─────────────────────────────────────────────────

def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["entries"]


def run_evaluation(
    mode: str = "deterministic",
    dry_run: bool = True,
    use_feedback: bool = True,
    filter_category: str | None = None,
    filter_language: str | None = None,
    filter_difficulty: str | None = None,
    max_entries: int | None = None,
    dataset_path: Path = DATASET_PATH,
    request_delay_s: float = 0.0,
    verbose: bool = False,
    resume_from: Path | None = None,
) -> EvaluationReport:
    """
    Run full evaluation against the ground truth dataset.

    Parameters
    ----------
    mode             : "deterministic" or "llm-assisted"
    dry_run          : skip Layer 3 CAPIF registry check
    use_feedback     : apply feedback correction loop (llm-assisted only)
    filter_category  : optional filter (e.g. "qod_session", "location_retrieval")
    filter_language  : optional filter ("en" or "tr")
    filter_difficulty: optional filter ("easy", "medium", "hard")
    max_entries      : limit number of entries (useful for quick smoke tests)
    dataset_path     : path to ground truth JSON
    request_delay_s  : seconds to sleep between entries (avoids API rate limits)
    verbose          : print progress to stdout

    Returns
    -------
    EvaluationReport with all metrics computed
    """
    entries = load_dataset(dataset_path)

    if filter_category:
        entries = [e for e in entries if e.get("category") == filter_category]
    if filter_language:
        entries = [e for e in entries if e.get("language") == filter_language]
    if filter_difficulty:
        entries = [e for e in entries if e.get("difficulty") == filter_difficulty]
    if max_entries:
        entries = entries[:max_entries]

    # Load previously completed entries for resume support
    completed_ids: set[str] = set()
    report = EvaluationReport(mode=mode)

    if resume_from and resume_from.exists():
        try:
            prev = json.loads(resume_from.read_text(encoding="utf-8"))
            for r in prev.get("results", []):
                if not r.get("error"):  # only replay successful results
                    completed_ids.add(r["id"])
                    # Reconstruct minimal EntryResult for metrics
                    er = EntryResult(
                        entry_id=r["id"],
                        intent=r.get("intent", ""),
                        language=r.get("language", "en"),
                        difficulty=r.get("difficulty", "medium"),
                        category=r.get("category", "unknown"),
                        mode=r.get("mode", mode),
                        expected_service_id=r.get("expected_service_id", ""),
                        expected_operation_id=r.get("expected_operation_id", ""),
                        actual_service_id=r.get("actual_service_id"),
                        actual_payload=r.get("actual_payload"),
                        service_correct=r.get("service_correct", False),
                        l1_passed=r.get("l1_passed", False),
                        l2_passed=r.get("l2_passed", False),
                        iwsr=r.get("iwsr", False),
                        feedback_attempted=r.get("feedback_attempted", False),
                        feedback_recovered=r.get("feedback_recovered", False),
                    )
                    report.add(er)
            if verbose and completed_ids:
                print(f"  Resumed: {len(completed_ids)} entries already done, skipping.", flush=True)
        except Exception:
            pass  # corrupt resume file — start fresh

    pending = [e for e in entries if e["id"] not in completed_ids]
    total = len(entries)
    done_offset = len(completed_ids)

    for idx, entry in enumerate(pending, start=done_offset + 1):
        if verbose:
            print(f"  [{idx}/{total}] {entry['id']} ...", flush=True)
        result = evaluate_entry(entry, mode=mode, dry_run=dry_run, use_feedback=use_feedback)
        report.add(result)
        if verbose:
            status = "OK" if result.iwsr else f"FAIL: {result.error or 'wrong service/invalid'}"
            print(f"         → {status}", flush=True)
        if request_delay_s > 0 and idx < total:
            time.sleep(request_delay_s)

    return report


# ─── Comparison utility ──────────────────────────────────────────────────────

def compare_modes(
    dry_run: bool = True,
    use_feedback: bool = True,
    max_entries: int | None = None,
    dataset_path: Path = DATASET_PATH,
) -> dict[str, Any]:
    """
    Run evaluation for both modes and return a side-by-side comparison.
    Only runs LLM-assisted if a provider is configured (avoids hard failures).
    """
    from backend.config import settings

    det_report = run_evaluation(
        mode="deterministic",
        dry_run=dry_run,
        use_feedback=False,
        max_entries=max_entries,
        dataset_path=dataset_path,
    )

    llm_report = None
    has_llm_key = bool(
        settings.gemini_api_key
        or settings.openai_api_key
        or settings.anthropic_api_key
    )
    if has_llm_key:
        llm_report = run_evaluation(
            mode="llm-assisted",
            dry_run=dry_run,
            use_feedback=use_feedback,
            max_entries=max_entries,
            dataset_path=dataset_path,
        )

    comparison: dict[str, Any] = {
        "deterministic": det_report.summary(),
    }
    if llm_report:
        comparison["llm-assisted"] = llm_report.summary()
        comparison["delta"] = {
            metric: round(
                llm_report.summary()["metrics"][metric]
                - det_report.summary()["metrics"][metric],
                4,
            )
            for metric in ["IWSR", "SCR", "SVR", "HR", "SS", "RRF"]
        }
    else:
        comparison["llm-assisted"] = "skipped — no LLM API key configured"

    return comparison
