#!/usr/bin/env python3
"""
Pre-demo health check: is every part of the live demo working right now?

  python scripts/demo_check.py          # ~30 s, makes 2 small LLM calls (GPT-4o-mini, Claude)

Prints one line per check and ends with DEMO READY or the list of what to fix.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import requests

API = "http://localhost:8000"
S1 = "Activate video-streaming quality for +905321234567 for the next 30 minutes."
OK, BAD = "\033[32m✔\033[0m", "\033[31m✘\033[0m"
failures: list[str] = []


def check(name: str, fn, fix: str) -> None:
    try:
        detail = fn()
        print(f" {OK} {name:34s} {detail or ''}")
    except Exception as exc:  # report every failure, keep checking the rest
        print(f" {BAD} {name:34s} {exc}")
        failures.append(f"{name}: {fix}")


def _env_has(key: str) -> bool:
    env = Path(__file__).resolve().parents[1] / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    return any(l.startswith(f"{key}=") and l.split("=", 1)[1].strip() for l in lines)


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30).stdout


def containers() -> str:
    names = set(sh("docker ps --format '{{.Names}}'").split())
    need = {"mini-telco-backend-capif", "register", "nef", "nef-qos", "camara-qod",
            "camara-location-retrieval", "pcf", "smf", "upf", "amf", "gnb", "ues"}
    missing = sorted(need - names)
    if missing:
        raise RuntimeError(f"not running: {', '.join(missing)}")
    return f"{len(names)} containers up"


def backend() -> str:
    requests.get(f"{API}/health", timeout=5).raise_for_status()
    return "http://localhost:8000/docs"


def capif() -> str:
    d = requests.get(f"{API}/capif/discover", timeout=30).json()
    apis = sorted(a.get("apiName") for a in (d.get("services") or {}).get("serviceAPIDescriptions", []))
    if d.get("status") != "discovered" or len(apis) < 5:
        raise RuntimeError(f"status={d.get('status')}, APIs={apis}")
    return f"{len(apis)} APIs discovered over mTLS"


def ues() -> str:
    ips = [l.split()[3] for l in sh("docker exec ues ip -4 -o addr").splitlines() if "uesimtun" in l]
    if len(ips) != 3:
        raise RuntimeError(f"{len(ips)} UE PDU sessions (expected 3)")
    return ", ".join(sorted(ips))


def plan(provider: str) -> str:
    requests.post(f"{API}/config/provider", json={"provider": provider}, timeout=10).raise_for_status()
    r = requests.post(f"{API}/orchestrate", json={"intent": S1, "dry_run": True,
                                                  "orchestration_mode": "llm-assisted"}, timeout=60)
    r.raise_for_status()
    d = r.json()
    v = d["validation"]
    if not (v["valid"] and v["registry_checked"]):
        raise RuntimeError(f"valid={v['valid']} registry_checked={v['registry_checked']}")
    return f"{d['planner']['model']}: {d['steps'][0]['service_id']}, L1-L3 pass, {d['timings_ms']['total']:.0f} ms"


def main() -> None:
    print("Mini-telco live demo check\n")
    check("Docker containers", containers, "run: bash scripts/demo_up.sh")
    check("Backend API", backend, "docker restart mini-telco-backend-capif")
    check("OpenCAPIF discovery (L3)", capif, "run: bash scripts/demo_up.sh (rebuilds CAPIF)")
    check("UERANSIM UEs on Open5GS", ues, "bash testbed/open5gs/up.sh")
    check("LLM planner: GPT-4o-mini", lambda: plan("openai"), "check internet / OPENAI_API_KEY")
    if _env_has("ANTHROPIC_API_KEY"):  # optional second LLM
        check("LLM planner: Claude Haiku 4.5", lambda: plan("anthropic"), "check internet / ANTHROPIC_API_KEY")
    else:
        print(f" – {'LLM planner: Claude Haiku 4.5':34s} skipped (no ANTHROPIC_API_KEY in .env)")
    try:
        requests.post(f"{API}/config/provider", json={"provider": "openai"}, timeout=10)
    except requests.RequestException:
        pass
    print()
    if failures:
        print("\033[31mNOT READY\033[0m")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\033[32mDEMO READY\033[0m  (planner set back to GPT-4o-mini)")


if __name__ == "__main__":
    main()
