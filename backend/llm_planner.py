import json
import threading
import time
from typing import Any

import requests

from backend.capif.client import discover_services
from backend.config import settings
from backend.models import ExecutionStep, PlannerMetadata
from backend.rag_context import get_all_services_summary, get_payload_schema_prompt, get_rag_metadata
from backend.service_catalog import CATALOG

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

# ─── Gemini free-tier rate limiter ───────────────────────────────────────────
# Gemini 2.0 Flash free tier: 15 RPM — enforce a minimum gap between calls.
# The limiter is process-wide (thread-safe) so concurrent requests don't burst.
_GEMINI_MIN_INTERVAL = float(
    __import__("os").getenv("GEMINI_MIN_INTERVAL_S", "4.5")  # 4.5 s → ~13 RPM, safely below 15 RPM
)
_gemini_last_call: float = 0.0
_gemini_lock = threading.Lock()


def _gemini_throttle() -> None:
    """Block until the minimum inter-call interval has elapsed."""
    global _gemini_last_call
    with _gemini_lock:
        now = time.monotonic()
        wait = _GEMINI_MIN_INTERVAL - (now - _gemini_last_call)
        if wait > 0:
            time.sleep(wait)
        _gemini_last_call = time.monotonic()


class LlmPlanningError(RuntimeError):
    pass


def _discovery_grounding() -> tuple[bool, list[str], dict[str, Any] | None]:
    try:
        discovered = discover_services()
    except Exception:
        return False, [], None

    services = discovered.get("services", {})
    api_descriptions = services.get("serviceAPIDescriptions", []) if isinstance(services, dict) else []
    names = [item.get("apiName", "") for item in api_descriptions if item.get("apiName")]
    return discovered.get("status") == "discovered", names, discovered


# Runtime provider override — set via POST /config/provider without container restart
_llm_provider_override: str | None = None


def set_llm_provider(provider: str) -> None:
    global _llm_provider_override
    _llm_provider_override = provider


def get_active_provider() -> str:
    return _llm_provider_override or settings.llm_provider


def _active_model_name() -> str:
    p = get_active_provider()
    if p == "openai":
        return settings.openai_model
    if p == "anthropic":
        return settings.anthropic_model
    return settings.gemini_model


# ─────────────────────────────────────────────
# Phase 1: LLM Planner — service & operation selection
# ─────────────────────────────────────────────

def _build_planner_prompt(
    intent: str,
    rag_summary: str,
    discovered_names: list[str],
    used_discovery: bool,
) -> str:
    return f"""You are the planning module of a CAPIF-aligned telco orchestration platform.

Your task: given a natural-language telecom intent, select the correct CAMARA service and operation.

Return JSON only. No markdown. No explanation outside JSON.

Required output format:
{{
  "service_id": "qod | qos-profiles | qos-provisioning | location-retrieval",
  "operation_id": "string — exact operationId from the schema below",
  "method": "GET | POST",
  "path": "string — exact path from the schema below",
  "rationale": "one sentence explaining why this service/operation was chosen"
}}

Selection rules:
- "location-retrieval" → user wants to know WHERE a device is
- "qos-profiles" → user wants to LIST or QUERY available QoS profiles
- "qos-provisioning" → user wants a PERMANENT/INDEFINITE QoS assignment
- "qod" → user wants a TEMPORARY QoS session (default for QoS boost requests)
- If CAPIF discovery lists specific services, prefer those; otherwise use local catalog

Available CAMARA services (from OpenAPI specs):
{rag_summary}

CAPIF discovery summary:
{json.dumps({"used_discovery": used_discovery, "discoveredApiNames": discovered_names}, indent=2)}

Intent to translate:
{intent}""".strip()


# ─────────────────────────────────────────────
# Phase 2: LLM Payload Generator — structured JSON payload
# ─────────────────────────────────────────────

