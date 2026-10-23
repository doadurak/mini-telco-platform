# Mini Telco Platform: setup and usage guide

How to install the platform on a new computer, start it, check it, and use it, both through the
API documentation page (Swagger) and through the terminal. Every request and every output line
used in the demo is explained.

---

## 1. What you are installing

The platform turns a request written in plain English or Turkish (an *intent*) into a validated
CAMARA network API call and executes it on a 5G core that runs in Docker on the same machine.

| Component | What it is | Where it comes from | Port(s) |
|---|---|---|---|
| **Orchestration backend** | Our FastAPI service: LLM planner, three-layer validator, cross-check, CAPIF client, executor | this repository (`backend/`) | 8000 |
| **OpenCAPIF** | 3GPP CAPIF reference implementation: API registry, invoker onboarding, mTLS | ETSI OCF, `v4.0.0-release` | 443, 8080, 8084, 8082, 8083, 8200 |
| **CAMARA QoD provider** | Quality-on-Demand API, forwards to NEF-QoS | NCSRD FRONT group (git submodule + our patch) | 8002 |
| **CAMARA Location provider** | Location Retrieval API, forwards to the NEF Monitoring Event API | NCSRD FRONT group (submodule + patch) | 8003 |
| **NEF-QoS** | 3GPP AsSessionWithQoS (TS 29.122) towards the PCF | NCSRD FRONT group (submodule + patch) | 8585 |
| **NEF Monitoring Event** | 3GPP Monitoring Event API; location data is emulated | NCSRD FRONT group (submodule + patch) | 9999 |
| **Open5GS 5G core** | AMF, SMF, UPF, PCF, … (PCF on host port 7777) | Docker image `gradiant/open5gs:2.7.2` | 7777, 27019 |
| **UERANSIM** | One gNB and three phones (UEs) | Docker image `gradiant/ueransim:3.2.6` | – |
| **Live console** | The demo page: Swagger + terminal buttons + live logs | this repository (`scripts/demo_video/`) | 8099 |

In total about 45 containers. The three phones get these numbers and IP addresses:

| Phone number (MSISDN) | UE IP address |
|---|---|
| +905321234567 | 10.45.0.10 |
| +12025550180 | 10.45.0.11 |
| +905551112233 | 10.45.0.12 |

---

## 2. Requirements

**Hardware**
- 16 GB RAM (the stack uses about 10 GB), 4 or more CPU cores.
- About 25 GB of free disk space (Docker images).

**Operating system**: one of
- **Windows 10/11 with WSL2** and an Ubuntu 22.04 or 24.04 distribution (the setup the platform was developed on), or
- **Ubuntu 22.04/24.04** directly (a VM is fine).

**Software**
- Docker: **Docker Desktop** with *WSL integration* enabled for Ubuntu (Windows), or **Docker Engine + the compose plugin** (Linux).
- In Ubuntu: `git`, `curl`, `netcat-openbsd`, `python3` (3.10 or newer) and `python3-venv`.

**Accounts and network**
- At least one LLM API key: **OpenAI** (GPT-4o-mini, the default), optionally **Anthropic** (Claude Haiku 4.5) and **Google** (Gemini 2.5 Flash).
- Internet access to github.com, labs.etsi.org (OpenCAPIF source and the `labs.etsi.org:5050` image registry), Docker Hub, and the LLM APIs. After installation, internet is only needed for the LLM calls.

---

## 3. Installation (once per computer, 30–60 minutes)

### 3.1 Windows only: WSL2, Ubuntu and Docker Desktop

1. Open **PowerShell as administrator** and run `wsl --install -d Ubuntu-24.04`. Restart Windows if asked, then open *Ubuntu* from the Start menu and create a Linux user.
2. Install **Docker Desktop** from docker.com and start it.
3. In Docker Desktop: *Settings → Resources → WSL integration* → switch on **Ubuntu-24.04** → *Apply & restart*.
4. In Docker Desktop: *Settings → Resources → Advanced*: give Docker at least **10 GB** of memory if a limit is shown.

