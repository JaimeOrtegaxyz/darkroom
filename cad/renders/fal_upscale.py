"""Upscale / re-resolve an approved render through fal.ai. Three routes:

  python3 fal_upscale.py topaz   <in.png> <out.png> [factor=1.25] [creativity=8]   # Topaz Creative (Bloom 2), creativity 1-9
  python3 fal_upscale.py redefine <in.png> <out.png> [factor=1.25] [creativity=5]  # Topaz Redefine (photo upscaler), creativity 1-6
  python3 fal_upscale.py banana  <in.png> <out.png> <screen.png>                    # Nano Banana Pro 4K re-render of the photo
  python3 fal_upscale.py clarity <in.png> <out.png> [factor=2] [creativity=0.3]     # Clarity (SD tile) upscaler, low creativity

Reads FAL_API_KEY from the repo .env. Prompts are layout-neutral: the photo itself is the layout reference.
"""
import base64, json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
key = [l.split("=",1)[1].strip().strip('"') for l in open(os.path.join(ROOT, ".env")) if l.startswith("FAL_API_KEY=")][0]
hdr = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
uri = lambda p: "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
LOOK = ("A premium studio product photograph of a small matte black cube device with a graphite front plate, flush black screws, "
        "round soft-touch rubber buttons (one red), a tiny glossy screen, standing on dark split-face slate against a charcoal "
        "backdrop, very low key. Fine real-material detail: rubber grain on the caps, matte micro-texture on the plastic, crisp "
        "machined screw sockets, stone texture. Photographic, not illustrated.")
mode, src, dst, *rest = sys.argv[1:]
if mode == "topaz":
    factor = float(rest[0]) if rest else 1.25; creativity = int(rest[1]) if len(rest) > 1 else 8
    model = "topaz/upscale/image/creative"
    body = {"image_url": uri(src), "model": "Bloom 2", "upscale_factor": factor, "creativity": creativity,
            "color_preservation": True, "autoprompt": True, "output_format": "png"}
elif mode == "redefine":
    factor = float(rest[0]) if rest else 1.25; creativity = int(rest[1]) if len(rest) > 1 else 5
    model = "fal-ai/topaz/upscale/image"
    body = {"image_url": uri(src), "model": "Redefine", "upscale_factor": factor, "creativity": creativity, "texture": 3,
            "prompt": LOOK, "autoprompt": False, "face_enhancement": False, "output_format": "png"}
elif mode == "banana":
    screen = rest[0] if rest else None      # omit for views where the screen is not visible (rear)
    model = "fal-ai/nano-banana-pro/edit"
    body = {"prompt": ("Reproduce the FIRST image exactly — same composition, same camera, same lighting, same object, every control "
                       "in the same place and shape, same slate slab and backdrop, same materials — as a flawless 4K studio photograph. "
                       "Add only real photographic detail: fine rubber grain on the caps, matte micro-texture on the plastic, crisp "
                       "screw sockets, stone texture. "
                       + ("The LAST image is the exact screen content; reproduce it pixel for pixel. " if screen else
                          "No screen is visible from this angle; do not add one. ")
                       + "Change nothing else. Landscape 16:9."),
            "image_urls": [uri(src)] + ([uri(screen)] if screen else []), "resolution": "4K", "aspect_ratio": "16:9", "output_format": "png"}
elif mode == "clarity":
    factor = float(rest[0]) if rest else 2; creativity = float(rest[1]) if len(rest) > 1 else 0.3
    model = "fal-ai/clarity-upscaler"
    body = {"image_url": uri(src), "upscale_factor": factor, "creativity": creativity, "resemblance": 0.75, "guidance_scale": 4,
            "num_inference_steps": 20, "prompt": LOOK, "enable_safety_checker": False}
else: sys.exit("mode: topaz | redefine | banana | clarity")
sub = json.load(urllib.request.urlopen(urllib.request.Request(f"https://queue.fal.run/{model}", data=json.dumps(body).encode(), headers=hdr)))
t0 = time.time()
while True:
    st = json.load(urllib.request.urlopen(urllib.request.Request(sub["status_url"], headers=hdr)))
    if st["status"] == "COMPLETED": break
    if st["status"] not in ("IN_QUEUE", "IN_PROGRESS"): sys.exit(str(st))
    time.sleep(4)
out = json.load(urllib.request.urlopen(urllib.request.Request(sub["response_url"], headers=hdr)))
im = out["images"][0] if "images" in out else out["image"]
urllib.request.urlretrieve(im["url"], dst); print(mode, "done in %.0fs" % (time.time()-t0), dst, im.get("width"), "x", im.get("height"))
