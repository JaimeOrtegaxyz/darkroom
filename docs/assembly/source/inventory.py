"""Component inventory, tint regions, feature anchors and per-view offsets.

Every number below that describes geometry comes from `P` (the parameter block of
cad/darkroom.scad, read by scad_params.py) or from the meshes themselves. Nothing is
re-modelled: meshes are only (a) split into connected pieces where the CAD leaves a
physical gap between separate items, and (b) tinted per triangle to mirror the CAD's own
color() calls, which STL export drops.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------------------
# components: id, number on the drawings, names, tints


@dataclass
class Part:
    key: str
    num: int
    name: str            # legend / label name
    short: str           # lane label
    note: str            # legend note
    tints: list          # [(tint name, hex)]; index 0 is the legend swatch
    source: str          # CAD module(s)
    status: str = "cad"  # cad | placeholder | unverified


PARTS = [
    Part("body", 1, "Body", "BODY", "one-piece open-front enclosure, corner posts inside",
         [("body", "#e9ebee")], "sleeve_solid()"),
    Part("sled", 2, "Sled", "SLED", "front plate + floor + rails + rear bulkhead, one part",
         [("sled", "#b4b8bf")], "sled() = front_plate() + sled_frame()"),
    Part("screws", 3, "M3 screw heads ×4", "M3 SCREW HEADS ×4", "low-head, flush; heads only in CAD",
         [("screw", "#4a4e55")], "screws()"),
    Part("display", 4, "Display, ST7789 1.3″", "ST7789 DISPLAY", "glass in a plate pocket, PCB behind; fit unverified",
         [("pcb", "#a9d3c6"), ("glass", "#323a46"), ("block", "#5d626a")], "lcd_module()", "unverified"),
    Part("caps", 5, "Button caps ×4", "BUTTON CAPS", "2×2 grid, Select red",
         [("cap", "#8e9298"), ("select", "#e2574c")], "buttons(): caps"),
    Part("switches", 6, "Tact switches ×4", "TACT SWITCHES", "12 mm switches on 16 mm carrier boards",
         [("carrier", "#c5dfb4"), ("tact", "#5a5f66")], "buttons(): tacts + carriers"),
    Part("reader", 7, "microSD reader", "MICROSD READER", "placeholder board; USB link to the Pi not modelled",
         [("pcb", "#e3dc9c"), ("socket", "#d7dadf")], "reader_board()", "placeholder"),
    Part("pi", 8, "Pi Zero 2 W", "PI ZERO 2 W", "65 × 30 board, 2×20 header",
         [("pcb", "#8cc59a"), ("header", "#3f444b"), ("metal", "#d4d7dc")], "pi_stack(): Pi board"),
    Part("pisugar", 9, "PiSugar 3", "PISUGAR 3", "battery board under the Pi; thickness unverified",
         [("sugar", "#aab3d4"), ("standoff", "#fbfbf9")], "pi_stack(): PiSugar + standoffs", "unverified"),
    Part("diffuser", 10, "Diffuser shelf", "DIFFUSER SHELF", "white 1.2 mm shelf on the sled rails",
         [("diffuser", "#fdfdfb")], "diffuser()"),
    Part("safelight", 11, "Safelight", "SAFELIGHT", "two 5 mm LEDs on a breakout",
         [("pcb", "#a9d3c6"), ("led", "#f3aa9c")], "safelight()"),
]
PART = {p.key: p for p in PARTS}


# ---------------------------------------------------------------------------------------
# meshes -> parts


def components(tris):
    """Connected components of a triangle soup (shared vertices)."""
    verts, inv = np.unique(tris.reshape(-1, 3), axis=0, return_inverse=True)
    faces = inv.reshape(-1, 3)
    parent = np.arange(len(verts))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b, c in faces:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[find(rc)] = ra
    root = np.array([find(i) for i in range(len(verts))])
    comp = root[faces[:, 0]]
    _, label = np.unique(comp, return_inverse=True)
    return label


def split_by_plane(tris, axis, value):
    """Split a mesh into (below, above) by whole connected components; refuse to cut."""
    label = components(tris)
    below = np.zeros(len(tris), dtype=bool)
    for c in np.unique(label):
        pts = tris[label == c].reshape(-1, 3)[:, axis]
        if pts.max() < value:
            below[label == c] = True
        elif pts.min() > value:
            pass
        else:
            raise SystemExit(f"split plane {axis}={value} would cut a connected component")
    return tris[below], tris[~below]


def build_parts(meshes, P):
    """Return {part key: (tris, tint index per triangle)} from the cached CAD meshes."""
    out = {}
    one = lambda t: (t, np.zeros(len(t), dtype=int))  # noqa: E731
    out["body"] = one(meshes["darkroom-sleeve"])
    out["sled"] = one(meshes["darkroom-sled"])
    out["screws"] = one(meshes["screws"])
    out["diffuser"] = one(meshes["diffuser"])

    t = meshes["display"]
    cy = t[:, :, 1].mean(1)
    tint = np.where(cy < P["face_t"] - 1e-6, 1, np.where(cy > P["face_t"] + P["lcd_pcb"][1] + 1e-6, 2, 0))
    out["display"] = (t, tint)

    # caps sit in the plate holes, 0.4 mm in front of the tact switches: split in that gap
    caps, sw = split_by_plane(meshes["controls"], 1, P["face_t"] - 0.2)
    c = caps.mean(1)
    # btn_pos: Select is column 2, row 1 (top-right); caps are within half a pitch of their centre
    sel = (np.abs(c[:, 0] - P["btn_cx"][1]) < P["btn_pitch"] / 2) & (np.abs(c[:, 2] - P["btn_cz"][0]) < P["btn_pitch"] / 2)
    out["caps"] = (caps, sel.astype(int))
    cy = sw[:, :, 1].mean(1)
    out["switches"] = (sw, (cy < P["face_t"] + P["tact"][2] - 1e-6).astype(int))

    t = meshes["reader"]
    z_top = P["slot_cz"] - P["slot_t"] / 2 - 0.3
    out["reader"] = (t, (t[:, :, 2].mean(1) > z_top + 1e-6).astype(int))

    # PiSugar below, Pi above, separated by the modelled pogo gap
    z_split = P["stack_z"] + P["sugar_t"] + P["stack_gap"] / 2
    sugar, pi = split_by_plane(meshes["pi"], 2, z_split)
    pcb_top = P["stack_z"] + P["sugar_t"] + P["stack_gap"] + P["pi_t"]
    c = pi.mean(1)
    header_y = P["stack_y"] + P["pi_d"] - 5.2
    tint = np.where(c[:, 2] > pcb_top + 1e-6, np.where(c[:, 1] > header_y - 1e-6, 1, 2), 0)
    out["pi"] = (pi, tint)
    out["pisugar"] = (sugar, (sugar[:, :, 2].mean(1) < P["stack_z"] - 1e-6).astype(int))

    t = meshes["safelight"]
    led = t[:, :, 2].mean(1) > P["bay_h"] + P["diff_t"] + 1.2 + 1e-6
    out["safelight"] = (t, led.astype(int))
    return out


# ---------------------------------------------------------------------------------------
# feature anchors: model-space points on named CAD features


def anchors(P):
    W, H, ft = P["W"], P["H"], P["face_t"]
    cap_front = ft - 0.4 - (P["btn_cap_h"] + ft - 0.4)
    stack_top = P["stack_z"] + P["sugar_t"]
    pcb_top = stack_top + P["stack_gap"] + P["pi_t"]
    led_top = P["px_z"] + 4 + P["px_d"] / 2
    z_rdr = P["slot_cz"] - P["slot_t"] / 2 - 0.3
    return {
        # key: (part, point, description of the feature)
        "body.top": ("body", [W * 0.62, P["D"] * 0.62, H], "top face"),
        "body.side": ("body", [W, P["D"] * 0.70, H * 0.55], "right wall"),
        "body.post": ("body", [W - P["wall_base"] - P["post"] / 2 - 1.6, ft + P["joint_g"], H - P["wall_base"] - P["post"] / 2 + 2.6], "top-right corner post"),
        "sled.plate": ("sled", [W - 8.5, 0.0, 42.0], "front plate face"),
        "sled.floor": ("sled", [W * 0.5, ft + 30, P["sled_floor_z"] + P["sled_floor_t"]], "sled floor"),
        "sled.bulkhead": ("sled", [W - 12.0, ft + P["sled_len"] - P["bulk_t"], P["bay_h"] + 14], "rear bulkhead"),
        "sled.slot": ("sled", [P["slot_cx"] - P["slot_land"][0] / 2 + 2.2, 0.0, P["slot_cz"] + 2.6], "slot pocket rim"),
        "screws.head": ("screws", [P["screw_inset"] + 2.0, 0.02, H - P["screw_inset"]], "top-left screw head"),
        "display.glass": ("display", [P["lcd_cx"] + 6, ft - P["lcd_glass"][1], P["lcd_cz"] + 6], "glass"),
        "display.pcb": ("display", [P["lcd_cx"] - 8, ft, P["lcd_cz"] - P["lcd_pcb"][2] / 2 - 2 + 3.5], "display PCB below the glass"),
        "caps.select": ("caps", [P["btn_cx"][1], cap_front, P["btn_cz"][0]], "Select cap (red)"),
        "caps.down": ("caps", [P["btn_cx"][0], cap_front, P["btn_cz"][1]], "Down cap"),
        "switches.tact": ("switches", [P["btn_cx"][0] - 2.5, ft + P["tact"][2] / 2, P["btn_cz"][0] + P["tact"][1] / 2], "top face, upper-left tact switch"),
        "switches.carrier": ("switches", [P["btn_cx"][1] + 8, ft + P["tact"][2] + 0.8, P["btn_cz"][0] + 4], "carrier board edge"),
        "reader.socket": ("reader", [P["slot_cx"] + 2.0, ft + 7.5, z_rdr + P["sd_socket"][2]], "push-push socket"),
        "reader.pcb": ("reader", [P["slot_cx"] + P["reader_pcb"][0] / 2 - 1.5, ft + 18, z_rdr], "reader PCB"),
        "pi.pcb": ("pi", [P["stack_x"] + 6.0, P["stack_y"] + 8, pcb_top], "Pi PCB"),
        "pi.header": ("pi", [P["stack_x"] + 40, P["stack_y"] + P["pi_d"] - 2.7, pcb_top + 8.5], "2x20 header top"),
        "pisugar.body": ("pisugar", [P["stack_x"] + P["pi_w"], P["stack_y"] + 10, P["stack_z"] + P["sugar_t"] * 0.5], "PiSugar side"),
        "diffuser.top": ("diffuser", [W * 0.30, ft + 26, P["bay_h"] + P["diff_t"]], "diffuser top"),
        "safelight.led": ("safelight", [W / 2 - P["px_pitch"] / 2, P["D"] / 2, led_top], "left LED"),
        "safelight.pcb": ("safelight", [W / 2 - (P["px_pitch"] + 10) / 2 + 2, P["D"] / 2 - 5, P["bay_h"] + P["diff_t"] + 1.2], "LED breakout"),
    }


# ---------------------------------------------------------------------------------------
# views: which parts, their offsets (mm, model axes), and the callouts


MOUNTED_ON_SLED = ["display", "caps", "switches", "reader", "pi", "pisugar"]


@dataclass
class View:
    key: str
    title: str
    subtitle: str
    parts: list
    offsets: dict
    callouts: list = field(default_factory=list)   # [(anchor key, label override or None, lane 'L'|'R')]


def views(P):
    zero = {k: [0.0, 0.0, 0.0] for k in PART}
    sled_y = -(P["D"] + 30.0)            # the sled leaves the body through the open front (-Y)
    sled = [0.0, sled_y, 0.0]
    exploded = {k: [0.0, 0.0, 0.0] for k in PART}
    for k in ["sled"] + MOUNTED_ON_SLED:
        exploded[k] = list(sled)
    exploded["screws"] = [0.0, sled_y - 26.0, 0.0]     # as in the CAD's own exploded mode
    exploded["diffuser"] = [0.0, sled_y, 58.0]       # lifted off its rails
    exploded["safelight"] = [0.0, sled_y, 58.0]      # rides on the diffuser
    # electronics detail: illustrative spacing only; every offset is a pure translation
    elec = {
        "display": [0.0, -30.0, 6.0],
        "caps": [0.0, -46.0, -6.0],
        "switches": [0.0, -30.0, -6.0],
        "reader": [-6.0, -30.0, -4.0],
        "pi": [0.0, 24.0, -8.0],
        "pisugar": [0.0, 24.0, -26.0],
        "safelight": [10.0, 10.0, 26.0],
    }
    return [
        View("exploded", "Exploded", "Loaded sled out of the body", list(PART), exploded, [
            ("body.top", None, "R"), ("body.post", None, "R"), ("sled.bulkhead", None, "R"),
            ("diffuser.top", None, "L"), ("safelight.led", None, "L"),
            ("display.glass", None, "L"), ("sled.plate", None, "L"),
            ("screws.head", None, "L"), ("caps.select", None, "L"),
        ]),
        View("assembled", "Assembled", "Sled in, four screws driven", list(PART), zero, [
            ("body.top", None, "R"), ("sled.plate", None, "R"), ("screws.head", None, "L"),
            ("display.glass", None, "L"), ("caps.select", None, "R"),
        ]),
        View("electronics", "Electronics", "Illustrative spacing of the parts the sled carries",
             ["display", "caps", "switches", "reader", "pi", "pisugar", "safelight"],
             {k: elec.get(k, [0.0, 0.0, 0.0]) for k in PART}, [
                 ("safelight.led", None, "L"), ("display.glass", None, "L"), ("display.pcb", None, "L"),
                 ("pi.header", None, "R"), ("pi.pcb", None, "R"), ("pisugar.body", None, "R"),
                 ("caps.select", None, "L"), ("switches.tact", None, "L"),
                 ("reader.socket", None, "L"),
             ]),
    ]
