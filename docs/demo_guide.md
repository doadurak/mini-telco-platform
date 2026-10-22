# Live demo guide

How to bring the testbed up and walk an audience that does not know the project through it
(about 25 minutes; the live part alone takes about 10).

## 1. Before the meeting (start 30 minutes early)

1. Start **Docker Desktop** and wait until it shows "Engine running".
2. Open the **Ubuntu** terminal and run:
   ```bash
   cd ~/mini-telco-platform && bash scripts/demo_up.sh
   ```
   It takes 5–8 minutes and must end with **DEMO READY** and the console URL.
3. Open **http://localhost:8099** in Edge or Chrome and press **F11** (full screen).
4. Keep open in other tabs or windows: Fig. 1 (`docs/fig1_architecture.pdf`), the paper PDF, and the
   demo video (`docs/demo_video/wmnc2026_live_demo.mp4`) as a fallback.
5. Internet is needed only for the LLM APIs. Have a phone hotspot ready.

Quick re-check at any time, without restarting anything: `venv/bin/python scripts/demo_check.py`.

If `demo_up.sh` says *Docker is not running* although Docker Desktop is open: quit Docker Desktop,
run `wsl --shutdown` in PowerShell, start Docker Desktop again, and re-run the script.

## 2. Flow of the meeting

