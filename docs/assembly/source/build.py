"""Build the Darkroom assembly drawings.

    python docs/assembly/source/build.py            # default: cached CAD meshes, never runs OpenSCAD
    python docs/assembly/source/build.py --export-meshes [--openscad PATH]
        # trusted machines only: re-export the per-module STLs from cad/darkroom.scad,
        # refresh mesh-cache.json.gz, then build

Outputs (docs/assembly/):
    exports/darkroom-assembly-sheet.{svg,png,pdf}    README sheet: exploded + assembled inset + electronics
    exports/darkroom-{assembled,exploded,electronics}.{svg,png,pdf}
    index.html                                        standalone viewer (the same files, embedded)
    build-report.json                                 hashes, transforms, anchor checks, render stats
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from compose import (INK, INK_SOFT, PAPER, Callout, Doc, draw_callouts, layout_callouts,  # noqa: E402
                     leaders_cross, text_width)
from inventory import PART, PARTS, anchors, build_parts, views  # noqa: E402
from meshes import MODULES, export_meshes, load_cache, seed_cache  # noqa: E402
from render import Camera, Mesh, Placed, draw_view, projected_bounds  # noqa: E402
from scad_params import read_params, sha256  # noqa: E402

ASM = HERE.parent
ROOT = ASM.parents[1]
CAD = ROOT / "cad" / "darkroom.scad"
CACHE = HERE / "mesh-cache.json.gz"
EXPORTS = ASM / "exports"

CAM = Camera(azimuth=35.0, elevation=28.0)
SS = 3                                     # label/depth buffer supersampling
LINE_W = {"main": {1: 1.5, 2: 0.95, 3: 0.55}, "inset": {1: 1.1, 2: 0.7, 3: 0.42}}
LINE_C = {1: INK, 2: INK, 3: "#6b7079"}
AXIS = "#7d828a"

MIN_SHOWN_PX2 = 300.0  # px^2; less visible area than this counts as hidden in a view (viewer routing)
LABEL = 17.0          # lane label size (sheet px)
LABEL_SP = 0.9
GAP = 31.0            # lane pitch
SHEET_W = 1200
M = 36                # outer margin

NOTE = ("Concept geometry from cad/darkroom.scad (v0.4); not a fabrication drawing or a confirmed build. "
        "The microSD reader is a placeholder board; display and PiSugar fit, retention and cabling are unverified.")

LANE_TEXT = {
    "body.top": "BODY", "body.side": "BODY", "body.post": "CORNER POSTS ×4",
    "sled.plate": "SLED · FRONT PLATE", "sled.floor": "SLED FLOOR", "sled.bulkhead": "SLED · REAR BULKHEAD",
    "sled.slot": "MICROSD SLOT",
    "screws.head": "M3 SCREW HEADS ×4",
    "display.glass": "ST7789 DISPLAY", "display.pcb": "DISPLAY PCB",
    "caps.select": "SELECT CAP (RED)", "caps.down": "BUTTON CAPS ×4",
    "switches.tact": "TACT SWITCHES ×4", "switches.carrier": "TACT SWITCHES",
    "reader.socket": "MICROSD READER", "reader.pcb": "READER BOARD",
    "pi.pcb": "PI ZERO 2 W", "pi.header": "2×20 HEADER",
    "pisugar.body": "PISUGAR 3",
    "diffuser.top": "DIFFUSER SHELF",
    "safelight.led": "SAFELIGHT · 2 LEDS", "safelight.pcb": "LED BREAKOUT",
}


# ---------------------------------------------------------------------------------------
# geometry


def load_geometry():
    P = read_params(CAD)
    meshes, cache_doc = load_cache(CACHE, CAD)
    parts = build_parts(meshes, P)
    mesh = {k: Mesh(k, t, tint) for k, (t, tint) in parts.items()}
    return P, mesh, cache_doc, parts


def placed_for(view, mesh):
    return [Placed(mesh[k], i, np.array(view.offsets[k], dtype=float)) for i, k in enumerate(view.parts)]


def frame_for(placed, x0, x1, y0, max_h, cx=None):
    """Width-limited (or height-limited) frame; returns frame and the drawing's pixel box."""
    from render import Frame
    u0, v0, u1, v1 = projected_bounds(CAM, placed)
    s = min((x1 - x0) / (u1 - u0), max_h / (v1 - v0))
    cx = (x0 + x1) / 2 if cx is None else cx
    fr = Frame(s, cx - s * (u0 + u1) / 2, y0 - s * v0)
    return fr, (cx - s * (u1 - u0) / 2, y0, cx + s * (u1 - u0) / 2, y0 + s * (v1 - v0))


