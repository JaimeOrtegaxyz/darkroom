# GEOMETRY — form-factor sketch v0.4

**Date:** 2026-09-01 (v0.1 and v0.2 same day, superseded). **v0.3:** screws flush, slot on the plate, one-piece black body, cap detail. **v0.4:** plate re-laid out — screen high, slot pocket + thumb dish bottom-left, 2×2 button grid bottom-right. **Status:** a sculpture to react to, not a freeze. Nothing here is verified against parts in hand.
This page turns the spec's Part 1 and the BOM's form-factor intent into numbers. The model in [`cad/darkroom.scad`](cad/darkroom.scad) is generated from these values — change them here *and* in the parameter block of the `.scad`; they must not drift apart.

**v0.2 register (user direction 2026-09-01):** this is *not* the sona toy. Hard-edged, an old PC more than a plaything: straight faces, one small fillet, visible screws on the front, no wordmark, no feet. Quietly cyberpunk, not over the top. v0.1's rolled edges, top-plate buttons, side slot and rubber feet were sona vocabulary and are gone.

What this sketches: the envelope, the front-loaded sled architecture, which face carries what, the wall-thickness zones for the glow, real component footprints.
What stays open: everything about retention inside the sled (standoffs, clips, cable routing), the reader board, the exact display module, button feel, whether the 4th corner is Power.

## 1. The idea — a hard cube, loaded from the front

A **body** (one piece: top, sides, bottom and rear wall, open only at the front; black smoked translucent PETG — reads black when idle, red when the safelight is on) and a **sled** (a graphite front plate with a floor, a diffuser shelf and a rear bulkhead hanging off its back). Every component mounts on the sled. You build the sled on the bench, slide it into the sleeve, drive four screws through the front plate into corner posts. To repair, four screws and the whole thing comes out the front.

The rear bulkhead brings the card reader and the PiSugar's USB-C/power to the depth of the rear wall; the sleeve's rear openings are just windows onto it.

The glow: the electronics stack lies flat in the base; above the diffuser shelf the sleeve is an empty **light chamber** with two safelight pixels in it. Walls are 1.8 mm around the chamber and 3 mm around the bay, so the upper ~55% glows and the base stays dim (spec 2.3, "wall thickness sculpts the glow"). The graphite front plate is opaque on purpose: it is the bezel of an old machine, and everything opaque lives on it anyway.

| Face | Carries |
|---|---|
| Front (the plate) | 1.3" screen in a shallow square recess, **horizontally centered, high on the face**; below it a control zone (z 8–32) whose top edge is shared: **microSD slot bottom-left — the shutter**, centered in a recessed rounded-rectangle pocket with a 45° lead-in, and a **half-disc thumb scallop** cut straight in below the pocket at the same depth, the recess's floor edge filleted; **four round buttons in a 2×2 grid bottom-right** — Up (top-left), **Select (top-right, red)**, Down (bottom-left), Power (bottom-right); **four M3 low-head screws** at the extreme corners, heads **flush** with the face |
| Rear | part of the same one-piece body, no panel; USB-C and PiSugar power pinhole cut into it, low |
| Top, sides | nothing — the glow |
| Bottom | nothing — it stands on its own face; no feet, no label |

## 2. Envelope

| Dimension | Value | Derivation |
|---|---|---|
| Width | **80 mm** | Pi stack 65 + sled clearance + 2 × 3 wall, plus room for the corner posts |
| Depth | **84 mm** | plate 3 + sled 77.7 + rear wall 3; a cube that is a hair deeper than wide, like a small case |
| Height | **80 mm** | 3 floor + electronics bay to z 34 + 44 chamber (incl. 1.8 top) |
| Fillet | **1.5 mm** on every edge | the only softening on the object |
| Joint | plate and sleeve meet flush and sharp, 0.2 mm hairline; an inner lip on the sled backs it so nothing shows through | |

