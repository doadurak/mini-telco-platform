import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
import urllib3
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from backend.config import ROOT_DIR, settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CAPIF_STORAGE_DIR = ROOT_DIR / "backend" / "capif"
RUNTIME_DIR = CAPIF_STORAGE_DIR / "runtime"
INVOKER_DETAILS_PATH = CAPIF_STORAGE_DIR / "invoker_details.json"
REGISTER_AUTH_PATH = CAPIF_STORAGE_DIR / "register_auth.json"
RUNTIME_CA_PATH = RUNTIME_DIR / "ca_root.crt"
RUNTIME_CERT_PATH = RUNTIME_DIR / "invoker.crt"
RUNTIME_KEY_PATH = RUNTIME_DIR / "invoker.key"
TIMEOUT_SECONDS = settings.capif_timeout_seconds


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _capif_base_url() -> str:
    if settings.capif_use_docker_network:
        return settings.capif_internal_base_url
    return settings.capif_base_url


def _register_base_url() -> str:
    if settings.capif_use_docker_network:
        return settings.register_internal_base_url
    return settings.register_base_url


def _http_probe_url() -> str:
    if settings.capif_use_docker_network:
        return "http://nginx:8080/test"
    return "http://localhost:8080/test"


def _build_url(path: str) -> str:
    return f"{_capif_base_url().rstrip('/')}/{path.lstrip('/')}"


def _build_register_url(path: str) -> str:
    return f"{_register_base_url().rstrip('/')}/{path.lstrip('/')}"


def _resolved_cert() -> Any:
    if settings.capif_client_cert and settings.capif_client_key:
        return (settings.capif_client_cert, settings.capif_client_key)
    if settings.capif_client_cert:
        return settings.capif_client_cert
    if RUNTIME_CERT_PATH.exists() and RUNTIME_KEY_PATH.exists():
        return (str(RUNTIME_CERT_PATH), str(RUNTIME_KEY_PATH))
    if RUNTIME_CERT_PATH.exists():
        return str(RUNTIME_CERT_PATH)
    return None


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    token: str | None = None,
    include_client_cert: bool = True,
) -> requests.Response:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    auth_token = token or settings.capif_token
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    cert = _resolved_cert() if include_client_cert else None

    return requests.request(
        method=method,
        url=_build_url(path),
        params=params,
        json=json_body,
        headers=headers,
        timeout=TIMEOUT_SECONDS,
        verify=settings.capif_verify_ssl,
        cert=cert,
    )


def _register_request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    auth: tuple[str, str] | None = None,
    bearer_token: str | None = None,
) -> requests.Response:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    return requests.request(
        method=method,
        url=_build_register_url(path),
        json=json_body,
        headers=headers,
        auth=auth,
        timeout=TIMEOUT_SECONDS,
        verify=settings.register_verify_ssl,
    )


def _generate_invoker_materials(common_name: str) -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .sign(private_key, hashes.SHA256())
    )

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return csr_pem, private_key_pem


def register_admin_login() -> dict[str, Any]:
    response = _register_request(
        "POST",
        "/login",
        auth=(settings.register_admin_username, settings.register_admin_password),
    )
    response.raise_for_status()
    return response.json()


def ensure_demo_user(admin_token: str) -> dict[str, Any]:
    payload = {
        "username": settings.register_demo_username,
        "password": settings.register_demo_password,
        "enterprise": settings.register_demo_enterprise,
        "country": settings.register_demo_country,
        "email": settings.register_demo_email,
        "purpose": settings.register_demo_purpose,
        "description": "Mini telco platform live invoker",
    }
    response = _register_request("POST", "/createUser", json_body=payload, bearer_token=admin_token)
    if response.status_code not in {201, 409}:
        response.raise_for_status()
    return {
        "status": "created" if response.status_code == 201 else "exists",
        "payload": response.json() if response.content else {},
    }


def get_demo_auth() -> dict[str, Any]:
    response = _register_request(
        "GET",
        "/getauth",
        auth=(settings.register_demo_username, settings.register_demo_password),
    )
    response.raise_for_status()
    return response.json()


def bootstrap_register_auth() -> dict[str, Any]:
    admin = register_admin_login()
    user = ensure_demo_user(admin["access_token"])
    auth = get_demo_auth()
    data = {
        "registerBaseUrl": _register_base_url(),
        "admin": {"access_token": admin.get("access_token")},
        "user": user,
        "auth": auth,
    }
    _write_json(REGISTER_AUTH_PATH, data)
    return data


def get_register_auth() -> dict[str, Any] | None:
    return _read_json(REGISTER_AUTH_PATH)


