#!/usr/bin/env python3
"""
Screen-record the running system for the WMNC 2026 demo video.

Drives the live console (scripts/demo_video/live_console.py, http://localhost:8099) in a real
browser: clicks through the backend's Swagger UI, runs demo commands in the terminal pane and
shows subtitles that follow an English voice-over. Nothing is mocked; every response comes
from the testbed.

  pip install playwright edge-tts mutagen       # uses the installed Microsoft Edge
  python scripts/demo_video/narration.py        # voice-over clips (once)
  python scripts/demo_video/record_demo.py --out demo_raw
  python scripts/demo_video/mux_demo.py demo_raw out.mp4   # trims the start, mixes in the voice-over
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narration import NARRATION, clip, durations  # noqa: E402

CONSOLE = "http://localhost:8099"
S1 = "Activate video-streaming quality for +905321234567 for the next 30 minutes."
S3 = "Provide network quality improvement for device +905551112233 for a long time"
OP = "#operations-{tag}-{op}"
FONT = "font-family:Segoe UI,Arial,sans-serif"


def brand_slide(title: str, subtitle: str, lines: str) -> str:
    """Title/end card in the style of the CTTC presentation template."""
    return (f'<div style="position:absolute;inset:0;overflow:hidden;background:#fff;{FONT}">'
            f'<div style="position:absolute;left:0;top:0;bottom:0;width:860px;'
            f'background:#001848 url(/static/network_bg.png) center/cover"></div>'
            f'<div style="position:absolute;left:700px;top:-420px;width:2200px;height:1920px;'
            f'border-radius:50%;background:#fff"></div>'
            f'<div style="position:absolute;left:1000px;right:70px;top:150px">'
            f'<img src="/static/cttc_logo.png" style="width:520px;margin-left:150px">'
            f'<div style="font-size:62px;font-weight:700;line-height:1.18;color:#111;margin-top:70px">{title}</div>'
            f'<div style="font-size:36px;font-weight:600;color:#0b3d91;margin-top:34px">{subtitle}</div>'
            f'<div style="font-size:28px;font-weight:600;color:#333;line-height:1.55;margin-top:80px">{lines}</div>'
            f'</div></div>')


def slide(title: str, body: str = "", img: str = "") -> str:
    pic = f'<img src="/static/{img}" style="max-height:800px;max-width:1700px;margin-top:14px">' if img else ""
    return (f'<div style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;'
            f'{FONT};color:#1d2733;text-align:center;padding:0 120px 90px">'
            f'<div style="font-size:54px;font-weight:700;color:#0b3d91">{title}</div>'
            f'<div style="font-size:32px;line-height:1.65;margin-top:26px;color:#2b3a4c">{body}</div>{pic}</div>')


class Demo:
    GAP = 0.45  # pause between sentences, seconds

    def __init__(self, page, t0: float):
        self.p = page
        self.sw = page.frame_locator("#swagger")
        self.t0 = t0
        self.busy_until = 0.0
        self.durs = durations()
        self.events: list[dict] = []

    # ── narration ──
    def say(self, key: str):
        """Start the voice-over of a scene (after the previous one ends); subtitles follow it."""
        self.sync()
        lines = NARRATION[key]
        durs = [self.durs[clip(key, i).name] for i in range(len(lines))]
        start = time.time() - self.t0
        self.p.evaluate("([l, d, g]) => demo.say(l, d, g)", [lines, durs, self.GAP])
        t = start
        for i, d in enumerate(durs):
            self.events.append({"clip": clip(key, i).name, "at": round(t, 3)})
            t += d + self.GAP
        self.busy_until = self.t0 + t

    def sync(self, extra: float = 0.0):
        """Wait until the current voice-over has finished (plus `extra` seconds)."""
        left = self.busy_until - time.time() + extra
        if left > 0:
            self.p.wait_for_timeout(int(left * 1000))

    def step(self, text: str):
        self.p.evaluate("t => demo.step(t)", text)

    def slide(self, html: str):
        self.p.evaluate("h => demo.slide(h)", html)

    # ── terminal pane ──
    def run(self, key: str):
        self.p.evaluate("k => { demo.run(k); }", key)

    def run_wait(self, key: str):
        self.run(key)
        self.p.wait_for_function("k => window.__done && window.__done[k]", arg=key, timeout=600_000)

    def wait(self, s: float):
        self.p.wait_for_timeout(int(s * 1000))

    # ── Swagger UI ──
    def open_op(self, tag: str, op: str):
        blk = self.sw.locator(OP.format(tag=tag.replace(" ", "_"), op=op))
        blk.scroll_into_view_if_needed()
        if blk.locator(".opblock-body").count() == 0:
            blk.locator(".opblock-summary").first.click()
        blk.locator("button.try-out__btn").first.wait_for()  # the block expands asynchronously
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
    d.say("intro")
    d.sync(0.5)
    d.slide(slide("System architecture", "", "fig1_architecture.png"))
    d.say("arch")
    d.sync(0.5)
    d.slide("")

    d.step("STEP 1 / 5 \u00b7 Testbed")
    d.say("status")
    d.run_wait("status")
    d.sync(0.5)

    d.step("STEP 2 / 5 \u00b7 Dry run")
    d.say("dry")
    blk = d.open_op("Orchestration", "orchestrate_orchestrate_post")
    d.execute(blk, {"intent": S1, "dry_run": True, "orchestration_mode": "llm-assisted"})
    d.show_response(blk, '"validation"')
    d.sync(0.8)

    prep()
    d.step("STEP 3 / 5 \u00b7 Live QoD on the 5G core")
    d.say("live")
    d.execute(blk, {"intent": S1, "dry_run": False, "orchestration_mode": "llm-assisted"})
    d.show_response(blk, '"execution_result"')
    d.say("live_res")
    d.sync(1.0)

    d.step("STEP 4 / 5 \u00b7 Vague intent")
    d.say("vague")
    d.execute(blk, {"intent": S3, "dry_run": False, "orchestration_mode": "llm-assisted"})
    d.show_response(blk, '"steps"')
    d.sync(1.0)
    d.close_op(blk)

    d.p.evaluate("demo.clearTerm()")
    d.step("STEP 5 / 5 \u00b7 Fault injection")
    d.say("faults")
    d.run_wait("faults")
    d.say("faults_res")
    d.sync(1.0)

    d.step("")
    d.slide(slide("Results on 300 test intents",
                  "Intent-wise success: GPT-4o-mini <b>97.3%</b> &middot; Gemini 2.5 Flash 96.0% &middot; "
                  "Claude Haiku 4.5 95.3%<br>"
                  "Ablation: single-phase planner 77.3% &middot; no registry grounding 16.3%<br>"
                  "Fault injection: L1 40/40 &middot; L2 80/80 &middot; L3 20/20 caught<br>"
                  "Load: ~160 req/s deterministic &middot; ~2.6 s per LLM-assisted plan"))
    d.say("results")
    d.sync(0.8)
    d.slide(brand_slide("Thank you",
                        "From Natural Language to Live 5G API Calls",
                        "Code, datasets and scripts:<br>"
                        "<span style='color:#0b3d91'>github.com/doadurak/mini-telco-platform</span>"))
    d.say("end")
    d.sync(2.0)


TITLE = brand_slide("Demo: From Natural Language to Live 5G API Calls",
                    "A CAPIF-Compliant, Multi-LLM Intent Orchestration Platform",
                    "IEEE WMNC 2026 &middot; Demo Track<br>"
                    "<span style='font-weight:400;font-size:25px;color:#555'>"
                    "T&uuml;rkan Do&#287;a Durak (UPC) &middot; Engin Zeydan, Luis Blanco (CTTC)</span>")


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
        t0 = time.time()  # the video starts when the page is created
        page.goto(CONSOLE)
        page.evaluate("h => demo.slide(h)", TITLE)
        page.frame_locator("#swagger").locator(OP.format(tag="Orchestration", op="orchestrate_orchestrate_post")) \
            .wait_for(timeout=30_000)
        page.wait_for_timeout(1500)
        trim = time.time() - t0 - 1.0  # the published video starts 1 s before the voice-over
        d = Demo(page, t0)
        scenes(d)
        print(f"recorded {time.time() - t0:.0f} s")
        video = page.video
        ctx.close()
        Path(video.path()).with_name("narration.json").write_text(
            json.dumps({"video": Path(video.path()).name, "trim": round(trim, 3), "events": d.events}, indent=1))
        b.close()


if __name__ == "__main__":
    main()
