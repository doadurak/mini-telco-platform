"""
Multi-Layer Validator — Deterministic Validation Layer

Three-tier verification matching the thesis architecture:

  Layer 1 — JSON Schema      : Pydantic structural validation
  Layer 2 — Semantic Policy  : Telecom domain rule enforcement
  Layer 3 — Registry Check   : CAPIF-discovered service consistency

Each layer is independent. Failures are tagged by layer so reliability
metrics (SCR, SVR, HR) can be computed separately.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any

from pydantic import ValidationError

from backend.models import (
    LayerResult,
    LocationRetrievalPayload,
    QodSessionPayload,
    QosProfilesQueryPayload,
    QosProvisioningPayload,
    ValidationResult,
)
from backend.service_catalog import CATALOG

# ─── Telecom Policy Constants ───────────────────────────────────────────────

# E.164: starts with +, country code 1-9, then 4-14 more digits (total 5-15)
_E164_RE = re.compile(r"^\+[1-9][0-9]{4,14}$")

# Valid QoS profile identifiers (CAMARA standard + platform-specific)
_VALID_QOS_PROFILES: frozenset[str] = frozenset(
    {
        "QOS_E",
        "QOS_S",
        "QOS_M",
        "QOS_L",
        "QOS_E_STREAMING",
        "QOS_GAMING",
        "QOS_LOW_LATENCY",
        "QOS_CRITICAL_COMMS",
    }
)

# QoD session duration policy (CAMARA recommended max: 86400s, platform MVP: 7200s)
_QOD_MAX_DURATION_S = 7200
_QOD_MIN_DURATION_S = 1

# Location retrieval maxAge bounds (CAMARA spec field name: maxAge)
_LOCATION_MAX_AGE_MAX_S = 3600
_LOCATION_MAX_AGE_MIN_S = 1

# Valid port range
_PORT_MIN = 1
_PORT_MAX = 65535


# ─── Layer 1: JSON Schema Validation ────────────────────────────────────────

def _validate_layer1(service_id: str, payload: dict[str, Any]) -> LayerResult:
    """Structural validation via Pydantic models (schema compliance)."""
    issues: list[str] = []

    try:
        if service_id == "qod":
            QodSessionPayload.model_validate(payload)
        elif service_id == "qos-profiles":
            QosProfilesQueryPayload.model_validate(payload)
        elif service_id == "qos-provisioning":
            QosProvisioningPayload.model_validate(payload)
        elif service_id == "location-retrieval":
            LocationRetrievalPayload.model_validate(payload)
        else:
            issues.append(f"[L1] Unknown service_id '{service_id}'. "
                          f"Valid: {sorted(CATALOG.keys())}")
    except ValidationError as exc:
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error["loc"])
            issues.append(f"[L1] {field}: {error['msg']}")

    return LayerResult(passed=not issues, issues=issues)


# ─── Layer 2: Semantic Policy Validation ────────────────────────────────────

def _check_phone_number(value: str | None, label: str, issues: list[str]) -> None:
    if value is None:
        return
    if not _E164_RE.match(value):
        issues.append(
            f"[L2] {label} must be E.164 format "
            f"(e.g. +905551112233). Got: '{value}'"
        )


def _check_device_identifier(device: dict[str, Any], issues: list[str]) -> None:
    """At least one of phoneNumber, ipv4Address, ipv6Address must be present."""
    has_phone = bool(device.get("phoneNumber"))
    has_ipv4 = bool(device.get("ipv4Address"))
    has_ipv6 = bool(device.get("ipv6Address"))
    if not (has_phone or has_ipv4 or has_ipv6):
        issues.append(
            "[L2] device must have at least one identifier: "
            "phoneNumber, ipv4Address, or ipv6Address."
        )


def _check_qos_profile(profile: str | None, service_id: str, issues: list[str]) -> None:
    if profile is None:
        issues.append(f"[L2] qosProfile is required for service '{service_id}'.")
        return
    if profile not in _VALID_QOS_PROFILES:
        issues.append(
            f"[L2] qosProfile '{profile}' is not a recognised CAMARA profile. "
            f"Valid values: {sorted(_VALID_QOS_PROFILES)}"
        )


def _check_ipv4(value: str | None, label: str, issues: list[str]) -> None:
    if value is None:
        return
    # Accept CIDR notation too (applicationServer sometimes uses /24 etc.)
    addr = value.split("/")[0] if "/" in value else value
    try:
        ipaddress.IPv4Address(addr)
    except ValueError:
        issues.append(f"[L2] {label} must be a valid IPv4 address. Got: '{value}'")


def _check_port(value: int | None, label: str, issues: list[str]) -> None:
    if value is None:
        return
    if not (_PORT_MIN <= value <= _PORT_MAX):
        issues.append(
            f"[L2] {label} must be between {_PORT_MIN} and {_PORT_MAX}. Got: {value}"
        )


def _check_operation_exists(
    service_id: str, operation_id: str, issues: list[str]
) -> None:
    """Verify that the LLM-selected operation actually exists in the catalog."""
    service = CATALOG.get(service_id)
    if service is None:
        return  # Already caught in L1
    valid_ops = [op.operation_id for op in service.operations]
    if operation_id and operation_id not in valid_ops:
        issues.append(
            f"[L2] operation_id '{operation_id}' not found in catalog for "
            f"service '{service_id}'. Valid operations: {valid_ops}"
        )


def _validate_layer2(
    service_id: str,
    operation_id: str,
    method: str,
    payload: dict[str, Any],
) -> LayerResult:
    """Telecom semantic policy checks."""
    issues: list[str] = []

    # Operation existence check
    _check_operation_exists(service_id, operation_id, issues)

    # Method consistency check
    service = CATALOG.get(service_id)
    if service and operation_id:
        for op in service.operations:
            if op.operation_id == operation_id and op.method.upper() != method.upper():
                issues.append(
                    f"[L2] Method mismatch: '{operation_id}' requires "
                    f"{op.method.upper()}, got {method.upper()}."
                )

    device = payload.get("device", {}) if isinstance(payload.get("device"), dict) else {}

    if service_id == "qod":
        _check_device_identifier(device, issues)
        _check_phone_number(device.get("phoneNumber"), "device.phoneNumber", issues)

        qos_profile = payload.get("qosProfile")
        _check_qos_profile(qos_profile, service_id, issues)

        duration = payload.get("duration")
        if duration is not None:
            if not isinstance(duration, int):
                issues.append(f"[L2] duration must be an integer (seconds). Got: {type(duration).__name__}")
            elif duration < _QOD_MIN_DURATION_S:
                issues.append(f"[L2] duration must be >= {_QOD_MIN_DURATION_S}s. Got: {duration}")
            elif duration > _QOD_MAX_DURATION_S:
                issues.append(
                    f"[L2] duration {duration}s exceeds platform policy max "
                    f"({_QOD_MAX_DURATION_S}s). Consider QoS Provisioning for longer assignments."
                )

        app_server = payload.get("applicationServer", {})
        if isinstance(app_server, dict):
            _check_ipv4(app_server.get("ipv4Address"), "applicationServer.ipv4Address", issues)
            _check_port(app_server.get("port"), "applicationServer.port", issues)
        elif app_server:
            issues.append("[L2] applicationServer must be an object with ipv4Address.")

    elif service_id == "qos-profiles":
        if device:
            _check_phone_number(device.get("phoneNumber"), "device.phoneNumber", issues)

    elif service_id == "qos-provisioning":
        _check_device_identifier(device, issues)
        _check_phone_number(device.get("phoneNumber"), "device.phoneNumber", issues)
        _check_qos_profile(payload.get("qosProfile"), service_id, issues)

    elif service_id == "location-retrieval":
        _check_device_identifier(device, issues)
        _check_phone_number(device.get("phoneNumber"), "device.phoneNumber", issues)

        # CAMARA spec field name is maxAge (not maxAgeSeconds)
        max_age = payload.get("maxAge")
        if max_age is not None:
            if not isinstance(max_age, int):
                issues.append(f"[L2] maxAge must be integer. Got: {type(max_age).__name__}")
            elif max_age < _LOCATION_MAX_AGE_MIN_S or max_age > _LOCATION_MAX_AGE_MAX_S:
                issues.append(
                    f"[L2] maxAge must be between "
                    f"{_LOCATION_MAX_AGE_MIN_S} and {_LOCATION_MAX_AGE_MAX_S}. Got: {max_age}"
                )

    return LayerResult(passed=not issues, issues=issues)


# ─── Layer 3: CAPIF Registry Consistency ────────────────────────────────────

def _validate_layer3(service_id: str) -> tuple[LayerResult, bool]:
    """
    CAPIF registry consistency check.

    Returns (LayerResult, registry_checked).
    Non-blocking: if CAPIF is unreachable, passes with a warning note.

    This layer enables computation of the Hallucination Rate (HR) metric:
      HR = |{w ∈ W | w ⊄ A_registered}| / |W|
    where A_registered = APIs discovered via CAPIF service registry.
    """
    try:
        from backend.capif.client import discover_services
        discovered = discover_services()
    except Exception:
        # CAPIF unreachable — non-blocking, mark as unchecked
        return LayerResult(passed=True, issues=[]), False

    status = discovered.get("status", "")
    if status != "discovered":
        return LayerResult(passed=True, issues=[]), False

    services_payload = discovered.get("services", {})
    api_descriptions = (
        services_payload.get("serviceAPIDescriptions", [])
        if isinstance(services_payload, dict)
        else []
    )

    # Build a normalised set of discovered API names
    discovered_names: set[str] = set()
    for item in api_descriptions:
        name = item.get("apiName", "")
        if name:
            discovered_names.add(name.lower().replace("-", "").replace("_", ""))

    # Normalise the local service_id for comparison
    normalised_service = service_id.lower().replace("-", "").replace("_", "")

    # Common name aliases for each service
    _ALIASES: dict[str, list[str]] = {
        "qod": ["qualityondemand", "qod", "qualityon-demand"],
        "qos-profiles": ["qosprofiles", "qosprofile"],
        "qos-provisioning": ["qosprovisioning", "qosprov"],
        "location-retrieval": ["locationretrieval", "devicelocation", "location"],
    }

    candidates = {normalised_service}
    for alias in _ALIASES.get(service_id, []):
        candidates.add(alias.lower().replace("-", "").replace("_", ""))

    found = bool(candidates.intersection(discovered_names))

    if not found:
        return (
            LayerResult(
                passed=False,
                issues=[
                    f"[L3] Service '{service_id}' was NOT found in CAPIF discovery results. "
                    f"Discovered APIs: {sorted(discovered_names) or 'none'}. "
                    "This may indicate an LLM hallucination or an unpublished service."
                ],
            ),
            True,
        )

    return LayerResult(passed=True, issues=[]), True


# ─── Public Entry Point ──────────────────────────────────────────────────────

def validate_step(
    service_id: str,
    payload: dict[str, Any],
    operation_id: str = "",
    method: str = "POST",
    *,
    skip_registry: bool = False,
) -> ValidationResult:
    """
    Run all three validation layers and return a consolidated ValidationResult.

    Parameters
    ----------
    service_id    : catalog service identifier
    payload       : LLM-generated request payload
    operation_id  : operation selected by LLM (for semantic checks)
    method        : HTTP method selected by LLM
    skip_registry : if True, skip Layer 3 (useful in dry-run / test mode)
    """
    l1 = _validate_layer1(service_id, payload)
    l2 = _validate_layer2(service_id, operation_id, method, payload)

    if skip_registry:
        l3 = LayerResult(passed=True, issues=[])
        registry_checked = False
    else:
        l3, registry_checked = _validate_layer3(service_id)

    all_issues = l1.issues + l2.issues + l3.issues
    valid = l1.passed and l2.passed and l3.passed

    return ValidationResult(
        valid=valid,
        issues=all_issues,
        layer1_schema=l1,
        layer2_semantic=l2,
        layer3_registry=l3,
        registry_checked=registry_checked,
    )
