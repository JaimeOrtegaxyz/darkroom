# The Darkroom Hardware Plan

## Cube Size And Rough Internal Fit

The current concept renders use an **85 mm x 85 mm x 85 mm external cube**.

Assuming a smoked translucent PETG shell with roughly **2 mm walls**, the rough
internal clear volume is about **81 mm x 81 mm x 81 mm** before subtracting for
screw bosses, standoffs, port cutouts, button hardware, and the front display
plate.

This is a plausible target size for the planned hardware. It gives enough room
for the Raspberry Pi Zero 2 W, PiSugar battery module, 1.3 inch square display,
three buttons, side ports, and the lower safelight chamber while keeping the
object visually cube-like.

## Known Component Envelopes

- **Raspberry Pi Zero 2 W:** official Zero form factor, **65 mm x 30 mm**.
  Source: <https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/>
- **PiSugar 3 for Pi Zero:** designed for the Raspberry Pi Zero / Zero 2
  footprint and includes the 1200 mAh battery, charging, and power handling.
  Source: <https://www.pisugar.com/products/pisugar-3-raspberry-pi-zero-battery>
- **1.3 inch 240x240 display:** square active display area is approximately
  **23.4 mm x 23.4 mm**. A Waveshare HAT carrier is about **65 mm x 30.2 mm**,
  but the chosen discrete ST7789 module can be mounted more flexibly.
  Source: <https://www.waveshare.com/wiki/1.3inch_LCD_HAT>

## Plausible Internal Arrangement

```text
85 mm cube external
~81 mm internal clear span

Front face:
- 1.3 inch square display module, roughly 30-40 mm square including PCB/bezel
- Three plain round buttons below the display
- Four black front screws, one per corner, with internal screw posts

Inside:
- Pi Zero 2 W + PiSugar stack, roughly 65 x 30 mm footprint
- Stack mounted vertically or offset behind/alongside the display
- Two red LEDs low behind the front wall for the safelight glow
- Short wiring/ribbon runs for display, buttons, LEDs, and ports
- Right-side microSD slot and USB-C port breakout
```

## Main Fit Risk

The main risk is the **microSD card reader implementation**. A chunky
off-the-shelf OTG card reader may work for prototyping, but it is unlikely to
fit cleanly as a final integrated slot without making the shell awkward.

For the final enclosure, prefer one of these:

- a compact internal **microSD breakout board** with only the slot exposed, or
- a stripped/embedded reader board mounted so the shell exposes a clean slot.

## Size Recommendation

Keep **85 mm cube external** as the working enclosure target.

Do not shrink below roughly **75 mm external** without doing a CAD pass around
exact part dimensions, port clearances, screw posts, and cable bend radii. The
85 mm cube leaves useful mechanical breathing room while still reading as a
small companion object.