def project_point(frame, pt):
    return frame.apply(CAM.project(np.asarray(pt, dtype=float)[None]))[0]


# ---------------------------------------------------------------------------------------
# one drawing panel into a Doc


def panel(doc, view, mesh, P, frame, region, prefix, weights, report, callout_spec=None, lanes=None):
    placed = placed_for(view, mesh)
    dr = draw_view(CAM, placed, frame, region, SS)
    keys = view.parts
    # fills, grouped per part, back to front
    doc.open(id=f"{prefix}-drawing", class_="drawing")
    doc.open(class_="fills")
    by_part = {}
    for part, tint, depth, loops in dr.fills:
        by_part.setdefault(part, []).append((depth, tint, loops))
    order = sorted(by_part, key=lambda p: np.median([d for d, _, _ in by_part[p]]))
    for p in order:
        doc.open(class_="part", data_part=keys[p])
        for _, tint, loops in by_part[p]:
            doc.area(loops, PART[keys[p]].tints[tint][1])
        doc.close()
    doc.close()
    doc.open(class_="lines")
    for i, k in enumerate(keys):
        doc.open(class_="part", data_part=k)
        for kind in (3, 2, 1):
            pls = [pl for part, kd, pl in dr.lines if part == i and kd == kind]
            if pls:
                doc.lines(pls, LINE_C[kind], weights[kind], cls={1: "ln-s", 2: "ln-c", 3: "ln-t"}[kind])
        doc.close()
    doc.close()
    # insertion axes for parts moved off their seats along one axis (screws)
    axes = []
    if "screws" in keys and view.offsets["screws"] != view.offsets["sled"]:
        for x in (P["screw_inset"], P["W"] - P["screw_inset"]):
            for z in (P["screw_inset"], P["H"] - P["screw_inset"]):
                a = project_point(frame, np.array([x, P["screw_head_h"], z]) + view.offsets["screws"])
                b = project_point(frame, np.array([x, P["screw_cb_deep"], z]) + view.offsets["sled"])
                axes.append(np.array([a[:2], b[:2]]))
    if axes:
        doc.open(class_="axes", data_part="screws")
        doc.lines(axes, AXIS, 0.8, cls="axis", dash="5 3")
        doc.close()
    doc.close()

    anchor_table = anchors(P)
    callouts, checks = [], []
    for key, lane in (callout_spec or []):
        part, pt, feature = anchor_table[key]
        off = np.array(view.offsets[part], dtype=float)
        sp = project_point(frame, np.array(pt) + off)
        ok, frac, ddepth = anchor_visible(dr, keys.index(part), sp)
        checks.append({"view": view.key, "panel": prefix, "anchor": key, "part": part, "feature": feature,
                       "model_point_mm": [round(v, 4) for v in pt], "offset_mm": off.tolist(),
                       "screen_px": [round(float(sp[0]), 2), round(float(sp[1]), 2)],
                       "own_part_fraction": round(frac, 3), "depth_delta_mm": round(ddepth, 4), "visible": ok})
        callouts.append(Callout(key, part, PART[part].num, LANE_TEXT[key], lane, (float(sp[0]), float(sp[1]))))
    if callouts:
        layout_callouts(callouts, lanes, LABEL, LABEL_SP, GAP)
    # visible area per part (px^2 of the output) from the occlusion-resolved label buffer
    lab_part = np.full(max(dr.label_info) + 1, -1)
    for lab, (p, _) in dr.label_info.items():
        lab_part[lab] = p
    hit = lab_part[dr.labels[dr.labels > 0]]
    counts = np.bincount(hit, minlength=len(keys))
    dr.visible_px = {k: round(float(counts[i]) / SS ** 2, 1) for i, k in enumerate(keys)}
    report["panels"].append({"panel": prefix, "view": view.key, "scale_px_per_mm": round(frame.scale, 5),
                             "offsets_mm": {k: view.offsets[k] for k in keys},
                             "visible_area_px2": dr.visible_px, "stats": dr.stats})
    report["anchors"] += checks
    return dr, callouts


