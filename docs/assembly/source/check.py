"""Deterministic checks for the assembly drawings. Exit status 1 if any check fails.

    python docs/assembly/source/check.py            # geometry, provenance, exports, viewer
    python docs/assembly/source/check.py --fast     # skip re-rendering the SVG/PDF exports

What is checked (no OpenSCAD, no browser):
  provenance   cache matches cad/darkroom.scad (SHA-256) and the repo's sleeve/sled STLs
  inventory    every module the CAD assembles is drawn exactly once; triangle count preserved
  geometry     mesh bounds agree with the SCAD parameters; integral parts are one solid;
               exactly four screw heads and no shafts; splits only between separate solids
  transforms   assembled offsets are exactly zero; the loaded sled moves as one along -Y;
               illustrative views separate parts that do not touch in the CAD
  interference source overlaps between parts (reported, not repaired)
  drawings     anchors visible on their own part, no crossing leaders, labels inside the page
  exports      SVG well-formed (no script/external refs), PDF one vector page with text,
               PNG at 2x, SVG/PDF byte-identical to a fresh render, viewer embeds the same bytes
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
from inventory import MOUNTED_ON_SLED, PART, components, views  # noqa: E402
from meshes import MODULES, parse_stl  # noqa: E402
from scad_params import sha256  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def bbox(t):
    v = t.reshape(-1, 3)
    return v.min(0), v.max(0)


def near(a, b, tol):
    return bool(np.all(np.abs(np.asarray(a, float) - np.asarray(b, float)) <= tol))


# ---------------------------------------------------------------------------------------


def provenance(P, meshes, cache_doc):
    check("cache built from current CAD", cache_doc["cad_sha256"] == sha256(build.CAD), cache_doc["cad_sha256"][:16])
    for name in ("darkroom-sleeve", "darkroom-sled"):
        repo = parse_stl((build.ROOT / "cad" / f"{name}.stl").read_bytes())
        a = np.unique(np.round(meshes[name].reshape(-1, 3), 4), axis=0)
        b = np.unique(np.round(repo.reshape(-1, 3), 4), axis=0)
        check(f"{name} identical to repo cad/{name}.stl", a.shape == b.shape and np.array_equal(a, b) and len(repo) == len(meshes[name]),
              f"{len(meshes[name])} triangles")
    text = build.CAD.read_text()
    body = re.search(r"module internals\(\)\s*\{([^}]*)\}", text).group(1)
    calls = set(re.findall(r"(\w+)\(\)", body))
    covered = {m.split("(")[0] for m in MODULES.values()}
    check("every module in internals() has a mesh", calls <= covered, ", ".join(sorted(calls)))
    asm = re.search(r'if \(part == "assembly"\)\s*\{([^}]*)\}', text).group(1)
    check("assembly = sleeve() + sled_loaded()", set(re.findall(r"(\w+)\(\)", asm)) == {"sleeve", "sled_loaded"})


def inventory_checks(P, meshes, parts):
    n_cache = sum(len(t) for t in meshes.values())
    n_parts = sum(len(t) for t, _ in parts.values())
    check("all source triangles drawn exactly once", n_cache == n_parts, f"{n_parts} of {n_cache}")
    for src, (a, b) in {"controls": ("caps", "switches"), "pi": ("pisugar", "pi")}.items():
        merged = np.concatenate([parts[a][0], parts[b][0]])
        def triangle_rows(t):
            rows = t.reshape(len(t), -1)
            return rows[np.lexsort(rows.T[::-1])]
        same = np.array_equal(triangle_rows(merged), triangle_rows(meshes[src]))
        check(f"{src} split into {a} + {b} is lossless", same)
    check("caps: 4 separate solids", len(np.unique(components(parts["caps"][0]))) == 4)
    sw, tint = parts["switches"]
    check("four separate tact switch bodies", len(np.unique(components(sw[tint == 1]))) == 4)
    n = len(np.unique(components(sw[tint == 0])))
    check("carrier boards: 16 mm boards on a 13 mm pitch overlap into one solid (source issue, kept)", n == 1, f"{n} solid")
    zs = P["stack_z"] + P["sugar_t"]
    check("PiSugar ends below the pogo gap, Pi starts above it",
          bbox(parts["pisugar"][0])[1][2] <= zs + 1e-6 and bbox(parts["pi"][0])[0][2] >= zs + P["stack_gap"] - 1e-6)
    for k in ("body", "sled", "diffuser", "display", "reader", "pi"):
        n = len(np.unique(components(parts[k][0])))
        check(f"{k} is one connected solid", n == 1, f"{n} component(s)")
    t = parts["pisugar"][0]
    lab = components(t)
    sizes = sorted(float(np.ptp(t[lab == c].reshape(-1, 3)[:, 0])) for c in np.unique(lab))
    check("PiSugar: one 65 mm board + four separate standoffs", len(sizes) == 5 and near(sizes[-1], P["pi_w"], 1e-6)
          and all(v < 5 for v in sizes[:4]), f"{len(sizes)} solids")
    # screws: exactly four heads, nothing longer than a head
    t = parts["screws"][0]
    lab = components(t)
    heads = [t[lab == c] for c in np.unique(lab)]
    centres = sorted((round(float(h.reshape(-1, 3)[:, 0].mean()), 2), round(float(h.reshape(-1, 3)[:, 2].mean()), 2)) for h in heads)
    want = sorted((x, z) for x in (P["screw_inset"], P["W"] - P["screw_inset"]) for z in (P["screw_inset"], P["H"] - P["screw_inset"]))
    depth = max(float(np.ptp(h.reshape(-1, 3)[:, 1])) for h in heads)
    check("exactly four M3 screw heads at the plate corners", len(heads) == 4 and near(centres, want, 0.05), str(centres))
    check("screw heads only (no shafts)", depth <= P["screw_head_h"] + 1e-6, f"max length along Y {depth:.3f} mm")
    caps, tint = parts["caps"]
    red = caps[tint == 1].reshape(-1, 3)
    check("one red Select cap, top-right of the grid", len(np.unique(components(caps[tint == 1]))) == 1
          and near([red[:, 0].mean(), red[:, 2].mean()], [P["btn_cx"][1], P["btn_cz"][0]], 0.05))


def bounds_checks(P, parts):
    ft, W, D, H = P["face_t"], P["W"], P["D"], P["H"]
    z_rdr = P["slot_cz"] - P["slot_t"] / 2 - 0.3 - P["reader_pcb"][2]
    exp = {
        "display": ([P["lcd_cx"] - P["lcd_pcb"][0] / 2, ft - P["lcd_glass"][1], P["lcd_cz"] - P["lcd_pcb"][2] / 2 - 2],
                    [P["lcd_cx"] + P["lcd_pcb"][0] / 2, ft + P["lcd_pcb"][1] + 8.5, P["lcd_cz"] + P["lcd_pcb"][2] / 2 - 2]),
        "reader": ([P["slot_cx"] - P["reader_pcb"][0] / 2, ft, z_rdr],
                   [P["slot_cx"] + P["reader_pcb"][0] / 2, ft + P["reader_pcb"][1], z_rdr + P["reader_pcb"][2] + P["sd_socket"][2]]),
        "pisugar": ([P["stack_x"], P["stack_y"], P["sled_floor_z"] + P["sled_floor_t"]],
                    [P["stack_x"] + P["pi_w"], P["stack_y"] + P["pi_d"], P["stack_z"] + P["sugar_t"]]),
        "diffuser": ([(W - P["sled_w"]) / 2 + 0.2, ft + 2, P["bay_h"]],
                     [(W + P["sled_w"]) / 2 - 0.2, ft + 2 + P["sled_len"] - P["bulk_t"] - 2.5, P["bay_h"] + P["diff_t"]]),
        "sled": ([0, 0, 0], [W, ft + P["sled_len"], H]),
        "body": ([0, ft + P["joint_g"], 0], [W, D, H]),
    }
    for k, (lo, hi) in exp.items():
        a, b = bbox(parts[k][0])
        tol = 0.05 if k in ("body", "sled") else 1e-4   # sphere-hull fillets stop a hair short of D
        check(f"{k} bounds match the SCAD parameters", near(a, lo, tol) and near(b, hi, tol),
              f"{np.round(a, 3).tolist()} .. {np.round(b, 3).tolist()}")


def transform_checks(P, parts):
    V = {v.key: v for v in views(P)}
    a = V["assembled"]
    check("assembled: every offset is exactly [0, 0, 0]", all(a.offsets[k] == [0.0, 0.0, 0.0] for k in a.parts) and set(a.parts) == set(PART))
    e = V["exploded"]
    s = e.offsets["sled"]
    check("exploded: body stays put", e.offsets["body"] == [0.0, 0.0, 0.0])
    check("exploded: sled moves along -Y only, fully clear of the body", s[0] == 0 and s[2] == 0 and -s[1] > P["sled_len"] + P["face_t"])
    check("exploded: mounted parts ride on the sled (loaded sled)", all(e.offsets[k] == s for k in MOUNTED_ON_SLED))
    sc = np.subtract(e.offsets["screws"], s)
    check("exploded: screws pulled straight out along -Y", sc[0] == 0 and sc[2] == 0 and sc[1] < 0, f"{sc.tolist()} mm from the plate")
    for k in ("diffuser", "safelight"):
        d = np.subtract(e.offsets[k], s)
        check(f"exploded: {k} lifted straight up off the sled", d[0] == 0 and d[1] == 0 and d[2] > 0, f"+{d[2]} mm")
    el = V["electronics"]
    check("electronics: only the parts the sled carries", set(el.parts) == set(MOUNTED_ON_SLED) | {"safelight"})
    # illustrative views separate parts that are separate in the CAD (no new overlaps)
    for view in (e, el):
        boxes = {k: [b + np.array(view.offsets[k]) for b in bbox(parts[k][0])] for k in view.parts}
        src = {k: bbox(parts[k][0]) for k in view.parts}
        bad = []
        for i, k in enumerate(view.parts):
            for j in view.parts[i + 1:]:
                if overlap(boxes[k], boxes[j]) > 1e-6 and overlap(src[k], src[j]) <= 1e-6:
                    bad.append(f"{k}/{j}")
        check(f"{view.key}: offsets create no new part overlaps", not bad, ", ".join(bad))


def overlap(a, b):
    lo, hi = np.maximum(a[0], b[0]), np.minimum(a[1], b[1])
    return float(np.prod(np.clip(hi - lo, 0, None)))


# ---------------------------------------------------------------------------------------
# solid interference by column ray parity (z intervals per (x, y) column)


def columns(tris, xs, ys):
    """{(i, j): sorted z crossings} for columns at xs[i], ys[j] (jittered off the mesh grid)."""
    out = {}
    for tri in tris:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        i0, i1 = np.searchsorted(xs, min(ax, bx, cx)), np.searchsorted(xs, max(ax, bx, cx))
        j0, j1 = np.searchsorted(ys, min(ay, by, cy)), np.searchsorted(ys, max(ay, by, cy))
        if i1 <= i0 or j1 <= j0:
            continue
        X, Y = np.meshgrid(xs[i0:i1], ys[j0:j1], indexing="ij")
        w0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        w1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        for (ii, jj), z in zip(np.argwhere(inside), (w0 * az + w1 * bz + w2 * cz)[inside]):
            out.setdefault((ii + i0, jj + j0), []).append(z)
    return {k: sorted(v) for k, v in out.items() if len(v) % 2 == 0}


def interference(parts, step=0.25):
    found = []
    keys = list(parts)
    boxes = {k: bbox(parts[k]) for k in keys}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            lo = np.maximum(boxes[a][0], boxes[b][0])
            hi = np.minimum(boxes[a][1], boxes[b][1])
            if np.any(hi - lo <= 1e-6):
                continue
            xs = np.arange(lo[0] + 0.0137, hi[0], step)
            ys = np.arange(lo[1] + 0.0291, hi[1], step)
            if len(xs) == 0 or len(ys) == 0:
                continue
            ca, cb = columns(parts[a], xs, ys), columns(parts[b], xs, ys)
            vol = 0.0
            for key in set(ca) & set(cb):
                za, zb = ca[key], cb[key]
                for p in range(0, len(za), 2):
                    for q in range(0, len(zb), 2):
                        vol += max(0.0, min(za[p + 1], zb[q + 1]) - max(za[p], zb[q]))
            vol *= step * step
            if vol > 0.5:
                found.append((a, b, round(vol, 1)))
    return found


# ---------------------------------------------------------------------------------------


def drawing_checks(report):
    bad = [f"{a['panel']}:{a['anchor']}" for a in report["anchors"] if not a["visible"]]
    check("every callout anchor sits on its own part's visible surface", not bad, ", ".join(bad) or f"{len(report['anchors'])} anchors")
    cross = {k: v for k, v in report["leader_crossings"].items() if v}
    check("no crossing leaders", not cross, json.dumps(cross))
    for name, boxes in report["label_boxes"].items():
        w = report["outputs"]["assembly-sheet" if name == "sheet" else name]["size_px"][0]
        inside = all(b[0] >= 0 and b[2] <= w for b in boxes)
        clash = [(i, j) for i in range(len(boxes)) for j in range(i + 1, len(boxes))
                 if boxes[i][0] < boxes[j][2] and boxes[j][0] < boxes[i][2] and boxes[i][1] < boxes[j][3] and boxes[j][1] < boxes[i][3]]
        check(f"{name}: labels inside the page and not overlapping", inside and not clash)
    hidden = {p["panel"]: [k for k, v in p["visible_area_px2"].items() if v < build.MIN_SHOWN_PX2] for p in report["panels"]}
    check("assembled view: only the outside is visible (internals occluded, not removed)",
          set(hidden["assembled"]) == {"switches", "reader", "pi", "pisugar", "diffuser", "safelight"}, ", ".join(hidden["assembled"]))


def export_checks(report, fast):
    from PIL import Image
    from pypdf import PdfReader
    exp = build.EXPORTS
    for name, out in report["outputs"].items():
        if name == "viewer":
            continue
        base = exp / f"darkroom-{name}"
        svg = base.with_suffix(".svg").read_text()
        root = ET.fromstring(svg)
        attrs = {a for el in root.iter() for a in el.attrib}
        check(f"{name}.svg well-formed, no malformed attributes", not [a for a in attrs if a.endswith("-")], f"{len(svg) // 1024} KB")
        check(f"{name}.svg self-contained", not re.search(r"<script|href=|url\(|@import", svg))
        parts_in = {el.get("data-part") for el in root.iter() if el.get("class") == "part"}
        check(f"{name}.svg has a class=part group per drawn part", len(parts_in) >= 5, ", ".join(sorted(p for p in parts_in if p)))
        for k, v in out.items():
            if isinstance(v, dict) and (build.ROOT / v["path"]).exists():
                ok = hashlib.sha256((build.ROOT / v["path"]).read_bytes()).hexdigest() == v["sha256"]
                check(f"{name}.{k} matches build-report hash", ok)
        w, h = out["size_px"]
        im = Image.open(base.with_suffix(".png"))
        check(f"{name}.png is the SVG at 2x", im.size == (2 * w, 2 * h), f"{im.size}")
        pdf = PdfReader(str(base.with_suffix(".pdf")))
        box = pdf.pages[0].mediabox
        text = pdf.pages[0].extract_text() or ""
        check(f"{name}.pdf one vector page at the SVG size", len(pdf.pages) == 1 and near([float(box.width), float(box.height)],
              [w * 0.6, h * 0.6], 0.01) and not pdf.pages[0].images
              and ("NOT TO SCALE" in text.upper() or "CONCEPT" in text.upper()))
        pdftoppm = shutil.which("pdftoppm")
        if pdftoppm:
            with tempfile.TemporaryDirectory() as tmp:
                subprocess.run([pdftoppm, "-png", "-r", "120", "-singlefile", str(base.with_suffix(".pdf")), f"{tmp}/p"], check=True)
                a = np.asarray(Image.open(f"{tmp}/p.png").convert("L"), float)
                b = np.asarray(Image.open(base.with_suffix(".png")).convert("L").resize((a.shape[1], a.shape[0]), Image.LANCZOS), float)
                diff = float(np.abs(a - b).mean())
                check(f"{name}.pdf raster matches the PNG", diff < 6.0, f"mean |diff| {diff:.2f} / 255")
    if not fast:
        P, mesh, _, _ = build.load_geometry()
        rep = {"panels": [], "anchors": [], "leader_crossings": {}, "label_boxes": {}}
        docs = {"assembly-sheet": build.build_sheet(P, mesh, rep)[0]}
        for v in views(P):
            docs[v.key] = build.build_view(v, P, mesh, rep)[0]
        with tempfile.TemporaryDirectory() as tmp:
            for name, d in docs.items():
                base = exp / f"darkroom-{name}"
                check(f"{name}.svg reproduces from source", d.svg() == base.with_suffix(".svg").read_text())
                d.pdf(Path(tmp) / "x.pdf", d.title)
                check(f"{name}.pdf reproduces from source", (Path(tmp) / "x.pdf").read_bytes() == base.with_suffix(".pdf").read_bytes())
    html = (build.ASM / "index.html").read_text()
    data = json.loads(re.search(r"const DATA = (\{.*?\});\n", html, re.S).group(1).replace("<\\/", "</"))
    for key, v in data["views"].items():
        base = exp / f"darkroom-{key}"
        same = (v["svg"].encode() == base.with_suffix(".svg").read_bytes()
                and base64.b64decode(v["png"]) == base.with_suffix(".png").read_bytes()
                and base64.b64decode(v["pdf"]) == base.with_suffix(".pdf").read_bytes())
        check(f"viewer embeds the exact {key} SVG/PNG/PDF", same)
    urls = set(re.findall(r"https?://[^\s\\\"'<>)]+", html)) - {"http://www.w3.org/2000/svg"}
    check("viewer is standalone (no network, no fetch)", not urls and not re.search(r"fetch\(|<link|<script src|import\(", html),
          ", ".join(sorted(urls)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fast", action="store_true", help="skip re-rendering exports and the interference scan")
    args = ap.parse_args()
    P, mesh, cache_doc, parts = build.load_geometry()
    from meshes import load_cache
    meshes, _ = load_cache(build.CACHE, build.CAD)
    report = json.loads((build.ASM / "build-report.json").read_text())
    provenance(P, meshes, cache_doc)
    inventory_checks(P, meshes, parts)
    bounds_checks(P, parts)
    transform_checks(P, parts)
    drawing_checks(report)
    if not args.fast:
        found = interference({k: parts[k][0] for k in parts})
        print("INFO  source interference between parts (assembled CAD):",
              "; ".join(f"{a} × {b} ≈ {v} mm³" for a, b, v in found) or "none")
        check("interference scan matches the documented source overlaps",
              {(a, b) for a, b, _ in found} == {("body", "switches"), ("diffuser", "switches")}, str(found))
    export_checks(report, args.fast)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
