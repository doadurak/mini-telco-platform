"""
RAG-Based API Context Engine

Parses CAMARA OpenAPI YAML specs and injects relevant schema information
into the LLM prompt. This is the core component that prevents hallucination
by grounding LLM reasoning in real schema constraints.

Architecture: AI Reasoning Layer → RAG-Based API Context Engine
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

from backend.config import ROOT_DIR

CAMARA_SERVICES_DIR = ROOT_DIR / "camara-services"

SERVICE_YAML_MAP: dict[str, str] = {
    "qod": "qod_v1.1.0.yaml",
    "qos-profiles": "qos_profiles_v1.1.0.yaml",
    "qos-provisioning": "qos_provisioning_v1.1.0.yaml",
}

# Location retrieval has no CAMARA YAML — we provide a hand-crafted schema
LOCATION_RETRIEVAL_SCHEMA: dict[str, Any] = {
    "service_id": "location-retrieval",
    "title": "Device Location Retrieval",
    "version": "v0.5",
    "base_path": "/location-retrieval/v0.5",
    "operations": [
        {
            "operationId": "retrieveLocation",
            "method": "POST",
            "path": "/retrieve",
            "summary": "Retrieve last known device location",
            "requestBody": {
                "required_fields": ["device"],
                "schema": {
                    "device": {
                        "type": "object",
                        "description": "Target device identifier",
                        "required_one_of": ["phoneNumber", "ipv4Address", "ipv6Address"],
                        "properties": {
                            "phoneNumber": {
                                "type": "string",
                                "format": "E.164",
                                "pattern": r"^\+[1-9][0-9]{7,14}$",
                                "example": "+905551112233",
                            }
                        },
                    },
                    "maxAge": {
                        "type": "integer",
                        "description": "Max age of cached location in seconds (CAMARA field name: maxAge)",
                        "minimum": 1,
                        "maximum": 3600,
                        "default": 300,
                    },
                },
            },
            "example_request": {
                "device": {"phoneNumber": "+905551112233"},
                "maxAge": 300,
            },
            "example_response": {
                "lastLocationTime": "2024-06-01T12:00:00Z",
                "area": {
                    "areaType": "POLYGON",
                    "boundary": [
                        {"latitude": 37.9838, "longitude": 23.7275},
                        {"latitude": 37.98, "longitude": 23.75},
                    ],
                },
            },
        }
    ],
    "constraints": [
        "device.phoneNumber must be E.164 format: starts with +, 8–15 digits",
        "Use maxAge (NOT maxAgeSeconds) — this is the CAMARA spec field name",
        "maxAge must be between 1 and 3600 seconds",
        "At least one device identifier must be provided",
    ],
}

_schema_cache: dict[str, dict[str, Any]] = {}


def _load_yaml(path: Path) -> dict[str, Any] | None:
    if not _YAML_AVAILABLE:
        return None
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a $ref like '#/components/schemas/Device' within the spec."""
    if not ref.startswith("#/"):
        return {}
    parts = ref.lstrip("#/").split("/")
    node: Any = spec
    for part in parts:
        if isinstance(node, dict):
            node = node.get(part, {})
        else:
            return {}
    return node if isinstance(node, dict) else {}


def _extract_schema_fields(
    spec: dict[str, Any],
    schema: dict[str, Any],
    depth: int = 0,
) -> dict[str, Any]:
    """Recursively extract field info from an OpenAPI schema node."""
    if depth > 4:
        return {}

    if "$ref" in schema:
        schema = _resolve_ref(spec, schema["$ref"])

    result: dict[str, Any] = {}

    # Handle allOf — properly merge properties across all sub-schemas
    if "allOf" in schema:
        merged_props: dict[str, Any] = {}
        merged_required: list[str] = []
        for sub in schema["allOf"]:
            sub_result = _extract_schema_fields(spec, sub, depth + 1)
            # Merge properties without overwriting existing ones
            for k, v in sub_result.items():
                if k == "properties" and "properties" in result:
                    result["properties"].update(v)
                elif k == "required" and "required" in result:
                    existing = result["required"]
                    result["required"] = existing + [r for r in v if r not in existing]
                else:
                    result[k] = v
            # Track merged props separately for clarity
            if "properties" in sub_result:
                merged_props.update(sub_result["properties"])
            if "required" in sub_result:
                merged_required += [r for r in sub_result["required"] if r not in merged_required]
        if merged_props:
            result["properties"] = merged_props
        if merged_required:
            result["required"] = merged_required
        return result

    schema_type = schema.get("type", "object")
    result["type"] = schema_type

    if "description" in schema:
        result["description"] = schema["description"][:200]

    if "enum" in schema:
        result["enum"] = schema["enum"]

    if "format" in schema:
        result["format"] = schema["format"]

    if "pattern" in schema:
        result["pattern"] = schema["pattern"]

    if "minimum" in schema:
        result["minimum"] = schema["minimum"]

    if "maximum" in schema:
        result["maximum"] = schema["maximum"]

    if "default" in schema:
        result["default"] = schema["default"]

    if "example" in schema:
        result["example"] = schema["example"]

    if schema_type == "object" and "properties" in schema:
        props: dict[str, Any] = {}
        for field_name, field_schema in schema["properties"].items():
            props[field_name] = _extract_schema_fields(spec, field_schema, depth + 1)
        result["properties"] = props
        if "required" in schema:
            result["required"] = schema["required"]

    return result


