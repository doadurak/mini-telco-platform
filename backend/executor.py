"""
executor.py — Real CAMARA provider calls.

Routes each ExecutionStep to the appropriate CAMARA provider:
  - QoD           → camara-QoD     POST /quality-on-demand/v1/sessions
  - QoS Profiles  → platform catalog (profiles known from NEF-QoS QOS_MAPPING)
  - QoS Provisioning → NEF-QoS     POST /3gpp-as-session-with-qos/v1/{scsAsId}/subscriptions
  - Location      → CamaraLocationRetrieval POST /location-retrieval/v0.5/retrieve

dry_run=True skips all HTTP calls and returns a plan preview.
"""
from __future__ import annotations

import requests
import urllib3

from backend.config import settings
from backend.models import ExecutionStep

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# QoS profiles supported by this platform (matches NEF-QoS QOS_MAPPING)
# These are returned for qos-profiles discovery requests without a network call.
# ---------------------------------------------------------------------------
_QOS_PROFILES: list[dict] = [
    {
        "name": "QOS_E",
        "description": "Basic video quality — up to 1 Mbps UL/DL",
        "status": "ACTIVE",
        "mediaType": "VIDEO",
        "maxBandwidthDl": "1 Mbps",
        "maxBandwidthUl": "1 Mbps",
    },
    {
        "name": "QOS_S",
        "description": "Standard video — up to 4 Mbps UL/DL",
        "status": "ACTIVE",
        "mediaType": "VIDEO",
        "maxBandwidthDl": "4 Mbps",
        "maxBandwidthUl": "4 Mbps",
    },
    {
        "name": "QOS_M",
        "description": "Medium video — up to 8 Mbps UL/DL",
        "status": "ACTIVE",
        "mediaType": "VIDEO",
        "maxBandwidthDl": "8 Mbps",
        "maxBandwidthUl": "8 Mbps",
    },
    {
        "name": "QOS_L",
        "description": "High-quality audio — up to 20 Mbps UL/DL",
        "status": "ACTIVE",
        "mediaType": "AUDIO",
        "maxBandwidthDl": "20 Mbps",
        "maxBandwidthUl": "20 Mbps",
    },
    {
        "name": "QOS_E_STREAMING",
        "description": "Enhanced streaming — up to 3 Mbps UL/DL",
        "status": "ACTIVE",
        "mediaType": "VIDEO",
        "maxBandwidthDl": "3 Mbps",
        "maxBandwidthUl": "3 Mbps",
    },
    {
        "name": "QOS_GAMING",
        "description": "Gaming profile — optimised for low latency, up to 10 Mbps",
        "status": "ACTIVE",
        "mediaType": "VIDEO",
        "maxBandwidthDl": "10 Mbps",
        "maxBandwidthUl": "10 Mbps",
    },
    {
        "name": "QOS_LOW_LATENCY",
        "description": "Low-latency profile — mission-critical real-time traffic",
        "status": "ACTIVE",
        "mediaType": "VIDEO",
        "maxBandwidthDl": "5 Mbps",
        "maxBandwidthUl": "5 Mbps",
    },
    {
        "name": "QOS_CRITICAL_COMMS",
        "description": "Critical communications — emergency / public-safety",
        "status": "ACTIVE",
        "mediaType": "CONTROL",
        "maxBandwidthDl": "2 Mbps",
        "maxBandwidthUl": "2 Mbps",
    },
]


# ---------------------------------------------------------------------------
# Internal HTTP helper
# ---------------------------------------------------------------------------
def _provider_call(
    method: str,
    url: str,
    json_body: dict | None = None,
) -> dict:
    """
    Make a single HTTP request to a CAMARA provider.
    Returns a structured dict with status, http_status, data, and error fields.
    Never raises — caller inspects the returned dict.
    """
    try:
        resp = requests.request(
            method=method,
            url=url,
            json=json_body,
            headers={"Content-Type": "application/json"},
            timeout=settings.provider_timeout_seconds,
            verify=settings.provider_verify_ssl,
        )
        resp.raise_for_status()
        body: dict = {}
        if resp.content:
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text}
        return {"status": "ok", "http_status": resp.status_code, "data": body}
    except requests.HTTPError as exc:
        detail: dict = {}
        if exc.response is not None:
            try:
                detail = exc.response.json()
            except Exception:
                detail = {"raw": exc.response.text}
        return {
            "status": "provider-http-error",
            "http_status": exc.response.status_code if exc.response is not None else 0,
            "error": str(exc),
            "detail": detail,
        }
    except requests.ConnectionError as exc:
        return {"status": "unreachable", "http_status": 0, "error": str(exc)}
    except requests.Timeout as exc:
        return {"status": "timeout", "http_status": 0, "error": str(exc)}
    except requests.RequestException as exc:
        return {"status": "request-error", "http_status": 0, "error": str(exc)}