def anchor_visible(dr, part_index, sp, radius=1.5):
    x0, y0 = dr.region[0], dr.region[1]
    ss = dr.ss
    cx, cy = (sp[0] - x0) * ss, (sp[1] - y0) * ss
    r = int(round(radius * ss))
    ys, xs = np.mgrid[-r:r + 1, -r:r + 1]
    keep = xs ** 2 + ys ** 2 <= r * r
    iy = np.clip(np.round(cy - 0.5 + ys[keep]).astype(int), 0, dr.labels.shape[0] - 1)
    ix = np.clip(np.round(cx - 0.5 + xs[keep]).astype(int), 0, dr.labels.shape[1] - 1)
    labs = dr.labels[iy, ix]
    parts = np.array([dr.label_info.get(int(l), (-1, -1))[0] for l in labs])
    frac = float((parts == part_index).mean())
    d = dr.depth[int(np.clip(round(cy - 0.5), 0, dr.labels.shape[0] - 1)), int(np.clip(round(cx - 0.5), 0, dr.labels.shape[1] - 1))]
    ddepth = float(abs(d - sp[2])) if np.isfinite(d) else 1e9
    return bool(frac >= 0.6 and ddepth < 0.6), frac, ddepth


# ---------------------------------------------------------------------------------------
# legend + furniture