| Time | Part | What is on screen |
|---|---|---|
| 0–2 min | The problem | Paper, first page |
| 2–6 min | Architecture | Fig. 1 |
| 6–16 min | **Live demo** | Console (http://localhost:8099) |
| 16–20 min | Results | Table I and II of the paper |
| 20–25 min | Limitations, next steps, questions | – |

### The problem (2 min)

> "Operators expose network capabilities through standard APIs, CAMARA on top of 3GPP CAPIF and the NEF.
> Using them still means knowing which API to call and writing a correct JSON payload. We let an operator
> write the request in plain English or Turkish; an LLM turns it into the API call, and a deterministic
> validator makes sure that only well-formed calls to published services reach a real 5G core."

### Architecture (4 min, Fig. 1, top to bottom)

1. **Interface:** a FastAPI backend with one endpoint, `POST /orchestrate`.
2. **Two-phase LLM planner:** phase 1 picks one of four CAMARA services, phase 2 writes the payload
   from that operation's OpenAPI schema. GPT-4o-mini, Claude Haiku 4.5 or Gemini 2.5 Flash, switchable
   at run time.
3. **Validator:** L1 JSON schema, L2 telecom rules (E.164 numbers, QoS profiles, durations, IPv4),
   L3 asks the live OpenCAPIF registry whether the service is published. A failure goes back to the LLM
   at most three times.
4. **Cross-check:** the validator cannot see a *wrong but published* service, so a live call whose
   service differs from the keyword planner's is held until the operator confirms it.
5. **Exposure and core:** OpenCAPIF (mTLS), CAMARA QoD / Location / QoS Provisioning from NCSRD,
   the NEF, and an Open5GS core with three UERANSIM phones. The PCF really authorises the QoS session.

### Live demo (10 min): the buttons in the terminal pane, left to right

| Button | Say | Point at |
|---|---|---|
| **Testbed** | "Everything here is running now: CAPIF, the providers, Open5GS and three simulated phones with their own IP addresses." | container counts, 5 discovered APIs, `uesimtun0-2` IPs |
| **S1 dry run** | "Video-streaming quality for 30 minutes. GPT picks QoD and builds the payload; all three layers pass, and L3 really asked CAPIF. Dry run: nothing is sent." | `PLAN`, `L1 L2 L3 PASS`, `registry_checked: true` |
| **S1 live** | "Same request, live. The phone number is resolved to the UE's IP from the core's subscriber database; the NEF asks the PCF, which answers 201." | `HTTP 201`, `UE IP 10.45.0.10`, `AVAILABLE`; bottom-right pane: `PCF … Response status code: 201` |
| **S2 live** | "Location: the NEF answers with an area." | `HTTP 200`, WGS-84 area |
| **S3 live** | "A vague request: better quality *for a long time*. All three LLMs pick QoS Provisioning, the plan is valid, but the keyword planner picks QoD, so the call is held." | `CROSS-CHECK … DISAGREES → HELD` |
| **S3 confirm** | "After the operator confirms, it goes to the core and the PCF accepts it." | `ACTIVE`, `UE IP 10.45.0.12` |
| *(Swagger, left)* | Let someone type an intent: open `POST /orchestrate` → *Try it out* → edit `intent` → *Execute*. Turkish works too. | the JSON response |
| *(Swagger)* | Switch the LLM: `POST /config/provider` with `{"provider": "anthropic"}`, then run S1 again: same plan from Claude. Switch back to `openai`. | `planner.model` |
| **Faults** | "We break correct plans on purpose: every fault is caught by its layer; schema and rule errors are repaired in one LLM round, an unpublished service is never executed." (about 30 s) | the L1/L2/L3 table |
| **Results** | Hand over to the results part. | |

Each live QoS button closes the earlier QoD session of that phone first, so the buttons can be pressed
again without a *409 conflict*.

### Results (4 min, paper Table I and II)

- 300 intents (152 English, 148 Turkish), three runs per LLM: IWSR **96.6% GPT-4o-mini, 96.0% Gemini,
  95.3% Claude**, keyword baseline 83.3%. Runs differ by at most 0.6 points.
- GPT's **native function calling** reaches only 36.0%, because it leaves out required fields the user
  did not mention; with our validator and feedback loop it reaches 96.0%.
- The remaining failures are mostly QoD vs. QoS Provisioning on hard intents; the cross-check holds
  75 of the 92 wrong selections before execution.
- One correction we made ourselves: in the submitted paper, 235 of the "GPT-4o-mini" results had been
  produced by Gemini (an unrecognised provider name fell back silently). The code now rejects unknown
  providers and records the model of every result; the camera-ready uses three clean GPT runs (97.3% → 96.6%).

### Limitations and next steps (2 min)

- UERANSIM cannot set up a dedicated QoS flow on the radio, so QoS is authorised in the core but not
  enforced on the air interface.
- The ground truth was labelled by us; independent labelling (especially of the 25 ambiguous intents)
  is future work.
- Intents, including phone numbers, go to an external LLM API: production needs pseudonymisation or a
  self-hosted model.
- Next: extended conference/journal version (ablations, scalability, function-calling comparison),
  a self-hosted LLM, a real gNB with QoS enforcement.

## 3. If something goes wrong

| Symptom | Do |
|---|---|
| A button prints `LLM planning failed` or hangs | Internet: switch to the phone hotspot. Or switch the LLM in Swagger (`POST /config/provider`, `anthropic`). |
| `L3 … registry_checked: false`, or a live call returns **503** | CAPIF lost its state: run `bash scripts/demo_up.sh` again (5–8 min). Meanwhile show the video. |
| S1 live shows `HTTP 409` | A QoD session is still open: press **S1 live** again (it closes the old session first). |
| Console page blank | `bash scripts/demo_up.sh` restarts it; or open http://localhost:8000/docs (Swagger only). |
| Nothing works | Play `docs/demo_video/wmnc2026_live_demo.mp4`; the recorded responses are in `docs/live_runs/`. |

## 4. Questions to expect

- **Why an LLM and not rules?** The keyword planner was written for 60 pilot intents (100% there) and
  drops to 79% on the other 240 phrasings; the LLMs stay at about 96%.
- **Can the LLM call something that does not exist?** No: L3 checks the live CAPIF registry and a live
  call is refused if the registry cannot be reached.
- **What if it picks the wrong, existing service?** That is what the cross-check is for (S3).
- **Is the 5G core real?** Yes, Open5GS with UERANSIM phones; the PCF log line is the proof. Only the
  radio-side enforcement is missing.
- **Latency?** 2–5 s with GPT or Claude, 7–8 s with Gemini; 80–99% of it is the LLM call.
  Without an LLM the platform serves about 160 requests per second.
- **Cost / privacy of external LLMs?** A few cents per hundred requests; phone numbers leave the
  premises, hence the pseudonymisation / self-hosted model point.
- **Which part is ours?** Planner, validator, cross-check, CAPIF integration, testbed integration and
  the evaluation. The CAMARA and NEF services are NCSRD's open-source code; Open5GS and UERANSIM are
  open source.
