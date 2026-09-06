# Darkroom Hardware Plan

Reconciled with the form-factor model on 2026-09-02. The numbers here are the
CAD's numbers: [`GEOMETRY.md`](GEOMETRY.md) is the written spec and
[`cad/darkroom.scad`](cad/darkroom.scad) the model; if this page and those
disagree, they win. Nothing is verified against parts in hand yet.

## Cube Size And Internal Fit

The enclosure is an **80 mm wide x 84 mm deep x 80 mm tall** hard cube with
1.5 mm fillets, a hair deeper than wide, like a small case.

It is two parts. The **body** is one print: top, sides, bottom and rear wall in
black smoked-translucent PETG, open only at the front. The **sled** is a
graphite front plate with a floor, a diffuser shelf and a rear bulkhead hanging
off its back. Everything mounts on the sled; you build it on the bench, slide it
in from the front and drive four screws. Repair is the same four screws.

Wall thickness sculpts the glow:

- **1.8 mm** on the chamber sides and top (the upper ~55 % glows)
- **3.0 mm** on the base walls, floor and rear wall (the base stays dim, the
  rear stays thick for the port openings)
- **4.0 mm** front plate, so a flush 2 mm screw head leaves 2 mm under it

Internal clear span is **74 x 77 x 74 mm** in the base and **76.4 mm** wide in
the chamber, before screw posts, sled rails and the components below.

## Known Component Envelopes

- **Raspberry Pi Zero 2 W:** 65 x 30 x 1.4 mm, M2.5 holes 3.5 mm from the
  corners (58 x 23 pattern).
  Source: <https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/>
- **PiSugar 3 for Pi Zero:** same 65 x 30 footprint, about 11 mm thick with the
  1200 mAh cell, 5.5 mm pogo gap to the Pi. Thickness is an estimate: verify.
  Source: <https://www.pisugar.com/products/pisugar-3-raspberry-pi-zero-battery>
- **1.3 inch 240 x 240 ST7789 module:** PCB 35 x 40 x 1.6 mm, glass
  27 x 29 x 2.6 mm, active area 23.4 mm square. Generic numbers: verify the
  Geek Factory unit.
  Source: <https://www.waveshare.com/wiki/1.3inch_LCD_HAT>
- **Buttons:** 12 mm tactile switches on 16 mm carriers behind Ø10 mm rubber
  caps.
- **microSD socket:** push-push, 14.5 x 15 x 1.9 mm body on a 24 x 22 mm
  board. Placeholder for BOM #6.

## Internal Arrangement

```text
80 x 84 x 80 external, front = the plate

Front plate (x across, z up, mm):
- 1.3" display, active 23.4 sq in a 32 sq bezel recess, centred at x 40, z 55
  (9 mm top margin); PCB on the back of the plate, glass in a pocket
- microSD slot bottom-left: 12.2 x 2.0 through opening at x 24.5, z 27.5,
  centred in a 26 x 9 mm recess with a half-disc thumb scallop below it;
  socket on a horizontal board right behind the plate
- four Ø10 buttons in a 2 x 2 grid bottom-right, columns x 50.5 / 63.5,
  rows z 27 / 14: Up, Select (red) / Down, Power; top row level with the
  recess's top edge
- four M3 low-head screws, black, flush, 5.5 mm in from each corner, into
  9 mm square posts inside the body

Inside, bottom to top:
- sled floor at z 3.3, 2 mm thick
- Pi Zero 2 W over the PiSugar 3, FLAT in the base, rear-biased: footprint
  x 7.5..72.5, y 47.7..77.7, PiSugar on 1.5 mm standoffs at z 6.8, Pi on top
  of the 5.5 mm pogo gap; the PiSugar's edge meets the sled's rear bulkhead
- white diffuser shelf at z 34, 1.2 mm, on 2 mm rails; cable pass-through at
  the rear
- safelight: two red LEDs above the shelf, chamber centre, 26 mm apart,
  pointing up (see below)
- empty light chamber from z 34 to the top

Rear wall (x, z), cut through the body and the bulkhead behind it:
- USB-C opening 9.4 x 3.6 at x 54, z 11.8 (the PiSugar's port)
- power pinhole Ø3.2 at x 26, same height (the PiSugar's button)
  Both positions are a guess at where they land on the PiSugar's edge: verify.
```

## Safelight: Two LEDs

The glow is two LEDs, not a strip. They sit on a small breakout on the diffuser
shelf, at the centre of the chamber, 26 mm apart and pointing up, so the light
fills the empty upper chamber and the thin walls pass it as deep red. In the
CAD and the BOM they are 5 mm WS2812 pixels (addressable, one data line, colour
set in software); plain 5 mm red LEDs on a GPIO with a resistor would do the
same job if the pixels prove fussy. Either way the concept is the same: two
point sources above the electronics, which is how they read in the renders,
two bright dots seen through the rear wall.

They moved from the earlier plan's spot low behind the front wall: the front is
now an opaque graphite plate and the base walls are 3 mm, so light down there
would go nowhere. Above the shelf it has 44 mm of chamber and 1.8 mm walls.

## Main Fit Risk

Still the **microSD card reader**. With the slot on the front plate, the
reader has to be a bare push-push socket on a small board (or a stripped OTG
reader) mounted flat behind the plate, its mouth at the slot; its USB link then
runs back to the Pi and is not modelled yet. The Steren dongle in the early BOM
does not fit this. Second risk: the PiSugar's port and button positions, which
set where the rear openings go.

## Size Recommendation

Keep **80 x 84 x 80 mm** as the working target. It is already 5 mm under the
earlier 85 mm cube; do not go smaller without a pass around exact part
dimensions, the reader board, screw posts and cable bend radii. The first print
should be the sleeve and sled STLs in [`cad/`](cad/) as an envelope fit check.