def legend(doc, keys, x0, y0, width, cols, prefix, name_size=17.0, note_size=15.0):
    doc.open(id=f"{prefix}-legend", class_="annotations legend")
    col_w = width / cols
    rows = -(-len(keys) // cols)
    row_h = name_size + note_size * 2.6 + 10
    for i, k in enumerate(keys):
        p = PART[k]
        c, r = i // rows, i % rows
        x, y = x0 + c * col_w, y0 + r * row_h
        doc.open(class_="legend-item", data_part=k)
        br = name_size * 0.62
        doc.circle(x + br, y + name_size * 0.35 - name_size * 0.36 + 1, br, fill=INK)
        doc.text(x + br, y + name_size * 0.36 + 1, str(p.num), name_size * 0.78, 700, "middle", "#ffffff")
        sx = x + 2 * br + 8
        for j, (_, col) in enumerate(p.tints[:3]):
            doc.rect(sx + j * 12, y - 7, 10, 14, fill=col, stroke=INK, width=0.6, rx=1.5)
        tx = sx + 3 * 12 + 6
        doc.text(tx, y + name_size * 0.36, p.name, name_size, 700, "start", INK)
        for li, line in enumerate(wrap(p.note, note_size, col_w - (tx - x) - 14)):
            doc.text(tx, y + name_size * 0.36 + (li + 1) * note_size * 1.3, line, note_size, 400, "start", INK_SOFT)
        doc.close()
    doc.close()
    return y0 + rows * row_h


def wrap(s, size, width):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_width(t, size) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def header(doc, title, sub, right):
    doc.open(class_="annotations header")
    doc.text(M, 50, title, 22, 700, "start", INK, 2.0)
    doc.text(M, 78, sub, 16, 400, "start", INK_SOFT)
    doc.text(SHEET_W - M, 50, right, 12.5, 700, "end", INK_SOFT, 1.4)
    doc.close()


def footer(doc, y, width=SHEET_W - 2 * M, size=15.0):
    doc.open(class_="annotations footer")
    doc.lines([np.array([[M, y - 22], [SHEET_W - M, y - 22]])], "#d5d7db", 1.0)
    for i, line in enumerate(wrap(NOTE, size, width)):
        doc.text(M, y + i * size * 1.35, line, size, 400, "start", INK_SOFT)
    doc.close()
    return y + len(wrap(NOTE, size, width)) * size * 1.35


def panel_title(doc, x, y, letter, text):
    doc.open(class_="annotations panel-title")
    doc.text(x, y, f"{letter}  {text}", 14.5, 700, "start", INK_SOFT, 1.5)
    doc.close()


# ---------------------------------------------------------------------------------------
# the README sheet


def build_sheet(P, mesh, report):
    V = {v.key: v for v in views(P)}
    doc = Doc(SHEET_W, 10, "Darkroom assembly sheet",
              "Exploded view of the Darkroom cube with an assembled inset and an electronics detail, "
              "drawn from cad/darkroom.scad in one parallel projection. Not to scale.")
    header(doc, "DARKROOM · ASSEMBLY",
           "A one-piece body and one front-loaded sled. One parallel projection of cad/darkroom.scad (v0.4); not to scale.",
           "CONCEPT ILLUSTRATION")
    lane_l, lane_r = 262, SHEET_W - 262

    # A: exploded
    ya = 104
    panel_title(doc, M, ya + 14, "A", "EXPLODED · LOADED SLED OUT THROUGH THE OPEN FRONT")
    ex = V["exploded"]
    fr, box = frame_for(placed_for(ex, mesh), 290, SHEET_W - 300, ya + 40, 640)
    region = (box[0] - 8, box[1] - 8, box[2] + 8, box[3] + 8)
    inset_w, inset_h = 214, 214
    inset_box = (SHEET_W - M - inset_w, box[3] - inset_h + 10, SHEET_W - M, box[3] + 10)
    _, ca = panel(doc, ex, mesh, P, fr, region, "sheet-exploded", LINE_W["main"], report,
                  [(k, l) for k, _, l in ex.callouts],
                  {"L": (lane_l, ya + 52, box[3]), "R": (lane_r, ya + 52, inset_box[1] - 34)})
    draw_callouts(doc, ca, LABEL, LABEL_SP, "sheet-exploded")
    report["leader_crossings"]["sheet-exploded"] = leaders_cross(ca)

    # assembled inset (no callouts; same projection, all offsets zero)
    asm = V["assembled"]
    doc.open(class_="annotations inset-frame")
    doc.rect(inset_box[0], inset_box[1] - 26, inset_w, inset_h + 26, fill="#ffffff", stroke="#cfd2d6", width=1.0, rx=6)
    doc.text(inset_box[0] + 12, inset_box[1] - 7, "ASSEMBLED", 12.5, 700, "start", INK_SOFT, 1.4)
    doc.close()
    fr2, box2 = frame_for(placed_for(asm, mesh), inset_box[0] + 18, inset_box[2] - 18, inset_box[1] + 10, inset_h - 26)
    reg2 = (box2[0] - 6, box2[1] - 6, box2[2] + 6, box2[3] + 6)
    panel(doc, asm, mesh, P, fr2, reg2, "sheet-assembled", LINE_W["inset"], report)

    # B: electronics detail
    yb = max(box[3], inset_box[3]) + 46
    doc.lines([np.array([[M, yb - 18], [SHEET_W - M, yb - 18]])], "#d5d7db", 1.0)
    panel_title(doc, M, yb + 14, "B", "ELECTRONICS · ILLUSTRATIVE SPACING, COLLAPSES TO THE CAD POSITIONS")
    el = V["electronics"]
    fr3, box3 = frame_for(placed_for(el, mesh), 300, SHEET_W - 300, yb + 44, 560)
    reg3 = (box3[0] - 8, box3[1] - 8, box3[2] + 8, box3[3] + 8)
    _, cb = panel(doc, el, mesh, P, fr3, reg3, "sheet-electronics", LINE_W["main"], report,
                  [(k, l) for k, _, l in el.callouts],
                  {"L": (lane_l, yb + 50, box3[3]), "R": (lane_r, yb + 50, box3[3])})
    draw_callouts(doc, cb, LABEL, LABEL_SP, "sheet-electronics")
    report["leader_crossings"]["sheet-electronics"] = leaders_cross(cb)

    # legend + footer
    yl = box3[3] + 56
    doc.lines([np.array([[M, yl - 26], [SHEET_W - M, yl - 26]])], "#d5d7db", 1.0)
    end = legend(doc, [p.key for p in PARTS], M, yl, SHEET_W - 2 * M, 3, "sheet")
    end = footer(doc, end + 30)
    doc.h = round(end + 22)
    report["label_boxes"]["sheet"] = [c.box for c in ca + cb]
    return doc, {"exploded": ca, "electronics": cb}


# ---------------------------------------------------------------------------------------
# one view per file (also what the viewer shows)


VIEW_TEXT = {
    "assembled": ("DARKROOM · ASSEMBLED", "Sled in, four screw heads flush. All part offsets are exactly zero."),
    "exploded": ("DARKROOM · EXPLODED", "The loaded sled leaves through the open front; the diffuser lifts off its rails."),
    "electronics": ("DARKROOM · ELECTRONICS", "Illustrative spacing of the parts the sled carries; every offset is a translation that collapses to the CAD position."),
}


def build_view(view, P, mesh, report):
    title, sub = VIEW_TEXT[view.key]
    doc = Doc(SHEET_W, 10, f"Darkroom — {view.title.lower()} view", sub + " Drawn from cad/darkroom.scad; not to scale.")
    header(doc, title, sub, "NOT TO SCALE")
    y0 = 108
    max_h = 600 if view.key != "assembled" else 560
    fr, box = frame_for(placed_for(view, mesh), 300, SHEET_W - 300, y0 + 16, max_h)
    region = (box[0] - 8, box[1] - 8, box[2] + 8, box[3] + 8)
    dr, cs = panel(doc, view, mesh, P, fr, region, view.key, LINE_W["main"], report,
                  [(k, l) for k, _, l in view.callouts],
                  {"L": (262, y0 + 20, box[3]), "R": (SHEET_W - 262, y0 + 20, box[3])})
    draw_callouts(doc, cs, LABEL, LABEL_SP, view.key)
    report["leader_crossings"][view.key] = leaders_cross(cs)
    stage = [0, y0 - 14, SHEET_W, box[3] + 30 - (y0 - 14)]
    yl = box[3] + 70
    doc.lines([np.array([[M, yl - 26], [SHEET_W - M, yl - 26]])], "#d5d7db", 1.0)
    end = legend(doc, view.parts, M, yl, SHEET_W - 2 * M, 3, view.key)
    end = footer(doc, end + 30)
    doc.h = round(end + 22)
    report["label_boxes"][view.key] = [c.box for c in cs]
    meta = {"key": view.key, "title": view.title, "heading": title, "subtitle": sub, "width": SHEET_W, "height": doc.h,
            "stage": [round(v, 2) for v in stage], "parts": view.parts,
            "shown": [k for k in view.parts if dr.visible_px[k] >= MIN_SHOWN_PX2],
            "callouts": [{"key": c.key, "part": c.part, "num": c.num, "label": c.label, "lane": c.lane,
                          "anchor": [round(v, 2) for v in c.anchor], "y": round(c.y, 2),
                          "box": [round(v, 2) for v in c.box]} for c in cs]}
    return doc, meta


# ---------------------------------------------------------------------------------------
# PNG via headless Chrome (renders the SVG exactly as a browser does)


def chrome_path():
    env = os.environ.get("CHROME_PATH")
    if env:
        return env
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if Path(p).exists():
            return p
    raise SystemExit("Set CHROME_PATH to a Chrome/Chromium executable (used to rasterise the SVGs).")


def rasterize(svgs, scale=2):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome_path(), headless=True)
        for svg_path, w, h in svgs:
            ctx = browser.new_context(viewport={"width": int(w), "height": int(h)}, device_scale_factor=scale)
            page = ctx.new_page()
            page.goto(svg_path.as_uri())
            raw = page.screenshot(clip={"x": 0, "y": 0, "width": int(w), "height": int(h)})
            ctx.close()
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            out = svg_path.with_suffix(".png")
            im.save(out, optimize=True)
        browser.close()


