"""Render one prompt from PROMPTS.md through fal.ai (Nano Banana Pro by default).

  python3 fal_render.py <tag> "<section heading>" <screen png> <ref png>... [--res 4K] [--ar 16:9]

Reads FAL_API_KEY from the repo's .env. Reuses the shared brief, the task section and
the SCREEN CONTENT line from PROMPTS.md so Codex and fal renders are apples to apples.
Output: ai/fal/<tag>-<res>.png
"""
import base64, json, os, re, sys, time, urllib.request, mimetypes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MODEL = os.environ.get("FAL_MODEL", "fal-ai/nano-banana-pro/edit")  # also: fal-ai/gpt-image-1.5/edit, fal-ai/bytedance/seedream/v4.5/edit

def env_key():
    for line in open(os.path.join(ROOT, ".env")):
        if line.startswith("FAL_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("FAL_API_KEY not in .env")

def prompt_parts(heading):
    md = open(os.path.join(HERE, "PROMPTS.md")).read()
    brief = re.search(r"^## Shared brief.*?\n(.*?)(?=^## )", md, re.S | re.M).group(1).strip()
    task = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", md, re.S | re.M).group(1).strip()
    screen = re.search(r"^> (SCREEN CONTENT:.*)$", md, re.M).group(1)
    return brief, task, screen

def data_uri(path):
    mt = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mt};base64," + base64.b64encode(open(path, "rb").read()).decode()

def main(argv):
    res, ar = "4K", "16:9"
    if "--res" in argv: i = argv.index("--res"); res = argv[i+1]; del argv[i:i+2]
    if "--ar" in argv: i = argv.index("--ar"); ar = argv[i+1]; del argv[i:i+2]
    tag, heading, screen_png, *refs = argv
    brief, task, screen = prompt_parts(heading)
    prompt = (f"{brief}\n\nTASK: {task}\n\n{screen}\n\n"
              f"Reference 1 is the primary composition guide; the other references are for detail; "
              f"the LAST image is the screen content. Output one image, landscape {ar}.")
    images = [data_uri(os.path.join(HERE, "ref", r)) for r in refs] + [data_uri(os.path.join(HERE, "screens", screen_png))]
    body = {"prompt": prompt, "image_urls": images, "num_images": 1}
    if "nano-banana" in MODEL: body.update(resolution=res, aspect_ratio=ar, output_format="png")
    elif "gpt-image" in MODEL: body.update(image_size="1536x1024", quality="high")
    elif "seedream" in MODEL: body.update(image_size={"width": 4096, "height": 2304})
    else: body.update(aspect_ratio=ar)
    key = env_key(); hdr = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    req = urllib.request.Request(f"https://queue.fal.run/{MODEL}", data=json.dumps(body).encode(), headers=hdr)
    sub = json.load(urllib.request.urlopen(req))
    status_url, resp_url = sub["status_url"], sub["response_url"]
    print("queued", sub.get("request_id"), flush=True)
    t0 = time.time()
    while True:
        st = json.load(urllib.request.urlopen(urllib.request.Request(status_url, headers=hdr)))
        if st["status"] == "COMPLETED": break
        if st["status"] not in ("IN_QUEUE", "IN_PROGRESS"): sys.exit(f"fal status: {st}")
        time.sleep(4)
    out = json.load(urllib.request.urlopen(urllib.request.Request(resp_url, headers=hdr)))
    print("done in %.0fs" % (time.time() - t0), out.get("description", "")[:200], flush=True)
    os.makedirs(os.path.join(HERE, "ai", "fal"), exist_ok=True)
    for n, im in enumerate(out["images"]):
        dst = os.path.join(HERE, "ai", "fal", f"{tag}-{MODEL.split('/')[1] if MODEL.count('/')==1 else MODEL.split('/')[-2]}{'' if n == 0 else n}.png")
        urllib.request.urlretrieve(im["url"], dst)
        print(dst, im.get("width"), "x", im.get("height"))

if __name__ == "__main__":
    main(sys.argv[1:])
