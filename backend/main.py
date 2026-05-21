import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

_notif_log = logging.getLogger("notifications")

from backend.config import ROOT_DIR, settings
from backend.executor import execute_step
from backend.feedback_engine import run_correction_loop
from backend.intent_engine import build_execution_plan
from backend.llm_planner import LlmPlanningError, build_llm_execution_plan, correct_payload_with_feedback
from backend.models import CatalogService, FeedbackMetadata, OrchestrationRequest, OrchestrationResponse, PlannerMetadata, ValidationResult
from backend.rag_context import get_payload_schema_prompt
from backend.routes.capif import router as capif_router
from backend.service_catalog import CATALOG
from backend.validator import validate_step

FRONTEND_INDEX = ROOT_DIR / "frontend" / "index.html"

app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description=(
        "AI-native telco orchestration backend with CAMARA capability catalog, "
        "CAPIF onboarding/publishing/discovery adapters, and intent-to-action orchestration."
    ),
    contact={"name": "Turkan Doga Durak"},
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Orchestration", "description": "Intent parsing, validation, and execution planning."},
        {"name": "Catalog", "description": "Developer-facing service catalog based on CAMARA capabilities."},
        {"name": "CAPIF Integration", "description": "OpenCAPIF onboarding, publishing, and discovery endpoints."},
    ],
    swagger_ui_parameters={"displayRequestDuration": True, "docExpansion": "list"},
)
app.include_router(capif_router)


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(FRONTEND_INDEX)


@app.get("/app", include_in_schema=False)
def frontend_app() -> FileResponse:
    return FileResponse(FRONTEND_INDEX)


@app.get("/health", tags=["Orchestration"])
def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "frontend": "/app",
        "swaggerUi": "/docs",
        "capifBaseUrl": settings.capif_base_url,
    }


@app.get("/catalog/services", response_model=list[CatalogService], tags=["Catalog"])
def list_services() -> list[CatalogService]:
    return list(CATALOG.values())


# ─── Notification receiver ────────────────────────────────────────────────────
# CAPIF sends a test notification here after invoker onboarding.
# QoD providers send session-state callbacks here (SUCCESSFUL/FAILED_RESOURCES_ALLOCATION).
# NEF-QoS sends AsSessionWithQoS status updates here.
# All payloads are logged and acknowledged with 204 No Content.

@app.post("/notifications", tags=["Orchestration"], status_code=204)
async def receive_notification(request: Request) -> None:
    """
    Webhook receiver for CAPIF test notifications and CAMARA provider callbacks.
    Accepts any JSON body, logs it, and returns 204 No Content.
    """
    try:
        body = await request.json()
    except Exception:
        body = await request.body()
        body = {"raw": body.decode("utf-8", errors="replace")}
    _notif_log.info("NOTIFICATION received: %s", body)


@app.get("/notifications", tags=["Orchestration"])
def notifications_info() -> dict:
    """Returns info about the notification endpoint (CAPIF probe support)."""
    return {
        "endpoint": "/notifications",
        "method": "POST",
        "description": "CAPIF test notification receiver and CAMARA provider callback webhook.",
        "status": "ready",
    }


@app.post("/orchestrate", response_model=OrchestrationResponse, tags=["Orchestration"])
def orchestrate(request: OrchestrationRequest) -> OrchestrationResponse:
    requested_mode = request.orchestration_mode
    if requested_mode == "auto":
        requested_mode = settings.orchestration_default_mode

    planner = PlannerMetadata(strategy="deterministic")
    if requested_mode == "llm-assisted":
        try:
            steps, planner = build_llm_execution_plan(request.intent)
            mode = "llm-assisted"
        except LlmPlanningError as exc:
            raise HTTPException(status_code=502, detail=f"LLM planning failed: {exc}") from exc
    else:
        mode, steps = build_execution_plan(request.intent)
        planner = PlannerMetadata(strategy="deterministic")
        if request.orchestration_mode == "auto" and settings.gemini_api_key:
            try:
                steps, planner = build_llm_execution_plan(request.intent)
                mode = "llm-assisted"
            except LlmPlanningError as exc:
                planner = PlannerMetadata(
                    strategy="deterministic",
                    fallback_reason=str(exc),
                )

    # ── Multi-step execution ──────────────────────────────────────────────────
    # Primary step drives validation, feedback loop, and service selection.
    # Subsequent steps are validated and executed in order; any step failure
    # is recorded in its execution_result without aborting the whole plan.
    first_step = steps[0]
    selected_service = CATALOG[first_step.service_id]

    validation = validate_step(
        service_id=first_step.service_id,
        payload=first_step.payload,
        operation_id=first_step.operation_id,
        method=first_step.method,
        skip_registry=request.dry_run,
    )

    feedback = FeedbackMetadata()

    # Feedback correction loop — only for LLM-assisted mode, primary step only
    if not validation.valid and mode == "llm-assisted":
        schema_context = get_payload_schema_prompt(first_step.service_id, first_step.operation_id)

        def _revalidate(step, skip_registry: bool):
            return validate_step(
                service_id=step.service_id,
                payload=step.payload,
                operation_id=step.operation_id,
                method=step.method,
                skip_registry=skip_registry,
            )

        first_step, validation, feedback = run_correction_loop(
            intent=request.intent,
            step=first_step,
            initial_validation=validation,
            schema_context=schema_context,
            correct_fn=correct_payload_with_feedback,
            revalidate_fn=_revalidate,
            skip_registry=request.dry_run,
        )
        steps = [first_step, *steps[1:]]

    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail={**validation.model_dump(), "feedback": feedback.model_dump()},
        )

    # Execute all steps; collect results
    execution_results: list[dict] = []
    for step in steps:
        execution_results.append(execute_step(step, dry_run=request.dry_run))

    return OrchestrationResponse(
        intent=request.intent,
        mode=mode,
        selected_service=selected_service,
        steps=steps,
        validation=validation,
        execution_result=execution_results[0],   # backward-compat: first step
        execution_results=execution_results,      # full multi-step results
        planner=planner,
        feedback=feedback,
    )