# ---------------------------------------------------------------------------------------
# viewer


def build_viewer(metas):
    tpl = (HERE / "viewer_template.html").read_text()
    data = {}
    for key, meta in metas.items():
        base = EXPORTS / f"darkroom-{key}"
        data[key] = dict(meta,
                         svg=base.with_suffix(".svg").read_text(),
                         png=base64.b64encode(base.with_suffix(".png").read_bytes()).decode(),
                         pdf=base64.b64encode(base.with_suffix(".pdf").read_bytes()).decode(),
                         sha256={ext: hashlib.sha256(base.with_suffix("." + ext).read_bytes()).hexdigest()
                                 for ext in ("svg", "png", "pdf")})
    legend_data = [{"key": p.key, "num": p.num, "name": p.name, "note": p.note, "status": p.status,
                    "tints": [c for _, c in p.tints]} for p in PARTS]
    blob = json.dumps({"views": data, "parts": legend_data, "note": NOTE}, separators=(",", ":"))
    blob = blob.replace("</", "<\\/")
    (ASM / "index.html").write_text(tpl.replace("/*__DATA__*/null", blob))


# ---------------------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export-meshes", action="store_true",
                    help="re-export STLs with OpenSCAD and refresh the cache (trusted OpenSCAD only)")
    ap.add_argument("--openscad", default="openscad", help="OpenSCAD executable for --export-meshes")
    ap.add_argument("--seed-stl-dir", type=Path, help="refresh the cache from existing per-module STLs")
    ap.add_argument("--no-png", action="store_true", help="skip Chrome rasterisation (SVG/PDF only)")
    args = ap.parse_args()

    if args.export_meshes:
        with tempfile.TemporaryDirectory() as tmp:
            export_meshes(CAD, Path(tmp), args.openscad)
            seed_cache(Path(tmp), CAD, CACHE, f"build.py --export-meshes ({args.openscad})")
    elif args.seed_stl_dir:
        seed_cache(args.seed_stl_dir, CAD, CACHE, f"build.py --seed-stl-dir {args.seed_stl_dir.name}")

    P, mesh, cache_doc, _ = load_geometry()
    EXPORTS.mkdir(exist_ok=True)
    report = {"cad": {"path": "cad/darkroom.scad", "sha256": sha256(CAD)},
              "mesh_cache": {"path": "docs/assembly/source/mesh-cache.json.gz", "sha256": sha256(CACHE),
                             "producer": cache_doc["producer"], "cad_sha256": cache_doc["cad_sha256"],
                             "meshes": {k: {"module": v["module"], "stl_sha256": v["stl_sha256"], "triangles": v["triangles"]}
                                        for k, v in cache_doc["meshes"].items()}},
              "camera": {"azimuth_deg": CAM.azimuth, "elevation_deg": CAM.elevation, "projection": "orthographic"},
              "views": {v.key: {"parts": v.parts, "offsets_mm": {k: v.offsets[k] for k in v.parts}} for v in views(P)},
              "panels": [], "anchors": [], "leader_crossings": {}, "label_boxes": {}, "outputs": {}}

    docs = {}
    sheet, _ = build_sheet(P, mesh, report)
    docs["assembly-sheet"] = sheet
    metas = {}
    for v in views(P):
        d, meta = build_view(v, P, mesh, report)
        docs[v.key] = d
        metas[v.key] = meta

    svgs = []
    for name, d in docs.items():
        base = EXPORTS / f"darkroom-{name}"
        base.with_suffix(".svg").write_text(d.svg())
        d.pdf(base.with_suffix(".pdf"), d.title)
        svgs.append((base.with_suffix(".svg"), d.w, d.h))
    if not args.no_png:
        rasterize(svgs)
    for name, d in docs.items():
        base = EXPORTS / f"darkroom-{name}"
        report["outputs"][name] = {ext: {"path": f"docs/assembly/exports/darkroom-{name}.{ext}",
                                         "sha256": hashlib.sha256(base.with_suffix("." + ext).read_bytes()).hexdigest()}
                                   for ext in ("svg", "pdf", "png") if base.with_suffix("." + ext).exists()}
        report["outputs"][name]["size_px"] = [d.w, d.h]
    build_viewer(metas)
    report["outputs"]["viewer"] = {"path": "docs/assembly/index.html",
                                   "sha256": hashlib.sha256((ASM / "index.html").read_bytes()).hexdigest()}
    report["label_boxes"] = {k: [[round(x, 2) for x in b] for b in v] for k, v in report["label_boxes"].items()}
    (ASM / "build-report.json").write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    bad = [a for a in report["anchors"] if not a["visible"]]
    for a in bad:
        print(f"WARNING anchor not on its visible part: {a['panel']} {a['anchor']} frac={a['own_part_fraction']} dz={a['depth_delta_mm']}")
    for k, v in report["leader_crossings"].items():
        if v:
            print(f"WARNING leader crossings in {k}: {v}")
    print("built", ", ".join(docs), "+ index.html")


if __name__ == "__main__":
    main()
