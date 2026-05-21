from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.capif.client import capif_status, discover_services, get_invoker_details, onboard_invoker, publish_service
from backend.service_catalog import CATALOG

router = APIRouter(prefix="/capif", tags=["CAPIF Integration"])


class OnboardInvokerRequest(BaseModel):
    api_invoker_information: str = Field(default="Mini-Telco-Platform-Orchestrator")
    public_key: str = Field(default="")
    notification_destination: str = Field(default="http://localhost:8000/notifications")


class PublishServiceRequest(BaseModel):
    name: str
    description: str
    version: str = "1.1.0"
    protocol: str = "HTTP_1_1"
    aef_id: str = Field(default="AEF_ID_1", alias="aefId")
    api_version: str = Field(default="v1.1.0", alias="apiVersion")


@router.get("/status")
def status() -> dict[str, Any]:
    return capif_status()


@router.get("/invoker")
def invoker_details() -> dict[str, Any]:
    details = get_invoker_details()
    if not details:
        raise HTTPException(status_code=404, detail="Invoker has not been onboarded yet.")
    return details


@router.post("/invokers/onboard")
def onboard(request: OnboardInvokerRequest) -> dict[str, Any]:
    return onboard_invoker(
        api_invoker_information=request.api_invoker_information,
        public_key=request.public_key,
        notification_destination=request.notification_destination,
    )


@router.get("/discover")
def discover() -> dict[str, Any]:
    result = discover_services()
    if result.get("status") == "fallback":
        result["localCatalog"] = [service.model_dump() for service in CATALOG.values()]
    return result


@router.post("/publish")
def publish(request: PublishServiceRequest) -> dict[str, Any]:
    payload = {
        "name": request.name,
        "description": request.description,
        "version": request.version,
        "protocol": request.protocol,
        "aefId": request.aef_id,
        "apiVersion": request.api_version,
    }
    return publish_service(payload)


@router.post("/publish/catalog")
def publish_catalog() -> dict[str, Any]:
    results = []
    for service in CATALOG.values():
        results.append(
            {
                "serviceId": service.service_id,
                "result": publish_service(
                    {
                        "name": service.title,
                        "description": service.description,
                        "version": service.version,
                    }
                ),
            }
        )
    return {"published": results}
