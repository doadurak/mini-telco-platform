"""
Structured Feedback Engine

Implements a bounded correction loop (max 3 iterations):
  1. Validate the LLM-generated payload
  2. If validation fails → format structured error feedback
  3. Send feedback to LLM for correction
  4. Re-validate corrected payload
  5. Repeat until valid or max_iterations reached

This component enables measurement of Recovery Rate after Feedback (RRF):
  RRF = |{w ∈ W_fail | corrected(w) is valid}| / |W_fail|

The feedback loop only runs for llm-assisted mode — deterministic payloads
that fail validation are not retried (they indicate catalog/planner bugs).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.models import (
    ExecutionStep,
    FeedbackIteration,
    FeedbackMetadata,
    ValidationResult,
)

if TYPE_CHECKING:
    pass

MAX_ITERATIONS = 3


def format_feedback_prompt(
    intent: str,
    service_id: str,
    operation_id: str,
    method: str,
    path: str,
    previous_payload: dict[str, Any],
    validation: ValidationResult,
    schema_context: str,
    iteration: int,
) -> str:
    """
    Build a structured correction prompt from validation issues.

    The prompt provides:
    - The original intent
    - The schema constraints (grounded RAG context)
    - The rejected payload
    - Layer-tagged error messages so the LLM understands exactly what failed
    """
    layer_issues = "\n".join(f"  - {issue}" for issue in validation.issues)

    layer_summary_parts = []
    if not validation.layer1_schema.passed:
        layer_summary_parts.append(f"Layer 1 (schema): {len(validation.layer1_schema.issues)} error(s)")
    if not validation.layer2_semantic.passed:
        layer_summary_parts.append(f"Layer 2 (semantic policy): {len(validation.layer2_semantic.issues)} error(s)")
    if not validation.layer3_registry.passed:
        layer_summary_parts.append(f"Layer 3 (CAPIF registry): {len(validation.layer3_registry.issues)} error(s)")

    layer_summary = "; ".join(layer_summary_parts) or "unknown layer"

    import json
    return f"""You are the correction module of a CAPIF-aligned telco orchestration platform.

Correction attempt {iteration} of {MAX_ITERATIONS}.

The payload you previously generated failed validation ({layer_summary}).
You must fix ALL listed issues and return a corrected JSON payload.

Original intent:
{intent}

Selected operation:
  service_id:   {service_id}
  operation_id: {operation_id}
  method:       {method}
  path:         {path}

{schema_context}

Rejected payload:
{json.dumps(previous_payload, indent=2, ensure_ascii=False)}

Validation errors (fix ALL of these):
{layer_issues}

Correction rules:
- phoneNumber MUST be E.164 format: starts with +, country code, then digits, total 5–15 chars
  Example: "+905551112233" (Turkey), "+34600000000" (Spain)
- qosProfile must be one of: QOS_E, QOS_S, QOS_M, QOS_L, QOS_E_STREAMING, QOS_GAMING, QOS_LOW_LATENCY, QOS_CRITICAL_COMMS
- duration must be an integer in seconds, between 1 and 7200
- maxAge must be an integer between 1 and 3600 (CAMARA field name is maxAge, not maxAgeSeconds)
- applicationServer.ipv4Address must be a valid IPv4 (e.g. "198.51.100.10")
- device must include at least one of: phoneNumber, ipv4Address, ipv6Address
- Do NOT add fields that are not in the schema above

Return ONLY the corrected payload JSON object — no markdown, no explanation:""".strip()


def run_correction_loop(
    intent: str,
    step: ExecutionStep,
    initial_validation: ValidationResult,
    schema_context: str,
    correct_fn: Any,
    revalidate_fn: Any,
    skip_registry: bool = False,
) -> tuple[ExecutionStep, ValidationResult, FeedbackMetadata]:
    """
    Bounded correction loop for LLM-generated payloads.

    Parameters
    ----------
    intent            : original user intent
    step              : the ExecutionStep with the failing payload
    initial_validation: validation result from the first attempt
    schema_context    : RAG schema context string for the selected operation
    correct_fn        : callable(prompt: str) -> dict[str, Any] — calls LLM for correction
    revalidate_fn     : callable(step: ExecutionStep, skip_registry: bool) -> ValidationResult
    skip_registry     : passed through to revalidate_fn

    Returns
    -------
    (corrected_step, final_validation, feedback_metadata)
    """
    feedback = FeedbackMetadata(
        attempted=True,
        max_iterations=MAX_ITERATIONS,
    )

    current_step = step
    current_validation = initial_validation

    for iteration in range(1, MAX_ITERATIONS + 1):
        feedback.iterations = iteration

        prompt = format_feedback_prompt(
            intent=intent,
            service_id=current_step.service_id,
            operation_id=current_step.operation_id,
            method=current_step.method,
            path=current_step.path,
            previous_payload=current_step.payload,
            validation=current_validation,
            schema_context=schema_context,
            iteration=iteration,
        )

        try:
            corrected_payload = correct_fn(prompt)
        except Exception as exc:
            feedback.history.append(
                FeedbackIteration(
                    iteration=iteration,
                    issues=current_validation.issues,
                    corrected_payload=None,
                    validation_passed=False,
                )
            )
            # LLM call itself failed — stop loop, return last known state
            break

        corrected_step = ExecutionStep(
            service_id=current_step.service_id,
            operation_id=current_step.operation_id,
            method=current_step.method,
            path=current_step.path,
            payload=corrected_payload,
            rationale=current_step.rationale,
        )

        new_validation = revalidate_fn(corrected_step, skip_registry)

        feedback.history.append(
            FeedbackIteration(
                iteration=iteration,
                issues=current_validation.issues,
                corrected_payload=corrected_payload,
                validation_passed=new_validation.valid,
            )
        )

        current_step = corrected_step
        current_validation = new_validation

        if new_validation.valid:
            feedback.recovered = True
            break

    return current_step, current_validation, feedback