```
 FRONT (80 × 80)                 REAR
 ┌●─────────────────────●┐      ┌───────────────────────┐
 │      ┌─────────┐      │      │                        │
 │      │ screen  │      │      │       black wall       │
 │      │  23.4²  │      │      │                        │
 │      └─────────┘      │      │   ▭ USB-C     · pwr    │
 │  ┌═══slot═══┐ (Up)(Sel)│      │                        │
 │  └───◡──────┘ (Dn)(Pwr)│      │                        │
 └●─────────────────────●┘      └───────────────────────┘
 ● = M3 low-head screw, flush, 5.5 in · ( ) = Ø10 cap · ◡ = half-disc thumb scallop
 screen bezel 32 sq, centre z 55 · pocket 26 × 9 at x 24.5, top z 32 · grid cols x 50.5 / 63.5, rows z 27 / 14
```

## 3. Walls, zones, sled

| Item | Value | Note |
|---|---|---|
| Glow walls (chamber sides + top) | **1.8 mm** | starts 14 mm behind the plate; the first 14 mm stay 3 mm as a frame for the corner posts |
| Base walls, floor, rear wall | **3.0 mm** | rear stays thick for the port openings |
| Front plate | **4.0 mm** | graphite; screen window 25 sq in a 32 sq × 0.8 recess centred at x 40, z 55 (9 mm top margin); 4 mm so a flush 2 mm screw head leaves 2 mm under it |
| Slot | through 12.2 × 2.0 r0.6 at x 24.5, z 27.5; landing pocket 26 × 9 r1.5, 1.2 deep, top edge z 32; 1 mm 45° lead-in; **thumb scallop**: a half-disc r 5.5 centred on the pocket's bottom edge, cut straight in to the same 1.2 depth, so pocket + disc are one flat-floored recess; the floor-to-wall edge of the whole recess has a 0.6 fillet | push-push socket on a horizontal PCB right behind the plate; a straight cut softened on its deep face, which reads clearly in photos (a spherical dish did not) |
| Button caps | Ø10 straight, r0.6 roll on the top edge, 1.4 proud, hole Ø10.3 (0.15/side — ream to fit after printing); Select red | 2×2 grid, 13 mm pitch, columns x 50.5 / 63.5, rows z 27 / 14; top row's top edge (z 32) is flush with the pocket's top edge; the cap fills its cutout; revolved profile in the model |
| Diffuser shelf | z = 34, 1.2 mm white PETG on 2 mm rails on the sled | cable pass-through at the rear |
| Sled | 73.4 wide × 76.7 long; 2 mm floor at z 3.3, notched at the front corners to clear the bottom posts; 2 mm bulkhead at the rear; 0.3 clearance per side to the sleeve | |
| Corner posts | 9 × 9 × 14 at the four inner front corners, 2.5 pilot on the screw pattern | |
| Screws | M3 **low-head** socket, **black anodized**, Ø5.5 × 2.0 head, Ø5.9 × 2.0 counterbore → flush, centers 5.5 from the face corners | |
| Body material | black smoked translucent PETG, one print | idle it is simply black; the 1.8 mm chamber walls pass the safelight as deep red, the 3 mm base and rear walls barely — **verify** with a swatch that black-tinted filament at 1.8 mm passes enough red |

## 4. Components — footprints used (verify against parts in hand)

| Part | Size used | Placement | Confidence |
|---|---|---|---|
| Pi Zero 2 W | 65 × 30 × 1.4, M2.5 holes 3.5 from corners (58 × 23 pattern) | flat on the sled floor, rear-biased so the PiSugar edge meets the bulkhead | official drawing — solid |
| PiSugar 3 (Zero) | 65 × 30 × 11 incl. cell, 5.5 pogo gap | under the Pi; USB-C + button to the rear | thickness estimate — **verify** |
| 1.3" ST7789 module | PCB 35 × 40 × 1.6, glass 27 × 29 × 2.6, active 23.4 sq | on the back of the plate, glass in a pocket | generic — **verify the Geek Factory unit** |
| Buttons | 12 mm tacts on 16 mm carriers behind Ø10 caps, 2×2 grid bottom-right | plate; the carriers stop 1 mm under the LCD PCB | BOM #4 prototype controls |
| microSD socket | push-push, 14.5 × 15 × 1.9 body on a 24 × 22 PCB | horizontal, right behind the plate under the slot, bottom-left | placeholder for BOM #6; the USB link to the Pi is not modeled |
| Safelight | 2 × WS2812 5 mm pixels, 26 apart, on a breakout on the shelf | chamber center, pointing up | BOM #4 |
| USB-C opening | 9.4 × 3.6, r 1.6 | rear, x 54, z ≈ 14 | **verify** the port's position on the PiSugar edge |
| Power pinhole | Ø3.2 | rear, x 26, same height | PiSugar button — **verify** |

