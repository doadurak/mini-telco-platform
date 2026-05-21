from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
CAMARA_SERVICES_DIR = ROOT_DIR / "camara-services"

load_dotenv(ROOT_DIR / ".env")


def _env_flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Mini Telco Orchestration Platform")
    environment: str = os.getenv("ENVIRONMENT", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    orchestration_default_mode: str = os.getenv("ORCHESTRATION_DEFAULT_MODE", "auto")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    capif_base_url: str = os.getenv("CAPIF_BASE_URL", "https://localhost")
    capif_internal_base_url: str = os.getenv("CAPIF_INTERNAL_BASE_URL", "https://nginx")
    capif_internal_hostname: str = os.getenv("CAPIF_INTERNAL_HOSTNAME", "capifcore")
    capif_use_docker_network: bool = _env_flag("CAPIF_USE_DOCKER_NETWORK", False)
    capif_token: str | None = os.getenv("CAPIF_TOKEN") or None
    capif_verify_ssl: bool = _env_flag("CAPIF_VERIFY_SSL", False)
    capif_timeout_seconds: int = int(os.getenv("CAPIF_TIMEOUT_SECONDS", "20"))
    capif_client_cert: str | None = os.getenv("CAPIF_CLIENT_CERT") or None
    capif_client_key: str | None = os.getenv("CAPIF_CLIENT_KEY") or None
    capif_onboard_path: str = os.getenv("CAPIF_ONBOARD_PATH", "/api-invoker-management/v1/onboardedInvokers")
    capif_publish_path: str = os.getenv("CAPIF_PUBLISH_PATH", "/published-apis/v1/apf_id/service-apis")
    capif_discover_path: str = os.getenv("CAPIF_DISCOVER_PATH", "/service-apis/v1/allServiceAPIs")
    capif_onboarding_secret: str | None = os.getenv("CAPIF_ONBOARDING_SECRET") or None
    capif_invoker_certificate: str | None = os.getenv("CAPIF_INVOKER_CERTIFICATE") or None
    capif_request_test_notification: bool = _env_flag("CAPIF_REQUEST_TEST_NOTIFICATION", True)

    register_base_url: str = os.getenv("REGISTER_BASE_URL", "https://localhost:8084")
    register_internal_base_url: str = os.getenv("REGISTER_INTERNAL_BASE_URL", "https://register:8080")
    register_verify_ssl: bool = _env_flag("REGISTER_VERIFY_SSL", False)
    register_admin_username: str = os.getenv("REGISTER_ADMIN_USERNAME", "admin")
    register_admin_password: str = os.getenv("REGISTER_ADMIN_PASSWORD", "password123")
    register_demo_username: str = os.getenv("REGISTER_DEMO_USERNAME", "mini_platform_demo")
    register_demo_password: str = os.getenv("REGISTER_DEMO_PASSWORD", "MiniPlatform123!")
    register_demo_enterprise: str = os.getenv("REGISTER_DEMO_ENTERPRISE", "CTTC")
    register_demo_country: str = os.getenv("REGISTER_DEMO_COUNTRY", "ES")
    register_demo_email: str = os.getenv("REGISTER_DEMO_EMAIL", "mini-platform@example.com")
    register_demo_purpose: str = os.getenv("REGISTER_DEMO_PURPOSE", "CAPIF live onboarding demo")

    # CAMARA Provider base URLs
    # Inside Docker (capif-network or host-gateway): use container names / host.docker.internal
    # Outside Docker: use localhost with mapped ports
    qod_provider_url: str = os.getenv("QOD_PROVIDER_URL", "http://localhost:8002")
    location_provider_url: str = os.getenv("LOCATION_PROVIDER_URL", "http://localhost:8003")
    nef_qos_provider_url: str = os.getenv("NEF_QOS_PROVIDER_URL", "http://localhost:8585")
    provider_timeout_seconds: int = int(os.getenv("PROVIDER_TIMEOUT_SECONDS", "30"))
    provider_verify_ssl: bool = _env_flag("PROVIDER_VERIFY_SSL", False)
    # NEF-QoS / 3GPP TS 29.122 AsSessionWithQoS parameters
    nef_scs_as_id: str = os.getenv("NEF_SCS_AS_ID", "1")
    nef_notification_url: str = os.getenv("NEF_NOTIFICATION_URL", "http://localhost:8000/notifications")
    nef_default_ue_ipv4: str = os.getenv("NEF_DEFAULT_UE_IPV4", "10.11.11.2")


settings = Settings()