def _build_payload_prompt(
    intent: str,
    service_id: str,
    operation_id: str,
    method: str,
    path: str,
    rationale: str,
    schema_context: str,
) -> str:
    return f"""You are the payload generation module of a CAPIF-aligned telco orchestration platform.

Your task: generate a valid JSON request payload for the selected CAMARA API operation.
The payload MUST conform exactly to the OpenAPI schema provided below.

Return JSON only. No markdown. Only the payload object — not the full plan.

Selected operation:
  service_id:   {service_id}
  operation_id: {operation_id}
  method:       {method}
  path:         {path}
  rationale:    {rationale}

{schema_context}

Payload generation rules:
- Extract the phone number from the intent if present (E.164 format: +countrycode + number)
- If no phone number found, use "+34600000000" as placeholder
- For QoD: include device.phoneNumber, qosProfile, duration (seconds, integer), applicationServer
- For location-retrieval: include device.phoneNumber and maxAge (integer, 1-3600) — field name is maxAge NOT maxAgeSeconds
- For qos-profiles: include device.phoneNumber
- For qos-provisioning: include device.phoneNumber and qosProfile
- QoS profile mapping from intent keywords:
    video/stream/streaming/broadcast/conference → QOS_E_STREAMING
    game/gaming                                → QOS_GAMING
    latency/low-latency                        → QOS_LOW_LATENCY
    critical/emergency/mission-critical        → QOS_CRITICAL_COMMS
    (default)                                  → QOS_E
- Duration mapping: "X minute/min" → X*60 seconds, "X hour/hours" → X*3600 seconds
- Only include fields listed in the schema; do NOT invent new fields
- applicationServer.ipv4Address must be a valid IPv4 (use "198.51.100.10" if not specified)

Intent:
{intent}

Generate only the payload JSON object:""".strip()


# ─────────────────────────────────────────────
# LLM call helpers
# ─────────────────────────────────────────────

_RETRYABLE_STATUS = {500, 502, 503, 504}  # 429 excluded — throttler already handles rate limiting; retrying 429 causes 70s hang
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 5.0  # seconds; doubles on each attempt


def _call_with_retry(fn, label: str) -> dict[str, Any]:
    """Call fn() up to _MAX_RETRIES times with exponential backoff on transient errors."""
    delay = _RETRY_BASE_DELAY
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status == 429:
                raise LlmPlanningError(
                    f"{label} rate limit exceeded (429) — quota exhausted. "
                    "Wait a minute (RPM) or until tomorrow (daily limit) before retrying."
                ) from exc
            if status in _RETRYABLE_STATUS and attempt < _MAX_RETRIES:
                time.sleep(delay)
                delay *= 2
                continue
            raise LlmPlanningError(f"{label} request failed: {exc}") from exc
        except requests.Timeout as exc:
            if attempt < _MAX_RETRIES:
                time.sleep(delay)
                delay *= 2
                continue
            raise LlmPlanningError(f"{label} request timed out after {_MAX_RETRIES} attempts") from exc
        except requests.RequestException as exc:
            raise LlmPlanningError(f"{label} request failed: {exc}") from exc
    raise LlmPlanningError(f"{label} failed after {_MAX_RETRIES} attempts")  # unreachable


def _call_gemini(prompt: str) -> dict[str, Any]:
    if not settings.gemini_api_key:
        raise LlmPlanningError("GEMINI_API_KEY is not configured.")

    _gemini_throttle()  # enforce free-tier rate limit before each call

    def _do():
        response = requests.post(
            GEMINI_API_URL.format(model=settings.gemini_model),
            headers={"X-goog-api-key": settings.gemini_api_key},
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": settings.llm_temperature,
                    "responseMimeType": "application/json",
                },
            },
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    return _call_with_retry(_do, "Gemini")


def _call_openai(prompt: str) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise LlmPlanningError("OPENAI_API_KEY is not configured.")

    def _do():
        response = requests.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model,
                "temperature": settings.llm_temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a CAPIF-aligned telco orchestration assistant. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    return _call_with_retry(_do, "OpenAI")


def _call_anthropic(prompt: str) -> dict[str, Any]:
    if not settings.anthropic_api_key:
        raise LlmPlanningError("ANTHROPIC_API_KEY is not configured.")

    def _do():
        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": ANTHROPIC_API_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": 1024,
                "temperature": settings.llm_temperature,
                "system": "You are a CAPIF-aligned telco orchestration assistant. Return only valid JSON.",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    return _call_with_retry(_do, "Anthropic")


def _call_llm(prompt: str) -> tuple[dict[str, Any], str]:
    p = get_active_provider()
    if p == "openai":
        return _call_openai(prompt), "openai"
    if p == "anthropic":
        return _call_anthropic(prompt), "anthropic"
    return _call_gemini(prompt), "gemini"


