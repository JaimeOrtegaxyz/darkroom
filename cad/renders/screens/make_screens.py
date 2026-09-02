"""Screen mockups for The Darkroom's 240x240 ST7789 (spec 1.6 / 3.1).

Drawn at native 240x240, saved as-is and at 4x nearest-neighbour (pixel-true)
for use as image-gen references. python3 make_screens.py
"""
from PIL import Image, ImageDraw, ImageFont
import qrcode, os, math

OUT = os.path.dirname(os.path.abspath(__file__))
S = 240
BG = (0, 0, 0)
FG = (222, 222, 216)          # off-white, not pure
DIM = (110, 110, 106)
RED = (232, 44, 32)           # the Select colour: what pressing Select / inserting will do
DEVRED = (110, 14, 10)        # developing glyph: low brightness so the safelight owns the moment
FONT = os.path.expanduser("~/Library/Fonts/BerkeleyMono-Regular.otf")
FONTB = os.path.expanduser("~/Library/Fonts/BerkeleyMono-Bold.otf")
def f(sz, bold=False): return ImageFont.truetype(FONTB if bold else FONT, sz)

FILTERS = ["Pathetic Scribble", "Turn to Cheese", "Goblin Mode", "Anime Portrait"]
LOADED = 3
MARGIN = 14

def new():
    im = Image.new("RGB", (S, S), BG); return im, ImageDraw.Draw(im)

def battery(d, pct=0.72, x=S-MARGIN-22, y=MARGIN+1):
    d.rectangle([x, y, x+20, y+9], outline=FG, width=1)
    d.rectangle([x+21, y+3, x+22, y+6], fill=FG)
    d.rectangle([x+2, y+2, x+2+round(16*pct), y+7], fill=FG)

def header(d, word, color=FG):
    d.text((MARGIN, MARGIN-1), word, font=f(12), fill=color)
    battery(d)

def dots(d, n=4, active=1, y=S-MARGIN-6, color=FG):
    step = 14; x0 = S/2 - step*(n-1)/2
    for i in range(n):
        cx = x0 + i*step
        if i == active: d.ellipse([cx-3, y-3, cx+3, y+3], fill=color)
        else: d.ellipse([cx-2, y-2, cx+2, y+2], outline=DIM, width=1)

def center(d, y, text, font, fill):
    w = d.textlength(text, font=font); d.text(((S-w)/2, y), text, font=font, fill=fill)

def save(im, name):
    im.save(f"{OUT}/{name}.png")
    im.resize((S*4, S*4), Image.NEAREST).save(f"{OUT}/{name}@4x.png")

# 1 IDLE — the loaded filter, and what insertion will do
im, d = new(); header(d, "READY")
center(d, 78, "FILM", f(11), DIM)
name = FILTERS[LOADED]
center(d, 96, name.upper(), f(22, True), FG)
d.line([MARGIN+30, 134, S-MARGIN-30, 134], fill=DIM, width=1)
center(d, 146, "INSERT CARD", f(13, True), RED)
center(d, 164, "to develop", f(12), DIM)
dots(d, active=LOADED)
save(im, "01-idle")

# 2 MENU — the decision phase, screen fully active
im, d = new(); header(d, "FILM")
sel = 2
for i, n in enumerate(FILTERS):
    y = 58 + i*34
    if i == sel:
        d.rectangle([MARGIN-4, y-7, S-MARGIN+4, y+19], fill=(28, 28, 28))
        d.polygon([(MARGIN+2, y+1), (MARGIN+2, y+11), (MARGIN+9, y+6)], fill=RED)
        d.text((MARGIN+18, y-1), n, font=f(15, True), fill=FG)
    else:
        d.text((MARGIN+18, y-1), n, font=f(15), fill=DIM if i != LOADED else FG)
    if i == LOADED and i != sel:
        d.ellipse([S-MARGIN-6, y+3, S-MARGIN-1, y+8], fill=FG)   # the one currently loaded
center(d, S-MARGIN-28, "SELECT loads", f(11), DIM)
dots(d, active=sel)
save(im, "02-menu")

# 3 DEVELOPING — mostly dark, one small glyph; 3 of 8 done
im, d = new()
done, total = 3, 8
r = 22; cx, cy = S/2, S/2 - 6
d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=DEVRED, width=2)
d.pieslice([cx-r, cy-r, cx+r, cy+r], -90, -90 + 360*done/total, fill=DEVRED)
center(d, cy + r + 12, f"{done}/{total}", f(11), DEVRED)
save(im, "03-developing")

# 4 DONE — QR hands off to the phone
im, d = new(); header(d, "DONE")
qr = qrcode.QRCode(border=0, box_size=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
qr.add_data("http://darkroom.local:8000/"); qr.make()
q = qr.make_image(fill_color=FG, back_color=BG).convert("RGB")
n = q.size[0]; px = 112 // n; q = q.resize((n*px, n*px), Image.NEAREST)
im.paste(q, ((S - q.size[0])//2, 46))
center(d, 172, "8 developed", f(13, True), FG)
center(d, 190, "scan to view", f(12), DIM)
dots(d, active=LOADED)
save(im, "04-done")

# 5 ERROR — brief cause, returns to IDLE by itself
im, d = new(); header(d, "ERROR", RED)
center(d, 88, "NO NETWORK", f(20, True), RED)
center(d, 122, "check wi-fi", f(12), FG)
center(d, 140, "card is untouched", f(12), DIM)
center(d, 176, "back in 6s", f(11), DIM)
save(im, "05-error")

# 6 POWER OFF — hold Select
im, d = new(); header(d, "HOLD")
center(d, 92, "POWER OFF", f(20, True), FG)
d.rectangle([MARGIN+20, 134, S-MARGIN-20, 142], outline=DIM, width=1)
d.rectangle([MARGIN+20, 134, MARGIN+20 + round((S-2*MARGIN-40)*0.6), 142], fill=RED)
center(d, 156, "keep holding SELECT", f(11), DIM)
save(im, "06-poweroff")

# contact sheet, 3x scale, labelled
labels = ["IDLE — loaded filter, insert = go", "MENU — Up/Down, Select loads", "DEVELOPING — glyph only, glow owns it",
          "DONE — QR to the gallery", "ERROR — cause, auto-returns", "HOLD SELECT — safe shutdown"]
names = ["01-idle","02-menu","03-developing","04-done","05-error","06-poweroff"]
T = S*3; pad = 30
sheet = Image.new("RGB", (3*(T+pad)+pad, 2*(T+pad+40)+pad), (36, 36, 38)); sd = ImageDraw.Draw(sheet)
lf = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
for i, nm in enumerate(names):
    x = pad + (i%3)*(T+pad); y = pad + (i//3)*(T+pad+40)
    sheet.paste(Image.open(f"{OUT}/{nm}.png").resize((T, T), Image.NEAREST), (x, y))
    sd.text((x, y+T+8), labels[i], font=lf, fill=(230,230,230))
sheet.save(f"{OUT}/00-screens-sheet.png")
print("ok")
