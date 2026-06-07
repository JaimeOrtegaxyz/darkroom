# The Darkroom — Build Spec

*A companion appliance to a keychain camera. You slot in the camera's SD card, and it transforms the photos with image generation while glowing red like a working darkroom. Results appear in a gallery on your phone.*

---

## 0. How to read this document

This spec is written to be handed to an LLM coding agent (e.g. Codex) the way the [openai/imagegencam](https://github.com/openai/imagegencam) repo is written to be handed to one. It is deliberately split into two kinds of content:

- **The reasoning and concept sections (Part 1)** capture *why* the device is the way it is. These are not technical, but they are load-bearing. Future work will flesh the product out further, and these ideas must not be lost or silently overridden. When a later decision seems to conflict with one of these, that is a flag to stop and reconcile, not to quietly drop the original intent.
- **The technical sections (Parts 2 onward)** are the build itself: parts, wiring, state machine, software architecture.

Read Part 1 first. It is the soul of the thing. Part 2 onward is the body.

---

# PART 1 — CONCEPT, ORIGIN, AND REASONING

## 1.1 Where this came from

This project began as a question about a cheap keychain camera (a "Magecam" thumb camera, ~$15 class, bought on AliExpress) and the [ImageGenCam](https://github.com/openai/imagegencam) project by OpenAI. ImageGenCam is a build-it-yourself digital camera: a Raspberry Pi Zero 2 W with a camera module, a small screen, and a battery, which snaps a photo, sends it to an image-generation API, and transforms it (e.g. "turn everyone into cheese," "anime portrait"). Its magic lives entirely in the network round-trip and the software, not in the optics.

The original question was: *could we make the keychain camera do what ImageGenCam does?*

The answer, after examining both, was **no — not by converting the camera.** That conclusion is important context, so it is preserved here in full:

- The keychain camera is a **closed appliance**: a fixed-function SoC of the kind found in cheap thumb cameras. It captures stills/video to a MicroSD card, shows a tiny preview, and nothing else. There is no exposed OS, no Wi-Fi, no way to run custom code, no compute to talk to an API. It is "the camera equivalent of a disposable lighter."
- These units across brands (including the Kodak Charmera) run **near-identical low-cost silicon and closed, undocumented firmware**. The premium ones reflect branding, not different hardware. Reflashing is not a viable path.
- ImageGenCam, by contrast, is **fundamentally a tiny networked computer that happens to have a camera.** The three things that make its loop possible — programmability, connectivity, compute — are exactly the three things the keychain camera lacks.

So the conversion idea was abandoned, and three alternative paths were considered:

1. **Firmware reflash** — *impossible.* Locked, undocumented, shared OEM silicon. Dead.
2. **Donor shell** — build the real ImageGenCam guts and 3D-print a case inspired by the keychain camera's charm. Viable but the Pi stack will never fit a sub-60g thumb-cam volume, so "inspired by" is the honest ceiling.
3. **Hybrid "dumb capture, smart darkroom"** — keep shooting on the keychain camera exactly as-is, and build a *separate* device that takes the camera's SD card and runs the photos through image generation. **This is the chosen path.**

## 1.2 The key insight: two charming dumb objects that rhyme

The reason the hybrid path won is **social, not technical.** A laptop running a watcher script is a chore. A dedicated physical object you slot a card into is a *ritual* — it has the same "press button, magic happens" charm as the keychain camera itself.

The mental model to hold onto:

> The camera is the dumb-but-charming **capture** device.
> The Darkroom is the dumb-but-charming **development** device.
> They rhyme. They are siblings.

This is why the Darkroom should feel like a companion to the camera, not like a desk peripheral. Design decisions throughout (power, charging gesture, form, glow) flow from this sibling relationship. Whenever a choice is ambiguous, prefer the option that makes the two feel like a matched pair.

## 1.3 Why "darkroom"

The device transforms images out of sight and then reveals them — which is exactly what a photographic darkroom does. This metaphor is not decoration; it drives the physical and interaction design:

- A darkroom works under a **red safelight.** Therefore the device **glows red while processing.** (Origin of the glow: it is a literal safelight metaphor, see 1.5.)
- A darkroom is where images "develop" over time. Therefore the **progress indicator is themed as developing** (a closing pie / sweeping clock), see 1.6.
- "Putting your card in here and watching what happens" is a **reveal** — the payoff is watching images resolve, the same emotional beat as watching a print come up in a developer tray.

## 1.4 The card slot is the shutter

A central interaction-design decision: **prompt selection happens *before* the card goes in, and the physical act of inserting the card is the commit action.**

Reasoning (preserve this — it resolves a real tension):
- Image generation takes several seconds per photo, so you cannot have a slow per-photo menu without killing the experience.
- The device therefore holds a **persistent "loaded filter" state**, exactly like a film camera holds whatever film stock is already loaded. You don't choose per-shot; you've committed to a stock.
- Before insertion, the screen shows what the conversion *will* be ("Ready — will transform to: Cheese"). You either accept it by inserting the card, or change it first with the buttons.
- **Inserting the card == "go."** No confirmation step, no post-insertion menu. The card slot becomes the shutter button of the darkroom. This makes insertion feel *causal* — you feed the machine and watch it react.

This also cleanly unifies the "always one filter" vs "pick from a list" question: the hardware is identical for both. Single-filter mode is just the list-mode device with the menu skipped. **Build the flexible version; the simple behavior is a configuration of it.**

## 1.5 The red glow — origin and intent

**Origin:** the glow is a *darkroom safelight*. It was chosen because it solves two problems at once:
1. It is the device's primary **status feedback** — breathing red means "working," dark means "done/idle." It reads across a room, which no cheap screen can.
2. It carries the **entire theme** in one gesture and makes the object feel *alive*.

**Why it must be untethered (subtle but important):** a device whose charm is *glowing* wants to glow without a cord running off its back. The breathing red reads as "this little object is alive and working," and that lands harder as a standalone object on a table. So the glow is part of *why* the device has a battery (see 1.7) — the battery protects the aesthetic, it is not just convenience.

**Intended implementation feel:** semi-translucent 3D-printed shell with an internal LED that glows *slowly* — a breathing fade, not a blink. The pulse can vary by phase (e.g. faster while uploading, slow breath while waiting on the API, solid when done, off when idle). The "slow glow" is a *software behavior* and should be tunable without touching hardware.

## 1.6 The screen — deliberately minimal, hands off to the phone

**Core principle (preserve):** no cheap screen we could afford will ever beat a phone for *looking at images*. Everyone carries a phone; phone screens look far better than any component we'd add. So:

- The on-device screen exists for the **decision** (choosing/confirming the filter) and for **device feedback**, not for viewing results.
- **Viewing results is the phone's job**, via a gallery served by the device (see 1.8).

**During processing, the screen gets out of the way so the red glow owns the moment.** The agreed behavior: the screen stays lit but goes *mostly dark*, showing only a small progress glyph — a moving clock hand or a closing pie chart that reflects how much of the task is complete. Division of labor:

> Red glow = *presence* ("I am working").
> Progress glyph = *progress* ("this much longer").
> Screen active = the *decision* phase. Screen quiet = the *magic* phase.

## 1.7 Power — battery + USB-C, charged like the camera

**Decision:** the device has a battery and charges over USB-C, using a **PiSugar** module.

Reasoning preserved:
- The model to copy is **the camera's own**: a self-contained rechargeable object you top up over USB-C. Same gesture, same cable. (Sibling relationship, 1.2.)
- A battery makes it a real handheld object you can pass around — which the "slot your card in and watch" use depends on.
- The battery **protects the safelight aesthetic** (1.5): glowing untethered is part of the charm.
- The PiSugar is chosen specifically because it bundles **battery + USB-C charging + a power button** into one module purpose-built for portable Pi appliances, rather than three separate problems. (It is also what ImageGenCam uses, reinforcing the sibling lineage.)

**Honest tradeoff (kept on record):** a battery adds bulk/weight and is the most failure-prone part over years (LiPos age). Accepted because this is meant to be carried and passed around. If a future variant is destined to be a permanent fixture in one spot, dropping the battery and running on USB-C wall power is the right call for *that* variant.

**Graceful shutdown matters:** a Pi dislikes being hard-cut mid-write. Power-off should be a clean "hold to power down," ideally folded into the existing three buttons (e.g. hold *Select*) and/or the PiSugar button wired to trigger a safe shutdown, not a brutal cut.

## 1.8 The phone gallery — no app, just a page

The device runs a **local web server** and hosts the transformed photos on its own Wi-Fi (its own network/hotspot, or a shared LAN). The phone connects and sees a small gallery. **No app to install, no cloud account for the viewer** — just a web page. The minimal on-device screen can show a **QR code** that drops you straight onto the gallery. (This is the same hand-off trick ImageGenCam uses for its companion app, again reinforcing the sibling lineage.)

Because generation takes seconds per photo, the device **transforms eagerly in the background** and the gallery **populates live** — the count ticks up, images resolve one by one. Watching an image sharpen into "cheese mode" is the payoff; design for that reveal.

## 1.9 Originals are sacred — the card is read-only

A defining constraint of the chosen path: **the SD card is never written to.** Originals stay pristine on the camera's card; there is no risk of corruption. Transformed images live **on the device**, not on the card. This was a deliberate advantage of the hybrid concept over any "rewrite the images in place" approach — it is safer and it respects that you may want to keep the originals in the camera.

## 1.10 The swappable transform — design seam to keep open

The image transformation should be treated as **one swappable function**: "transform this image with this prompt → return a new image." OpenAI's image API is the first implementation, but the seam must allow another API, or eventually a local model, with no change to the rest of the system. This costs nothing now and keeps the future open; bake it in from the start rather than deferring it. (The *choice* of alternative backends is a later software decision; the *seam* is built now.)

## 1.11 Summary of the object as it now stands

A 3D-printed translucent box. On its face: three buttons, a small screen, and an SD-card slot. Inside: a Raspberry Pi Zero 2 W, a PiSugar for battery + USB-C charging + power button, and an addressable LED for the safelight glow. It runs a local web server that phones connect to for a live gallery. You choose a filter on the screen with the buttons; inserting the card commits it; the box breathes red while it transforms the photos in the background, a small clock/pie glyph ticking on the otherwise-dark screen; finished images appear on your phone. The camera feeds it cards; it feeds your phone images. The card is never modified.

---

# PART 2 — HARDWARE

## 2.1 Bill of materials

| Part | Purpose | Notes |
|---|---|---|
| Raspberry Pi Zero 2 W (with headers) | The brain; Wi-Fi + compute | Same core as ImageGenCam; we drop the camera module, display HAT, and battery HAT it uses for capture |
| PiSugar 3 (for Pi Zero) | LiPo battery + USB-C charging + power button | One module solves power, charging, and clean power-on/off |
| Small display | Filter selection + progress glyph + QR code | A ~1.3" SPI IPS or an SPI/I²C OLED is plenty. It does NOT show result images |
| 3 momentary push buttons | Up / Down / Select | Select doubles as "hold to power down" |
| 1–2 addressable RGB LEDs (WS2812 / NeoPixel) | The red safelight glow | Driven by the Pi; breathing fade in software |
| USB SD-card reader (USB-A → micro-USB OTG, or direct) | Reads the camera's card | The card is read-only to us |
| MicroSD card (for the Pi OS) | Boots the Pi | Separate from the camera's card |
| 3D-printed translucent shell | Body + light diffusion | Semi-translucent filament; thin walls (~1.5–2mm) where light should escape |
| Wiring / JST leads / standoffs | Assembly | — |

> The camera's own SD card is an **input consumable**, not part of the BOM — it arrives with the user, from the keychain camera.

## 2.2 Notable wiring points

- **Buttons:** 3 GPIO inputs with internal pull-ups; debounce in software.
- **NeoPixel:** single data GPIO (note the Pi's WS2812 timing usually wants the PWM/DMA pin; document the chosen library's pin constraint). Keep a common ground.
- **Display:** SPI preferred for redraw speed of the progress glyph; I²C acceptable for a static-ish UI.
- **PiSugar:** sits on the Pi's back / power pins per its own docs; exposes battery state over I²C and a button you can map to safe shutdown.
- **SD reader:** via the Pi's USB OTG. Detect insertion/removal in software (udev or polling).

## 2.3 Shell / light design notes

- Print in **semi-translucent** filament (natural PETG or translucent red). PETG is recommended (durability; ImageGenCam also recommends PETG for its folding case).
- **Wall thickness sculpts the glow:** ~1.5–2mm escapes light nicely; thicker walls stay opaque. Use thickness to control *where* the red shows.
- Position the LED(s) so the glow is diffuse, not a hot point — a small internal cavity / diffuser chamber helps.
- The card slot should be physically prominent and satisfying — it is "the shutter" (1.4).

---

# PART 3 — INTERACTION & STATE MACHINE

## 3.1 States

```
IDLE            screen shows current loaded filter + "insert card to develop"; LED off (or faint idle)
                QR code reachable here too (or via a button)
MENU            user pressed Up/Down; screen shows filter list; Select loads a filter, returns to IDLE
                (MENU is the "decision phase" — screen fully active)
CARD_INSERTED   transition trigger = card detected. Commits the loaded filter. → DEVELOPING
DEVELOPING      screen goes mostly dark + progress glyph; LED breathes red
                device scans card (read-only), uploads each new JPEG, collects results
                gallery populates live
DONE            LED solid (brief) then fades to idle; screen shows "done — scan to view" + QR
                results remain available on the device
ERROR           screen shows brief cause (e.g. no network, no photos found); LED signals (e.g. amber/red blink)
```

## 3.2 Rules

- **Filter is persistent state.** Changing it happens only in MENU. IDLE always displays the currently loaded filter so the user knows what insertion will do (1.4).
- **Insertion is the commit.** No confirmation dialog. (1.4)
- **Single-filter mode** is a settings flag that skips MENU entirely — same hardware, simpler behavior (1.4 / 1.11).
- **Hold Select = safe shutdown** (1.7). Also honor the PiSugar button for power.
- **Card is never written** (1.9). Mount read-only if possible; never delete/modify source files.
- **During DEVELOPING the screen must not compete with the glow** — mostly dark + one small glyph only (1.6).

## 3.3 Progress glyph

- A closing pie chart or sweeping clock hand on an otherwise-dark screen.
- Reflects fraction of photos completed (e.g. 3 of 8 transformed).
- Themed as "developing." Keep it tiny and low-brightness so red dominates (1.6).

## 3.4 Safelight (LED) behavior

Implement as a small software module with named patterns; all timings tunable:

| Phase | Pattern |
|---|---|
| IDLE | off, or very faint slow pulse |
| Uploading a photo | slightly faster red pulse |
| Waiting on API | slow red "breathing" fade (sine ramp) |
| DONE | brief solid red, then fade out |
| ERROR | red (or amber) blink |

The "breathing" is a sine-wave brightness ramp — a few lines of code (1.5).

---

# PART 4 — SOFTWARE ARCHITECTURE

## 4.1 Language / platform

- Python on Raspberry Pi OS (matches ImageGenCam's stack; ~94% Python there).
- Run the app as a service that starts on boot.

## 4.2 Modules

```
darkroom/
  main.py            # state machine, boot, orchestration
  inputs.py          # 3-button handling + debounce + hold-to-shutdown
  display.py         # menu UI, progress glyph, QR rendering
  safelight.py       # NeoPixel breathing/patterns (named phases, tunable timings)
  card.py            # SD detect (insert/remove), read-only scan of DCIM for new JPEGs
  transform.py       # THE SWAPPABLE SEAM (see 4.4)
  gallery.py         # local web server + live-updating gallery page
  store.py           # where transformed images + metadata live on-device
  config.py          # loaded filter, prompts list, single-filter flag, timings, network mode
  prompts.py         # built-in prompt definitions
```

## 4.3 Card handling (`card.py`)

- Detect insertion (udev event or poll).
- Mount/treat as **read-only**.
- Walk the standard `DCIM` folder for JPEGs (these cameras save standard JPEG/MP4 into standard DCIM folders — confirmed for this device class).
- Track which files are new vs already-processed (hash or filename+mtime), so re-inserting the same card doesn't redo everything unless asked.
- Never write, move, or delete on the card (1.9).

## 4.4 The swappable transform seam (`transform.py`) — IMPORTANT

Define one interface:

```python
def transform(image_bytes: bytes, prompt: str) -> bytes:
    """Take an image + a prompt, return a transformed image. Backend-agnostic."""
```

- First implementation: OpenAI image generation API. API key supplied via config/env (the user will top up an OpenAI key).
- Must be swappable for another API or a local model with **no change** to `main.py`, `card.py`, or `gallery.py` (1.10).
- Keep prompts in `prompts.py` / `config.py`, editable (ideally also from the gallery page later).
- Built-in starter prompts (from ImageGenCam, good defaults): Pathetic Scribble, Turn to Cheese, Goblin Mode, Anime Portrait.

## 4.5 Eager background processing + live gallery (`gallery.py`)

- Transform photos in a background worker queue; **don't block** the UI.
- Gallery is a local web page served by the device; phone connects over the device's network.
- Page **auto-refreshes / streams** so images appear one-by-one as they finish (the reveal — 1.8).
- Show a QR code on the device screen (IDLE/DONE) that links straight to the gallery URL.
- No app install, no viewer login (1.6 / 1.8).

## 4.6 Network

- Default: device joins a Wi-Fi network and serves the gallery on the LAN; phone on same network.
- Portable mode: device as its own hotspot / AP so it works away from home (mirrors ImageGenCam's hotspot guidance). Note: API calls still need an upstream internet path — fully offline operation is out of scope until a local model backend is added via the 4.4 seam.
- **Never put image data or keys in URL query strings**; keep the API key in env/config on the device only.

## 4.7 Config (`config.py`)

- `loaded_filter` (persistent)
- `single_filter_mode` (bool)
- `prompts` (list, editable)
- safelight timings per phase
- network mode (LAN vs AP)
- API backend selection + key (env)

---

# PART 5 — BUILD ORDER (suggested)

1. **Pi + PiSugar bring-up.** Boot, confirm battery + USB-C charging + clean shutdown.
2. **Buttons + display.** Get MENU/IDLE navigation and the loaded-filter display working (no card yet).
3. **Safelight.** NeoPixel breathing patterns per phase. Tune the "slow glow."
4. **Card detect + read-only DCIM scan.** Print found JPEGs to console.
5. **Transform seam.** Wire OpenAI backend; transform one image end to end.
6. **Background queue + gallery.** Serve the live page; QR on screen; watch it populate.
7. **Tie the state machine together.** Insertion = commit; progress glyph; DONE/ERROR.
8. **Shell.** Print translucent, tune wall thickness for the glow, mount everything.
9. **Remix.** Editable prompts from the phone, alternate backends, single-filter party mode, etc.

---

# PART 6 — THINGS NOT TO LOSE (quick index back to Part 1)

- Camera and Darkroom are **sibling charming-dumb objects** (1.2) — let it guide ambiguous calls.
- **Card slot = shutter; selection before insertion** (1.4).
- **Red glow = darkroom safelight**, doubles as status, must be **untethered** to feel alive (1.5, 1.7).
- **Screen is for the decision, phone is for looking**; screen goes mostly-dark with a developing glyph during processing (1.6).
- **Originals are sacred; card is read-only** (1.9).
- **Transform is a swappable seam** (1.10).
- Battery tradeoff is **accepted on purpose** for portability; a fixed-location variant could drop it (1.7).
