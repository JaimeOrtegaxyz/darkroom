"""Sheet composition: callout lanes, legend, and one display list written to SVG and PDF.

The SVG and the PDF are both serialised from the same display list, so their geometry,
tints and text positions are identical by construction (PDF units = SVG px x PT_PER_PX).
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field

import numpy as np
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas

FONT = "Helvetica, Arial, 'Liberation Sans', sans-serif"
PDF_FONT = {400: "Helvetica", 700: "Helvetica-Bold"}
PT_PER_PX = 0.6
INK = "#22252a"
INK_SOFT = "#5c616a"
LEADER = "#4a4f57"
PAPER = "#fbfbfa"


def text_width(s, size, weight=400, spacing=0.0):
    return stringWidth(s, PDF_FONT[weight], size) + spacing * max(len(s) - 1, 0)


def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


# ---------------------------------------------------------------------------------------
# display list


@dataclass
class Item:
    kind: str
    data: dict


@dataclass
class Group:
    attrs: dict
    items: list = field(default_factory=list)


class Doc:
    def __init__(self, w, h, title, desc):
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.root = Group({})
        self.stack = [self.root]

    def open(self, **attrs):
        g = Group(attrs)
        self.stack[-1].items.append(g)
        self.stack.append(g)
        return g

    def close(self):
        self.stack.pop()

    def add(self, kind, **data):
        self.stack[-1].items.append(Item(kind, data))

    # primitives -------------------------------------------------------------------
    def area(self, loops, fill, edge=0.5):
        """Closed even-odd region; `edge` px of same-colour stroke closes AA hairlines."""
        self.add("area", loops=loops, fill=fill, edge=edge)

    def lines(self, polylines, stroke, width, cls=None, dash=None):
        self.add("lines", polylines=polylines, stroke=stroke, width=width, cls=cls, dash=dash)

    def circle(self, cx, cy, r, fill=None, stroke=None, width=0):
        self.add("circle", cx=cx, cy=cy, r=r, fill=fill, stroke=stroke, width=width)

    def rect(self, x, y, w, h, fill=None, stroke=None, width=0, rx=0):
        self.add("rect", x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, width=width, rx=rx)

    def text(self, x, y, s, size, weight=400, anchor="start", fill=INK, spacing=0.0, cls=None):
        self.add("text", x=x, y=y, s=s, size=size, weight=weight, anchor=anchor, fill=fill, spacing=spacing, cls=cls)

    # SVG ------------------------------------------------------------------------------
    def svg(self):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(self.w)}" height="{fmt(self.h)}" '
               f'viewBox="0 0 {fmt(self.w)} {fmt(self.h)}" font-family="{FONT}" role="img" aria-labelledby="title desc">',
               f'<title id="title">{html.escape(self.title)}</title><desc id="desc">{html.escape(self.desc)}</desc>',
               f'<rect width="{fmt(self.w)}" height="{fmt(self.h)}" fill="{PAPER}"/>']
        self._svg_items(self.root.items, out)
        out.append("</svg>\n")
        return "\n".join(out)

    def _svg_items(self, items, out):
        for it in items:
            if isinstance(it, Group):
                attrs = " ".join(f'{_attr(k)}="{html.escape(str(v))}"' for k, v in it.attrs.items())
                out.append(f"<g {attrs}>")
                self._svg_items(it.items, out)
                out.append("</g>")
                continue
            d = it.data
            if it.kind == "area":
                path = " ".join("M" + " ".join(f"{fmt(x)} {fmt(y)}" for x, y in lp) + "Z" for lp in d["loops"])
                edge = f' stroke="{d["fill"]}" stroke-width="{fmt(d["edge"])}" stroke-linejoin="round"' if d["edge"] else ""
                out.append(f'<path d="{path}" fill="{d["fill"]}" fill-rule="evenodd"{edge}/>')
            elif it.kind == "lines":
                path = " ".join("M" + " ".join(f"{fmt(x)} {fmt(y)}" for x, y in pl) for pl in d["polylines"])
                cls = f' class="{d["cls"]}"' if d["cls"] else ""
                dash = f' stroke-dasharray="{d["dash"]}"' if d["dash"] else ""
                out.append(f'<path{cls} d="{path}" fill="none" stroke="{d["stroke"]}" stroke-width="{fmt(d["width"])}" '
                           f'stroke-linecap="round" stroke-linejoin="round"{dash}/>')
            elif it.kind == "circle":
                out.append(f'<circle cx="{fmt(d["cx"])}" cy="{fmt(d["cy"])}" r="{fmt(d["r"])}" fill="{d["fill"] or "none"}"'
                           + (f' stroke="{d["stroke"]}" stroke-width="{fmt(d["width"])}"' if d["stroke"] else "") + "/>")
            elif it.kind == "rect":
                out.append(f'<rect x="{fmt(d["x"])}" y="{fmt(d["y"])}" width="{fmt(d["w"])}" height="{fmt(d["h"])}"'
                           + (f' rx="{fmt(d["rx"])}"' if d["rx"] else "")
                           + f' fill="{d["fill"] or "none"}"'
                           + (f' stroke="{d["stroke"]}" stroke-width="{fmt(d["width"])}"' if d["stroke"] else "") + "/>")
            elif it.kind == "text":
                cls = f' class="{d["cls"]}"' if d["cls"] else ""
                ls = f' letter-spacing="{fmt(d["spacing"])}"' if d["spacing"] else ""
                wt = ' font-weight="700"' if d["weight"] == 700 else ""
                # explicit start-anchored x so every renderer (and the PDF) agrees on placement
                x = d["x"] - _anchor_shift(d)
                out.append(f'<text{cls} x="{fmt(x)}" y="{fmt(d["y"])}" font-size="{fmt(d["size"])}"{wt}{ls} '
                           f'fill="{d["fill"]}">{html.escape(d["s"])}</text>')

    # PDF ------------------------------------------------------------------------------
    def pdf(self, path, title):
        k = PT_PER_PX
        c = rl_canvas.Canvas(str(path), pagesize=(self.w * k, self.h * k), invariant=1, pageCompression=1)
        c.setTitle(title)
        c.setAuthor("Darkroom")
        c.setSubject(self.desc)
        c.setCreator("docs/assembly/source/build.py")
        c.translate(0, self.h * k)
        c.scale(k, -k)                       # SVG px, y down
        c.setFillColor(HexColor(PAPER))
        c.rect(0, 0, self.w, self.h, stroke=0, fill=1)
        c.setLineCap(1)
        c.setLineJoin(1)
        self._pdf_items(c, self.root.items)
        c.showPage()
        c.save()

    def _pdf_items(self, c, items):
        for it in items:
            if isinstance(it, Group):
                self._pdf_items(c, it.items)
                continue
            d = it.data
            if it.kind == "area":
                p = c.beginPath()
                for lp in d["loops"]:
                    p.moveTo(*lp[0])
                    for x, y in lp[1:]:
                        p.lineTo(x, y)
                    p.close()
                c.setFillColor(HexColor(d["fill"]))
                c.setStrokeColor(HexColor(d["fill"]))
                c.setLineWidth(d["edge"])
                c.drawPath(p, stroke=1 if d["edge"] else 0, fill=1, fillMode=0)
            elif it.kind == "lines":
                p = c.beginPath()
                for pl in d["polylines"]:
                    p.moveTo(*pl[0])
                    for x, y in pl[1:]:
                        p.lineTo(x, y)
                c.setStrokeColor(HexColor(d["stroke"]))
                c.setLineWidth(d["width"])
                c.setDash([float(v) for v in d["dash"].split()] if d["dash"] else [])
                c.drawPath(p, stroke=1, fill=0)
                c.setDash([])
            elif it.kind == "circle":
                if d["fill"]:
                    c.setFillColor(HexColor(d["fill"]))
                if d["stroke"]:
                    c.setStrokeColor(HexColor(d["stroke"]))
                    c.setLineWidth(d["width"])
                c.circle(d["cx"], d["cy"], d["r"], stroke=1 if d["stroke"] else 0, fill=1 if d["fill"] else 0)
            elif it.kind == "rect":
                if d["fill"]:
                    c.setFillColor(HexColor(d["fill"]))
                if d["stroke"]:
                    c.setStrokeColor(HexColor(d["stroke"]))
                    c.setLineWidth(d["width"])
                if d["rx"]:
                    c.roundRect(d["x"], d["y"], d["w"], d["h"], d["rx"], stroke=1 if d["stroke"] else 0, fill=1 if d["fill"] else 0)
                else:
                    c.rect(d["x"], d["y"], d["w"], d["h"], stroke=1 if d["stroke"] else 0, fill=1 if d["fill"] else 0)
            elif it.kind == "text":
                x = d["x"] - _anchor_shift(d)
                c.saveState()
                c.translate(x, d["y"])
                c.scale(1, -1)
                t = c.beginText(0, 0)
                t.setFont(PDF_FONT[d["weight"]], d["size"])
                t.setCharSpace(d["spacing"])
                t.setFillColor(HexColor(d["fill"]))
                t.textOut(d["s"])
                c.drawText(t)
                c.restoreState()


def _attr(k):
    """Python keyword-safe names to SVG attributes: class_ -> class, data_part -> data-part."""
    return k.rstrip("_").replace("_", "-")


def _anchor_shift(d):
    w = text_width(d["s"], d["size"], d["weight"], d["spacing"])
    return {"start": 0.0, "middle": w / 2, "end": w}[d["anchor"]]


# ---------------------------------------------------------------------------------------
# callout lanes


@dataclass
class Callout:
    key: str            # anchor key, e.g. "pi.header"
    part: str
    num: int
    label: str
    lane: str           # "L" | "R"
    anchor: tuple       # (x, y) px
    y: float = 0.0      # label baseline centre
    box: tuple = ()     # label bbox (x0, y0, x1, y1)
    attach: tuple = ()  # leader end at the label
    leader: list = field(default_factory=list)


def spread(prefs, lo, hi, gap):
    """1-D label placement: keep order, keep >= gap apart, stay in [lo, hi], stay near prefs."""
    clusters = []  # [sum of prefs, count, top]

    def clamp(top, n):
        return min(max(top, lo), hi - (n - 1) * gap)

    for p in prefs:
        clusters.append([p, 1, clamp(p, 1)])
        while len(clusters) > 1:
            a, b = clusters[-2], clusters[-1]
            if a[2] + a[1] * gap <= b[2]:
                break
            s, n = a[0] + b[0], a[1] + b[1]
            clusters[-2:] = [[s, n, clamp(s / n - (n - 1) * gap / 2, n)]]
    out = []
    for _, n, top in clusters:
        out += [top + i * gap for i in range(n)]
    return out


def layout_callouts(callouts, lanes, size, spacing, gap, bounds=(36, 1164)):
    """lanes = {"L": (x_text_end, y_lo, y_hi), "R": (x_text_start, y_lo, y_hi)}; blocks stay inside bounds."""
    badge_r = size * 0.62
    for side in ("L", "R"):
        cs = sorted([c for c in callouts if c.lane == side], key=lambda c: c.anchor[1])
        if not cs:
            continue
        x_edge, y_lo, y_hi = lanes[side]
        ys = spread([c.anchor[1] for c in cs], y_lo, y_hi, gap)
        for c, y in zip(cs, ys):
            c.y = y
            tw = text_width(c.label, size, 400, spacing)
            block = 2 * badge_r + 8 + tw
            if side == "L":
                x1 = max(x_edge, bounds[0] + block)
                x0 = x1 - block
                c.attach = (x1 + 8, y)
            else:
                x0 = min(x_edge, bounds[1] - block)
                x1 = x0 + block
                c.attach = (x0 - 8, y)
            c.box = (x0, y - size * 0.8, x1, y + size * 0.8)
            stub = 14 if side == "L" else -14
            elbow = (c.attach[0] + stub, y)
            c.leader = [c.anchor, elbow, c.attach]
    return callouts


def draw_callouts(doc, callouts, size, spacing, prefix, leaders_only=False):
    badge_r = size * 0.62
    doc.open(id=f"{prefix}-leaders", class_="leaders")
    for c in callouts:
        doc.open(class_="leader", data_part=c.part, data_callout=c.key)
        doc.lines([np.array(c.leader)], LEADER, 0.9)
        doc.circle(c.anchor[0], c.anchor[1], 2.6, fill=INK, stroke="#ffffff", width=1.0)
        doc.close()
    doc.close()
    if leaders_only:
        return
    doc.open(id=f"{prefix}-labels", class_="annotations labels")
    for c in callouts:
        x0, _, x1, _ = c.box
        doc.open(class_="label", data_part=c.part, data_callout=c.key)
        bx = x0 + badge_r
        doc.circle(bx, c.y, badge_r, fill=INK)
        doc.text(bx, c.y + size * 0.36, str(c.num), size * 0.78, 700, "middle", "#ffffff")
        doc.text(bx + badge_r + 8, c.y + size * 0.36, c.label, size, 400, "start", INK, spacing)
        doc.close()
    doc.close()


def leaders_cross(callouts):
    """Pairs of leaders that intersect (other than at shared anchors)."""
    bad = []
    segs = []
    for c in callouts:
        for a, b in zip(c.leader[:-1], c.leader[1:]):
            segs.append((c.key, np.array(a, float), np.array(b, float)))
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            ki, a, b = segs[i]
            kj, p, q = segs[j]
            if ki == kj:
                continue
            if _seg_x(a, b, p, q):
                bad.append((ki, kj))
    return sorted(set(bad))


def _seg_x(a, b, p, q):
    def cr(o, u, v):
        return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])
    d1, d2, d3, d4 = cr(p, q, a), cr(p, q, b), cr(a, b, p), cr(a, b, q)
    return (d1 * d2 < 0) and (d3 * d4 < 0)
