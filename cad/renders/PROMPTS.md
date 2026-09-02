# Render prompts — v0.4, round 8 (2026-09-01)

**Round 7 principle:** prompts are SHORT. Shape comes from the attached CAD images, not from prose — round 6 described the pocket, dish and grid in words and the model over-rounded everything it was told about (see `ai/archive/round6/`). Now the brief says only: copy the attached topology, soften edges realistically, change materials/light/camera. Per-view text is a few lines.

**Round 7 result:** the short brief works. Pocket, dish, slot lead-in, caps and screws follow the CAD closely; B's body now reads as black plastic lit from inside. Drift: in C/C2 the pocket's rectangular boundary is faint (the dish and the 45° lead-in carry the shape); D failed twice — the model rendered the front despite the rear refs, retried separately with rear refs only (no 03/08 attached) plus one camera sentence: camera then passes, but the third attempt lit the internals warm white instead of red and rendered the body as clear smoked glass — kept as `ai/D-glow-rear.png` for the camera/topology, glow still open. Round 6 kept in `ai/archive/round6/` for comparison.

**Round 8:** CAD change, not a prompt change — the spherical thumb dish (which no model rendered legibly) became a straight half-disc cut merged into the pocket, flat floor, 0.6 fillet on the floor edge. Reference pack regenerated; same brief. Round 7 in `ai/archive/round7/`.
**Round 8 result:** all five pass. The keyhole recess reads exactly (crisp wall, soft floor edge) in A, C, C2; D finally has red LEDs and a black frosted body. Minor drift: in C the slot mouth shows a hint of metal inside (looks like a USB-C receptacle); B's top glow still a touch translucent. This is the current set in `ai/`.

**Round 9 (2026-09-02, picks):** 5 takes per view in `ai/archive/picks/` (sheets `00-sheet-*.png`). Chosen: A-3, C-4. B-3 and D-2 liked for the frosted look, but every glow take drew the cube's edges and corners noticeably darker than the faces, as if a frame ran round every edge — misleading, the walls are uniform. B and D re-run with one added sentence (uniform glow to the edges, no dark bands) → takes #6–10 (`00-sheet-*-r2.png`). Result: the sentence works on the edges but the model trades it for a brighter, more transparent body — Codex's own notes flag "clear-red drift" on three D takes. B-7 and B-10 keep the frosted look with even edges; D-8 is the closest compromise, D-7/D-10 are even but glassy. **User pick: D-9** (no dark edges at all) → promoted to `ai/D-glow-rear.png`. B re-run with D-9 attached as the FIRST image plus one sentence ("the same object photographed from behind in this exact glow state — match its body precisely… now seen from the front") → takes #11–15 (`00-sheet-B-hero-glow-r3.png`). This is the trick that works: a finished render of the same object as material reference beats any wording. All five frosted, glow to the edges; #12 and #15 cleanest. User not sold on any → 10 more identical takes, #16–25 (`00-sheet-B-hero-glow-r4.png`). All consistent with the direction; variation is mostly in how much the glow blooms on the side face and whether the top edge keeps a faint dark rim. **User pick: B-19.**

**Approved set (2026-09-02)** in `ai/`: A = picks A-3, B = picks B-19, C = picks C-4, D = picks D-9. C2 (front, IDLE) not picked yet. Everything else — every take, rounds 6–8 and the v0.3 rounds — is under `ai/archive/` (`archive/picks/` has all 50 takes and the sheets).

## Screen (round 3)

The screen contents are no longer left to the model. `screens/make_screens.py` draws the six UI states at the panel's native 240 × 240 (`screens/`), and each prompt attaches the exact state as its last image with the line below. Hero gets `02-menu`, glow hero `03-developing`, front views `04-done` and `01-idle`. Loaded film in the mockups: Anime Portrait.

> SCREEN CONTENT: the final attached image is exactly what the 1.3" screen displays, pixel for pixel — reproduce it faithfully on the screen (same text, same layout, same colours, black background), scaled to the screen's glass, seen through it with a slight glass reflection. Do not invent, rearrange or add any screen text.

## Shared brief (prepended to every prompt)

Turn the attached CAD renders into a product photograph. The CAD images are the ground truth for SHAPE: reproduce their topology exactly — every edge, recess, opening and control in the same place, size, proportion and shape. Do not round, soften, enlarge, shrink, move or reinterpret any feature; the only softening allowed is realistic tiny fillets and machined edges a real 3D-printed part would have. Ignore the CAD's flat shading and cream/black backgrounds.

Materials only: body = matte black smoked-translucent PETG, reads plain black when unlit; front plate = matte graphite, edge to edge, no frame; four flush black anodized socket screws; round soft-touch rubber button caps, the top-right one red; screen = glossy glass showing the attached screen image pixel for pixel. No logos, text, feet or stickers.

Photo: premium hardware shot, 180 mm lens look, 16:9 landscape, object in the middle third, on a slab of dark split-face slate spanning the frame, charcoal backdrop, very low key.

