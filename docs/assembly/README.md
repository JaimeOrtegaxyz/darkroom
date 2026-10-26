# Assembly drawings

Illustrated assembly of the Darkroom concept, drawn from [`cad/darkroom.scad`](../../cad/darkroom.scad)
(v0.4). Concept geometry, **not a build guide**: the reader board is a placeholder and the
display/PiSugar fit, retention and cabling are unverified. See [evidence.md](evidence.md).

| File | What |
|---|---|
| `exports/darkroom-assembly-sheet.svg` (`.png`, `.pdf`) | README sheet: exploded view, assembled inset, electronics detail, legend |
| `exports/darkroom-{assembled,exploded,electronics}.svg` (`.png`, `.pdf`) | one view per file, numbered callouts + legend |
| `index.html` | standalone viewer: the three views, part highlighting, downloads of the files above |
| `build-report.json` | hashes, camera, per-view offsets, anchor checks, visible areas, render stats |
| `source/` | generator, checks, browser QA, mesh cache |

`index.html` is a single offline file (no network, no external assets). Download it or open
it from a clone; its SVG/PNG/PDF buttons save byte-identical copies of the exports for the
view on screen. GitHub shows it as source, it does not run it.

## Rebuild

Python 3.10+ with [`source/requirements.txt`](source/requirements.txt), and Chrome or
Chromium for the PNGs (`CHROME_PATH=...` if it is not in a standard location).

```bash
python docs/assembly/source/build.py         # all exports, index.html, build-report.json (~20 s)
python docs/assembly/source/check.py         # geometry, provenance and export checks
python docs/assembly/source/qa_browser.py    # drives index.html in headless Chrome
```

The build reads only `source/mesh-cache.json.gz`, a lossless copy of per-module STL exports
of the CAD, and refuses to run if the SHA-256 of `cad/darkroom.scad` no longer matches the
one recorded in the cache. It never runs OpenSCAD. After a CAD change, re-export the meshes
on a machine with a trusted OpenSCAD install:

```bash
python docs/assembly/source/build.py --export-meshes [--openscad /path/to/openscad]
```

That exports every module in `meshes.MODULES` with `-D 'part="none"'`, rewrites the cache
with the new CAD hash, and rebuilds. Then re-run `check.py`; it fails if a module was added
to `internals()` without a mesh, or if mesh bounds drift from the SCAD parameters.

## How the drawing is made

One orthographic camera (azimuth 35°, elevation 28°) for every view. Each part mesh is moved
by a per-view offset (all exactly zero when assembled), projected, back-face culled and
rasterised into a supersampled label/depth buffer. Silhouettes, creases (> 30°) and tangent
edges are clipped analytically against every front-facing triangle in front of them, so the
linework is exact rather than depth-buffer sampled. Tint fills are traced from the label
buffer into closed even-odd polygons that sit under the lines. Callout anchors are model-space
points on named CAD features, projected with the same camera and rejected by the build if
they do not land on their own part's visible surface. The SVG and the PDF are written from
one display list; the PNG is the SVG rendered by Chrome at 2×.
