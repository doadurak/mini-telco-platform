#!/usr/bin/env python3
"""
Screen-record the running system for the WMNC 2026 demo video.

Drives the live console (scripts/demo_video/live_console.py, http://localhost:8099) in a real
browser: clicks through the backend's Swagger UI, runs demo commands in the terminal pane and
shows burned-in subtitles. Nothing is mocked; every response comes from the testbed.

  pip install playwright            # uses the installed Microsoft Edge
  python scripts/demo_video/record_demo.py --out demo_raw
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request

from playwright.sync_api import sync_playwright

CONSOLE = "http://localhost:8099"
S1 = "Activate video-streaming quality for +905321234567 for the next 30 minutes."
S3 = "Provide network quality improvement for device +905551112233 for a long time"
OP = "#operations-{tag}-{op}"


def slide(title: str, body: str = "", img: str = "") -> str:
    pic = f'<img src="/static/{img}" style="max-height:780px;max-width:1700px;margin-top:18px">' if img else ""
    return (f'<div style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;'
            f'font-family:Segoe UI,Arial;color:#1d2733;text-align:center;padding:0 120px">'
            f'<div style="font-size:54px;font-weight:700">{title}</div>'
            f'<div style="font-size:30px;line-height:1.5;margin-top:22px;color:#3b4a5c">{body}</div>{pic}</div>')


class Demo:
    def __init__(self, page):
        self.p = page
        self.sw = page.frame_locator("#swagger")

    def sub(self, text: str):
        self.p.evaluate("t => demo.sub(t)", text)

    def slide(self, html: str):
        self.p.evaluate("h => demo.slide(h)", html)

    def run(self, key: str):
        self.p.evaluate("k => { demo.run(k); }", key)

    def run_wait(self, key: str):
        self.run(key)
        self.p.wait_for_function("k => window.__done && window.__done[k]", arg=key, timeout=600_000)

    def wait(self, s: float):
        self.p.wait_for_timeout(int(s * 1000))

    def open_op(self, tag: str, op: str):
        blk = self.sw.locator(OP.format(tag=tag.replace(" ", "_"), op=op))
        blk.scroll_into_view_if_needed()
        if blk.locator(".opblock-body").count() == 0:
            blk.locator(".opblock-summary").first.click()
        tri = blk.get_by_role("button", name="Try it out", exact=True)
        if tri.count():
            tri.click()
        return blk

    def close_op(self, blk):
        cancel = blk.get_by_role("button", name="Cancel", exact=True)
        if cancel.count():
            cancel.click()
        blk.locator(".opblock-summary").first.click()

    def execute(self, blk, body: dict | None = None):
        if body is not None:
            ta = blk.locator("textarea.body-param__text")
            ta.fill("")
            ta.type(json.dumps(body, indent=2), delay=6)
        if blk.locator("button.btn-clear").count():
            blk.locator("button.btn-clear").click()
            self.p.wait_for_timeout(300)
        blk.locator("button.execute").click()
        self.p.wait_for_timeout(500)
        for _ in range(240):
            st = blk.evaluate("el => [el.querySelectorAll('.live-responses-table').length, "
                              "el.querySelectorAll('.loading-container').length]")
            if st[0] and not st[1]:
                break
            self.p.wait_for_timeout(500)

    def show_response(self, blk, needle: str | None = None):
        """Scroll the Swagger response so that `needle` is near the top of the visible area."""
        code = blk.locator(".live-responses-table .response-col_description pre.microlight").first
        code.scroll_into_view_if_needed()
        if needle:
            code.evaluate("""(el, n) => {
                el.style.maxHeight = '600px'; el.style.overflowY = 'auto';
                (el.closest('tr') || el).scrollIntoView({block: 'start'});
                const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
                const nodes = []; let text = '';
                for (let t; (t = w.nextNode());) { nodes.push([t, text.length]); text += t.nodeValue; }
                const i = text.indexOf(n); if (i < 0) return;
                const [node, off] = nodes.filter(([, o]) => o <= i).pop();
                const r = document.createRange(); r.setStart(node, i - off); r.setEnd(node, i - off + 1);
                el.scrollTop += r.getBoundingClientRect().top - el.getBoundingClientRect().top - 40;
            }""", needle)


MASK_JS = r"""
if (location.port === '8000') {
  const re = /\+(\d{5})\d{5}(\d{2})/g;
  const fix = root => {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let t; (t = w.nextNode());)
      if (/\+\d{12}/.test(t.nodeValue)) t.nodeValue = t.nodeValue.replace(re, '+$1•••••$2');
  };
  new MutationObserver(ms => ms.forEach(m => m.addedNodes.forEach(n => {
    if (n.nodeType === 3) { if (n.parentNode) fix(n.parentNode); } else if (n.nodeType === 1) fix(n);
  }))).observe(document, {childList: true, subtree: true});
}
"""


def api(path: str, body: dict):
    req = urllib.request.Request(f"http://localhost:8000{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=30).read()


def prep():
    urllib.request.urlopen(f"{CONSOLE}/prep", timeout=60).read()


def scenes(d: Demo):
    # 0:00 title
    d.slide(slide("LLM-Assisted Multi-Layer Validated Network API Orchestration",
                  "Live demo of the running system &mdash; WMNC 2026<br>"
                  "OpenCAPIF &middot; CAMARA QoD / Location &middot; NEF AsSessionWithQoS &middot; "
                  "Open5GS 5G core &middot; UERANSIM"))
    d.wait(6)
    d.slide(slide("Architecture", "", "fig1_architecture.png"))
    d.sub("Natural-language intent &rarr; two-phase LLM planner &rarr; validator L1 schema / L2 telecom rules / "
          "L3 live CAPIF registry &rarr; CAMARA / NEF &rarr; Open5GS PCF")
    d.wait(11)
    d.slide("")

    # status: everything is real, not mocked
    d.sub("Reviewer concern: is the core network real? &mdash; Every component below is a running container.")
    d.run_wait("status")
    d.wait(5)

    # CAPIF discovery
    d.sub("GET /capif/discover &mdash; the invoker discovers published network APIs from OpenCAPIF over mTLS")
    blk = d.open_op("CAPIF Integration", "discover_capif_discover_get")
    d.execute(blk)
    d.show_response(blk, '"api_name"')
    d.wait(7)
    d.close_op(blk)

    # S1 dry run
    d.sub("S1, dry_run = true: the plan is generated and validated by all three layers, but no provider is called")
    blk = d.open_op("Orchestration", "orchestrate_orchestrate_post")
    d.execute(blk, {"intent": S1, "dry_run": True, "orchestration_mode": "llm-assisted"})
    d.show_response(blk, '"steps"')
    d.wait(6)
    d.show_response(blk, '"validation"')
    d.sub("L1 schema &#10003;  L2 telecom rules &#10003;  L3 CAPIF registry &#10003; (registry_checked: true) "
          "&mdash; execution: dry-run")
    d.wait(7)

    # S1 live
    prep()
    d.sub("Same intent, dry_run = false: CAMARA QoD &rarr; NEF AsSessionWithQoS &rarr; Open5GS PCF "
          "(watch the NEF log on the right)")
    d.execute(blk, {"intent": S1, "dry_run": False, "orchestration_mode": "llm-assisted"})
    d.show_response(blk, '"execution_result"')
    d.wait(4)
    d.sub("HTTP 201, qosStatus AVAILABLE; the UE IP 10.45.0.10 is resolved from the 5G core subscriber DB, "
          "E_STREAMING &rarr; operator profile QOS_S; PCF answers 201")
    d.wait(9)

    # S3 live: under-specified intent
    d.sub("S3, vague intent (&ldquo;for a long time&rdquo;): no duration is given, so the planner selects "
          "CAMARA QoS Provisioning instead of a time-bounded QoD session")
    d.execute(blk, {"intent": S3, "dry_run": False, "orchestration_mode": "llm-assisted"})
    d.show_response(blk, '"steps"')
    d.wait(7)
    d.sub("The plan passes L1/L2/L3 and is executed on the live provider for UE 10.45.0.12")
    d.show_response(blk, '"execution_result"')
    d.wait(7)
    d.close_op(blk)

    # provider switch
    d.sub("POST /config/provider &mdash; switch the planner to Claude Haiku 4.5 at run time")
    blk = d.open_op("Orchestration", "switch_provider_config_provider_post")
    d.execute(blk, {"provider": "anthropic"})
    d.show_response(blk)
    d.wait(4)
    d.close_op(blk)
    blk = d.open_op("Orchestration", "orchestrate_orchestrate_post")
    d.sub("S1 again with Claude Haiku 4.5: same validated CAMARA plan, different LLM backend")
    d.execute(blk, {"intent": S1, "dry_run": True, "orchestration_mode": "llm-assisted"})
    d.show_response(blk, '"planner"')
    d.wait(7)
    d.close_op(blk)
    blk = d.open_op("Orchestration", "switch_provider_config_provider_post")
    d.execute(blk, {"provider": "openai"})
    d.close_op(blk)

    # fault injection
    d.p.evaluate("demo.clearTerm()")
    d.sub("Reviewer concern: what does each validator layer actually catch? &mdash; live fault injection per layer")
    d.run_wait("faults")
    d.wait(8)

    # load
    d.p.evaluate("demo.clearTerm()")
    d.sub("Reviewer concern: scalability &mdash; concurrent load against the live backend (short run)")
    d.run_wait("load")
    d.sub("Every request passes live L3 discovery. Short run while screen-recording; the full run in the paper "
          "reaches ~160 req/s deterministic, ~2.6 s per LLM-assisted plan")
    d.wait(9)

    # results
    d.slide(slide("Results on 300 intents",
                  "IWSR: GPT-4o-mini 97.3% &middot; Gemini 2.5 Flash 96.0% &middot; Claude Haiku 4.5 95.3% "
                  "&middot; deterministic 83.3%<br>"
                  "Ablation: single-phase 77.3% &middot; ungrounded 16.3%<br>"
                  "Fault injection: L1 40/40 &middot; L2 80/80 &middot; L3 20/20 caught<br>"
                  "Load: ~160 req/s deterministic (10 clients) &middot; ~2.6 s per LLM-assisted plan"))
    d.sub("")
    d.wait(11)
    d.slide(slide("Thank you",
                  "Code, datasets and scripts:<br><b>github.com/doadurak/mini-telco-platform</b>"))
    d.wait(6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="demo_raw")
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="msedge", headless=not a.headed)
        ctx = b.new_context(viewport={"width": 1920, "height": 1080},
                            record_video_dir=a.out, record_video_size={"width": 1920, "height": 1080})
        ctx.add_init_script(MASK_JS)
        api("/config/provider", {"provider": "openai"})
        page = ctx.new_page()
        page.goto(CONSOLE)
        page.frame_locator("#swagger").locator(OP.format(tag="Orchestration", op="orchestrate_orchestrate_post")) \
            .wait_for(timeout=30_000)
        page.wait_for_timeout(1500)
        t0 = time.time()
        scenes(Demo(page))
        print(f"recorded {time.time() - t0:.0f} s")
        ctx.close()
        b.close()


if __name__ == "__main__":
    main()