def _extract_text(response_json: dict[str, Any], provider: str) -> str:
    if provider == "openai":
        choices = response_json.get("choices", [])
        if not choices:
            raise LlmPlanningError("LLM returned no choices.")
        text = (choices[0].get("message", {}).get("content") or "").strip()
    elif provider == "anthropic":
        content = response_json.get("content", [])
        if not content:
            raise LlmPlanningError("Anthropic returned no content.")
        text = (content[0].get("text") or "").strip()
    else:
        candidates = response_json.get("candidates", [])
        if not candidates:
            raise LlmPlanningError("LLM returned no candidates.")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "\n".join(p.get("text", "") for p in parts if p.get("text")).strip()
    if not text:
        raise LlmPlanningError("LLM returned an empty response.")
    return text


def _parse_json_response(text: str, context: str) -> dict[str, Any]:
    # Strip markdown code fences that some models (e.g. Claude) add around JSON
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        result = json.loads(stripped)
        if not isinstance(result, dict):
            raise LlmPlanningError(f"{context}: expected JSON object, got {type(result).__name__}")
        return result
    except json.JSONDecodeError as exc:
        raise LlmPlanningError(f"{context}: invalid JSON — {exc}") from exc


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def build_llm_execution_plan(intent: str) -> tuple[list[ExecutionStep], PlannerMetadata]:
    """
    Two-phase LLM orchestration:
    Phase 1 (LLM Planner)          → selects service + operation using RAG-grounded summaries
    Phase 2 (LLM Payload Generator) → generates payload using operation-specific schema context
    """
    used_discovery, discovered_names, discovered_payload = _discovery_grounding()
    rag_meta = get_rag_metadata()

    metadata = PlannerMetadata(
        strategy="llm-assisted",
        model=_active_model_name(),
        used_discovery=used_discovery,
        grounding_services=list(CATALOG.keys()),
        rag_context_loaded=rag_meta.get("yaml_parsed", False),
        rag_services=rag_meta.get("services_loaded", []),
        raw_plan={"capifDiscovery": discovered_payload} if discovered_payload else None,
    )

    # ── Phase 1: Service & Operation Selection ──
    rag_summary = json.dumps(get_all_services_summary(), indent=2)
    planner_prompt = _build_planner_prompt(intent, rag_summary, discovered_names, used_discovery)

    raw_plan_response, provider = _call_llm(planner_prompt)
    plan_text = _extract_text(raw_plan_response, provider)
    plan = _parse_json_response(plan_text, "LLM Planner (Phase 1)")

    required_plan_keys = {"service_id", "operation_id", "method", "path", "rationale"}
    missing = required_plan_keys.difference(plan.keys())
    if missing:
        raise LlmPlanningError(f"LLM Planner missing keys: {sorted(missing)}")

    service_id = plan["service_id"]
    operation_id = plan["operation_id"]

    if service_id not in CATALOG:
        raise LlmPlanningError(f"LLM selected unsupported service '{service_id}'.")

    metadata.raw_plan = {"phase1_plan": plan}

    # ── Phase 2: Payload Generation with Schema Context ──
    schema_context = get_payload_schema_prompt(service_id, operation_id)
    payload_prompt = _build_payload_prompt(
        intent=intent,
        service_id=service_id,
        operation_id=operation_id,
        method=plan["method"],
        path=plan["path"],
        rationale=plan["rationale"],
        schema_context=schema_context,
    )

    raw_payload_response, _ = _call_llm(payload_prompt)
    payload_text = _extract_text(raw_payload_response, provider)
    payload = _parse_json_response(payload_text, "LLM Payload Generator (Phase 2)")

    metadata.raw_plan["phase2_payload"] = payload

    step = ExecutionStep(
        service_id=service_id,
        operation_id=operation_id,
        method=plan["method"],
        path=plan["path"],
        payload=payload,
        rationale=plan["rationale"],
    )

    return [step], metadata


# ─────────────────────────────────────────────
# Single-call variant (1 API call instead of 2) — for quota-constrained evaluation
# ─────────────────────────────────────────────

