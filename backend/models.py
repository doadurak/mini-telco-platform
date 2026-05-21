from typing import Any, Literal

from pydantic import BaseModel, Field


class Device(BaseModel):
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    ipv4_address: str | None = Field(default=None, alias="ipv4Address")
    ipv6_address: str | None = Field(default=None, alias="ipv6Address")


class ApplicationServer(BaseModel):
    ipv4_address: str = Field(alias="ipv4Address")
    port: int | None = None


class QodSessionPayload(BaseModel):
    device: Device
    qos_profile: str = Field(alias="qosProfile")
    duration: int = Field(gt=0, le=86400)
    application_server: ApplicationServer = Field(alias="applicationServer")
    sink: str | None = None


class QosProfilesQueryPayload(BaseModel):
    device: Device | None = None


class QosProvisioningPayload(BaseModel):
    device: Device
    qos_profile: str = Field(alias="qosProfile")
    sink: str | None = None


class LocationRetrievalPayload(BaseModel):
    device: Device
    max_age: int = Field(default=300, alias="maxAge", gt=0, le=3600)


class CatalogOperation(BaseModel):
    operation_id: str
    method: str
    path: str
    summary: str


class CatalogService(BaseModel):
    service_id: str
    title: str
    version: str
    description: str
    base_path: str
    source: str
    operations: list[CatalogOperation]


class ExecutionStep(BaseModel):
    service_id: str
    operation_id: str
    method: str
    path: str
    payload: dict[str, Any]
    rationale: str


class LayerResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    valid: bool
    issues: list[str] = Field(default_factory=list)
    layer1_schema: LayerResult = Field(default_factory=lambda: LayerResult(passed=True))
    layer2_semantic: LayerResult = Field(default_factory=lambda: LayerResult(passed=True))
    layer3_registry: LayerResult = Field(default_factory=lambda: LayerResult(passed=True))
    registry_checked: bool = False


class PlannerMetadata(BaseModel):
    strategy: Literal["deterministic", "llm-assisted"]
    model: str | None = None
    used_discovery: bool = False
    grounding_services: list[str] = Field(default_factory=list)
    fallback_reason: str | None = None
    raw_plan: dict[str, Any] | None = None
    rag_context_loaded: bool = False
    rag_services: list[str] = Field(default_factory=list)


class FeedbackIteration(BaseModel):
    iteration: int
    issues: list[str]
    corrected_payload: dict[str, Any] | None = None
    validation_passed: bool = False


class FeedbackMetadata(BaseModel):
    attempted: bool = False
    iterations: int = 0
    recovered: bool = False
    max_iterations: int = 3
    history: list[FeedbackIteration] = Field(default_factory=list)


class OrchestrationRequest(BaseModel):
    intent: str
    dry_run: bool = True
    orchestration_mode: Literal["auto", "deterministic", "llm-assisted"] = "auto"


class OrchestrationResponse(BaseModel):
    intent: str
    mode: Literal["deterministic", "llm-assisted"]
    selected_service: CatalogService
    steps: list[ExecutionStep]
    validation: ValidationResult
    execution_result: dict[str, Any]          # first step result (backward compat)
    execution_results: list[dict[str, Any]] = Field(default_factory=list)  # all steps
    planner: PlannerMetadata
    feedback: FeedbackMetadata = Field(default_factory=FeedbackMetadata)