All following commands run **in the Ubuntu terminal**, not in PowerShell.

### 3.2 Linux only: Docker Engine

Install Docker Engine and the compose plugin as described on docs.docker.com, then allow your user to use Docker:
`sudo usermod -aG docker $USER` and log out and in again.

### 3.3 Both: packages, code, setup script

```bash
sudo apt update && sudo apt install -y git curl netcat-openbsd python3 python3-venv
cd ~
git clone --recurse-submodules https://github.com/doadurak/mini-telco-platform.git
cd mini-telco-platform
bash scripts/setup.sh
```

`scripts/setup.sh` does six things and prints ✔ for each:

| Step | What it does |
|---|---|
| 1. Prerequisites | Checks git, Docker (running), docker compose, Python ≥ 3.10, venv, curl, nc, and the RAM. |
| 2. Provider repositories | Downloads the four NCSRD repositories (git submodules, pinned versions) and applies our patches from `providers/patches/`: ports, Docker networks, CAPIF host names, the NEF Monitoring Event fixes, and the compose files the upstream repositories do not include. |
| 3. OpenCAPIF | Downloads ETSI OpenCAPIF `v4.0.0-release` into `~/OpenCAPIF/capif` (unchanged upstream code). |
| 4. Python | Creates `venv/` and installs `requirements.txt` (used by the demo scripts and the evaluation). |
| 5. Configuration | Creates `.env` from `.env.example` and warns if no LLM API key is set. |
| 6. Docker network | Creates the shared Docker network `capif-network`. |

It is safe to run the script again; finished steps are skipped.

### 3.4 Add the API key(s)

Open `.env` (for example `nano .env`) and fill in at least:

```
OPENAI_API_KEY=sk-...
```

Optional: `ANTHROPIC_API_KEY=...` and `GEMINI_API_KEY=...`. Keep `LLM_PROVIDER=openai`.
Never commit `.env`; it is excluded by `.gitignore`.

### 3.5 First start

```bash
bash scripts/demo_up.sh
```

The first run downloads all Docker images and builds four of them: **15–30 minutes**. Later starts take
**5–8 minutes**. The script must end like this:

```
 ✔ Docker containers                  44 containers up
 ✔ Backend API                        http://localhost:8000/docs
 ✔ OpenCAPIF discovery (L3)           5 APIs discovered over mTLS
 ✔ UERANSIM UEs on Open5GS            10.45.0.10/32, 10.45.0.11/32, 10.45.0.12/32
 ✔ LLM planner: GPT-4o-mini           gpt-4o-mini: qod, L1-L3 pass, 3957 ms
 ✔ LLM planner: Claude Haiku 4.5      claude-haiku-4-5-20251001: qod, L1-L3 pass, 2483 ms

DEMO READY  (planner set back to GPT-4o-mini)

Live console: http://localhost:8099
```

Without an Anthropic key, the Claude line says *skipped*; everything works with GPT-4o-mini.
Then open **http://localhost:8099** in a browser (Edge or Chrome on Windows work: WSL forwards the ports).

---

## 4. Daily operation

| Task | Command (in `~/mini-telco-platform`) |
|---|---|
| Start everything, from any state | `bash scripts/demo_up.sh` |
| Check that everything works (30 s, 2 small LLM calls) | `venv/bin/python scripts/demo_check.py` |
| Live console | http://localhost:8099 |
| API documentation only (Swagger) | http://localhost:8000/docs |
| Stop the platform | `./start.sh --stop` (OpenCAPIF and the 5G core keep running; `docker stop $(docker ps -q)` stops everything) |
| See all containers | `docker ps` |

**After a reboot, sleep or Docker restart, always run `bash scripts/demo_up.sh` again.** The 5G core
containers restart by themselves, but OpenCAPIF keeps its certificates in memory (Vault runs in
development mode), so it must be rebuilt; `demo_up.sh` does that (`scripts/reset_capif.sh`) and
onboards everything again.

