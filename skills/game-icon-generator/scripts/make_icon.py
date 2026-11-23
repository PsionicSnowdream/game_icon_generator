#!/usr/bin/env python3
"""Make game icons with Pollinations and cut the background out.

One icon:
    python make_icon.py "a red health potion" -o icons/potion.png

A set (JSON object, name -> subject):
    python make_icon.py --batch icons.json -d icons/

The key is read from POLLINATIONS_API_KEY (or --key-file). Needs Pillow and numpy.
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://gen.pollinations.ai"
MODEL = "microsoft/mai-image-2.7-flash"
MIN_SIDE = 768  # this model refuses smaller images: we ask for 768 and shrink afterwards
STYLE = (
    "cute cartoon game icon, chunky shapes, thick dark brown outline, vibrant saturated colors, "
    "soft cel shading with a glossy white highlight, one single object in the center, "
    "floating in mid air, no shadow, no ground, solid flat pure green background, no text, no letters, no border"
)


def load_key(key_file):
    if key_file:
        return Path(key_file).read_text(encoding="utf-8").strip()
    key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    if not key:
        sys.exit("No API key. Set POLLINATIONS_API_KEY or pass --key-file (keys: https://enter.pollinations.ai/keys).")
    return key


def fetch(prompt, key, seed, model, retries=3):
    query = {"model": model, "width": MIN_SIDE, "height": MIN_SIDE, "nologo": "true"}
    if seed is not None:
        query["seed"] = seed
    url = f"{BASE}/image/{urllib.parse.quote(prompt, safe='')}?{urllib.parse.urlencode(query)}"
    headers = {"Authorization": f"Bearer {key}", "User-Agent": "game-icon-generator"}
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(8 * (attempt + 1))  # the model allows about 12 requests a minute
                continue
            sys.exit(f"HTTP {e.code}: {e.read()[:300].decode('utf-8', 'replace')}")
    sys.exit("gave up after retries")


def cut_background(img, tol=70.0):
    """Flood-fill the flat background from the image edges. Colors inside the object stay, the edge is softened."""
    import numpy as np
    from PIL import Image

    arr = np.array(img.convert("RGBA")).astype(np.float32)
    h, w = arr.shape[:2]
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])[:, :3]
    bg = np.median(border, axis=0)
    dist = np.sqrt(((arr[:, :, :3] - bg) ** 2).sum(axis=2))
    lo, hi = tol * 0.6, tol
    seen = np.zeros((h, w), dtype=bool)
    queue = deque()
    for x in range(w):
        for y in (0, h - 1):
            if dist[y, x] < hi:
                seen[y, x] = True
                queue.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if dist[y, x] < hi and not seen[y, x]:
                seen[y, x] = True
                queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and dist[ny, nx] < hi:
                seen[ny, nx] = True
                queue.append((ny, nx))
    alpha = np.full((h, w), 255, dtype=np.float32)
    soft = np.clip((dist - lo) / (hi - lo), 0, 1) * 255
    alpha[seen] = soft[seen]
    edge = seen & (alpha > 0) & (alpha < 255)
    a01 = np.clip(alpha / 255.0, 0.05, 1)
    for c in range(3):  # take the background color out of the soft edge
        channel = arr[:, :, c]
        channel[edge] = np.clip((channel[edge] - bg[c] * (1 - a01[edge])) / a01[edge], 0, 255)
    arr[:, :, 3] = alpha
    out = Image.fromarray(arr.astype(np.uint8), "RGBA")
    box = out.getbbox()
    if box:  # crop to the object and put it on a square canvas with a little margin
        out = out.crop(box)
        side = int(max(out.size) * 1.08)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(out, ((side - out.size[0]) // 2, (side - out.size[1]) // 2), out)
        out = canvas
    return out


def make(subject, path, key, size, seed, style, model, keep_background, force):
    from PIL import Image

    path = Path(path)
    if path.exists() and not force:
        return f"{path}: exists, skipped"
    raw = fetch(f"{subject}, {style}", key, seed, model)
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    if not keep_background:
        img = cut_background(img)
    img = img.resize((size, size), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return f"{path}: ok"


def main():
    ap = argparse.ArgumentParser(description="Make game icons with Pollinations.")
    ap.add_argument("subject", nargs="?", help="what to draw, e.g. 'a red health potion'")
    ap.add_argument("-o", "--out", help="output PNG for a single icon")
    ap.add_argument("--batch", help="JSON file: {name: subject}")
    ap.add_argument("-d", "--dir", default="icons", help="output folder for --batch (default: icons)")
    ap.add_argument("--size", type=int, default=256, help="final side in pixels (default: 256)")
    ap.add_argument("--seed", type=int, help="same seed + same prompt gives the same icon")
    ap.add_argument("--style", default=STYLE, help="style text added after the subject")
    ap.add_argument("--style-file", help="read the style text from a file")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--keep-background", action="store_true", help="skip the background cut-out")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--workers", type=int, default=3, help="parallel requests for --batch (default: 3)")
    ap.add_argument("--key-file", help="file with the API key (otherwise POLLINATIONS_API_KEY)")
    a = ap.parse_args()

    style = Path(a.style_file).read_text(encoding="utf-8").strip() if a.style_file else a.style
    key = load_key(a.key_file)
    if a.batch:
        subjects = json.loads(Path(a.batch).read_text(encoding="utf-8"))
        jobs = [(s, Path(a.dir) / f"{name}.png") for name, s in subjects.items()]
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            for line in pool.map(lambda j: make(j[0], j[1], key, a.size, a.seed, style, a.model, a.keep_background, a.force), jobs):
                print(line, flush=True)
    elif a.subject and a.out:
        print(make(a.subject, a.out, key, a.size, a.seed, style, a.model, a.keep_background, a.force))
    else:
        ap.error("give a subject and -o, or --batch")


if __name__ == "__main__":
    main()
