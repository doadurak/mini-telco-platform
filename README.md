# Mini-Telco Orchestration Platform

> **AI-native, CAPIF-compliant 5G service orchestration platform** for evaluating
> LLM-based intent-to-API translation reliability in CAMARA service exposure environments.
>
> Full technical documentation: [`docs/platform_technical_paper.tex`](docs/platform_technical_paper.tex)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [CAMARA Services](#camara-services)
3. [Orchestration Modes](#orchestration-modes)
4. [CAPIF Integration](#capif-integration)
5. [Validation Framework](#validation-framework)
6. [Reliability Metrics](#reliability-metrics)
7. [Quick Start](#quick-start)
8. [Full Stack Startup](#full-stack-startup)
9. [Environment Variables](#environment-variables)
10. [API Reference](#api-reference)
11. [Evaluation](#evaluation)
12. [Known Issues](#known-issues)

---

## Architecture Overview

Four isolated layers with strict separation between probabilistic LLM reasoning
and deterministic telecom enforcement:

```
┌─────────────────────────────────────────┐
│           AI REASONING LAYER            │
│  Intent → RAG Context → LLM Planner    │
│                       → Payload Gen    │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│        DETERMINISTIC VALIDATION         │
│  L1: JSON Schema  (Pydantic)           │
│  L2: Telecom Semantic Policy           │
│  L3: CAPIF Registry Consistency        │
│       │ fail → Feedback Engine (×3)    │
└──────────────────┬──────────────────────┘
                   │ valid only
┌──────────────────▼──────────────────────┐
│          3GPP EXPOSURE LAYER            │
│  camara-QoD | NEF-QoS | CamaraLoc     │
└─────────────────────────────────────────┘
        ↕ all layers feed into ↕
┌─────────────────────────────────────────┐
│         RELIABILITY MONITORING          │
│  IWSR | SCR | SVR | HR | SS | RRF     │
└─────────────────────────────────────────┘
```

---

## CAMARA Services

| Service ID | Title | Version | Provider (Port) | Operation |
|---|---|---|---|---|
| `qod` | Quality-on-Demand | v1.1.0 | camara-QoD (8002) | `createSession` |
| `qos-profiles` | QoS Profiles | v1.1.0 | Platform catalog | `retrieveQoSProfiles`, `getQosProfile` |
| `qos-provisioning` | QoS Provisioning | v1.1.0 | NEF-QoS (8585) | `createQosAssignment` |
| `location-retrieval` | Device Location | v0.5 | CamaraLoc (8003) | `retrieveLocation` |

### QoS Profile Reference

| Profile | Media | DL/UL | Use Case |
|---|---|---|---|
| `QOS_E` | VIDEO | 1 Mbps | Basic video |
| `QOS_S` | VIDEO | 4 Mbps | Standard video |
| `QOS_M` | VIDEO | 8 Mbps | Medium video |
| `QOS_L` | AUDIO | 20 Mbps | High-quality audio |
| `QOS_E_STREAMING` | VIDEO | 3 Mbps | Enhanced streaming |
| `QOS_GAMING` | VIDEO | 10 Mbps | Gaming / low latency |
| `QOS_LOW_LATENCY` | VIDEO | 5 Mbps | Mission-critical RT |
| `QOS_CRITICAL_COMMS` | CONTROL | 2 Mbps | Emergency / public safety |

---

## Orchestration Modes

### `POST /orchestrate` – `orchestration_mode` parameter

| Mode | Behaviour |
|---|---|
| `auto` | Tries LLM planner first if API key configured; falls back to deterministic |
| `deterministic` | Rule-based keyword router (no LLM, no API key required) |
| `llm-assisted` | Requires LLM API key; fails with 502 if LLM unavailable |

### Deterministic Planner — Routing Priority

1. **Location** → keywords: `location, locate, where, gps, konum, nerede`
2. **Provisioning** → keywords: `permanent, persist, indefinite, kalıcı, sürekli, daimi`
3. **Profile discovery** → requires BOTH a profile noun (`profile/profil`) AND a discovery verb (`list, available, hangi, mevcut`)
4. **Default** → QoD session

### LLM-Assisted Planner — Two-Phase Pipeline

1. **Phase 1 (Planning):** LLM selects service, operation, method from RAG service summary
2. **Phase 2 (Payload):** LLM generates structured JSON payload grounded in full CAMARA OpenAPI schema

**Rate limiting:** Built-in 4.5 s inter-call throttler for Gemini free tier (15 RPM). HTTP 429 fails fast (no retry hang).

**Supported providers:** `gemini` (default), `openai`, `anthropic` — set via `LLM_PROVIDER` in `.env`.

---

## CAPIF Integration

Full 3GPP CAPIF (TS 23.222) API Invoker lifecycle:

| Endpoint | Description |
|---|---|
| `POST /capif/invokers/onboard` | Register as CAPIF API Invoker (mTLS cert issuance) |
| `GET /capif/discover` | Discover published CAMARA services from CAPIF registry |
| `GET /capif/status` | CAPIF connectivity and invoker status |
| `GET /capif/invoker` | Current invoker details |
| `POST /notifications` | Webhook for CAPIF test notifications + provider callbacks (→ 204) |
| `GET /notifications` | Webhook metadata for CAPIF probes |

**Onboarding flow:**
1. HTTP Basic Auth → Register (port 8084) → JWT token
2. CSR submission → CAPIF CA signs invoker certificate
3. mTLS certificate stored in container for authenticated discovery

---

## Validation Framework

Three independent layers — all must pass before execution:

### Layer 1 — JSON Schema (SCR metric)
Pydantic structural validation. Catches missing required fields, wrong types,
out-of-range values.

### Layer 2 — Telecom Semantic Policy (SVR metric)
- E.164 phone number format: `+[1-9][0-9]{4,14}`
- At least one device identifier (phoneNumber / ipv4Address / ipv6Address)
- QoS profile must be one of the 8 valid CAMARA identifiers
- QoD duration: 1–7200 s (platform policy max)
- `maxAge` for location: 1–3600 s (**field name is `maxAge`, NOT `maxAgeSeconds`**)
- Valid IPv4 for applicationServer
- Operation ID must exist in catalog; HTTP method must match catalog

### Layer 3 — CAPIF Registry (HR metric)
- Queries live CAPIF discovery endpoint
- Verifies selected service exists in registry
- Non-blocking: if CAPIF unreachable, skips with `registry_checked: false`

### Feedback Engine (RRF metric)
When LLM payload fails validation:
1. Structured correction prompt sent back to LLM (original intent + rejected payload + layer-tagged errors)
2. LLM returns corrected payload
3. Re-validate → repeat up to **3 iterations**
4. `feedback.recovered = true` if any iteration succeeds

---

## Reliability Metrics

| Metric | Formula | Measures |
|---|---|---|
| **IWSR** | `valid_plans / total_intents` | End-to-end success rate |
| **SCR** | `l1_passes / total_plans` | JSON schema compliance |
| **SVR** | `l2_passes / l1_passes` | Telecom semantic correctness |
| **HR** | `wrong_service / total_plans` | Hallucinated (non-existent) service selection |
| **SS** | `1 - (distinct_outputs-1)/runs` | Output consistency across runs |
| **RRF** | `feedback_recovered / feedback_attempted` | Correction loop effectiveness |

---

## Quick Start

### Local (no Docker)

```bash
cd /home/turkad/mini-telco-platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open: [http://localhost:8000](http://localhost:8000) · [Swagger](http://localhost:8000/docs)

### Docker (backend only)

```bash
# Without OpenCAPIF
docker compose up --build

# With OpenCAPIF network (capif-network must exist)
docker compose -f docker-compose.capif.yml up --build
```

### Post-startup CAPIF onboarding

```bash
# Clear stale cache
docker exec mini-telco-backend-capif sh -c \
  'rm -f /app/backend/capif/invoker_details.json \
         /app/backend/capif/register_auth.json'

# Onboard
curl -X POST http://localhost:8000/capif/invokers/onboard \
  -H 'Content-Type: application/json' \
  -d '{
    "api_invoker_information": "Mini-Telco-Platform-Orchestrator",
    "public_key": "",
    "notification_destination": "http://localhost:8000/notifications"
  }'
```

---

## Full Stack Startup

```bash
chmod +x start.sh
./start.sh           # Start everything (OpenCAPIF + NEF + providers + backend)
./start.sh --stop    # Stop all managed services
./start.sh --status  # Show running container status
```

**Startup order:**
1. `capif-network` Docker bridge
2. OpenCAPIF stack (nginx + capifcore + register + vault + mongo)
3. NEF Monitoring stack (port 9999)
4. NEF-QoS / AsSessionWithQoS (port 8585)
5. camara-QoD provider (port 8002)
6. CamaraLocationRetrieval (port 8003)
7. mini-telco-backend (port 8000)
8. CAPIF automated setup (create users → publish services → onboard invoker)

**Port map:**

| Service | Port | Docs |
|---|---|---|
| mini-telco-backend | 8000 | http://localhost:8000/docs |
| camara-QoD | 8002 | http://localhost:8002/docs |
| CamaraLocationRetrieval | 8003 | http://localhost:8003/docs |
| OpenCAPIF Register | 8084 | https://localhost:8084 |
| NEF-QoS | 8585 | http://localhost:8585/docs |
| NEF Monitoring | 9999 | http://localhost:9999/docs |
| OpenCAPIF (nginx/TLS) | 443 | https://localhost |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini`, `openai`, or `anthropic` |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `GEMINI_MIN_INTERVAL_S` | `4.5` | Rate limiter inter-call gap (s) |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base URL |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `MOCK_MODE` | `false` | `true` = no live provider calls |
| `ORCHESTRATION_DEFAULT_MODE` | `auto` | Default mode for `auto` requests |
| `LLM_TEMPERATURE` | `0.1` | LLM generation temperature |
| `LLM_TIMEOUT_SECONDS` | `30` | LLM request timeout |
| `CAPIF_BASE_URL` | `https://localhost` | External CAPIF URL |
| `CAPIF_USE_DOCKER_NETWORK` | `false` | `true` when on capif-network |
| `CAPIF_INTERNAL_BASE_URL` | `https://nginx` | Internal CAPIF gateway |
| `CAPIF_VERIFY_SSL` | `false` | CAPIF TLS verification |
| `CAPIF_REQUEST_TEST_NOTIFICATION` | `true` | Request CAPIF test notification |
| `QOD_PROVIDER_URL` | `http://host.docker.internal:8002` | camara-QoD provider |
| `LOCATION_PROVIDER_URL` | `http://host.docker.internal:8003` | Location provider |
| `NEF_QOS_PROVIDER_URL` | `http://host.docker.internal:8585` | NEF-QoS provider |
| `REGISTER_ADMIN_USERNAME` | `admin` | OpenCAPIF register admin |
| `REGISTER_ADMIN_PASSWORD` | `password123` | OpenCAPIF register password |
| `REGISTER_DEMO_USERNAME` | `mini_platform_demo` | Platform CAPIF user |

---

## API Reference

### Orchestrate

```http
POST /orchestrate
Content-Type: application/json

{
  "intent": "Boost video streaming for +905551112233 for 15 minutes",
  "dry_run": true,
  "orchestration_mode": "auto"
}
```

**Example intents:**

```json
// QoD – LLM mode
{ "intent": "QoD session for +905551112233 with QOS_L for 300 seconds",
  "orchestration_mode": "llm-assisted", "dry_run": false }

// Location – deterministic
{ "intent": "Where is device +306912345678?",
  "orchestration_mode": "deterministic", "dry_run": true }

// QoS profiles discovery
{ "intent": "List available QoS profiles for +34600000000",
  "orchestration_mode": "auto", "dry_run": true }

// Permanent QoS assignment (Turkish)
{ "intent": "+905551112233 numaralı cihaza kalıcı QOS_L ata",
  "orchestration_mode": "deterministic", "dry_run": true }
```

### Health

```http
GET /health
→ { "status": "ok", "mockMode": false, "environment": "development" }
```

### CAPIF Discovery

```http
GET /capif/discover
→ { "status": "discovered", "services": { "serviceAPIDescriptions": [...] } }
```

---

## Evaluation

```bash
# Activate venv first
source venv/bin/activate

# Deterministic baseline (fast, no API quota)
python scripts/run_evaluation.py \
  --mode deterministic \
  --output datasets/eval_results_deterministic.json

# LLM-assisted (max 10 entries, 4.5 s delay for Gemini free tier)
python scripts/run_evaluation.py \
  --mode llm-single \
  --max 10 \
  --delay 4.5 \
  --output datasets/eval_results_llm.json

# Resume interrupted run
python scripts/run_evaluation.py \
  --mode llm-assisted \
  --resume datasets/eval_results_llm.json \
  --delay 4.5
```

Dataset: `datasets/ground_truth.json` — 60 entries, EN/TR, easy/medium/hard

---

## Known Issues

| Issue | Status | Workaround |
|---|---|---|
| QoS Provisioning live calls fail (PCF unreachable) | Open | Use `dry_run: true` |
| Gemini daily quota (1500 RPD free tier) | Operational limit | Use `--max 10` per run; resets midnight PT |
| CAPIF cert expiry after 180 days | Operational | Delete invoker cache, re-onboard |
| `maxAgeSeconds` (old field name) rejected | Fixed  | All layers now use `maxAge` |
| LLM 429 caused 70s hang (retry loop) | Fixed  | 429 now fails fast |
| Duration "300 seconds" parsed as 18000 s | Fixed  | Seconds unit now handled correctly |

---

## Project Structure

```
mini-telco-platform/
├── backend/
│   ├── main.py              # FastAPI app + all routes
│   ├── config.py            # Settings (loaded from .env)
│   ├── models.py            # All Pydantic data models
│   ├── service_catalog.py   # CAMARA service catalog (4 services)
│   ├── intent_engine.py     # Deterministic planner (keyword routing)
│   ├── llm_planner.py       # LLM planner + rate limiter + RAG grounding
│   ├── rag_context.py       # CAMARA YAML parser + schema injection
│   ├── validator.py         # 3-layer validator (L1/L2/L3)
│   ├── feedback_engine.py   # Bounded correction loop (max 3 iter)
│   ├── executor.py          # CAMARA provider HTTP dispatch
│   ├── evaluation_engine.py # IWSR/SCR/SVR/HR/SS/RRF computation
│   └── capif/               # CAPIF onboard/discover/publish
├── camara-services/         # CAMARA OpenAPI YAML specs
├── datasets/                # Ground truth + evaluation results
├── docs/                    # Technical paper (LaTeX)
├── providers/               # NEF / NEF-QoS / camara-QoD / CamaraLoc
├── scripts/                 # Evaluation harness
├── frontend/index.html      # Landing page
├── docker-compose.yml
├── docker-compose.capif.yml # CAPIF-network variant
├── Dockerfile
├── .env                     # Environment configuration
└── start.sh                 # Full-stack startup automation
```

---

*Türkan Doğa Durak — CTTC, 2026*