def _extract_operation_context(
    spec: dict[str, Any],
    path: str,
    method: str,
    operation: dict[str, Any],
) -> dict[str, Any]:
    """Extract structured context for a single API operation."""
    ctx: dict[str, Any] = {
        "operationId": operation.get("operationId", ""),
        "method": method.upper(),
        "path": path,
        "summary": operation.get("summary", ""),
    }

    request_body = operation.get("requestBody", {})
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    raw_schema = json_content.get("schema", {})

    if raw_schema:
        ctx["requestSchema"] = _extract_schema_fields(spec, raw_schema)

    # Extract inline examples from the spec
    examples = json_content.get("examples", {})
    if examples:
        first_example_key = next(iter(examples))
        first_example = examples[first_example_key]
        if "$ref" in first_example:
            example_ref = first_example["$ref"]
            parts = example_ref.lstrip("#/").split("/")
            node: Any = spec
            for part in parts:
                node = node.get(part, {}) if isinstance(node, dict) else {}
            if isinstance(node, dict) and "value" in node:
                ctx["exampleRequest"] = node["value"]

    return ctx


def _build_service_context(service_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Build a structured context dict from an OpenAPI spec."""
    info = spec.get("info", {})
    servers = spec.get("servers", [])
    base_path = servers[0].get("url", "") if servers else ""

    # Strip variable template from base_path
    if "{apiRoot}" in base_path:
        base_path = base_path.replace("{apiRoot}", "")

    operations: list[dict[str, Any]] = []
    for path_str, path_item in spec.get("paths", {}).items():
        for method in ("get", "post", "put", "patch", "delete"):
            if method in path_item:
                op_ctx = _extract_operation_context(spec, path_str, method, path_item[method])
                operations.append(op_ctx)

    # Extract QoS profile enum values if present
    qos_profile_enum: list[str] = []
    schemas = spec.get("components", {}).get("schemas", {})
    for schema_name, schema_body in schemas.items():
        if "profile" in schema_name.lower() or "qosprofile" in schema_name.lower():
            if "enum" in schema_body:
                qos_profile_enum.extend(schema_body["enum"])
        if schema_name == "QosProfileName" and "enum" in schema_body:
            qos_profile_enum.extend(schema_body["enum"])

    ctx: dict[str, Any] = {
        "service_id": service_id,
        "title": info.get("title", ""),
        "version": info.get("version", ""),
        "base_path": base_path,
        "operations": operations,
    }

    if qos_profile_enum:
        ctx["validQosProfiles"] = list(set(qos_profile_enum))

    return ctx


def _load_all_schemas() -> dict[str, dict[str, Any]]:
    """Load and parse all CAMARA YAML specs into structured schema cache."""
    cache: dict[str, dict[str, Any]] = {}

    for service_id, yaml_filename in SERVICE_YAML_MAP.items():
        yaml_path = CAMARA_SERVICES_DIR / yaml_filename
        spec = _load_yaml(yaml_path)
        if spec:
            cache[service_id] = _build_service_context(service_id, spec)
        else:
            # Fallback: minimal context without YAML parsing
            cache[service_id] = {"service_id": service_id, "note": "YAML not parsed (pyyaml missing)"}

    cache["location-retrieval"] = LOCATION_RETRIEVAL_SCHEMA
    return cache


def _get_cache() -> dict[str, dict[str, Any]]:
    global _schema_cache
    if not _schema_cache:
        _schema_cache = _load_all_schemas()
    return _schema_cache


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def get_service_context(service_id: str) -> dict[str, Any]:
    """Return full schema context for a specific service."""
    return _get_cache().get(service_id, {})


def get_all_services_summary() -> list[dict[str, Any]]:
    """Return a compact summary of all services for LLM service-selection phase."""
    cache = _get_cache()
    summaries: list[dict[str, Any]] = []
    for service_id, ctx in cache.items():
        ops = [
            {
                "operationId": op.get("operationId"),
                "method": op.get("method"),
                "path": op.get("path"),
                "summary": op.get("summary"),
            }
            for op in ctx.get("operations", [])
        ]
        summaries.append(
            {
                "service_id": service_id,
                "title": ctx.get("title", ""),
                "base_path": ctx.get("base_path", ""),
                "operations": ops,
            }
        )
    return summaries


def get_payload_schema_prompt(service_id: str, operation_id: str) -> str:
    """
    Return a compact, LLM-friendly schema description for a specific operation.
    Used to ground the LLM Payload Generator with real schema constraints.
    """
    ctx = get_service_context(service_id)
    if not ctx:
        return f"No schema context available for service '{service_id}'."

    target_op: dict[str, Any] | None = None
    for op in ctx.get("operations", []):
        if op.get("operationId") == operation_id:
            target_op = op
            break

    if not target_op:
        ops = [op.get("operationId") for op in ctx.get("operations", [])]
        return f"Operation '{operation_id}' not found in '{service_id}'. Available: {ops}"

    lines: list[str] = [
        f"=== CAMARA Schema: {ctx.get('title')} — {target_op['method']} {target_op['path']} ===",
        f"Operation: {target_op['operationId']}",
        f"Summary: {target_op.get('summary', '')}",
        "",
    ]

    schema = target_op.get("requestSchema")
    if schema:
        lines.append("Request body schema (JSON):")
        lines.append(json.dumps(schema, indent=2, ensure_ascii=False))
        lines.append("")

    example = target_op.get("exampleRequest")
    if example:
        lines.append("Official CAMARA example request:")
        lines.append(json.dumps(example, indent=2, ensure_ascii=False))
        lines.append("")

    if "constraints" in ctx:
        lines.append("Constraints:")
        for c in ctx["constraints"]:
            lines.append(f"  - {c}")
        lines.append("")

    valid_profiles = ctx.get("validQosProfiles")
    if valid_profiles:
        lines.append(f"Valid QoS profile values: {valid_profiles}")
        lines.append("")

    lines.append("IMPORTANT rules:")
    lines.append("  - phoneNumber MUST be E.164 format: starts with +, 8-15 digits total")
    lines.append("  - Only use fields present in the schema above")
    lines.append("  - Do not invent field names not listed in the schema")
    lines.append("  - duration must be in seconds (integer > 0)")

    return "\n".join(lines)


def get_rag_context_for_planner(
    service_id: str | None = None,
    operation_id: str | None = None,
) -> str:
    """
    Main entry point for LLM Planner context injection.

    If service_id is known → inject full schema for that service.
    If service_id is None → inject compact summaries of all services.
    """
    if service_id and operation_id:
        return get_payload_schema_prompt(service_id, operation_id)

    if service_id:
        ctx = get_service_context(service_id)
        ops_text = json.dumps(ctx.get("operations", []), indent=2, ensure_ascii=False)
        valid_profiles = ctx.get("validQosProfiles")
        result = f"=== {ctx.get('title', service_id)} Schema Context ===\n{ops_text}"
        if valid_profiles:
            result += f"\nValid QoS profile values: {valid_profiles}"
        return result

    # No service selected yet — return compact summary for service selection
    summaries = get_all_services_summary()
    return (
        "=== Available CAMARA Services (from OpenAPI specs) ===\n"
        + json.dumps(summaries, indent=2, ensure_ascii=False)
    )


def get_rag_metadata() -> dict[str, Any]:
    """Return metadata about what was loaded (for PlannerMetadata)."""
    cache = _get_cache()
    return {
        "yaml_parsed": _YAML_AVAILABLE,
        "services_loaded": list(cache.keys()),
        "camara_specs_dir": str(CAMARA_SERVICES_DIR),
        "yaml_files": [f.name for f in CAMARA_SERVICES_DIR.glob("*.yaml")] if CAMARA_SERVICES_DIR.exists() else [],
    }
