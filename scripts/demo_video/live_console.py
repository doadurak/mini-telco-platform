#!/usr/bin/env python3
"""
Live console for screen-recording the demo (http://localhost:8099).

One page shows the real Swagger UI (left), live `docker logs -f` of the backend and of
NEF-QoS -> Open5GS PCF (right), a terminal pane that streams whitelisted demo commands,
and a subtitle bar. Everything shown is produced by the running system.

  python scripts/demo_video/live_console.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PY = sys.executable
CLI = f"{PY} scripts/demo_cli.py"

# Only these commands can be run from the page
COMMANDS = {
    "status": f"{CLI} status",
    "evidence": f"{CLI} core-evidence",
    "faults": f"{CLI} faults --per-fault 1",
    "load": f"{CLI} load --quick",
    "results": f"{CLI} results",
}
# Shown on screen instead of the interpreter path
SHOWN = {
    "status": "python scripts/demo_cli.py status",
    "evidence": "python scripts/demo_cli.py core-evidence",
    "faults": "python scripts/demo_cli.py faults --per-fault 1",
    "load": "python scripts/demo_cli.py load --quick",
    "results": "python scripts/demo_cli.py results",
}
LOGS = {
    "backend": ("mini-telco-backend-capif", None),
    "nefqos": ("nef-qos", ("Created subscription", "Response status code", "PCF successfully", "Forwarding")),
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _sse_start(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _send(self, line: str, event: str = "line"):
        self.wfile.write(f"event: {event}\ndata: {json.dumps(line)}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _stream(self, cmd: str, keep=None):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        p = subprocess.Popen(cmd, shell=True, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace", env=env, bufsize=1)
        try:
            for line in p.stdout:
                line = line.rstrip("\n")
                if keep is None or any(k in line for k in keep):
                    self._send(line)
            self._send("", "end")
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            p.kill()

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            body = (HERE / "console.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        elif u.path.startswith("/static/"):
            f = HERE / "static" / Path(u.path).name
            ctype = "image/png" if f.suffix == ".png" else "application/octet-stream"
            self.send_response(200 if f.exists() else 404)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            if f.exists():
                self.wfile.write(f.read_bytes())
        elif u.path == "/run" and q.get("k", [""])[0] in COMMANDS:
            k = q["k"][0]
            self._sse_start()
            self._send(SHOWN[k], "cmd")
            self._stream(COMMANDS[k])
        elif u.path == "/logs" and q.get("c", [""])[0] in LOGS:
            name, keep = LOGS[q["c"][0]]
            self._sse_start()
            self._stream(f"docker logs -f --tail 0 {name}", keep)
        elif u.path == "/prep":
            # close open QoD sessions so the live QoD call does not hit 409 CONFLICT
            subprocess.run(f"{PY} -c \"import sys; sys.path.insert(0,'scripts'); import demo_cli as d; "
                           f"d._close_qod_sessions('+905321234567','10.45.0.10'); "
                           f"d._close_qod_sessions('+905551112233','10.45.0.12')\"", shell=True, cwd=ROOT)
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    print("live console on http://localhost:8099")
    ThreadingHTTPServer(("0.0.0.0", 8099), Handler).serve_forever()