def onboard_invoker(
    api_invoker_information: str = "Mini-Telco-Platform-Orchestrator",
    public_key: str = "",
    notification_destination: str = "http://localhost:8000/notifications",
) -> dict[str, Any]:
    csr_pem, private_key_pem = _generate_invoker_materials(settings.register_demo_username)
    onboarding_information: dict[str, Any] = {
        "apiInvokerPublicKey": public_key or csr_pem,
    }
    if settings.capif_onboarding_secret:
        onboarding_information["onboardingSecret"] = settings.capif_onboarding_secret
    if settings.capif_invoker_certificate:
        onboarding_information["apiInvokerCertificate"] = settings.capif_invoker_certificate

    payload = {
        "notificationDestination": notification_destination,
        "apiInvokerInformation": api_invoker_information,
        "onboardingInformation": onboarding_information,
        "requestTestNotification": settings.capif_request_test_notification,
        "supportedFeatures": "0",
    }

    try:
        register_data = bootstrap_register_auth()
        access_token = register_data["auth"]["access_token"]
        response = _request(
            "POST",
            settings.capif_onboard_path,
            json_body=payload,
            token=access_token,
            include_client_cert=False,
        )
        response.raise_for_status()
        data = response.json()
        onboarding_info = data.get("onboardingInformation", {})
        if register_data["auth"].get("ca_root"):
            _write_text(RUNTIME_CA_PATH, register_data["auth"]["ca_root"])
        if onboarding_info.get("apiInvokerCertificate"):
            _write_text(RUNTIME_CERT_PATH, onboarding_info["apiInvokerCertificate"])
        _write_text(RUNTIME_KEY_PATH, private_key_pem)
        data["status"] = "live-onboarded"
        data["register"] = {
            "registerBaseUrl": _register_base_url(),
            "username": settings.register_demo_username,
        }
        data["capifBaseUrl"] = _capif_base_url()
    except requests.RequestException:
        raise

    _write_json(INVOKER_DETAILS_PATH, data)
    return data


def get_invoker_details() -> dict[str, Any] | None:
    return _read_json(INVOKER_DETAILS_PATH)


def get_invoker_id() -> str | None:
    details = get_invoker_details()
    if not details:
        return None
    return details.get("apiInvokerId")


def capif_status() -> dict[str, Any]:
    register_probe = None
    try:
        response = requests.get(_register_base_url(), timeout=TIMEOUT_SECONDS, verify=settings.register_verify_ssl)
        register_probe = {"reachable": True, "statusCode": response.status_code}
    except requests.RequestException as exc:
        register_probe = {"reachable": False, "error": str(exc)}

    http_probe = None
    try:
        response = requests.get(_http_probe_url(), timeout=TIMEOUT_SECONDS)
        http_probe = {"reachable": True, "statusCode": response.status_code}
    except requests.RequestException as exc:
        http_probe = {"reachable": False, "error": str(exc)}

    secure_checks: list[dict[str, Any]] = []
    for path in (settings.capif_onboard_path, settings.capif_discover_path):
        try:
            response = requests.get(_build_url(path), timeout=TIMEOUT_SECONDS, verify=settings.capif_verify_ssl)
            secure_checks.append({"path": path, "reachable": True, "statusCode": response.status_code})
        except requests.RequestException as exc:
            secure_checks.append({"path": path, "reachable": False, "error": str(exc)})

    return {
        "capifBaseUrl": _capif_base_url(),
        "registerBaseUrl": _register_base_url(),
        "dockerNetworkMode": settings.capif_use_docker_network,
        "httpProbe": http_probe,
        "registerProbe": register_probe,
        "secureChecks": secure_checks,
        "runtimeCertPresent": RUNTIME_CERT_PATH.exists(),
        "runtimeKeyPresent": RUNTIME_KEY_PATH.exists(),
        "invokerOnboarded": INVOKER_DETAILS_PATH.exists(),
    }


def discover_services() -> dict[str, Any]:
    invoker_id = get_invoker_id()
    if not invoker_id:
        return {
            "status": "not-onboarded",
            "message": "Invoker has not been onboarded yet.",
            "services": [],
        }

    try:
        response = _request("GET", settings.capif_discover_path, params={"api-invoker-id": invoker_id})
        response.raise_for_status()
        body = response.json() if response.content else []
        return {
            "status": "discovered",
            "invokerId": invoker_id,
            "endpoint": f"{_build_url(settings.capif_discover_path)}?{urlencode({'api-invoker-id': invoker_id})}",
            "services": body,
        }
    except requests.RequestException as exc:
        return {
            "status": "error",
            "invokerId": invoker_id,
            "message": str(exc),
            "endpoint": f"{_build_url(settings.capif_discover_path)}?{urlencode({'api-invoker-id': invoker_id})}",
            "services": [],
        }


def publish_service(service_info: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "apiName": service_info["name"],
        "description": service_info["description"],
        "version": service_info.get("version", "1.1.0"),
        "protocol": service_info.get("protocol", "HTTP_1_1"),
        "aefProfiles": [
            {
                "aefId": service_info.get("aefId", "AEF_ID_1"),
                "versions": [{"apiVersion": service_info.get("apiVersion", "v1.1.0")}],
            }
        ],
        "supportedFeatures": "0",
    }
    try:
        response = _request("POST", settings.capif_publish_path, json_body=payload)
        response.raise_for_status()
        return response.json() if response.content else {"status": "published"}
    except requests.RequestException as exc:
        return {
            "status": "error",
            "message": str(exc),
            "targetEndpoint": _build_url(settings.capif_publish_path),
            "submittedPayload": payload,
        }


def invoke_service(step: dict[str, Any]) -> dict[str, Any]:
    discovery = discover_services()
    return {
        "status": "adapter-ready",
        "capifBaseUrl": _capif_base_url(),
        "verifySsl": settings.capif_verify_ssl,
        "dockerNetworkMode": settings.capif_use_docker_network,
        "discovery": discovery,
        "step": step,
    }
