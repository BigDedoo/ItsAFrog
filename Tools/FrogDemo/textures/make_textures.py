#!/usr/bin/env python3
"""Generate tileable hand-painted ground textures with Meshy text-to-image.

For each texture: one Meshy image (raw/<name>_<n>.png), then a seamless
version with a wrap-blend, plus a normal and a roughness map derived from it:
  <name>_color.png, <name>_normal.png (DirectX green-down, as Unreal expects), <name>_rough.png
Usage: python3 make_textures.py generate [names...]   # spend credits
       python3 make_textures.py process <name> <raw.png>
"""
import json
import os
import sys
import time
import urllib.request

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.meshy.ai/openapi/v1/text-to-image"
COMMON = ("seamless tileable texture, orthographic view straight down at the ground, flat even lighting, "
          "no cast shadows, no perspective, no horizon, no border, fills the frame edge to edge, "
          "stylized hand-painted game texture like a cozy painted fantasy village game, soft smooth painterly brush strokes, low contrast")
PROMPTS = {
    "grass": "Top-down ground texture of a short stylized grass lawn, gentle variation between fresh mid green, "
             "warm yellow-green patches and cool blue-green, short blades suggested by small soft strokes, "
             "a few tiny pale flowers, " + COMMON,
    "dirt": "Top-down ground texture of a stylized packed dirt path, warm earthy brown with soft mauve and ochre tones, "
            "a few small rounded flat pebbles and tiny stray grass blades, " + COMMON,
}
ROUGH = {"grass": (0.85, 0.12), "dirt": (0.9, 0.1)}  # base, variation


def call(method, url, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def generate(name, n, model="nano-banana-pro"):
    tid = call("POST", API, {"ai_model": model, "prompt": PROMPTS[name], "aspect_ratio": "1:1"})["result"]
    while True:
        t = call("GET", f"{API}/{tid}")
        if t["status"] in ("SUCCEEDED", "FAILED", "CANCELED"):
            break
        time.sleep(5)
    if t["status"] != "SUCCEEDED":
        raise RuntimeError(f"{name}: {t.get('task_error')}")
    out = os.path.join(HERE, "raw", f"{name}_{n}.png")
    urllib.request.urlretrieve(t["image_urls"][0], out)
    print(name, n, "->", out, t.get("consumed_credits"), "credits")
    return out


def make_seamless(a):
    """Cross-fade the image with a half-offset copy of itself; the copy's edges wrap cleanly."""
    h, w = a.shape[:2]
    rolled = np.roll(a, (h // 2, w // 2), (0, 1))
    y = np.minimum(np.arange(h), h - 1 - np.arange(h)) / (h / 2)
    x = np.minimum(np.arange(w), w - 1 - np.arange(w)) / (w / 2)
    ramp = lambda v: np.clip((v - 0.0) / 0.45, 0, 1) ** 1.5  # 0 at the border, 1 from ~22% in
    m = np.minimum.outer(ramp(y), ramp(x))
    # Bias the blend by brightness so strokes on top win instead of ghosting into each other.
    la, lr = a.mean(2), rolled.mean(2)
    m = np.clip(m + (la - lr) * 0.6 * (m * (1 - m)) * 4, 0, 1)[..., None]
    return a * m + rolled * (1 - m)


def blur_wrap(g, r):
    """Gaussian blur through the FFT, which wraps at the edges so the result still tiles."""
    h, w = g.shape
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
    k = np.exp(-2 * (np.pi * r) ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(g) * k)).astype(np.float32)


def process(name, raw):
    a = np.asarray(Image.open(raw).convert("RGB").resize((1024, 1024), Image.LANCZOS), dtype=np.float32) / 255
    s = make_seamless(a)
    Image.fromarray((s * 255).round().astype(np.uint8)).save(os.path.join(HERE, f"{name}_color.png"))
    lum = s @ np.array([0.3, 0.59, 0.11], dtype=np.float32)
    height = blur_wrap(lum, 1.5)
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 4.0
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 4.0
    n = np.dstack([-dx, dy, np.ones_like(dx)])  # DirectX convention (green down), what Unreal expects
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    Image.fromarray(((n * 0.5 + 0.5) * 255).round().astype(np.uint8)).save(os.path.join(HERE, f"{name}_normal.png"))
    base, var = ROUGH[name]
    r = np.clip(base + (0.5 - blur_wrap(lum, 2)) * var * 2, 0, 1)
    Image.fromarray((r * 255).round().astype(np.uint8), mode="L").save(os.path.join(HERE, f"{name}_rough.png"))
    tiled = np.tile(s, (2, 2, 1))
    Image.fromarray((tiled * 255).round().astype(np.uint8)).resize((1024, 1024)).save(os.path.join(HERE, f"{name}_tiled2x2.png"))
    print("processed", name)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "raw"), exist_ok=True)
    if sys.argv[1] == "generate":
        for name in sys.argv[2:] or PROMPTS:
            for n in (1, 2):
                generate(name, n)
    else:
        process(sys.argv[2], sys.argv[3])