# ---------------------------------------------------------------------------
# Per-service execution handlers
# ---------------------------------------------------------------------------
def _execute_qod(step: ExecutionStep) -> dict:
    """
    CAMARA QoD — POST /quality-on-demand/v1/sessions
    Provider: FRONT-research-group/camara-QoD (port 8002)
    """
    url = f"{settings.qod_provider_url.rstrip('/')}/quality-on-demand/v1/sessions"
    result = _provider_call("POST", url, step.payload)

    if result["status"] == "ok":
        data = result["data"]
        return {
            "status": "created",
            "sessionId": str(data.get("sessionId", "")),
            "qosStatus": data.get("qosStatus", "REQUESTED"),
            "qosProfile": data.get("qosProfile"),
            "startedAt": data.get("startedAt"),
            "expiresAt": data.get("expiresAt"),
            "duration": data.get("duration"),
            "provider": {
                "url": url,
                "http_status": result["http_status"],
            },
        }

    return {
        "status": "provider-error",
        "provider": {
            "url": url,
            "http_status": result["http_status"],
            "error": result.get("error"),
            "detail": result.get("detail"),
        },
    }


def _execute_qos_profiles(step: ExecutionStep) -> dict:
    """
    CAMARA QoS Profiles — returns the platform's supported profiles.

    No dedicated CAMARA qos-profiles provider exists in the FRONT stack.
    The profiles are defined in the NEF-QoS QOS_MAPPING and advertised
    via the CAPIF catalog; we return the authoritative list directly.
    This is compliant with CAMARA qos-profiles v1.1 semantics.
    """
    device = step.payload.get("device", {})
    return {
        "status": "ok",
        "device": device,
        "qosProfiles": _QOS_PROFILES,
        "source": "capif-catalog",
        "totalProfiles": len(_QOS_PROFILES),
    }


def _execute_qos_provisioning(step: ExecutionStep) -> dict:
    """
    CAMARA QoS Provisioning — creates a persistent QoS subscription.

    Translates CAMARA QoS Provisioning to 3GPP TS 29.122
    AsSessionWithQoS via NEF-QoS (FRONT-research-group/NEF-QoS, port 8585).
    """
    payload = step.payload
    phone: str = payload.get("device", {}).get("phoneNumber", "+34600000000")
    qos_profile: str = payload.get("qosProfile", "QOS_E")
    scs_as_id = settings.nef_scs_as_id

    url = (
        f"{settings.nef_qos_provider_url.rstrip('/')}"
        f"/3gpp-as-session-with-qos/v1/{scs_as_id}/subscriptions"
    )

    # 3GPP TS 29.122 AsSessionWithQoS subscription body
    # ueIpv4Addr is the UE's IP on the NEF subnet — configurable via NEF_DEFAULT_UE_IPV4
    nef_payload = {
        "msisdn": phone,
        "externalId": phone.lstrip("+") + "@domain.com",
        "notificationDestination": settings.nef_notification_url,
        "qosReference": qos_profile,
        "ueIpv4Addr": settings.nef_default_ue_ipv4,
    }

    result = _provider_call("POST", url, nef_payload)

    if result["status"] == "ok":
        data = result["data"]
        return {
            "status": "created",
            "assignmentId": str(data.get("subscriptionId", data.get("self", ""))),
            "assignmentStatus": "ACTIVE",
            "qosProfile": qos_profile,
            "device": payload.get("device"),
            "provider": {
                "url": url,
                "http_status": result["http_status"],
            },
        }

    return {
        "status": "provider-error",
        "provider": {
            "url": url,
            "http_status": result["http_status"],
            "error": result.get("error"),
            "detail": result.get("detail"),
        },
    }


def _execute_location(step: ExecutionStep) -> dict:
    """
    CAMARA Location Retrieval — POST /location-retrieval/v0.5/retrieve
    Provider: FRONT-research-group/CamaraLocationRetrieval (port 8080 / host 8003)

    The intent engine stores the max-age field as 'maxAgeSeconds' for clarity;
    the CAMARA provider expects 'maxAge' (seconds).  We translate here.
    """
    url = (
        f"{settings.location_provider_url.rstrip('/')}"
        "/location-retrieval/v0.5/retrieve"
    )

    # Translate maxAgeSeconds → maxAge (CAMARA spec field name)
    adapted: dict = dict(step.payload)
    if "maxAgeSeconds" in adapted:
        adapted["maxAge"] = adapted.pop("maxAgeSeconds")

    result = _provider_call("POST", url, adapted)

    if result["status"] == "ok":
        data = result["data"]
        return {
            "status": "ok",
            "lastLocationTime": data.get("lastLocationTime"),
            "area": data.get("area"),
            "device": data.get("device"),
            "provider": {
                "url": url,
                "http_status": result["http_status"],
            },
        }

    return {
        "status": "provider-error",
        "provider": {
            "url": url,
            "http_status": result["http_status"],
            "error": result.get("error"),
            "detail": result.get("detail"),
        },
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def execute_step(step: ExecutionStep, dry_run: bool = True) -> dict:
    """
    Execute a single orchestration step.

    dry_run=True  → returns the planned payload without any HTTP calls (schema preview).
    dry_run=False → routes to the appropriate real CAMARA provider.
    """
    if dry_run:
        return {
            "status": "dry-run",
            "serviceId": step.service_id,
            "operationId": step.operation_id,
            "method": step.method,
            "path": step.path,
            "payload": step.payload,
        }

    if step.service_id == "qod":
        return _execute_qod(step)
    if step.service_id == "qos-profiles":
        return _execute_qos_profiles(step)
    if step.service_id == "qos-provisioning":
        return _execute_qos_provisioning(step)
    if step.service_id == "location-retrieval":
        return _execute_location(step)

    return {"status": "unsupported", "serviceId": step.service_id}