## A · hero, idle
Camera and framing as reference 1. Safelight off: body plain black. Softbox key upper-left, thin cool rim from behind right. Screen: MENU.

## B · hero, glow
Same camera as A. Safelight on: the black frosted body is lit deep red from INSIDE — it stays an opaque-looking black plastic that glows, never a transparent red box; brightest near the top, ember at the base. The walls are uniform: the glow runs evenly right up to every edge and corner — no dark bands, frames or ribs along the edges, the corners are as lit as the faces. Key light nearly off. Screen: DEVELOPING.

## C · front, straight on
Camera dead-on as reference 3; plate detail as reference 8. Show material truth: rubber caps, screw sockets, the slot pocket, glass reflection. Screen: DONE (C) / IDLE (C2).

## D · glow, rear three-quarter
Camera as references 4/5. Safelight on as in B. Rear wall is the same one-piece body with the USB-C opening and pinhole. Internals (references 6/7) show only as faint silhouettes through the glowing black: the electronics stack low, the diffuser shelf mid-height, two bright LED points above it. The walls are uniform: the glow runs evenly right up to every edge and corner — no dark bands, frames or ribs along the edges.

## Model bake-off (2026-09-01, hero on MENU, same brief, via fal.ai — `fal_render.py`; the refine script was folded into `fal_upscale.py`)

| Model | Res | Layout | Mood | Screen | Notes |
|---|---|---|---|---|---|
| Codex image tool (gpt-image) | ~1680 px | ✔ | ✔ best | ✔ pixel-faithful | the reference look |
| gpt-image-1.5 edit, quality high | 1536×1024 | ✔ | ✔ | ~ one glyph glitch | same family as Codex, hard cap on size |
| Nano Banana Pro 4K | 5504×3072 | ✘ moved buttons into a pad | flat first try, ok with the low-key line | ✔ pixel-faithful | best materials, weakest layout obedience |
| Seedream 4.5 | 4096×2304 | ✘ | ✘ | ✘ wrote the prompt on the screen | out |
| gpt-image-1.5 → Banana Pro 4K refine | 5504×3072 | ✔ | ✔ | ✔ | best output; drifted to a straight-on camera |
| gpt-image-1.5 → Topaz 4× | 6144×4096 | ✔ | ✔ | fuzzy, glitch baked in | cheap, faithful, no new truth |

Working pipeline: compose with gpt-image (Codex or fal), then hand the photo + the screen PNG to Banana Pro at 4K with "reproduce this photograph exactly". Outputs in `ai/fal/`.

## Upscale pass (2026-09-02) — `fal_upscale.py`, outputs in `ai/upscale/`

Hero (A, 1672 × 941) through three routes, same-region crops compared:

| Route | Output | Verdict |
|---|---|---|
| Topaz Creative (Bloom 2), creativity 8/9, colour preservation on, ×1.25 | 2090 px | ~ best material rendering of the three: real rubber and plastic texture, crisp slot lead-in, red cap keeps its matte; but the screen text is rewritten and the slot mouth grows a metal contact strip |
| (wrong endpoint first: Topaz Redefine c5 — kept as `*-wrong-endpoint.png`; worse on every count) | 2090 px | ✘ |
| Nano Banana Pro 4K re-render, photo as ref 1 + screen PNG last | 5504 px | ✔ screen pixel-faithful, recess/caps identical, real micro-texture added; slightly warmer/greyer plate |
| Clarity upscaler ×2, creativity 0.3, resemblance 0.75 | 3344 px | ~ geometry exact, materials good, but screen text drifts ("Goblin Node", "SELEOT londs") |

Banana re-render is the only route that keeps the screen. Three more Banana takes of the hero (`A-banana-4k-2..4`): all keep the text; #2 dulls the caps' rubber and hollows the page dots, #3 and #4 are the cleanest (matte caps, faithful dots, crisp recess). Topaz Creative has the best surfaces. Obvious combo: Topaz Creative for the object, then composite the @4x screen PNG (or Banana's screen) back over the panel.

**Finals via Banana Pro 4K (2026-09-02):** hero = `A-banana-4k-3` → `A-hero-menu-4k.png`. B, C, D each run ×3 (`ai/upscale/`). Lesson: for the rear view do NOT attach the screen PNG — Banana painted the DEVELOPING mockup onto the rear wall (kept in `upscale/rejected/`); `fal_upscale.py banana` now takes the screen as optional and says "no screen visible from this angle" when omitted. C-1 has a "soan to view" typo; C-2/C-3 clean. All three D reruns clean.

**Cleanup (2026-09-02):** user picks B-3, C-3, D-1. The four Banana 4K finals are the only AI renders kept — `{A-hero-menu,B-hero-glow,C-front-done,D-glow-rear}-4k.png` in this folder (5504 × 3072). Every other AI render — all takes, every round, the Codex originals and the other upscales — was deleted at the user's request. The screen mockups (`screens/`) stay; the CAD reference pack was removed too and is regenerated from `darkroom.scad` when needed.