`demo_up.sh` in detail:

1. `scripts/reset_capif.sh` recreates OpenCAPIF, then runs `start.sh`, which starts in this order:
   the NEF stack, the Open5GS + UERANSIM testbed (`testbed/open5gs/up.sh`), NEF-QoS, the CAMARA QoD and
   Location providers and our backend; it then creates the CAPIF user, lets the NEF publish the five
   network APIs in CAPIF and onboards our backend as a CAPIF invoker.
2. It closes QoD sessions left open by earlier runs (a second session for the same phone would get *409*).
3. It runs the health check (`scripts/demo_check.py`) and starts the live console.

---

## 5. How a request is processed

Example: *"Activate video-streaming quality for +905321234567 for the next 30 minutes."*

| # | Step | Code |
|---|---|---|
| 1 | `POST /orchestrate` receives the intent. | `backend/main.py` `orchestrate()` |
| 2 | **Planner, phase 1:** the LLM picks one of four CAMARA services (QoD, QoS Profiles, QoS Provisioning, Location Retrieval). Its prompt contains the service summaries and the APIs published in CAPIF. | `backend/llm_planner.py` `build_llm_execution_plan()` |
| 3 | **Planner, phase 2:** the LLM writes the JSON payload; its prompt contains the OpenAPI schema of the chosen operation. | same function; schemas: `backend/rag_context.py`, `camara-services/` |
| 4 | **L1 schema:** the payload is checked against the operation's Pydantic model (field names, types, required fields). | `backend/validator.py` `_validate_layer1` |
| 5 | **L2 telecom rules:** E.164 phone number, QoS profile known to the operator, duration 1–7200 s, valid IPv4, operation exists. | `_validate_layer2` |
| 6 | **L3 registry:** the backend asks OpenCAPIF (over mTLS) whether the service is published. | `_validate_layer3`, `backend/capif/client.py` |
| 7 | **Feedback:** if L1–L3 fail, the error messages go back to the LLM, at most three times. | `backend/feedback_engine.py` |
| 8 | **Cross-check:** the keyword planner plans the same intent; if it picks another service, a live call is held until it is sent again with `confirm_service: true`. | `backend/main.py`, `backend/intent_engine.py` |
| 9 | **Execution** (only if `dry_run` is false): the phone number is resolved to the UE IP from the Open5GS subscriber database; the intent-level QoS profile is mapped to the operator profile (e.g. `QOS_E_STREAMING → QOS_S`); the CAMARA provider is called. | `backend/executor.py`, `backend/device_resolver.py`, `backend/qos_profiles.py` |
| 10 | **Core:** QoD → NEF-QoS (AsSessionWithQoS) → Open5GS **PCF**, which binds the session to the UE's PDU session and answers 201. Provisioning goes directly to NEF-QoS; Location goes to the NEF Monitoring Event API. | providers + `testbed/open5gs` |

---

## 6. Using the API documentation page (Swagger)

Open **http://localhost:8000/docs** (or the left half of the live console). For each endpoint:
click the row → **Try it out** → edit the body → **Execute** → read **Server response → Response body**.

### 6.1 `POST /orchestrate` (the main endpoint)

**Request body**

| Field | Values | Meaning |
|---|---|---|
| `intent` | text | The request in English or Turkish. Use one of the three phone numbers above for live calls. |
| `dry_run` | `true` (default) / `false` | `true`: plan and validate only, no provider is called. `false`: also execute on the 5G core. |
| `orchestration_mode` | `auto` (default), `llm-assisted`, `deterministic` | `llm-assisted`: always the LLM planner. `deterministic`: keyword planner only, no LLM. `auto`: LLM if a key is set, keyword planner as fallback. |
| `check_registry` | `true` (default) / `false` | Run L3 against OpenCAPIF. With `false`, L3 is skipped. |
| `confirm_service` | `false` (default) / `true` | Confirms a live call that the cross-check would otherwise hold. |