## 5. Renders and modes

**Camera:** OpenSCAD's perspective FOV is fixed (about a 60 mm-equivalent lens) and the CLI cannot change it. The perspective views are therefore rendered at 3× distance and 3× resolution and cropped to the centre third, which is optically a ~180 mm lens — the contained, product-shot look. Recipe: `--imgsize=4800,3600 --camera=…,990` then `sips -c 1200 1600 file.png`. Orthographic views are unchanged.

**Render notes (for the eventual real render, not modeled here):** front and rear plates matte graphite; screws black anodized with a machined sheen on the socket edge; button caps soft-touch rubber, matte with a slight sheen, Select in red; body black smoked translucent PETG, plain black idle, red glowing through in the glow state; no seam anywhere on the body.

**AI studio renders (2026-09-02):** `cad/renders/` — the four approved v0.4 renders, Nano Banana Pro 4K (5504 × 3072): `A-hero-menu-4k.png` (hero on the MENU screen), `B-hero-glow-4k.png` (glow hero on DEVELOPING), `C-front-done-4k.png` (front on DONE), `D-glow-rear-4k.png` (rear glow, internals showing through). Nothing else is kept. Pipeline: Codex image tool from a CAD reference pack (hero idle/lit, front ortho, rear, rear lit, exploded, section, closeup — regenerate with the commands in the header of `darkroom.scad`) with the short brief in `PROMPTS.md`, then `fal_upscale.py banana` (photo + screen PNG; no screen PNG for the rear view). Lessons that stuck: shape comes from the attached CAD images, not prose; a finished render of the same object is the best material reference; only Banana keeps the screen text through an upscale.

**Screen mockups:** `cad/renders/screens/` — the six UI states of spec 3.1 drawn at the panel's native 240 × 240 by `make_screens.py` (IDLE, MENU, DEVELOPING, DONE, ERROR, hold-Select power-off), kept as the @4x versions plus a contact sheet. Language: state word top-left, battery top-right, filter-position dots at the bottom, off-white monospace on black, red reserved for what Select or insertion will do; DEVELOPING is a dim red pie and a count, nothing else. Attached as the last image of each render prompt with a "reproduce pixel for pixel" line. These are the reference for `display.py`'s Pi backend too.

**CAD views** are not checked in; the commands in the header of `cad/darkroom.scad` regenerate them (hero, glow, rear, front ortho, section, closeup, exploded with tags). Modes: `part = assembly | sleeve | sled | internals | exploded | exploded_tags | section`. STLs: `darkroom-sleeve.stl`, `darkroom-sled.stl` — printable as-is for an envelope fit check, not for the internals.

## 6. Open questions

1. **The 4th corner — decided: keep four buttons** (2026-09-01). The 4th is Power: a wake/shutdown button on GPIO3 beside the PiSugar's own. Firmware detail.
2. **Plate colour.** Graphite plate + translucent body drawn here. An all-translucent version is one colour swap; the glow would then also leak around the buttons and screws.
3. **Slot — decided: on the plate** (2026-09-01), below the screen. Consequence: the reader lives on the plate and its USB link runs back to the Pi; reader choice (BOM #6) now has to be a bare socket or a tiny board, not the Steren dongle.
4. **Proportion.** 80 × 84 × 80. A taller chamber gives the glow more presence; this size keeps it hand-sized.
5. **Sled retention inside.** The sled is drawn as plate + floor + bulkhead; nothing holds the Pi stack, the reader or the diffuser yet. Standoffs and clips come with the first print.
