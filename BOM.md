# Darkroom — Bill of Materials (Mexico)

**Researched:** 2026-06-07  
**Exchange rate used:** 1 USD = 17.47 MXN (Banxico FIX rate, 2026-06-06)  
**Scope:** Purchase-ready BOM for building one Darkroom — a Raspberry Pi Zero 2 W appliance in a translucent 3D-printed shell. Prices are in MXN where the retailer lists MXN; for international sources the USD price is given with approximate MXN conversion in parentheses. Stock status reflects the state of each listing at time of research; online inventory changes daily — verify before ordering.

---

## Design decisions — component review, 2026-06-07

Outcome of a component-level review (Codex consult + form-factor discussion). The supplier
research below is unaffected; these notes pin down *what* to build with.

1. **Brain: Pi Zero 2 W, confirmed.** Right shape for a networked Linux appliance (Wi-Fi,
   Python/Flask/PIL, USB OTG, SPI, GPIO). Fallback order if the stock wait becomes
   unacceptable: Zero 2 WH imported from the US, then Pi 3A+ (more headroom and full-size
   USB, but hurts the small-object premise). No other SBC families, no microcontrollers —
   this is a Linux appliance, not an MCU gadget.
2. **Display: discrete path chosen.** Bare 1.3" ST7789 + separate buttons is the build.
   The Waveshare HAT is demoted to an *optional bench bring-up tool*: its edge-mounted
   buttons would force the shell around dev-board geometry, and the face layout
   (screen/buttons/slot) must feel intentional.
3. **Buttons: the $3 12mm tact switches are prototype controls.** The final build wants
   panel-mount momentary buttons, or tact switches under proper caps with a mounting
   strategy — the controls should feel deliberate, not like exposed PCB parts.
4. **Safelight LED: prototype with the stick, but design the shell around 1–3 individual
   pixels.** An 8-LED stick is a line of hot spots; a diffuse safelight wants individual
   WS2812/SK6812 pixels placed in a diffuser cavity (spec 2.3). Don't lock the enclosure
   to the stick. *Wiring note:* Pi GPIO is 3.3V and WS2812 data nominally wants 5V logic —
   1–3 pixels on short leads usually work as-is; if flaky, add a level shifter (74AHCT125)
   or power the pixels at ~4.3V through a 1N4001 diode drop.
5. **PiSugar 3: kept. Safe shutdown is a hard bring-up requirement.** Verify that
   hold-Select and/or the PiSugar button trigger a clean Linux shutdown *before* the
   enclosure design is frozen (spec 1.7) — not a nice-to-have.
6. **Card reader: must present as a clean integrated slot.** The slot is the shutter
   (spec 1.4) — a dangling dongle breaks the ritual. Embed the reader so only the microSD
   slot is exposed through the shell wall, or swap to a small internal reader / USB breakout
   that allows it. Treat the specific reader as provisional until the shell is designed.

### Form factor intent (recorded 2026-06-07, updated 2026-09-02 to the CAD)

Self-contained hard cube, 80 × 84 × 80 mm (see [`HARDWARE_PLAN.md`](HARDWARE_PLAN.md) and
[`GEOMETRY.md`](GEOMETRY.md)). Everything lives on the graphite front plate: screen high and
centred, microSD slot bottom-left in a keyhole recess, four round buttons in a 2 × 2 grid
bottom-right (Up, Select red / Down, Power), four flush screws. USB-C and the PiSugar's power
pinhole are on the rear wall. Everything is integrated into the body's faces; nothing hangs off
it. Somewhat larger than minimal is acceptable if integration requires it; the untethered
glow and handheld pass-around quality (spec 1.2 / 1.5) stay non-negotiable.

---

## Main BOM