**Example 1, dry run**

```json
{"intent": "Activate video-streaming quality for +905321234567 for the next 30 minutes.",
 "dry_run": true, "orchestration_mode": "llm-assisted"}
```

**Example 2, live call:** the same body with `"dry_run": false`.

**Example 3, a vague request** (held by the cross-check, then confirmed):

```json
{"intent": "Provide network quality improvement for device +905551112233 for a long time",
 "dry_run": false, "orchestration_mode": "llm-assisted"}
```

Send it a second time with `"confirm_service": true` to execute it.

**Example 4, an invalid request that the validator repairs:**

```json
{"intent": "Give video quality to +905321234567 for 5 hours", "dry_run": true, "orchestration_mode": "llm-assisted"}
```

L2 rejects 18000 s (maximum 7200 s), and the feedback loop corrects the duration to 7200.

**Response body**

| Field | Meaning |
|---|---|
| `mode` | `llm-assisted` or `deterministic`: which planner produced the plan. |
| `selected_service` | The CAMARA service chosen (catalogue entry with its operations). |
| `steps[]` | The plan: `service_id`, `operation_id`, `method`, `path`, `payload` (the CAMARA request body the LLM wrote) and `rationale` (the LLM's one-sentence reason). Multi-request intents give several steps. |
| `validation.valid` | `true` if all three layers passed. |
| `validation.layer1_schema` / `layer2_semantic` / `layer3_registry` | `passed` and the `issues` found by each layer. |
| `validation.registry_checked` | `true` if L3 really reached OpenCAPIF. `false` means CAPIF was unreachable (a live call is then refused). |
| `feedback` | `attempted`, `iterations`, `recovered` and the `history` of corrections (issues sent back to the LLM and the corrected payload). |
| `service_crosscheck` | `keyword_planner_service`, `agrees` and `held` (true if a live call was stopped for confirmation). |
| `execution_result` | What the execution did; see the table below. `execution_results` lists it for every step. |
| `planner` | `model` (e.g. `gpt-4o-mini`), `used_discovery` (whether the CAPIF list was in the prompt), `raw_plan` (the raw LLM outputs). |
| `timings_ms` | `planning`, `validation`, `feedback`, `execution`, `total` in milliseconds. |

**`execution_result.status`**

| Status | Meaning | Main fields |
|---|---|---|
| `dry-run` | Nothing was sent. | the planned `payload` |
| `created` (QoD) | The QoD session was created. | `sessionId`, `qosStatus` (`AVAILABLE`), `qosProfile` (operator profile), `requestedQosProfile`, `resolvedUeIpv4`, `duration`, `provider.http_status` (201) |
| `created` (Provisioning) | The QoS assignment was created in the core. | `assignmentStatus` (`ACTIVE`), `resolvedUeIpv4`, `ueIpv4Source` (`subscriber-db`), `provider.http_status` (201) |
| `ok` (Location) | The location was retrieved. | `area` (WGS-84 polygon), `lastLocationTime` |
| `ok` (QoS Profiles) | The list of profiles the platform supports. | `qosProfiles` |
| `held-for-confirmation` | The cross-check stopped the live call. | `reason`; resend with `confirm_service: true` |
| `provider-error` | The provider answered with an error. | `provider.http_status`, `error`, `detail` (e.g. 409: session already open) |

**HTTP status codes of `/orchestrate`**

| Code | When |
|---|---|
| 200 | Planned (and executed or held); read `execution_result`. |
| 422 | The plan still failed validation after three corrections; `detail` lists the issues. |
| 502 | The LLM call failed (no internet, wrong key, quota). |
| 503 | Live call refused because L3 could not reach OpenCAPIF: run `bash scripts/demo_up.sh`. |

### 6.2 Other endpoints

| Endpoint | Use |
|---|---|
| `GET /health` | Is the backend up? |
| `GET /catalog/services` | The four CAMARA services and their operations. |
| `GET /config/provider`, `POST /config/provider` | Show / switch the LLM at run time. Body: `{"provider": "openai"}`, `"anthropic"` or `"gemini"`. |
| `GET /capif/status` | Connection to OpenCAPIF, certificates present. |
| `GET /capif/invoker` | Our invoker identity in CAPIF. |
| `GET /capif/discover` | The network APIs published in CAPIF (should list 5). |
| `POST /capif/invokers/onboard` | Onboard the backend as a CAPIF invoker (done by `start.sh`). |
| `POST /capif/publish`, `POST /capif/publish/catalog` | Publish services in CAPIF (done by `start.sh`). |
| `POST /notifications` | Callback receiver for CAPIF and provider notifications. |

The same calls work without Swagger, for example:

```bash
curl -s -X POST http://localhost:8000/orchestrate -H 'Content-Type: application/json' \
  -d '{"intent": "Where is +905551112233?", "dry_run": false, "orchestration_mode": "llm-assisted"}'
```

---

## 7. Using the terminal and the live console

### 7.1 The live console (http://localhost:8099)

| Area | Content |
|---|---|
| Left | The Swagger page of the backend (section 6). |
| Right, top: **Terminal** | Each button runs a real command on the machine; its output appears line by line. The first line (`turkad@testbed:~/mini-telco-platform$ …`) is the command itself. |
| Right, middle | `docker logs -f mini-telco-backend-capif`: every request the backend receives, with its HTTP status. |
| Right, bottom | `docker logs -f nef-qos`: the NEF forwarding QoS requests to the Open5GS PCF and the PCF's answer. |

| Button | Command it runs |
|---|---|
| Testbed | `python scripts/demo_cli.py status` |
| S1 dry run | `python scripts/demo_cli.py run s1` |
| S1 live | `python scripts/demo_cli.py run s1 --live` |
| S2 live | `python scripts/demo_cli.py run s2 --live` |
| S3 live | `python scripts/demo_cli.py run s3 --live` |
| S3 confirm | `python scripts/demo_cli.py run s3 --live --confirm` |
| Faults | `python scripts/demo_cli.py faults --per-fault 1` |
| Results | `python scripts/demo_cli.py results` |
| Clear | empties the terminal pane |

The same commands can be typed in the Ubuntu terminal (`venv/bin/python scripts/demo_cli.py …`).
The scenarios: **S1** = video-streaming quality for 30 minutes (QoD); **S2** = location of a phone;
**S3** = a vague request without a duration (*"for a long time"*).

### 7.2 `demo_cli.py status` (Testbed)

| Output | Meaning |
|---|---|
| `OpenCAPIF (CCF, register, Vault)  22 up` … | Number of running containers per group. |
| `CAPIF discovery (invoker INV…, mTLS): discovered` + 5 API names | Our backend is a CAPIF invoker and found the five published network APIs. |
| `uesimtun0  10.45.0.11/32` … | The three UERANSIM phones and the IP addresses the 5G core assigned to them. |

### 7.3 `demo_cli.py run …` (S1, S2, S3)

| Output line | Meaning |
|---|---|
| `REQUEST intent: … dry_run: …` | The intent sent to `POST /orchestrate` (phone number masked on screen). |
| `PLAN gpt-4o-mini: qod / createSession` | Model, chosen service and operation (planner phase 1). |
| `payload: {…}` | The CAMARA request body the LLM wrote (phase 2). |
| `VALIDATION L1 schema PASS L2 semantic PASS L3 CAPIF registry PASS` | Result of the three layers. |
| `registry_checked: true` | L3 really queried OpenCAPIF. |
| `CROSS-CHECK keyword planner selects qod: agrees` | The keyword planner chose the same service. `DISAGREES -> live call HELD` means the live call was stopped. |
| `EXECUTION dry-run: … provider NOT called` | Dry run: nothing was sent. |
| `EXECUTION held for operator confirmation, provider NOT called` | Stopped by the cross-check (S3 live). |
| `EXECUTION provider HTTP 201 :8002/quality-on-demand/v1/sessions` | The CAMARA provider accepted the call. |
| `UE IP 10.45.0.10 (5GC subscriber DB)` | Phone number resolved to the UE's IP from the Open5GS database. |
| `profile QOS_E_STREAMING -> QOS_S` | Intent-level profile mapped to the operator profile the network enforces. |
| `status: AVAILABLE` / `ACTIVE` | QoD session active / QoS assignment active. |
| `location area: Polygon with N WGS-84 points` | S2: the location returned by the NEF (emulated data). |
| `TIMINGS planning … validation … execution … total` | Time per stage; planning is the LLM call. |
| `REFUSED … CAPIF registry unreachable` | OpenCAPIF lost its state: run `bash scripts/demo_up.sh`. |

In the **bottom log pane**, a live QoS call (S1 live, S3 confirm) shows:
`Created subscription …` → `Forwarding subscription … to PCF` → `Response status code: 201` →
`PCF successfully allocated resources …`. This is the PCF of the Open5GS core accepting the session.

### 7.4 Other commands

| Command | Shows |
|---|---|
| `demo_cli.py faults --per-fault 1` | Faults injected into correct plans: which layer catches each, whether feedback repairs it (L1/L2 yes, unpublished service no). |
| `demo_cli.py results` | IWSR, SCR, SVR, HR of each planner on the 300-intent benchmark. |
| `demo_cli.py core-evidence` | The last NEF→PCF log lines and the SMF's list of UE sessions. |
| `demo_cli.py load --quick` | A short concurrency test (requests per second, latency). |
| `docker logs --tail 20 pcf` | The Open5GS PCF's own log. |

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `setup.sh`: *Docker is installed but not running* | Start Docker Desktop (Windows) or `sudo systemctl start docker`. |
| `Cannot connect to the Docker daemon` in Ubuntu although Docker Desktop runs | Docker Desktop → Settings → Resources → WSL integration: enable Ubuntu. If it is enabled: quit Docker Desktop, run `wsl --shutdown` in PowerShell, start Docker Desktop again. |
| `setup.sh`: a patch *does not apply* | The provider folder is half-patched or locally changed. Reset it with `git -C providers/<name> checkout . && git -C providers/<name> clean -fd` (this deletes the untracked files in that folder) and run `setup.sh` again. |
| Health check ✘ *OpenCAPIF discovery* or live calls return **503** | Run `bash scripts/demo_up.sh` (OpenCAPIF lost its in-memory certificates after a restart). |
| Health check ✘ *UERANSIM UEs* | `bash testbed/open5gs/up.sh`. |
| `LLM planning failed` / HTTP 502 | Check internet and the key in `.env`; then `docker compose -f docker-compose.capif.yml up -d --build` to reload `.env` into the backend. |
| Live QoD returns `provider-error` 409 | A session for that phone is still open: run the S1 live button again (it closes the old session first). |
| Port already in use | Another program uses one of the ports in section 1; stop it. |
| The machine becomes slow / WSL hangs | The stack needs about 10 GB; close other heavy programs and avoid running evaluations while the demo runs. |

---

## 9. Reproducing the evaluation (optional)

```bash
venv/bin/python scripts/summarize_runs.py     # Table I of the paper from the stored result files
LLM_PROVIDER=openai venv/bin/python scripts/run_evaluation.py --mode llm-assisted --no-registry \
  --output /tmp/my_run.json                     # a new GPT-4o-mini run on the 300 intents (~25 min, ~1 USD)
venv/bin/python -m pytest -q tests            # unit tests (no API calls)
```

The result files, the dataset and the scripts are described in the main `README.md`.
