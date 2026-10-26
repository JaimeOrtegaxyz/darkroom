"""Source meshes for the assembly drawings.

Default path: load `mesh-cache.json.gz`, a lossless, compact copy of per-module STL
exports of cad/darkroom.scad. The cache records the SHA-256 of the CAD file it was
exported from; the build refuses to run if cad/darkroom.scad has changed since.

`seed_cache()` rebuilds the cache from a directory of STL exports (hash-checked).
`export_meshes()` regenerates those STLs with OpenSCAD. It is never called by the
default build; run it only with `build.py --export-meshes` on a trusted OpenSCAD.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from scad_params import sha256

CACHE_FORMAT = "darkroom-mesh-cache/1"

# mesh name -> OpenSCAD module call in cad/darkroom.scad (exported with -D 'part="none"')
MODULES = {
    "darkroom-sleeve": "sleeve_solid()",
    "darkroom-sled": "sled()",  # front_plate() + sled_frame(): one integral part
    "screws": "screws()",
    "display": "lcd_module()",
    "controls": "buttons()",
    "reader": "reader_board()",
    "pi": "pi_stack()",
    "diffuser": "diffuser()",
    "safelight": "safelight()",
}

VERTEX = re.compile(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)")


def parse_stl(data: bytes) -> np.ndarray:
    """Triangles (n, 3, 3) float64 from ASCII or binary STL, in file order."""
    if not data.lstrip().startswith(b"solid") or b"facet" not in data[:2000]:
        n = int.from_bytes(data[80:84], "little")
        rec = np.frombuffer(data[84:84 + 50 * n], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", 9), ("a", "<u2")]))
        return rec["v"].astype(np.float64).reshape(-1, 3, 3)
    vals = VERTEX.findall(data)
    return np.array(vals, dtype=np.float64).reshape(-1, 3, 3)


def weld(tris: np.ndarray):
    verts, inv = np.unique(tris.reshape(-1, 3), axis=0, return_inverse=True)
    return verts, inv.reshape(-1, 3)


def seed_cache(stl_dir: Path, cad: Path, cache: Path, producer: str) -> dict:
    meshes = {}
    for name, module in MODULES.items():
        path = stl_dir / f"{name}.stl"
        data = path.read_bytes()
        verts, faces = weld(parse_stl(data))
        meshes[name] = {
            "module": module,
            "stl_sha256": hashlib.sha256(data).hexdigest(),
            "triangles": int(len(faces)),
            "vertices": verts.tolist(),
            "faces": faces.tolist(),
        }
    doc = {
        "format": CACHE_FORMAT,
        "cad_path": "cad/darkroom.scad",
        "cad_sha256": sha256(cad),
        "producer": producer,
        "export": "openscad -D 'part=\"none\"' on a wrapper `include <cad/darkroom.scad>` + the module call",
        "meshes": meshes,
    }
    raw = json.dumps(doc, separators=(",", ":"), sort_keys=True).encode()
    cache.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    return doc


def load_cache(cache: Path, cad: Path) -> dict:
    doc = json.loads(gzip.decompress(cache.read_bytes()))
    if doc.get("format") != CACHE_FORMAT:
        raise SystemExit(f"{cache.name}: unknown cache format")
    actual = sha256(cad)
    if doc["cad_sha256"] != actual:
        raise SystemExit(
            f"cad/darkroom.scad changed (sha256 {actual[:12]}…, cache built from {doc['cad_sha256'][:12]}…).\n"
            "The cached meshes no longer describe the CAD. Re-export them on a trusted OpenSCAD install:\n"
            "  python build.py --export-meshes")
    if set(doc["meshes"]) != set(MODULES):
        raise SystemExit("mesh cache inventory does not match MODULES")
    out = {}
    for name, m in doc["meshes"].items():
        if m["module"] != MODULES[name]:
            raise SystemExit(f"{name}: cache module {m['module']} != {MODULES[name]}")
        v = np.array(m["vertices"], dtype=np.float64)
        f = np.array(m["faces"], dtype=np.int64)
        out[name] = v[f]
    return out, doc


def export_meshes(cad: Path, out_dir: Path, openscad: str = "openscad") -> None:
    """Dormant: regenerate per-module STLs from the CAD. Not used by the default build."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, module in MODULES.items():
        wrapper = out_dir / f"{name}.scad"
        wrapper.write_text(f"include <{cad.resolve()}>\n{module};\n")
        subprocess.run([openscad, "-D", 'part="none"', "-o", str(out_dir / f"{name}.stl"), str(wrapper)], check=True)