def _build_single_call_prompt(
    intent: str,
    rag_summary: str,
    discovered_names: list[str],
    used_discovery: bool,
) -> str:
    return f"""You are a CAPIF-aligned telco orchestration platform.

Given a natural-language telecom intent, you must:
1. Select the correct CAMARA service and operation
2. Generate a valid JSON request payload for that operation

Return a SINGLE JSON object with both the plan and payload. No markdown. No explanation outside JSON.

Required output format:
{{
  "service_id": "qod | qos-profiles | qos-provisioning | location-retrieval",
  "operation_id": "exact operationId from the catalog",
  "method": "GET | POST",
  "path": "exact path from the catalog",
  "rationale": "one sentence explaining the selection",
  "payload": {{
    ... valid request body for this operation ...
  }}
}}

Service selection rules:
- "location-retrieval" → user wants to know WHERE a device is
- "qos-profiles" → user wants to LIST or QUERY available QoS profiles
- "qos-provisioning" → user wants a PERMANENT/INDEFINITE QoS assignment
- "qod" → user wants a TEMPORARY QoS session (default for QoS boost requests)

Payload rules:
- Extract phone number from intent in E.164 format (starts with +); if none, use "+34600000000"
- For qod: include device.phoneNumber, qosProfile, duration (seconds integer 1-7200), applicationServer {{ipv4Address, port}}
- For location-retrieval: include device.phoneNumber, maxAge (integer 1-3600) — field name is maxAge NOT maxAgeSeconds
- For qos-profiles: include device.phoneNumber (optional)
- For qos-provisioning: include device.phoneNumber, qosProfile
- QoS profile values: QOS_E, QOS_S, QOS_M, QOS_L, QOS_E_STREAMING, QOS_GAMING, QOS_LOW_LATENCY, QOS_CRITICAL_COMMS
  → video/stream/broadcast/conference → QOS_E_STREAMING
  → game/gaming → QOS_GAMING
  → latency/low-latency → QOS_LOW_LATENCY
  → critical/emergency → QOS_CRITICAL_COMMS
  → (default) → QOS_E
- Duration: "X minutes" → X*60 seconds; "X hours" → X*3600 seconds; default 900
- applicationServer.ipv4Address: use "198.51.100.10" if not in intent
- Do NOT invent field names not in the schema

Available CAMARA services:
{rag_summary}

CAPIF discovery: {json.dumps({'used': used_discovery, 'apis': discovered_names})}

Intent: {intent}""".strip()


def build_llm_execution_plan_single_call(
    intent: str,
) -> tuple[list[ExecutionStep], PlannerMetadata]:
    """
    Single-call LLM orchestration: service selection + payload generation in one API request.
    Uses half the API quota compared to build_llm_execution_plan().
    Intended for evaluation runs where quota is limited.
    """
    used_discovery, discovered_names, discovered_payload = _discovery_grounding()
    rag_meta = get_rag_metadata()

    metadata = PlannerMetadata(
        strategy="llm-assisted",
        model=_active_model_name(),
        used_discovery=used_discovery,
        grounding_services=list(CATALOG.keys()),
        rag_context_loaded=rag_meta.get("yaml_parsed", False),
        rag_services=rag_meta.get("services_loaded", []),
        raw_plan={"capifDiscovery": discovered_payload, "mode": "single-call"} if discovered_payload else {"mode": "single-call"},
    )

    rag_summary = json.dumps(get_all_services_summary(), indent=2)
    prompt = _build_single_call_prompt(intent, rag_summary, discovered_names, used_discovery)

    raw_response, provider = _call_llm(prompt)
    text = _extract_text(raw_response, provider)
    result = _parse_json_response(text, "LLM Single-Call Planner")

    required_keys = {"service_id", "operation_id", "method", "path", "rationale", "payload"}
    missing = required_keys.difference(result.keys())
    if missing:
        raise LlmPlanningError(f"LLM single-call response missing keys: {sorted(missing)}")

    service_id = result["service_id"]
    if service_id not in CATALOG:
        raise LlmPlanningError(f"LLM selected unsupported service '{service_id}'.")

    payload = result["payload"]
    if not isinstance(payload, dict):
        raise LlmPlanningError(f"LLM payload must be a JSON object, got {type(payload).__name__}")

    metadata.raw_plan["single_call_result"] = result

    step = ExecutionStep(
        service_id=service_id,
        operation_id=result["operation_id"],
        method=result["method"],
        path=result["path"],
        payload=payload,
        rationale=result["rationale"],
    )

    return [step], metadata


# ─────────────────────────────────────────────
# Feedback correction (Phase 3: single-call correction)
# ─────────────────────────────────────────────

def correct_payload_with_feedback(prompt: str) -> dict[str, Any]:
    """
    Call the LLM with a structured correction prompt and return the corrected payload dict.
    Raises LlmPlanningError if the LLM call or JSON parse fails.
    """
    raw_response, provider = _call_llm(prompt)
    text = _extract_text(raw_response, provider)
    return _parse_json_response(text, "LLM Feedback Correction")