| # | Part | Recommended Source | Price (MXN) | Availability | Notes |
|---|------|--------------------|-------------|--------------|-------|
| 1 | **Raspberry Pi Zero 2 W** (bare, no headers) | [AG Electrónica — RASPBERRYPI-ZERO-2W](https://agelectronica.com/detalle?busca=RASPBERRYPI-ZERO-2W) | $429 MXN (IVA inc.) | Out of stock online; **400 units arriving 2026-07-31** | No headers included. Soldering required or use row 1a below. Monterrey branch has 4 units in person. |
| 1a | **Raspberry Pi Zero 2 W — headers add-on** (or buy 1WH) | Solder yourself: buy bare board + 40-pin header strip (~$20 MXN at any local electronics shop). Alternatively wait for stock at [330ohms Zero 2 W con Headers](https://www.330ohms.com/shop/p3-b0086-raspberry-pi-zero-2-w-con-headers-1600) | $444 MXN (with headers, 330ohms — currently AGOTADO) | Out of stock | 330ohms bare Zero 2 W also listed AGOTADO at $414 MXN. Pre-soldered WH from Amazon.com US: ~$19–22 USD (~$332–$384 MXN) — see Alternates. |
| 2 | **PiSugar 3 (for Pi Zero, 1200 mAh)** | [pisugar.com official store](https://www.pisugar.com/products/pisugar-3-raspberry-pi-zero-battery) direct, or [Amazon.com.mx listing B09MJ8SCGD](https://www.amazon.com.mx/Pisugar-Bater%C3%ADa-litio-para-1200/dp/B09MJ8SCGD) | $39.99 USD (~$699 MXN) from official store; Amazon.com.mx listing exists (verify price in cart) | In stock (96 units on Tindie; Amazon.com.mx listing present) | **LiPo battery — see Ordering Notes.** Contains 1200 mAh LiPo. Includes power button and I2C battery gauge. Ships from China via official store; check Amazon.com.mx listing for domestic fulfillment. |
| 3A | **Display — HAT path (optional bench bring-up only — see Design decisions #2): Waveshare 1.3inch LCD HAT** (240×240 IPS, ST7789, SPI, 1× joystick + 3× user buttons built in) | [PiShop.us](https://www.pishop.us/product/240x240-1-3inch-ips-lcd-display-hat-for-raspberry-pi/) — $15.95 USD (~$279 MXN) + international shipping | ~$279–320 MXN (product) + ~$15–25 USD shipping to MX | **In stock** at PiShop.us | Covers display AND all 3 buttons in one part. Eliminates need for line items 4a/4b. Verify Amazon.com.mx availability before ordering from US. LCSC has it at $8.42 USD but minimum-qty shipping adds cost. |
| 3B | **Display — discrete path (CHOSEN — see Design decisions #2): 1.3" ST7789 SPI bare module** (240×240 IPS) | [Geek Factory MX](https://www.geekfactory.mx/producto/display-lcd-de-1-3-pulgadas-spi-st7789/) | **$170 MXN** | In stock (domestic) | No buttons or joystick — requires separate buttons (line item 4). Available domestically; ~3 day shipping anywhere in Mexico. |
| 4 | **4× momentary push buttons** (12×12 mm tactile, PCB mount) — only needed for discrete path; Up, Select, Down, Power in the plate's 2 × 2 grid | [Geek Factory MX — push button estándar](https://www.geekfactory.mx/producto/push-button-estandar-4-pines-pulsador-boton/) | $1 MXN each = **$4 MXN** for 4 | In stock | 4-pin, 1.6×1.6×0.7 cm tactile switch. Add colorful caps from the [330ohms push button kit at Cyberpuerta](https://www.cyberpuerta.mx/Por-Marca/330OHMS/330Ohms-Kit-de-Push-Button-con-Capucha.html) if desired for nicer feel. |
| 5 | **WS2812B NeoPixel LED stick (8 LEDs)** | [Geek Factory MX — NeoPixel Stick 8×WS2812](https://www.geekfactory.mx/producto/neopixel-stick-8-x-5050-leds-rgb-ws2812/) | **$39 MXN** | In stock (domestic) | 8 individually addressable LEDs, WS2812B/SK6812 compatible. Entire stick controlled via 1 GPIO. Prototype part only: the enclosure uses two individual 5 mm pixels on the diffuser shelf (HARDWARE_PLAN.md, Safelight); the stick is for bench bring-up, or cut two pixels off it. |
| 6 | **Micro-USB OTG microSD card reader** | [Steren USB-685 — Lector microSD/USB 3en1 OTG](https://www.steren.com.mx/lector-microsd-usb-3-en-1-otg.html) | **$74 MXN** (25% promo price; regular $99 MXN) | In stock (domestic) | Has micro-USB OTG plug — plugs directly into Pi Zero's OTG port. Also has USB-A and USB-C. Hundreds of Steren stores nationwide; same-day pickup possible. **Provisional: must end up embedded as a clean slot in the shell (Design decisions #6).** |
| 7 | **MicroSD card 32 GB, A1** (for Pi OS) | [Steren — Kingston 32 GB U1/V10/A1](https://www.steren.com.mx/memoria-microsd-de-32-gb-kingston-clase-u1-v10-a1.html) | **~$170–200 MXN** (verify; Steren 64 GB A1 listed at $383 MXN; 32 GB variant on same page) | In stock (domestic, multiple Steren locations) | Kingston Canvas Select. A1 class is sufficient for Pi OS boot. Also widely available at Walmart, Liverpool, Elektra. |
| 8 | **Translucent PETG filament, 1.75 mm, 1 kg** (natural/clear) | [Amazon.com.mx — Polymaker PolyLite PETG Transparente](https://www.amazon.com.mx/Polymaker-Filamento-transparente-impresoras-filamentos/dp/B09DKMCNMW) | **~$558 MXN** (based on search data; verify at checkout) | Available on Amazon.com.mx (verify before ordering) | PolyLite PETG transparent/natural is ideal — optically clear, decent light transmission. Print at 230–240°C nozzle / 70–80°C bed. Alternative: 3D Market MX at ~$890 MXN if Amazon listing is unavailable. |
| 9 | **Misc consumables** (40-pin female-female jumper wire set, M2.5 nylon standoff kit, a few JST pigtail leads) | [Geek Factory MX — cables Dupont](https://www.geekfactory.mx/producto/cables-dupont/) + any local standoff kit | **~$150 MXN eyeball total** | Available domestically | Dupont 40-wire set ~$20–26 MXN at Geek Factory; M2.5 nylon standoff kit ~$80–120 MXN on Amazon.com.mx or MercadoLibre; JST leads ~$20 MXN. |

---

## Alternates

### 1. Raspberry Pi Zero 2 W

| Source | Price | Notes |
|--------|-------|-------|
| [330ohms.com — Zero 2 W](https://www.330ohms.com/products/raspberry-pi-zero-2-w) | $414 MXN | AGOTADO at time of research. Official Raspberry Pi reseller in MX; watch for restock. |
| [330ohms.com — Zero 2 W con Headers](https://www.330ohms.com/shop/p3-b0086-raspberry-pi-zero-2-w-con-headers-1600) | $444 MXN | AGOTADO. Pre-soldered headers — ideal for this project. |
| [Amazon.com — Pi Zero 2 WH pre-soldered](https://www.amazon.com/Zero-Pre-Soldered-Color-Coded-Quad-Core-Bluetooth/dp/B0DS68NPGF) | ~$19–22 USD (~$332–$384 MXN + shipping/import) | Ships from US; may attract ~25% import duties at the border, or ship via forwarding service. |
| [MercadoLibre MX — search](https://listado.mercadolibre.com.mx/raspberry-pi-zero-2w) | $500–$900+ MXN | Third-party resellers; prices vary. Verify seller reputation. Scalper pricing common when stock is scarce — don't pay above $600 MXN for the bare board. |
| [AG Electrónica](https://agelectronica.com/detalle?busca=RASPBERRYPI-ZERO-2W) | $429 MXN | Restock of 400 units expected 2026-07-31. Best domestic option when in stock. |

### 2. PiSugar 3

| Source | Price | Notes |
|--------|-------|-------|
| [Tindie — PiSugar 3 for Pi Zero](https://www.tindie.com/products/pisugar/pisugar-3-battery-for-raspberry-pi-zero/) | $39.99 USD (~$699 MXN) | 96 in stock. Ships from China. LiPo battery may be held by customs — see Ordering Notes. |
| [AliExpress item 1005006035059663](https://www.aliexpress.com/item/1005006035059663.html) | ~$35–40 USD (~$611–$699 MXN) (verify before buying) | Ships from China; Standard Shipping to MX ~15–35 days. Same LiPo caveat applies. |
| [Amazon.com.mx B09MJ8SCGD](https://www.amazon.com.mx/Pisugar-Bater%C3%ADa-litio-para-1200/dp/B09MJ8SCGD) | Verify at checkout (listing exists) | If fulfilled by Amazon MX this could be fastest. Verify it is PiSugar 3 (not PiSugar 2) for Pi Zero before buying. |

### 3A. Waveshare 1.3inch LCD HAT (HAT path)

| Source | Price | Notes |
|--------|-------|-------|
| [PiShop.us](https://www.pishop.us/product/240x240-1-3inch-ips-lcd-display-hat-for-raspberry-pi/) | $15.95 USD (~$279 MXN) + shipping | In stock. Ships internationally; verify MX shipping cost at checkout. |
| [LCSC Electronics](https://www.lcsc.com/product-detail/LCD-Screen_Waveshare-1-3inch-LCD-HAT_C359937.html) | $8.42 USD (~$147 MXN) | Cheapest unit price, 40 in stock. LCSC ships to MX but shipping cost offsets savings for 1 unit. Good for multiples. |
| Amazon.com.mx search | ~$300–450 MXN (verify) | Search "Waveshare 1.3 LCD HAT" on Amazon.com.mx — listings appear via third-party sellers; prices/availability vary (verify before buying). |

### 3B. Bare ST7789 1.3" display module (discrete path)

| Source | Price | Notes |
|--------|-------|-------|
| [MercadoLibre MX — TFT 1.3" ST7789 SPI 240×240](https://www.mercadolibre.com.mx/display-tft-lcd-13-spi-rgb-240x240-st7789/p/MLM2044472908) | ~$80–150 MXN (verify before buying) | Multiple listings; prices vary. Verify it is SPI 240×240, not I2C or smaller OLED. |
| [AliExpress — generic ST7789 1.3" module](https://www.aliexpress.com/w/wholesale-st7789-1-3-display.html) | ~$3–5 USD (~$52–$87 MXN) | Cheapest option; 15–35 day shipping. |

### 5. WS2812B LEDs (alternate forms)

| Source | Price | Notes |
|--------|-------|-------|
| [UNIT Electronics — NeoPixel SMD 5×5mm](https://uelectronics.com/producto/neopixel-rgb-5x5mm-smd-ws2812b-b/) | Verify on site | SMD form; requires soldering to breakout board. |
| [AliExpress — 8mm through-hole WS2812B 5-pack](https://www.aliexpress.com/item/4000199040560.html) | ~$4.99 USD (~$87 MXN) for 5-pack | Through-hole; easiest to mount in the shell. 15–35 day shipping. |
| [MercadoLibre — WS2812B NeoPixel various](https://listado.mercadolibre.com.mx/led-ws2812b-neopixel) | ~$30–$80 MXN | Various forms. |

### 6. USB OTG Card Reader (alternate)

| Source | Price | Notes |
|--------|-------|-------|
| [Amazon.com.mx — UGREEN USB-C OTG reader](https://www.amazon.com.mx/UGREEN-tarjetas-Windows-Macbook-Samsung/dp/B07D1J88CF) | Verify on site | USB-C, not micro-USB — requires separate micro-USB OTG adapter if used with Pi Zero. Good backup option. |
| Any USB-A microSD reader + [Steren micro-USB OTG adapter] | ~$50–80 MXN combo | Two-part approach; functional but clunkier to use. |

### 7. MicroSD 32 GB A1

| Source | Price | Notes |
|--------|-------|-------|
| [Amazon.com.mx — SanDisk 32 GB microSD Ultra](https://www.amazon.com.mx/s?k=SanDisk+32GB+microSD+A1+clase+10) | ~$150–$250 MXN (verify) | SanDisk Ultra A1 widely available; verify listing is genuine (not counterfeit). |
| Any Walmart, Coppel, Liverpool | ~$150–$250 MXN | Walk-in purchase same day; no delivery wait. |

### 8. Translucent PETG Filament (alternate sources)

| Source | Price | Notes |
|--------|-------|-------|
| [3D Market MX](https://www.3dmarket.mx/p/polylite-petg-polymaker/) | ~$890 MXN | Domestic 3D printing specialist; wider color selection. |
| [3D Factory MX — PolyLite PETG](https://3dfactory.mx/products/polylite-petg) | ~$595 MXN (listed; verify stock — showed Agotado at research time) | Same Polymaker product as Amazon listing. |
| [MercadoLibre MX — filamento PETG transparente](https://listado.mercadolibre.com.mx/filamento-petg-transparente) | ~$350–$600 MXN | Generic brands (CCTREE, eSUN) at lower price; quality slightly more variable. |

---

## Subtotals

### HAT path (Waveshare LCD HAT — display + buttons in one module)

| Line item | Source | MXN |
|-----------|--------|-----|
| Pi Zero 2 W (bare, AG Electrónica — July restock) | AG Electrónica | $429 |
| + 40-pin header strip (if soldering own) | Local shop | ~$20 |
| PiSugar 3 | Amazon.com.mx / official store | ~$699 |
| Waveshare 1.3" LCD HAT (PiShop.us, ~$15.95 + ~$20 shipping) | PiShop.us | ~$558 |
| NeoPixel Stick 8× WS2812 | Geek Factory MX | $39 |
| Steren OTG card reader | Steren | $74 |
| Kingston 32 GB microSD A1 | Steren | ~$185 |
| Polymaker PETG transparent 1 kg | Amazon.com.mx | ~$558 |
| Misc (jumpers, standoffs, JST) | Geek Factory / Amazon.com.mx | ~$150 |
| **HAT PATH TOTAL** | | **~$2,712 MXN (~$155 USD)** |

### Discrete path (bare display + 3 separate buttons)

| Line item | Source | MXN |
|-----------|--------|-----|
| Pi Zero 2 W (bare, AG Electrónica — July restock) | AG Electrónica | $429 |
| + 40-pin header strip | Local shop | ~$20 |
| PiSugar 3 | Amazon.com.mx / official store | ~$699 |
| Geek Factory 1.3" ST7789 bare module | Geek Factory MX | $170 |
| 4× tactile push buttons | Geek Factory MX | $4 |
| NeoPixel Stick 8× WS2812 | Geek Factory MX | $39 |
| Steren OTG card reader | Steren | $74 |
| Kingston 32 GB microSD A1 | Steren | ~$185 |
| Polymaker PETG transparent 1 kg | Amazon.com.mx | ~$558 |
| Misc (jumpers, standoffs, JST) | Geek Factory / Amazon.com.mx | ~$150 |
| **DISCRETE PATH TOTAL** | | **~$2,328 MXN (~$133 USD)** |

> **The discrete path is the chosen build** (see Design decisions #2): cheaper, fully domestic, and it frees the face design. The HAT path remains listed only as an optional bench bring-up platform — buy it only if validating hardware before the shell exists is worth ~$385 MXN extra.

---

## Ordering Notes

### What ships domestic vs. from China

**Buy domestically in Mexico:**
- Pi Zero 2 W — AG Electrónica (restock July 2026) or 330ohms (watch for restock); do not pay scalper prices above ~$600 MXN
- NeoPixel stick — Geek Factory MX, in stock
- 1.3" ST7789 bare display (discrete path) — Geek Factory MX, in stock, $170 MXN
- Push buttons — Geek Factory MX, $1 each
- OTG card reader — Steren (nationwide stores), $74 MXN
- MicroSD 32 GB — Steren, Walmart, Liverpool (walk-in same day)
- PETG filament — Amazon.com.mx (Prime-eligible, 1–3 day delivery if Prime)
- Jumper wires, dupont cables — Geek Factory MX or Tecneu
- M2.5 standoff kit — Amazon.com.mx or MercadoLibre

**Import from international source:**
- **PiSugar 3** — no domestic stock found. Best path is Amazon.com.mx listing (verify fulfillment); otherwise order from PiSugar official store or Tindie (ships from China, 15–30 days)
- **Waveshare 1.3" LCD HAT** (if taking HAT path) — PiShop.us ($15.95 + shipping); no confirmed Mexican domestic stock found. LCSC is cheapest per unit but shipping adds cost. Allow 7–15 days shipping from US

### LiPo / battery shipping caveat (PiSugar 3)

The PiSugar 3 contains a 1200 mAh lithium polymer cell. LiPo batteries are classified as UN Class 9 dangerous goods for air transport (IATA PI 965/968). International sellers (AliExpress, Tindie) frequently ship small consumer LiPo devices to Mexico via economy shipping using postal/courier networks that accept small-capacity batteries inside equipment — but there is real risk of:
- Customs hold or seizure (rare for <100 Wh cells, but not zero)
- Longer-than-expected delivery (2–6 weeks is common)
- Carrier refusal for air shipping, routing via sea (8–12 weeks)

**Recommended mitigation:** Check the Amazon.com.mx listing first ([B09MJ8SCGD](https://www.amazon.com.mx/Pisugar-Bater%C3%ADa-litio-para-1200/dp/B09MJ8SCGD)). If it shows in-stock with domestic Amazon fulfillment (i.e., not "ships from abroad"), that is the fastest, lowest-risk path. If it shows "ships from international seller," treat it the same as ordering from AliExpress/Tindie. PiSugar's official store claims Mexico is available in their dropdown — but get a firm shipping confirmation before paying.

### Pi Zero 2 W stock situation

This board has historically been constrained. As of June 2026:
- **330ohms**: AGOTADO (both bare and with-headers variants)
- **AG Electrónica**: Out of stock online; 400 units due 2026-07-31, 4 in Monterrey store
- **Microbot.com.mx**: Listed at $465 MXN but AGOTADO
- **MercadoLibre**: Third-party sellers list it $500–$900 MXN — these are often scalper/arbitrage prices and not worth paying above ~$550 MXN

**Best strategy:** If you are in or near Monterrey, contact AG Electrónica directly to reserve from the July restock (400 units is enough — call ahead). Otherwise, monitor rpilocator.com filtering for MX retailers, or order the WH (pre-soldered header) variant directly from Amazon.com US if you can absorb the ~25–30% import tax risk (items under $50 USD often clear without formal import declaration, but this is not guaranteed).

### Waveshare LCD HAT (HAT path)

No confirmed domestic stock in Mexico found at research time. PiShop.us ($15.95) is a solid US-based authorized reseller. Budget $15–25 USD for shipping to Mexico ($262–$437 MXN). Order early; transit 7–15 business days. If Amazon.com.mx shows a Waveshare HAT listing from a seller — compare price + delivery time. LCSC ($8.42 USD, 40 in stock) is worth considering only if ordering multiple units.

### Expected lead times

| Item | Lead time (to your door in MX) |
|------|-------------------------------|
| Steren products (card reader, microSD) | Same day in-store, or 1–4 days delivery |
| Geek Factory MX | 2–5 business days (domestic courier) |
| Amazon.com.mx (Prime, domestic) | 1–3 days |
| PiShop.us / international US | 7–15 business days |
| PiSugar (AliExpress/Tindie from CN) | 15–35 days (standard); 10–15 days (AliExpress expedited) |
| AG Electrónica Pi restock | ~2026-07-31 (confirmed arrival date) |

### Risk summary

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Pi Zero 2 W out of stock everywhere domestic | High | Wait for AG Electrónica July restock (confirmed) or buy WH from Amazon.com US and accept import risk |
| PiSugar 3 LiPo customs delay | Medium | Try Amazon.com.mx first; if unavailable, order AliExpress Express shipping |
| Waveshare LCD HAT no domestic stock | Low-medium | PiShop.us is reliable; 7–15 day wait is manageable |
| MercadoLibre Pi Zero scalper pricing | Medium | Do not pay above $600 MXN for bare board |
| PETG filament variant mismatch | Low | Confirm you buy the *transparent/natural* variant (not colored) — the listing B09DKMCNMW is the correct transparent one |
