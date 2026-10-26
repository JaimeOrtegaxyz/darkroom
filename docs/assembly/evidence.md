# Evidence: what the assembly drawings show, and how sure we are

Purpose: an illustrated, CAD-derived explanation of how the Darkroom concept goes together.
It is not a fabrication drawing and not a confirmed build. Source of truth:
[`cad/darkroom.scad`](../../cad/darkroom.scad) (v0.4), with [`GEOMETRY.md`](../../GEOMETRY.md)
and [`HARDWARE_PLAN.md`](../../HARDWARE_PLAN.md). Hashes and per-view numbers are in
[`build-report.json`](build-report.json).

## Where the geometry comes from

| Item | Evidence | Treatment in the drawings |
|---|---|---|
| Body, sled, screw heads, display, controls, reader, Pi stack, diffuser, safelight | Per-module STL exports of `cad/darkroom.scad` (`sleeve_solid()`, `sled()`, `screws()`, `lcd_module()`, `buttons()`, `reader_board()`, `pi_stack()`, `diffuser()`, `safelight()`), cached losslessly in `source/mesh-cache.json.gz` with the CAD's SHA-256 | **CAD-exact.** All 16,614 triangles are drawn; none are added, moved within a part, or repaired |
| Body and sled | Cache meshes are vertex-identical to the repository's `cad/darkroom-sleeve.stl` and `cad/darkroom-sled.stl` | **CAD-exact.** Each is one connected solid; the sled (front plate + floor + rails + rear bulkhead) is never split |
| Pi Zero 2 W vs PiSugar 3 | `pi_stack()` is one module; the CAD leaves a 5.5 mm pogo gap between the two boards | **CAD-derived split** by whole connected solids at the gap; no solid is cut (checked) |
| Button caps vs tact switches + carriers | `buttons()` is one module; caps stop 0.4 mm in front of the switches | **CAD-derived split** in that gap; lossless (checked) |
| Tints | The CAD's `color()` calls (lost in STL export) | **Mirrored per triangle** from SCAD parameters: Select cap red, PCBs green family, glass dark, etc. Tints are lightened for print; hues distinguish parts, they are not material claims |
| Feature anchors, split planes, screw axes | Parameter block of `cad/darkroom.scad`, read by `source/scad_params.py` | **CAD-derived points**, projected with the drawing camera; every anchor is checked to land on its own part's visible surface |
| Exploded and electronics offsets | Chosen for explanation | **Illustrative.** Pure translations listed below; all are exactly `[0, 0, 0]` in the assembled view |
| Body translucency, screen content, cables, connectors, fastener shafts, retention | Not modelled in the CAD | **Not drawn.** Surfaces are drawn opaque; nothing is invented to fill the gaps |

## Views

One orthographic camera for every view: azimuth 35° from the front toward +X, elevation 28°.
Not to scale; each panel is fitted to its space.

- **Assembled** — every offset `[0, 0, 0]`. Internals are occluded by the body, not removed; the
  viewer sends a selection of a hidden part to a view where it can be seen.
- **Exploded** — the body stays; the loaded sled (with display, caps, switches, reader, Pi,
  PiSugar) moves `[0, -114, 0]` out through the open front; the screw heads a further 26 mm
  along their own axes (the same 26 mm as the CAD's `exploded` mode) with dashed insertion
  axes; the diffuser and safelight lift `+58` mm off the sled rails.
- **Electronics** — illustrative spacing of what the sled carries (mm): display `[0,-30,6]`,
  caps `[0,-46,-6]`, switches `[0,-30,-6]`, reader `[-6,-30,-4]`, Pi `[0,24,-8]`, PiSugar
  `[0,24,-26]`, safelight `[10,10,26]`. Setting them to zero reproduces the CAD positions; the
  check confirms they introduce no overlaps the CAD does not already have.

## Source issues found (documented, not repaired)

| Issue | Where | Size |
|---|---|---|
| Bottom-right tact switch and its carrier board run into the body's bottom-right corner post | `buttons()` vs `corner_posts()` | ≈ 65 mm³ (sampled) |
| Top-row carrier boards (z 19–35) pass through the diffuser shelf (z 34–35.2) | `buttons()` vs `diffuser()` | ≈ 44 mm³ |
| 16 mm carrier boards on a 13 mm button pitch overlap one another and merge into one solid | `buttons()`, `tact` / `btn_pitch` | 3 mm overlaps |
| LED bodies start 1.8 mm above the safelight breakout (no leads modelled) | `safelight()`, `px_z` | 3 separate solids |
| PiSugar USB-C and power blocks sit entirely inside the PiSugar envelope, 1 mm short of the bulkhead | `pi_stack()` | not visible |
| Comments disagree with values: `sled_len` "77.7" is 76.7; GEOMETRY.md envelope row says plate 3 mm (it is 4); header says v0.3 for v0.4; the architecture comment still puts the card slot in the rear wall | `cad/darkroom.scad`, `GEOMETRY.md` | text only |

Interference is measured by `source/check.py` (z-column ray parity, 0.25 mm grid) on the
assembled CAD; overlaps under ~0.25 mm (the 0.02 mm `EPS` seams) are below its resolution.

## Limitations

- The microSD reader is a placeholder board; its USB link to the Pi is not modelled.
- Display and PiSugar dimensions are generic or estimated; fit, retention, standoffs/clips
  and cabling are unverified (GEOMETRY.md §4, §6).
- Screws are heads only, as in the CAD; there are no shafts or threads to draw.
- The meshes were not re-exported for this change; the cache is the earlier per-module
  export, accepted because its CAD hash matches and the body/sled match the repo STLs. A
  fresh OpenSCAD export (`build.py --export-meshes`) has not been verified here.
- Hidden-line removal is exact against the mesh triangles; visible fragments shorter than
  2.5 px are dropped as specks, and near-coincident edges a fraction of a millimetre apart
  (e.g. a button cap in its 0.15 mm hole clearance) can render as a broken line at high zoom.
- PNGs are rendered by Chrome from the SVGs; label fonts are Helvetica/Arial, so text may
  shift slightly on systems that substitute another sans-serif.

## Method

Adapted from Jakub Krehel's technical-drawing skill (CAD projection workflow: exact CAD
geometry, one parallel projection, model-space feature anchors, occlusion resolved before
linework, numbered callouts in perimeter lanes, NTS). The skill bundle itself was not
installed or run; `source/render.py` is a custom hidden-line renderer that grew out of an
earlier experiment and replaces its depth-buffer edge sampling with analytic clipping.
