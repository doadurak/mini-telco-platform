#!/usr/bin/env python3
"""
Readable live demo commands against the running platform (used for the demo video).

Every command calls the real system and prints a compact view of the response:

  demo_cli.py status                  containers, CAPIF-published APIs, UE PDU sessions
  demo_cli.py run s1 [--live]         POST /orchestrate for a scenario (default dry_run=true)
  demo_cli.py core-evidence           NEF-QoS log lines for the PCF application session
  demo_cli.py compare s1              same intent on all three LLM backends (dry_run)
  demo_cli.py faults                  per-layer fault injection (live L3, real feedback loop)
  demo_cli.py load                    short concurrency test
  demo_cli.py results                 recorded 300-entry results, ablations, pilot split

MSISDNs are masked in the output.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import requests

API = "http://localhost:8000"
QOD = "http://localhost:8002/quality-on-demand/v1"
ROOT = Path(__file__).resolve().parent.parent

SCENARIOS = {
    "s1": ("Activate video-streaming quality for +905321234567 for the next 30 minutes.", "10.45.0.10"),
    "s2": ("Retrieve the current location of device +905551112233.", None),
    "s3": ("Provide network quality improvement for device +905551112233 for a long time", "10.45.0.12"),
}
PHONE_RE = re.compile(r"\+\d{10,15}")


def mask(text: str) -> str:
    return PHONE_RE.sub(lambda m: m.group()[:6] + "•" * (len(m.group()) - 8) + m.group()[-2:], text)


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


def ok(flag: bool) -> str:
    return "PASS" if flag else "FAIL"


# ── status ───────────────────────────────────────────────────────────────────

GROUPS = {
    "OpenCAPIF (CCF, register, Vault)": lambda n: n.startswith("services-") or n in ("register", "helper"),
    "CAMARA / NEF providers": lambda n: n in ("camara-qod", "camara-location-retrieval", "nef", "nef-qos"),
    "Open5GS 5GC + UERANSIM": lambda n: n in ("nrf", "scp", "ausf", "udm", "udr", "pcf", "bsf", "nssf",
                                              "amf", "smf", "upf", "gnb", "ues", "mongo5g"),
    "Orchestration backend": lambda n: n == "mini-telco-backend-capif",
}


def cmd_status(_):
    names = sh("docker ps --format '{{.Names}}'").split()
    print("Running containers")
    for label, match in GROUPS.items():
        print(f"  {label:34s} {sum(1 for n in names if match(n)):3d} up")
    d = requests.get(f"{API}/capif/discover", timeout=20).json()
    apis = sorted(a.get("apiName") for a in (d.get("services") or {}).get("serviceAPIDescriptions", []))
    print(f"\nCAPIF discovery (invoker {d.get('invokerId', '?')[:12]}..., mTLS): {d.get('status')}")
    for a in apis:
        print(f"  - {a}")
    ues = [l.split() for l in sh("docker exec ues ip -4 -o addr").splitlines() if "uesimtun" in l]
    print("\nUE PDU sessions (UERANSIM -> Open5GS UPF)")
    for u in ues:
        print(f"  {u[1]:10s} {u[3]}")


# ── orchestrate ──────────────────────────────────────────────────────────────

def _close_qod_sessions(phone: str, ip: str) -> None:
    body = {"device": {"phoneNumber": phone, "ipv4Address": {"publicAddress": ip, "privateAddress": ip}}}
    try:
        items = requests.post(f"{QOD}/retrieve_sessions", json=body, timeout=10).json()
        items = items if isinstance(items, list) else items.get("sessions", [])
        for s in items:
            requests.delete(f"{QOD}/sessions/{s['sessionId']}", timeout=10)
    except Exception:
        pass


def _orchestrate(intent: str, live: bool) -> dict:
    r = requests.post(f"{API}/orchestrate", json={"intent": intent, "dry_run": not live,
                                                   "orchestration_mode": "llm-assisted"}, timeout=120)
    return r.json()


def cmd_run(a):
    intent, ue_ip = SCENARIOS[a.scenario]
    if a.live and ue_ip:
        _close_qod_sessions(PHONE_RE.search(intent).group(), ue_ip)
    d = _orchestrate(intent, a.live)
    v, step, ex = d["validation"], d["steps"][0], d["execution_result"]
    print(f"REQUEST     intent: \"{mask(intent)}\"")
    print(f"            dry_run: {str(not a.live).lower()}   mode: llm-assisted")
    print(f"PLAN        {d['planner'].get('model')}: {step['service_id']} / {step['operation_id']}")
    for i, chunk in enumerate(textwrap.wrap(mask(json.dumps(step["payload"])), 84)):
        print(("            payload: " if i == 0 else "                     ") + chunk)
    print(f"VALIDATION  L1 schema {ok(v['layer1_schema']['passed'])}   L2 semantic {ok(v['layer2_semantic']['passed'])}"
          f"   L3 CAPIF registry {ok(v['layer3_registry']['passed'])}")
    print(f"            registry_checked: {str(v['registry_checked']).lower()}  (live CAPIF discovery over mTLS)")
    if ex.get("status") == "dry-run":
        print("EXECUTION   dry-run: plan validated, provider NOT called")
    else:
        p = ex.get("provider", {})
        print(f"EXECUTION   provider HTTP {p.get('http_status')}  {p.get('url', '').replace('http://host.docker.internal', '')}")
        if ex.get("resolvedUeIpv4"):
            print(f"            UE IP {ex['resolvedUeIpv4']} (5GC subscriber DB)   profile "
                  f"{ex.get('requestedQosProfile')} -> {ex.get('qosProfile')}")
        if ex.get("qosStatus") or ex.get("assignmentStatus"):
            print(f"            status: {ex.get('qosStatus') or ex.get('assignmentStatus')}")
        if ex.get("area"):
            print(f"            location area: {ex['area'].get('areaType')} with {len(ex['area'].get('boundary', []))} WGS-84 points")
    t = d.get("timings_ms", {})
    print(f"TIMINGS     planning {t.get('planning', 0):.0f} ms | validation {t.get('validation', 0):.0f} ms | "
          f"execution {t.get('execution', 0):.0f} ms | total {t.get('total', 0):.0f} ms")


def cmd_core_evidence(_):
    print("NEF-QoS -> Open5GS PCF (Npcf_PolicyAuthorization), last 2 minutes:")
    lines = sh("docker logs --since 120s nef-qos 2>&1").splitlines()
    keep = [l for l in lines if "Created subscription" in l or "Response status code" in l]
    for l in keep[-4:]:
        print("  " + re.sub(r"^\S+\s+\w+\s+", "", l)[:110])
    print("\nSMF view of the UE PDU sessions:")
    sessions = {}
    for l in sh("docker logs smf 2>&1").splitlines():
        m = re.search(r"UE SUPI\[(\S+)\].*IPv4\[(\S+)\]", l)
        if m:
            sessions[m.group(1)] = m.group(2)
    for supi, ip in sorted(sessions.items()):
        print(f"  {supi}  {ip}")


def cmd_compare(a):
    intent, _ = SCENARIOS[a.scenario]
    payloads = {}
    print(f"{'LLM backend':27s} {'plan':>6s}   CAMARA payload (key fields)")
    for prov in ("openai", "anthropic", "gemini"):
        requests.post(f"{API}/config/provider", json={"provider": prov}, timeout=10)
        d = _orchestrate(intent, live=False)
        p = payloads[prov] = d["steps"][0]["payload"]
        t = d["timings_ms"]["planning"]
        print(f"{d['planner']['model']:27s} {t / 1000:4.1f} s   {d['steps'][0]['service_id']}  "
              f"qosProfile={p.get('qosProfile')}  duration={p.get('duration')}  "
              f"appServer={(p.get('applicationServer') or {}).get('ipv4Address')}  "
              f"device={mask((p.get('device') or {}).get('phoneNumber', ''))}")
    requests.post(f"{API}/config/provider", json={"provider": "openai"}, timeout=10)
    same = len({json.dumps(p, sort_keys=True) for p in payloads.values()}) == 1
    print(f"\nIdentical CAMARA payload across all three LLM backends: {'yes' if same else 'no'}")


# ── experiments ──────────────────────────────────────────────────────────────

def cmd_faults(a):
    c = "mini-telco-backend-capif"
    sh(f"docker exec {c} mkdir -p /app/datasets /app/scripts")
    sh(f"docker cp {ROOT}/scripts/layer_fault_injection.py {c}:/app/scripts/")
    sh(f"docker cp {ROOT}/datasets/eval_results_gpt4omini_300.json {c}:/app/datasets/")
    out = sh(f"docker exec -e LLM_PROVIDER=openai -w /app {c} python scripts/layer_fault_injection.py "
             f"--per-fault {a.per_fault} --seed 11")
    print("Faults injected into correct plans; live L3; real LLM feedback loop (max 3 iterations)\n")
    print(f"{'layer':5s} {'fault':16s} {'caught':>7s} {'repaired':>9s} {'iters':>6s} {'feedback':>9s}")
    for l in out.splitlines():
        m = re.match(r"(L\d) (\S+)\s+detected (\S+)\s+repaired (\S+)\s+iters (\S+)\s+feedback (\d+) ms", l)
        if m:
            print(f"{m.group(1):5s} {m.group(2):16s} {m.group(3):>7s} {m.group(4):>9s} {m.group(5):>6s} "
                  f"{int(m.group(6)) / 1000:>7.1f} s")


def cmd_load(a):
    det_n, llm_n = (30, 5) if a.quick else (40, 10)
    out = sh(f"cd {ROOT} && {sys.executable} scripts/load_test.py --det-levels 1,10 --det-requests {det_n} "
             f"--llm-levels 1,5 --llm-requests {llm_n}")
    print(f"{'planner':14s} {'clients':>7s} {'ok':>6s} {'req/s':>7s} {'p50':>8s} {'p95':>8s}  L3 live")
    for l in out.splitlines():
        r = ast.literal_eval(l)  # load_test prints one dict per level
        print(f"{r['mode']:14s} {r['concurrency']:>7d} {r['ok']:>3d}/{r['requests']:<3d}{r['throughput_rps']:>6.1f} "
              f"{r['p50_ms']:>6d}ms {r['p95_ms']:>6d}ms  {r['registry_checked']}/{r['ok']}")


def cmd_results(_):
    ds = ROOT / "datasets"
    rows = [("Keyword baseline", "eval_results_deterministic_300.json"),
            ("GPT-4o-mini", "eval_results_gpt4omini_300.json"),
            ("Claude Haiku 4.5", "eval_results_llm_anthropic_haiku45_300.json"),
            ("Gemini 2.5 Flash", "eval_results_gemini25flash_300.json"),
            ("Ablation: single call", "eval_results_gpt4omini_single_300.json"),
            ("Ablation: no schema", "eval_results_gpt4omini_ungrounded_300.json")]
    pilot = {r["id"] for r in json.loads((ds / "legacy_pilot_60/eval_results_deterministic.json").read_text())["results"]}
    print(f"{'planner (300 unique intents)':26s} {'IWSR':>6s} {'SCR':>6s} {'SVR':>6s} {'HR':>6s}  {'pilot 60':>8s} {'held-out 240':>12s}")
    for name, f in rows:
        d = json.loads((ds / f).read_text())
        m, res = d["summary"]["metrics"], d["results"]
        p = sum(r["iwsr"] for r in res if r["id"] in pilot)
        h = sum(r["iwsr"] for r in res if r["id"] not in pilot)
        print(f"{name:26s} {m['IWSR']:6.1%} {m['SCR']:6.1%} {m['SVR']:6.1%} {m['HR']:6.1%}  "
              f"{p:>5d}/60 {h:>8d}/240")
    print("\nThe keyword rules were written for the 60-entry pilot (archived in datasets/legacy_pilot_60/).")
    l3 = json.loads((ds / "l3_rescore_300.json").read_text())
    print(f"Live L3 re-validation: {sum(x['registry_checked'] for x in l3)} plans checked, "
          f"{sum(x['l3_rejections'] for x in l3)} rejected.")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("run"); p.add_argument("scenario", choices=SCENARIOS); p.add_argument("--live", action="store_true")
    p.set_defaults(fn=cmd_run)
    sub.add_parser("core-evidence").set_defaults(fn=cmd_core_evidence)
    p = sub.add_parser("compare"); p.add_argument("scenario", choices=SCENARIOS); p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("faults"); p.add_argument("--per-fault", type=int, default=2); p.set_defaults(fn=cmd_faults)
    p = sub.add_parser("load"); p.add_argument("--quick", action="store_true"); p.set_defaults(fn=cmd_load)
    sub.add_parser("results").set_defaults(fn=cmd_results)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
