"""Browser QA for docs/assembly/index.html (headless Chrome via Playwright; no browser download).

    CHROME_PATH=/path/to/chrome python docs/assembly/source/qa_browser.py [--out DIR]

Opens the viewer from file://, then checks: no page errors or network requests; SVG
annotations hidden and replaced by one HTML label per callout; highlighting dims the
other parts; Escape and Reset clear it; a part hidden in the current view opens a view
where it is visible; every download is byte-identical to the checked-in export, including
a download whose view is switched while the file is being prepared; no horizontal page
overflow at phone and desktop widths. Screenshots and a JSON report go to --out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import ASM, EXPORTS, chrome_path  # noqa: E402

VIEWS = ["assembled", "exploded", "electronics"]
FAIL = []


def ok(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not cond:
        FAIL.append(name)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "darkroom-assembly-qa")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    report = {"downloads": [], "widths": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome_path(), headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page = ctx.new_page()
        errors, requests = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("request", lambda r: requests.append(r.url))
        page.goto((ASM / "index.html").as_uri())
        page.wait_for_selector("#host svg")

        for v in VIEWS:
            page.click(f"#view-{v}")
            st = page.evaluate("""() => ({
                pressed: document.querySelector('#view-%s').getAttribute('aria-pressed'),
                parts: document.querySelectorAll('#host svg .part').length,
                bad: [...document.querySelectorAll('#host svg *')].flatMap(e => [...e.attributes].map(a => a.name)).filter(n => n.endsWith('-')).length,
                annotations: [...document.querySelectorAll('#host svg .annotations')].map(e => getComputedStyle(e).display),
                callouts: document.querySelectorAll('#callouts .callout').length,
                svgLabels: document.querySelectorAll('#host svg .label').length,
                visibleText: [...document.querySelectorAll('#host svg text')].filter(t => t.getBoundingClientRect().width > 0).length,
            })""" % v)
            ok(f"{v}: view selected", st["pressed"] == "true")
            ok(f"{v}: SVG part groups present, no malformed attributes", st["parts"] > 0 and st["bad"] == 0, f"{st['parts']} part groups")
            ok(f"{v}: SVG annotations hidden, one HTML label per callout",
               all(d == "none" for d in st["annotations"]) and st["visibleText"] == 0 and st["callouts"] == st["svgLabels"] > 0,
               f"{st['callouts']} labels")
            page.screenshot(path=str(out / f"viewer-{v}-1440.png"))

        # highlight + reset on the exploded view
        page.click("#view-exploded")
        page.click('#legend .item[data-part="sled"]')
        op = page.evaluate("""() => {
            const on = [...document.querySelectorAll('#host svg .part.is-on')].map(e => +getComputedStyle(e).opacity);
            const off = [...document.querySelectorAll('#host svg .part:not(.is-on)')].map(e => +getComputedStyle(e).opacity);
            return {on: Math.min(...on), off: Math.max(...off), n: on.length};
        }""")
        page.wait_for_timeout(250)
        op = page.evaluate("""() => {
            const on = [...document.querySelectorAll('#host svg .part.is-on')].map(e => +getComputedStyle(e).opacity);
            const off = [...document.querySelectorAll('#host svg .part:not(.is-on)')].map(e => +getComputedStyle(e).opacity);
            return {on: Math.min(...on), off: Math.max(...off), n: on.length};
        }""")
        ok("highlight: selected part opaque, others dimmed", op["n"] >= 2 and op["on"] == 1 and op["off"] < 0.3, json.dumps(op))
        page.screenshot(path=str(out / "viewer-exploded-highlight-sled.png"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        cleared = page.evaluate("() => !document.querySelector('#stage').classList.contains('has-focus') && !document.querySelector('#legend [aria-pressed=\"true\"]')")
        ok("Escape clears the highlight", cleared)
        page.focus('#legend .item[data-part="body"]')
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        sel = page.evaluate("() => document.querySelector('#legend [aria-pressed=\"true\"]')?.dataset.part")
        ok("keyboard: arrow + Enter selects the next part", sel == "sled", str(sel))
        page.click("#reset")
        ok("Reset clears the highlight", page.evaluate("() => !document.querySelector('#legend [aria-pressed=\"true\"]')"))

        # hidden part: Pi inside the assembled cube -> routed to a view where it is visible
        page.click("#view-assembled")
        page.click('#legend .item[data-part="pi"]')
        page.wait_for_timeout(250)
        st = page.evaluate("""() => ({view: [...document.querySelectorAll('#views button')].find(b => b.getAttribute('aria-pressed') === 'true').id,
            status: document.querySelector('#status').textContent,
            on: document.querySelectorAll('#host svg .part.is-on[data-part="pi"]').length})""")
        ok("hidden part opens a view where it is visible", st["view"] == "view-electronics" and st["on"] > 0 and "hidden" in st["status"], st["status"])
        page.screenshot(path=str(out / "viewer-routed-pi.png"))
        page.click("#reset")

        # downloads: every view x format, byte-identical to the exports
        for v in VIEWS:
            page.click(f"#view-{v}")
            for fmt in ("svg", "png", "pdf"):
                with page.expect_download() as info:
                    page.click(f'[data-fmt="{fmt}"]')
                d = info.value
                dest = out / "downloads" / d.suggested_filename
                dest.parent.mkdir(exist_ok=True)
                d.save_as(dest)
                same = sha(dest) == sha(EXPORTS / f"darkroom-{v}.{fmt}")
                report["downloads"].append({"view": v, "format": fmt, "file": d.suggested_filename, "identical": same})
                ok(f"download {v}.{fmt} identical to export", same and d.suggested_filename == f"darkroom-{v}.{fmt}")
        # view switched while the download is being prepared
        page.click("#view-exploded")
        with page.expect_download() as info:
            page.click('[data-fmt="png"]')
            page.click("#view-assembled")
        d = info.value
        dest = out / "downloads" / ("switched-" + d.suggested_filename)
        d.save_as(dest)
        ok("download keeps the view it was started from", d.suggested_filename == "darkroom-exploded.png"
           and sha(dest) == sha(EXPORTS / "darkroom-exploded.png"), d.suggested_filename)

        # widths
        for w in (320, 390, 768, 1024, 1440):
            page.set_viewport_size({"width": w, "height": 900})
            page.click("#view-exploded")
            page.wait_for_timeout(150)
            m = page.evaluate("""() => ({overflow: document.documentElement.scrollWidth > window.innerWidth,
                compact: document.querySelector('#stage').classList.contains('compact'),
                badge: Math.min(...[...document.querySelectorAll('.callout .badge')].map(b => b.getBoundingClientRect().height)),
                font: parseFloat(getComputedStyle(document.querySelector('.item small')).fontSize)})""")
            report["widths"][w] = m
            ok(f"{w}px: no page overflow, badges >= 16px, legend text >= 12px", not m["overflow"] and m["badge"] >= 16 and m["font"] >= 12, json.dumps(m))
            page.screenshot(path=str(out / f"viewer-exploded-{w}.png"), full_page=w <= 768)
        ok("no page errors", not errors, "; ".join(errors))
        ext = [u for u in requests if not u.startswith(("file:", "data:", "blob:"))]
        ok("no network requests", not ext, ", ".join(ext))
        browser.close()
    report["failed"] = FAIL
    (out / "qa-browser-report.json").write_text(json.dumps(report, indent=1))
    print(f"\n{'all passed' if not FAIL else f'{len(FAIL)} failed'}; screenshots in {out}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
