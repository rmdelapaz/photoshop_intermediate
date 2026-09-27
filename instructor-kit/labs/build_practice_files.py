#!/usr/bin/env python3
"""Generate every synthetic practice file for the Photoshop Intermediate course labs.

Each lab README (labs/module-N/README.md) has a "Practice file specs" section; this
script implements those specs one function per file, grouped by module, and writes
the results into labs/module-N/practice/. Everything is drawn from scratch (no
photographs, no stock), so the output is safe to hand to enrolled learners.

Dependencies
    Python 3.9+
    Pillow >= 10.1   (PIL: Image, ImageDraw, ImageFilter, ImageFont, ImageCms, ImageEnhance)
    numpy  >= 1.20
    Fonts: DejaVu Sans / DejaVu Sans Bold if installed (Linux: fonts-dejavu-core);
           otherwise a common system sans (Arial / Helvetica) or Pillow's built-in font.

Usage (from instructor-kit/, or from anywhere; paths resolve from this file)
    python3 labs/build_practice_files.py              # build all modules
    python3 labs/build_practice_files.py --module 4   # build one module (repeatable)

Output is deterministic (fixed seeds per file) and idempotent: running it again
overwrites the same files with identical pixels. Each written file is printed.
"""

from __future__ import annotations

import argparse
import math
import sys
import zlib
from collections import namedtuple
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageEnhance, ImageFilter, ImageFont

LABS = Path(__file__).resolve().parent
KIT = LABS.parent
F32 = np.float32


def _fixed_srgb_icc() -> bytes:
    """LittleCMS's built-in sRGB profile, with its creation timestamp pinned (and the
    optional profile ID cleared) so that regenerated files are byte-identical."""
    icc = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    icc[24:36] = bytes.fromhex("07ea00010001000000000000")      # 2026-01-01 00:00:00
    icc[84:100] = bytes(16)
    return bytes(icc)


SRGB_ICC = _fixed_srgb_icc()
WRITTEN: list[Path] = []

# --------------------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------------------


def rng(name: str) -> np.random.Generator:
    """A fixed, per-file random generator (seed derived from the file's name)."""
    return np.random.default_rng(zlib.crc32(name.encode("utf-8")))


def hexc(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    return tuple(float(x) + (float(y) - float(x)) * t for x, y in zip(a, b))


def out_path(module: int, name: str, folder: str = "practice") -> Path:
    p = LABS / f"module-{module}" / folder / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _record(p: Path) -> None:
    WRITTEN.append(p)
    try:
        rel = p.relative_to(KIT)
    except ValueError:
        rel = p
    print(f"  wrote {rel}  ({p.stat().st_size / 1024:,.0f} KB)")


def to_u8(a: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(a), 0, 255).astype(np.uint8)


def save_jpg(img, module, name, quality=90, icc=True, dpi=72, subsampling=None):
    """Save an RGB float array / PIL image as a baseline JPEG (no EXIF)."""
    if isinstance(img, np.ndarray):
        img = Image.fromarray(to_u8(img))
    p = out_path(module, name)
    kw = dict(quality=quality, dpi=(dpi, dpi), optimize=True)
    if subsampling is not None:
        kw["subsampling"] = subsampling
    if icc:
        kw["icc_profile"] = SRGB_ICC
    img.save(p, "JPEG", **kw)
    _record(p)


def save_png(img, module, name, icc=True, dpi=72, folder="practice"):
    if isinstance(img, np.ndarray):
        img = Image.fromarray(to_u8(img))
    p = out_path(module, name, folder)
    kw = dict(optimize=True, dpi=(dpi, dpi))
    if icc:
        kw["icc_profile"] = SRGB_ICC
    img.save(p, "PNG", **kw)
    _record(p)


def save_txt(text: str, module: int, name: str) -> None:
    p = out_path(module, name)
    p.write_text(text, encoding="utf-8", newline="\n")
    _record(p)


# ---- fonts ---------------------------------------------------------------------------

_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF",
    "/usr/local/share/fonts", "/Library/Fonts", "/System/Library/Fonts/Supplemental",
    "C:/Windows/Fonts",
]


@lru_cache(maxsize=None)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf", "Helvetica-Bold.ttf"]
             if bold else ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf", "Helvetica.ttf"])
    for n in names:
        for cand in [n] + [f"{d}/{n}" for d in _FONT_DIRS]:
            try:
                return ImageFont.truetype(cand, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


# ---- gradients and noise -------------------------------------------------------------

def _interp(t: np.ndarray, stops) -> np.ndarray:
    pos = [s[0] for s in stops]
    cols = np.array([s[1] if not isinstance(s[1], str) else hexc(s[1]) for s in stops], float)
    return np.stack([np.interp(t, pos, cols[:, c]) for c in range(3)], -1).astype(F32)


def vgrad(w, h, stops, y0=0.0, y1=None):
    """Vertical gradient (h, w, 3). stops = [(t, color), ...] with t in 0..1 over y0..y1."""
    y1 = h if y1 is None else y1
    t = np.clip((np.arange(h, dtype=F32) + 0.5 - y0) / (y1 - y0), 0, 1)
    col = _interp(t, stops)
    return np.ascontiguousarray(np.broadcast_to(col[:, None, :], (h, w, 3)))


def hgrad(w, h, stops, x0=0.0, x1=None):
    x1 = w if x1 is None else x1
    t = np.clip((np.arange(w, dtype=F32) + 0.5 - x0) / (x1 - x0), 0, 1)
    col = _interp(t, stops)
    return np.ascontiguousarray(np.broadcast_to(col[None, :, :], (h, w, 3)))


def solid(w, h, color):
    c = hexc(color) if isinstance(color, str) else color
    return np.ones((h, w, 3), F32) * np.array(c, F32)


def coords(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    return xx + 0.5, yy + 0.5


def add_noise(img, sigma, r, mono=False, sigma_map=None):
    """Per-pixel Gaussian noise; mono=True adds the same value to R, G and B."""
    h, w = img.shape[:2]
    n = r.standard_normal((h, w, 1) if mono else (h, w, 3), dtype=F32) * F32(sigma)
    if sigma_map is not None:
        n = n * sigma_map[..., None]
    img += n
    np.clip(img, 0, 255, out=img)
    return img


def add_uniform_noise(img, amp, r):
    img += r.integers(-amp, amp + 1, img.shape).astype(F32)
    np.clip(img, 0, 255, out=img)
    return img


def smooth_wave(xs, base, amp, parts, phase=0.0):
    """Sum of sines normalised to +/- amp. parts = [(period, weight, phase), ...]."""
    y = np.zeros_like(xs, dtype=float)
    tw = sum(p[1] for p in parts)
    for period, weight, ph in parts:
        y += weight * np.sin(2 * np.pi * xs / period + ph + phase)
    return base + amp * y / tw


def blur_img(img: np.ndarray, radius: float) -> np.ndarray:
    return np.asarray(Image.fromarray(to_u8(img)).filter(ImageFilter.GaussianBlur(radius)), F32)


def quad_bezier(p0, p1, p2, n=64):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = (np.array(p, float) for p in (p0, p1, p2))
    pts = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
    return [tuple(p) for p in pts]


def convex_hull(points):
    pts = sorted(set((float(x), float(y)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def rand_color_near(r, c, spread):
    return tuple(int(np.clip(v + r.integers(-spread, spread + 1), 0, 255)) for v in c)


# --------------------------------------------------------------------------------------
# Supersampled drawing: Canvas -> Mask (alpha only) or Layer (RGBA), positioned anywhere
# --------------------------------------------------------------------------------------

Mask = namedtuple("Mask", "x y a")            # a: (h, w) float 0..1, top-left at (x, y)
Layer = namedtuple("Layer", "x y rgb a")      # rgb: (h, w, 3) float, a: (h, w) float 0..1


class Canvas:
    """A supersampled drawing surface in global pixel coordinates.

    box = (x0, y0, x1, y1) is the region covered (plus `pad` on every side, so later
    blurs are not clipped). mode "L" draws coverage/alpha; mode "RGBA" draws colored
    shapes (later shapes replace earlier ones). Downsampling with a box filter gives
    clean anti-aliasing.
    """

    def __init__(self, box, ss=3, mode="L", pad=0, resample=Image.BOX):
        self.resample = resample
        x0, y0, x1, y1 = box
        self.x0 = int(math.floor(x0 - pad))
        self.y0 = int(math.floor(y0 - pad))
        self.w = int(math.ceil(x1 + pad)) - self.x0
        self.h = int(math.ceil(y1 + pad)) - self.y0
        self.ss = ss
        self.mode = mode
        self.im = Image.new(mode, (self.w * ss, self.h * ss), 0 if mode == "L" else (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    # coordinate helpers
    def P(self, x, y):
        return ((x - self.x0) * self.ss, (y - self.y0) * self.ss)

    def B(self, x0, y0, x1, y1):
        a, b = self.P(x0, y0)
        c, d = self.P(x1, y1)
        return [min(a, c), min(b, d), max(a, c), max(b, d)]

    def _f(self, fill):
        if self.mode == "L":
            return int(round(fill if fill is not None else 255))
        if isinstance(fill, str):
            fill = hexc(fill)
        fill = tuple(int(round(v)) for v in fill)
        return fill if len(fill) == 4 else fill + (255,)

    # primitives
    def ellipse(self, cx, cy, rx, ry, fill=255):
        self.d.ellipse(self.B(cx - rx, cy - ry, cx + rx, cy + ry), fill=self._f(fill))

    def circle(self, cx, cy, r, fill=255):
        self.ellipse(cx, cy, r, r, fill)

    def rect(self, x0, y0, x1, y1, fill=255):
        self.d.rectangle(self.B(x0, y0, x1, y1), fill=self._f(fill))

    def rrect(self, x0, y0, x1, y1, r, fill=255):
        self.d.rounded_rectangle(self.B(x0, y0, x1, y1), radius=r * self.ss, fill=self._f(fill))

    def poly(self, pts, fill=255):
        self.d.polygon([self.P(x, y) for x, y in pts], fill=self._f(fill))

    def pieslice(self, cx, cy, r, a0, a1, fill=255):
        self.d.pieslice(self.B(cx - r, cy - r, cx + r, cy + r), a0, a1, fill=self._f(fill))

    def line(self, pts, width, fill=255, round_caps=False):
        w = max(1, int(round(width * self.ss)))
        self.d.line([self.P(x, y) for x, y in pts], fill=self._f(fill), width=w, joint="curve")
        if round_caps:
            for x, y in (pts[0], pts[-1]):
                self.circle(x, y, width / 2, fill)

    def text(self, x, y, s, fnt_size, bold=False, fill=255, anchor="la", **kw):
        f = font(int(round(fnt_size * self.ss)), bold)
        self.d.text(self.P(x, y), s, font=f, fill=self._f(fill), anchor=anchor, **kw)

    # results
    def _down(self):
        im = self.im
        if self.ss > 1:
            im = im.resize((self.w, self.h), self.resample)
        return im

    def mask(self, blur=0.0) -> Mask:
        im = self._down()
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        return Mask(self.x0, self.y0, np.asarray(im, F32) / 255.0)

    def layer(self, blur=0.0) -> Layer:
        im = self._down()  # Pillow premultiplies RGBA when resampling
        if blur:
            im = im.convert("RGBa").filter(ImageFilter.GaussianBlur(blur)).convert("RGBA")
        a = np.asarray(im, F32)
        return Layer(self.x0, self.y0, a[..., :3].copy(), a[..., 3] / 255.0)


def _slices(base_shape, x, y, shp):
    H, W = base_shape[:2]
    h, w = shp[:2]
    bx0, by0 = max(x, 0), max(y, 0)
    bx1, by1 = min(x + w, W), min(y + h, H)
    if bx0 >= bx1 or by0 >= by1:
        return None
    return ((slice(by0, by1), slice(bx0, bx1)),
            (slice(by0 - y, by1 - y), slice(bx0 - x, bx1 - x)))


def _color_for(color, base, m, sb, sm):
    if isinstance(color, np.ndarray) and color.ndim == 3:
        if color.shape[:2] == base.shape[:2]:
            return color[sb]
        return color[sm]
    c = hexc(color) if isinstance(color, str) else color
    return np.array(c, F32)


def paint(base, m: Mask, color, opacity=1.0):
    """Composite a flat color (or a color array) through a mask."""
    s = _slices(base.shape, m.x, m.y, m.a.shape)
    if s is None:
        return
    sb, sm = s
    a = (m.a[sm] * opacity)[..., None]
    base[sb] = base[sb] * (1 - a) + _color_for(color, base, m, sb, sm) * a


def darken(base, m: Mask, amount):
    """Multiply toward black: amount 0.6 = '60 % black' shadow."""
    s = _slices(base.shape, m.x, m.y, m.a.shape)
    if s is None:
        return
    sb, sm = s
    base[sb] = base[sb] * (1 - (m.a[sm] * amount)[..., None])


def over(base, L: Layer, opacity=1.0):
    s = _slices(base.shape, L.x, L.y, L.a.shape)
    if s is None:
        return
    sb, sm = s
    a = (L.a[sm] * opacity)[..., None]
    base[sb] = base[sb] * (1 - a) + L.rgb[sm] * a


def full_mask(m: Mask, w, h) -> np.ndarray:
    out = np.zeros((h, w), F32)
    s = _slices((h, w), m.x, m.y, m.a.shape)
    if s:
        out[s[0]] = m.a[s[1]]
    return out


def erode(a: np.ndarray, px: int) -> np.ndarray:
    im = Image.fromarray(to_u8(a * 255)).filter(ImageFilter.MinFilter(2 * px + 1))
    return np.asarray(im, F32) / 255.0


def soft_blob(c: Canvas, r, cx, cy, width, height, n=(3, 5), fill=255):
    """A cloud/leaf-like blob made of overlapping ellipses inside width x height."""
    for _ in range(int(r.integers(n[0], n[1] + 1))):
        ex = cx + r.uniform(-0.3, 0.3) * width
        ey = cy + r.uniform(-0.25, 0.2) * height
        c.ellipse(ex, ey, r.uniform(0.25, 0.45) * width, r.uniform(0.3, 0.5) * height, fill)


# ======================================================================================
# Module 1: Advanced Selection & Masking
# ======================================================================================

# ======================================================================================
# Module 1 · Advanced Selection & Masking (Session 1): L01–L03
# ======================================================================================
#
#   l01-high-contrast-landscape.jpg   L01 guided build: near-blown sky over a dark valley
#   l01-still-life-window-light.jpg   L01 solo: window-lit still life (glow + midtones)
#   l02-bare-tree-sky.jpg             L02 guided build: bare tree, Blue channel separates
#   l02-new-sky.jpg                   L02 guided build: replacement sunset sky
#   l02-grunge-texture.jpg            L02 Step 4: dark texture on white (Blend-If)
#   l02-fireworks-on-black.jpg        L02 solo: bright bursts on black (Blend-If darks)
#   l03-curly-hair-portrait.jpg       L03 guided build: curly hair + flyaways on teal
#   l03-new-background.jpg            L03 guided build: warm bokeh backdrop
#   l03-hair-busy-background.jpg      L03 solo: same sitter, auburn hair, busy foliage
#   instructor/l03-hair-cutout-reference.png   catch-up cutout (RGBA, no fringe)

_M1_PW, _M1_PH = 1600, 2000          # portrait size (L03)


def _m1_full(box, draw, W, H, ss=3, blur=0.0, pad=6):
    """Draw with a supersampled L canvas; return a full-frame 0..1 mask."""
    c = Canvas(box, ss=ss, pad=pad)
    draw(c)
    return full_mask(c.mask(blur), W, H)


def _m1_paint_full(img, a, color, opacity=1.0):
    paint(img, Mask(0, 0, a), color, opacity)


def _m1_lowfreq(r, w, h, cell, lo=0.0, hi=1.0):
    """Smooth random field (h, w) in lo..hi, feature size about `cell` px."""
    sw, sh = max(2, w // cell + 2), max(2, h // cell + 2)
    small = (r.random((sh, sw)) * 255).astype(np.uint8)
    im = Image.fromarray(small).resize((w, h), Image.BICUBIC)
    f = np.asarray(im, F32) / 255.0
    return lo + (hi - lo) * f


def _m1_sphere_light(W, H, cx, cy, rx, ry, light=(-0.55, -0.45, 0.70)):
    """Lambert term (h, w) for an ellipsoid seen head-on, lit from `light`."""
    xx, yy = coords(W, H)
    nx = (xx - cx) / rx
    ny = (yy - cy) / ry
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    lx, ly, lz = light
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    return np.clip((nx * lx + ny * ly + nz * lz) / n, 0, 1).astype(F32)


def _m1_pine(c, x, base_y, height, width):
    """A layered pine silhouette on a canvas."""
    tiers = 7
    for k in range(tiers):
        t0 = k / tiers
        top = base_y - height * (1 - t0 * 0.92) - height * 0.08
        bot = base_y - height * (0.72 - t0 * 0.72) if k < tiers - 1 else base_y - height * 0.05
        half = width * (0.25 + 0.75 * (k + 1) / tiers) / 2
        c.poly([(x, top), (x + half, bot), (x + half * 0.35, bot - height * 0.02),
                (x - half * 0.35, bot - height * 0.02), (x - half, bot)])
    c.rect(x - width * 0.05, base_y - height * 0.08, x + width * 0.05, base_y)


# --------------------------------------------------------------------------------------
# L01 · Luminosity Masks
# --------------------------------------------------------------------------------------

def m1_high_contrast_landscape():
    name = "l01-high-contrast-landscape.jpg"
    r = rng(name)
    W, H = 2400, 1600
    xx, yy = coords(W, H)
    # sky: bright, close to blown, with cloud detail living in the top 15 levels
    img = vgrad(W, H, [(0, (214, 229, 244)), (0.55, (240, 244, 248)), (1, (251, 251, 248))], 0, 820)
    sun = np.exp(-(((xx - 1830) ** 2 + (yy - 250) ** 2) / (2 * 260.0 ** 2)))
    img += (sun * 40)[..., None]
    core = np.exp(-(((xx - 1830) ** 2 + (yy - 250) ** 2) / (2 * 55.0 ** 2)))
    img += (core * 90)[..., None]
    for _ in range(9):
        cx, cy = r.uniform(100, 2300), r.uniform(80, 560)
        wd, ht = r.uniform(300, 700), r.uniform(90, 200)
        cm = Canvas((cx - wd, cy - ht, cx + wd, cy + ht), ss=1, pad=60)
        soft_blob(cm, r, cx, cy, wd, ht, n=(4, 7))
        m = cm.mask(blur=28)
        paint(img, Mask(m.x, m.y + int(ht * 0.3), m.a), (214, 222, 232), 0.55)   # gray underside
        paint(img, m, (253, 253, 251), 0.85)
    np.clip(img, 0, 255, out=img)

    xs = np.arange(0, W + 1, 8, dtype=float)
    # far range: hazy, bright-ish midtones
    far = smooth_wave(xs, 760, 70, [(900, 1, 0.3), (380, 0.5, 1.1), (170, 0.25, 2.0)])
    c = Canvas((0, 600, W, H), ss=2)
    c.poly([(0, H)] + list(zip(xs, far)) + [(W, H)])
    paint(img, c.mask(), vgrad(W, H, [(0, (176, 186, 200)), (1, (150, 160, 172))], 700, 900))
    # middle range: midtones
    mid = smooth_wave(xs, 890, 90, [(700, 1, 2.2), (260, 0.45, 0.4), (110, 0.2, 1.7)])
    c = Canvas((0, 700, W, H), ss=2)
    c.poly([(0, H)] + list(zip(xs, mid)) + [(W, H)])
    midcol = vgrad(W, H, [(0, (104, 112, 116)), (1, (70, 78, 76))], 780, 1050)
    midcol *= _m1_lowfreq(r, W, H, 90, 0.9, 1.1)[..., None]
    paint(img, c.mask(), midcol)
    # foreground valley: deep shadows with detail to lift (grass, path, rocks)
    fg = smooth_wave(xs, 1060, 60, [(1300, 1, 0.8), (420, 0.4, 2.6)])
    c = Canvas((0, 900, W, H), ss=2)
    c.poly([(0, H)] + list(zip(xs, fg)) + [(W, H)])
    fgm = c.mask()
    fgcol = vgrad(W, H, [(0, (30, 38, 26)), (1, (13, 17, 12))], 1000, H)
    fgcol *= _m1_lowfreq(r, W, H, 40, 0.75, 1.25)[..., None]
    grass = r.standard_normal((H, W)).astype(F32)
    grass = np.asarray(Image.fromarray(to_u8(128 + grass * 40)).filter(ImageFilter.BoxBlur(1)), F32) - 128
    fgcol += (grass * 0.18)[..., None]
    paint(img, fgm, fgcol)
    # a winding path and some rocks (only visible once the shadows are lifted)
    c = Canvas((0, 1000, W, H), ss=2)
    pts = quad_bezier((980, H + 20), (1500, 1330), (1250, 1130), 60)
    c.line(pts, 34)
    paint(img, c.mask(blur=3), (40, 37, 30), 0.9)
    c = Canvas((0, 1050, W, H), ss=2)
    for _ in range(18):
        rx_, ry_ = r.uniform(300, 2300), r.uniform(1180, 1560)
        c.ellipse(rx_, ry_, r.uniform(20, 45), r.uniform(7, 14))
    paint(img, c.mask(blur=2), (38, 38, 35), 0.7)
    # a pale cabin: bright, but not as bright as the sky (the "bright shirt" test)
    c = Canvas((1480, 1040, 1720, 1230), ss=3)
    c.rect(1500, 1120, 1690, 1215)
    paint(img, c.mask(), (192, 178, 156))
    c = Canvas((1480, 1040, 1720, 1230), ss=3)
    c.poly([(1485, 1125), (1595, 1060), (1705, 1125)])
    paint(img, c.mask(), (48, 38, 34))
    c = Canvas((1480, 1040, 1720, 1230), ss=3)
    c.rect(1535, 1150, 1565, 1185)
    c.rect(1625, 1150, 1655, 1185)
    c.rect(1585, 1160, 1607, 1215)
    paint(img, c.mask(), (60, 50, 40))
    # dark pines rising into the sky on both sides (a hand-painted mask's nightmare)
    c = Canvas((0, 300, W, H), ss=3)
    for x, base, ht, wd in ((90, 1180, 780, 250), (260, 1150, 620, 210), (390, 1170, 470, 170),
                            (2080, 1140, 560, 190), (2230, 1170, 820, 260), (2370, 1150, 650, 210)):
        _m1_pine(c, x, base, ht, wd)
    paint(img, c.mask(blur=0.6), (14, 21, 16))
    add_noise(img, 2.2, r)
    save_jpg(img, 1, name)


def m1_still_life_window_light():
    name = "l01-still-life-window-light.jpg"
    r = rng(name)
    W, H = 2000, 1400
    xx, yy = coords(W, H)
    # dark wall with window light falling off from the upper left
    img = solid(W, H, (44, 38, 34))
    fall = np.clip(1.25 - np.hypot(xx - 200, yy - 150) / 1500, 0.3, 1.2)
    img *= fall[..., None]
    # table
    c = Canvas((0, 950, W, H), ss=2)
    c.rect(0, 1000, W, H)
    tm = c.mask()
    table = hgrad(W, H, [(0, (128, 100, 76)), (1, (54, 42, 34))])
    table *= (0.92 + 0.08 * np.sin(yy / 7 + np.sin(xx / 210) * 2))[..., None]
    paint(img, tm, table)
    # soft shadows on the table (cast to the right, away from the window)
    c = Canvas((600, 900, W, H), ss=1, pad=40)
    c.ellipse(1150, 1040, 330, 40)
    c.ellipse(1480, 1060, 160, 28)
    darken(img, c.mask(blur=22), 0.55)
    # dark glass bottle (deep shadows)
    L = _m1_sphere_light(W, H, 1370, 700, 120, 420)
    c = Canvas((1200, 150, 1540, 1070), ss=3)
    c.rrect(1260, 520, 1480, 1045, 60)
    c.rrect(1335, 230, 1405, 560, 25)
    paint(img, c.mask(), np.clip(np.array((22, 40, 30), F32) * (0.5 + 1.1 * L[..., None]), 0, 255))
    c = Canvas((1200, 150, 1540, 1070), ss=3)
    c.rrect(1290, 560, 1310, 1000, 10)
    paint(img, c.mask(blur=3), (200, 215, 205), 0.55)                 # specular streak
    # cream ceramic jug (highlights and midtones)
    L = _m1_sphere_light(W, H, 900, 760, 290, 300)
    c = Canvas((560, 330, 1260, 1070), ss=3)
    c.ellipse(900, 760, 290, 290)
    c.rrect(760, 400, 1040, 620, 40)
    c.ellipse(900, 410, 150, 38)
    jm = c.mask()
    jug = np.array((222, 208, 184), F32) * (0.32 + 0.78 * L[..., None])
    spec = (L ** 30 * 90)[..., None]
    paint(img, jm, np.clip(jug + spec, 0, 255))
    c = Canvas((1100, 480, 1320, 900), ss=3)
    c.line(quad_bezier((1150, 540), (1330, 600), (1160, 860), 40), 34)
    paint(img, c.mask(), (120, 108, 94))                               # handle in shade
    c = Canvas((560, 330, 1260, 1070), ss=3)
    c.ellipse(900, 410, 118, 24)
    paint(img, c.mask(), (40, 34, 30))                                  # mouth opening
    # two lemons and a pear (saturated midtones + highlights)
    for cx, cy, rx, ry, col in ((520, 990, 120, 92, (232, 190, 52)), (330, 1010, 110, 85, (226, 182, 48)),
                                (1640, 960, 118, 150, (150, 170, 70))):
        L = _m1_sphere_light(W, H, cx, cy, rx, ry)
        c = Canvas((cx - rx, cy - ry, cx + rx, cy + ry), ss=3, pad=4)
        c.ellipse(cx, cy, rx, ry)
        f = np.array(col, F32) * (0.25 + 0.85 * L[..., None]) + (L ** 25 * 70)[..., None]
        paint(img, c.mask(), np.clip(f, 0, 255))
    # linen cloth draped over the table edge
    c = Canvas((0, 980, 700, H), ss=2)
    c.poly([(0, 1000), (560, 1000), (640, 1400), (0, 1400)])
    cm = c.mask()
    cloth = np.array((205, 200, 190), F32) * (0.55 + 0.45 * np.clip(1 - xx / 900, 0, 1))[..., None]
    cloth *= (0.9 + 0.1 * np.sin(xx / 18 + yy / 60))[..., None]
    paint(img, cm, cloth)
    add_noise(img, 2.0, r)
    save_jpg(img, 1, name)


# --------------------------------------------------------------------------------------
# L02 · Channel Masking & Blend-If
# --------------------------------------------------------------------------------------

def _m1_branch(c, r, x, y, ang, length, width, depth):
    """Recursive branching; ang in radians, 0 = right, pi/2 = up."""
    bend = r.uniform(-0.12, 0.12)
    x2 = x + length * math.cos(ang)
    y2 = y - length * math.sin(ang)
    mx = (x + x2) / 2 - bend * length * math.sin(ang)
    my = (y + y2) / 2 - bend * length * math.cos(ang)
    w2 = width * 0.82
    pts = quad_bezier((x, y), (mx, my), (x2, y2), 10 if width > 3 else 5)
    if width > 2.5:
        c.circle(x, y, width / 2)
    c.line(pts, (width + w2) / 2)
    if w2 < 0.75 or depth >= 12:
        return
    n = 3 if (r.random() < 0.22 and depth > 2) else 2
    for k in range(n):
        spread = r.uniform(0.25, 0.62) * (1 if k % 2 == 0 else -1)
        if n == 3 and k == 2:
            spread = r.uniform(-0.12, 0.12)
        a2 = ang + spread + (math.pi / 2 - ang) * 0.10          # a slight pull upward
        _m1_branch(c, r, x2, y2, a2, length * r.uniform(0.70, 0.84),
                   w2 * r.uniform(0.66, 0.78), depth + 1)
    if depth > 5 and r.random() < 0.6:                          # extra fine twiglets
        _m1_branch(c, r, (x + x2) / 2, (y + y2) / 2, ang + r.choice([-1, 1]) * r.uniform(0.5, 0.9),
                   length * 0.45, max(0.8, w2 * 0.45), 11)


def m1_bare_tree_sky():
    name = "l02-bare-tree-sky.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = vgrad(W, H, [(0, (74, 132, 214)), (1, (168, 200, 236))], 0, 1260)
    for _ in range(6):                                            # thin high cloud
        cx, cy = r.uniform(0, W), r.uniform(80, 900)
        wd, ht = r.uniform(350, 800), r.uniform(50, 120)
        cm = Canvas((cx - wd, cy - ht, cx + wd, cy + ht), ss=1, pad=50)
        soft_blob(cm, r, cx, cy, wd, ht, n=(3, 6))
        paint(img, cm.mask(blur=30), (236, 242, 250), 0.45)
    xs = np.arange(0, W + 1, 8, dtype=float)
    ridge = smooth_wave(xs, 1270, 18, [(900, 1, 0.5), (300, 0.4, 1.2)])
    c = Canvas((0, 1150, W, H), ss=2)                             # distant hedge line
    hedge = ridge - 26 - 16 * np.abs(np.sin(xs / 37)) - 10 * np.abs(np.sin(xs / 13))
    c.poly([(0, H)] + list(zip(xs, hedge)) + [(W, H)])
    paint(img, c.mask(blur=0.8), (52, 64, 48))
    c = Canvas((0, 1150, W, H), ss=2)
    c.poly([(0, H)] + list(zip(xs, ridge)) + [(W, H)])
    field = vgrad(W, H, [(0, (92, 82, 52)), (1, (58, 50, 34))], 1260, H)
    field *= _m1_lowfreq(r, W, H, 60, 0.85, 1.15)[..., None]
    paint(img, c.mask(), field)
    # the tree: thousands of branches, down to sub-pixel twigs
    c = Canvas((0, 0, W, H), ss=3)
    c.poly([(1120, 1380), (1150, 1100), (1195, 1100), (1225, 1380)])           # trunk + flare
    c.ellipse(1172, 1380, 90, 16)
    _m1_branch(c, r, 1172, 1120, math.pi / 2 + 0.03, 265, 46, 0)
    _m1_branch(c, r, 1165, 1000, math.pi / 2 + 0.55, 230, 26, 3)
    _m1_branch(c, r, 1180, 960, math.pi / 2 - 0.62, 240, 26, 3)
    tm = c.mask(blur=0.35)
    bark = np.array((54, 44, 38), F32) * _m1_lowfreq(r, W, H, 25, 0.85, 1.15)[..., None]
    paint(img, tm, bark)
    add_noise(img, 2.5, r)
    save_jpg(img, 1, name)


def m1_new_sky():
    name = "l02-new-sky.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = vgrad(W, H, [(0, (38, 46, 96)), (0.45, (132, 84, 120)), (0.75, (228, 124, 86)),
                       (1, (252, 186, 104))], 0, 1300)
    for _ in range(12):                                           # clouds lit from below
        cx, cy = r.uniform(-100, 2500), r.uniform(150, 1000)
        wd, ht = r.uniform(300, 700), r.uniform(50, 130)
        cm = Canvas((cx - wd, cy - ht, cx + wd, cy + ht), ss=1, pad=40)
        soft_blob(cm, r, cx, cy, wd, ht, n=(4, 7))
        m = cm.mask(blur=18)
        paint(img, m, (70, 50, 80), 0.55)
        edge = Mask(m.x, m.y + int(ht * 0.25), m.a)
        paint(img, Mask(m.x, m.y, np.clip(m.a - edge.a, 0, 1)), (255, 170, 110), 0.7)
    add_noise(img, 1.6, r)
    save_jpg(img, 1, name)


def m1_grunge_texture():
    name = "l02-grunge-texture.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = solid(W, H, (246, 243, 236))
    # stains: low-frequency blotches, only the darkest parts of the field show
    for cell, amt in ((260, 60), (90, 40), (30, 22)):
        f = _m1_lowfreq(r, W, H, cell)
        img -= (np.clip((f - 0.66) * 3.0, 0, 1) * amt)[..., None] * np.array((1.0, 1.05, 1.2), F32)
    # speckle and dust
    c = Canvas((0, 0, W, H), ss=2)
    for _ in range(2600):
        x, y = r.uniform(0, W), r.uniform(0, H)
        rad = r.uniform(0.6, 2.2) if r.random() < 0.9 else r.uniform(3, 9)
        c.circle(x, y, rad, int(r.uniform(120, 255)))
    paint(img, c.mask(blur=0.6), (58, 50, 44), 0.85)
    # scratches
    c = Canvas((0, 0, W, H), ss=2)
    for _ in range(110):
        x, y = r.uniform(0, W), r.uniform(0, H)
        a, ln = r.uniform(0, math.pi), r.uniform(40, 420)
        x2, y2 = x + ln * math.cos(a), y + ln * math.sin(a)
        c.line(quad_bezier((x, y), ((x + x2) / 2 + r.uniform(-20, 20), (y + y2) / 2 + r.uniform(-20, 20)),
                           (x2, y2), 16), r.uniform(0.8, 2.2), int(r.uniform(90, 220)))
    paint(img, c.mask(blur=0.4), (70, 62, 55), 0.8)
    add_noise(img, 3.0, r, mono=True)
    save_jpg(img, 1, name)


def m1_fireworks_on_black():
    name = "l02-fireworks-on-black.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = solid(W, H, (5, 6, 12))
    bursts = ((620, 520, 360, (255, 170, 80)), (1380, 380, 420, (120, 200, 255)),
              (1900, 700, 300, (255, 110, 170)), (1050, 900, 250, (200, 255, 150)))
    for cx, cy, rad, col in bursts:
        c = Canvas((cx - rad * 1.3, cy - rad * 1.3, cx + rad * 1.3, cy + rad * 1.6), ss=2, pad=30)
        tips = Canvas((cx - rad * 1.3, cy - rad * 1.3, cx + rad * 1.3, cy + rad * 1.6), ss=2, pad=30)
        for _ in range(170):
            a = r.uniform(0, 2 * math.pi)
            r0, r1 = rad * r.uniform(0.15, 0.35), rad * r.uniform(0.75, 1.05)
            droop = r1 * 0.12
            p0 = (cx + r0 * math.cos(a), cy + r0 * math.sin(a))
            p2 = (cx + r1 * math.cos(a), cy + r1 * math.sin(a) + droop)
            p1 = ((p0[0] + p2[0]) / 2, (p0[1] + p2[1]) / 2 - droop * 0.2)
            c.line(quad_bezier(p0, p1, p2, 12), r.uniform(1.2, 2.6), int(r.uniform(140, 255)))
            tips.circle(p2[0], p2[1], r.uniform(2, 4.5))
        m = c.mask()
        glow = c.mask(blur=14)
        paint(img, glow, col, 0.55)
        paint(img, m, lerp(col, (255, 255, 255), 0.45))
        paint(img, tips.mask(blur=3), lerp(col, (255, 255, 255), 0.7), 0.9)
        paint(img, tips.mask(), (255, 255, 245))
    add_noise(img, 2.0, r)
    save_jpg(img, 1, name)


# --------------------------------------------------------------------------------------
# L03 · The Hard Cutout: an illustrated sitter with curly hair and flyaways
# --------------------------------------------------------------------------------------

def _m1_curl(c, r, x, y, rr, width, outward):
    """A small spiral curl near (x, y), drifting in direction `outward` (radians)."""
    turns = r.uniform(1.0, 1.8)
    n = int(18 * turns)
    ph = r.uniform(0, 2 * math.pi)
    pts = []
    for k in range(n + 1):
        t = k / n
        ang = ph + t * turns * 2 * math.pi
        rad = rr * (0.35 + 0.65 * t)
        drift = t * rr * 0.9
        pts.append((x + rad * math.cos(ang) + drift * math.cos(outward),
                    y + rad * math.sin(ang) * 0.85 + drift * math.sin(outward)))
    c.line(pts, width)


def _m1_portrait(seed, bg, hair_col, hair_hi, sweater, fringe_mix):
    """Render the L03 sitter over `bg` and over black/white (for the RGBA reference).

    Returns (photo, over_black, over_white). The photo's flyaways and hair edge carry a
    color fringe (`fringe_mix` toward the local background); the references do not."""
    r = rng(seed)
    W, H = _M1_PW, _M1_PH
    xx, yy = coords(W, H)
    targets = [bg.copy(), solid(W, H, (0, 0, 0)), solid(W, H, (255, 255, 255))]

    def put(a, col, opacity=1.0, photo_col=None):
        for k, t in enumerate(targets):
            paint(t, Mask(0, 0, a), photo_col if (k == 0 and photo_col is not None) else col, opacity)

    # hair colour field: low-frequency variation plus a sheen on the lit (left) side
    hv = _m1_lowfreq(r, W, H, 45, 0.78, 1.18)
    sheen = np.clip(1 - np.hypot(xx - 560, yy - 620) / 700, 0, 1) ** 2
    hair = np.array(hair_col, F32) * hv[..., None]
    hair = hair + (np.array(hair_hi, F32) - np.array(hair_col, F32)) * (sheen * 0.8)[..., None]
    hair = np.clip(hair, 0, 255)

    # 1. hair mass (behind the face): a curly bob down to the shoulders
    def mass(c):
        c.ellipse(800, 900, 470, 470)
        c.ellipse(470, 1270, 200, 330)
        c.ellipse(1130, 1270, 200, 330)
        c.ellipse(800, 1000, 380, 370)
    hm = _m1_full((250, 380, 1350, 1660), mass, W, H, ss=2)
    # bumpy curly silhouette: curls sitting on the outline
    band = np.clip(hm - erode(hm, 3), 0, 1)
    edge_pts = np.argwhere((band > 0.25) & (yy < 1560))
    gy, gx = np.gradient(blur_img(np.repeat((hm * 255)[..., None], 3, 2), 6)[..., 0])
    pick = edge_pts[r.choice(len(edge_pts), 900, replace=False)]

    def outline_curls(c):
        for py, px in pick[:620]:
            nx, ny = -gx[py, px], -gy[py, px]
            out = math.atan2(ny, nx)
            ox, oy = px - 6 * math.cos(out), py - 6 * math.sin(out)
            _m1_curl(c, r, ox, oy, r.uniform(12, 30), r.uniform(4, 8), out)
    curls = _m1_full((150, 280, 1450, 1720), outline_curls, W, H, ss=2)
    hair_all = np.maximum(hm, curls)
    put(hair_all, hair)

    # 2. sweater, neck, face
    def sw(c):
        c.ellipse(800, 2260, 760, 560)
    swm = _m1_full((0, 1700, W, H), sw, W, H, ss=2)
    knit = np.array(sweater, F32) * (0.86 + 0.14 * np.sin(xx / 9) * np.sin(yy / 11))[..., None]
    knit *= np.clip(1.15 - np.abs(xx - 700) / 1400, 0.6, 1.2)[..., None]
    put(swm, knit)

    skin = np.array((212, 160, 128), F32)

    def neck(c):
        c.rrect(690, 1300, 910, 1780, 60)
    nm = _m1_full((650, 1250, 950, 1850), neck, W, H)
    put(nm, skin * np.where(yy < 1480, 0.72, 0.86)[..., None])

    L = _m1_sphere_light(W, H, 800, 1020, 255, 330)
    face_col = np.clip(skin * (0.62 + 0.48 * L[..., None]), 0, 255)

    def face(c):
        c.ellipse(800, 1020, 250, 330)
    fm = _m1_full((520, 660, 1080, 1380), face, W, H)
    put(fm, face_col)

    # 3. features
    def brows(c):
        for x0, x1 in ((665, 775), (825, 935)):
            c.line(quad_bezier((x0, 925), ((x0 + x1) / 2, 900), (x1, 922), 20), 12)
    put(_m1_full((640, 880, 960, 950), brows, W, H), np.array(hair_col, F32) * 0.9)
    for ex in (720, 880):
        def eye(c, ex=ex):
            c.poly(quad_bezier((ex - 52, 990), (ex, 948), (ex + 52, 990), 20) +
                   quad_bezier((ex + 52, 990), (ex, 1026), (ex - 52, 990), 20))
        em = _m1_full((ex - 60, 940, ex + 60, 1035), eye, W, H)
        put(em, (236, 232, 224))
        irm = _m1_full((ex - 30, 960, ex + 30, 1020), lambda c, ex=ex: c.circle(ex, 990, 22), W, H) * em
        put(irm, (80, 56, 38))
        put(_m1_full((ex - 12, 978, ex + 12, 1002), lambda c, ex=ex: c.circle(ex, 990, 9), W, H), (14, 12, 12))
        put(_m1_full((ex - 10, 975, ex, 985), lambda c, ex=ex: c.circle(ex - 6, 982, 4), W, H), (255, 255, 255))
        put(_m1_full((ex - 60, 940, ex + 60, 1000),
                     lambda c, ex=ex: c.line(quad_bezier((ex - 54, 991), (ex, 946), (ex + 54, 990), 20), 5),
                     W, H), (50, 34, 28))

    def nose(c):
        c.line([(805, 1010), (822, 1120)], 10)
    nose_m = _m1_full((780, 990, 850, 1140), nose, W, H, blur=5)
    for t in targets:
        darken(t, Mask(0, 0, nose_m), 0.14)
    put(_m1_full((760, 1120, 850, 1150), lambda c: (c.ellipse(785, 1135, 11, 6), c.ellipse(830, 1135, 11, 6)),
                 W, H), (120, 70, 60), 0.8)

    def lips(c):
        c.poly(quad_bezier((725, 1210), (800, 1180), (875, 1210), 30) +
               quad_bezier((875, 1210), (800, 1262), (725, 1210), 30))
    put(_m1_full((710, 1170, 890, 1270), lips, W, H), (178, 92, 88))
    blush = np.exp(-(((xx - 650) ** 2 + (yy - 1100) ** 2) / (2 * 50.0 ** 2))) + \
        np.exp(-(((xx - 950) ** 2 + (yy - 1100) ** 2) / (2 * 50.0 ** 2)))
    put((blush * fm * 0.25).astype(F32), (220, 110, 100))

    # 4. front hair: curls falling over the forehead and temples
    def fringe(c):
        c.poly([(540, 820), (560, 700), (680, 640), (800, 630), (930, 640), (1040, 700), (1060, 820),
                (980, 760), (900, 800), (820, 750), (740, 800), (650, 770)])
        c.ellipse(570, 1000, 55, 220)
        c.ellipse(1030, 1000, 55, 220)
        for _ in range(60):
            x = r.uniform(560, 1040)
            _m1_curl(c, r, x, 800 - 0.9 * abs(x - 800) * 0.25 + r.uniform(-30, 10),
                     r.uniform(14, 26), r.uniform(5, 8), math.pi / 2)
        for _ in range(50):
            side = r.choice([540, 1060])
            _m1_curl(c, r, side + r.uniform(-30, 30), r.uniform(820, 1220), r.uniform(12, 24),
                     r.uniform(5, 8), math.pi / 2)
    frm = _m1_full((460, 560, 1140, 1300), fringe, W, H, ss=2)
    put(frm, hair)

    # 5. interior curl texture (colour only, inside the hair)
    hn = np.maximum(hair_all * (1 - fm) * (1 - nm) * (1 - swm), frm)

    def texture(c):
        for py, px in np.argwhere(hn > 0.9)[
                r.choice(int((hn > 0.9).sum()), 1300, replace=False)]:
            _m1_curl(c, r, px, py, r.uniform(8, 20), r.uniform(2, 4), r.uniform(0, 2 * math.pi))
    tex = _m1_full((150, 280, 1450, 1720), texture, W, H, ss=2)
    hair_now = np.maximum(hair_all * (1 - fm) * (1 - nm) * (1 - swm), frm)
    put(tex * hair_now, np.clip(np.array(hair_hi, F32) * 1.05, 0, 255), 0.55)
    tex2 = _m1_full((150, 280, 1450, 1720), texture, W, H, ss=2)
    put(tex2 * hair_now, np.array(hair_col, F32) * 0.55, 0.5)

    # 6. flyaways: fine, semi-transparent strands springing off the outline
    def flyaways(c):
        for py, px in pick[620:]:
            nx, ny = -gx[py, px], -gy[py, px]
            a = math.atan2(ny, nx) + r.uniform(-0.6, 0.6)
            ln = 40 + 220 * r.random() ** 1.6
            steps = max(6, int(ln / 6))
            x, y = float(px), float(py)
            curl_amp, curl_f = r.uniform(0.15, 0.5), r.uniform(0.15, 0.35)
            pts = [(x, y)]
            for k in range(steps):
                a += r.uniform(-0.12, 0.12) + curl_amp * math.sin(k * curl_f * 2 * math.pi) * 0.3
                x += 6 * math.cos(a)
                y += 6 * math.sin(a)
                pts.append((x, y))
            c.line(pts, r.uniform(0.9, 1.8), int(r.uniform(0.35, 0.85) * 255))
    fly = _m1_full((0, 0, W, 1750), flyaways, W, H, ss=3, blur=0.3)
    fly_true = np.clip(np.array(hair_hi, F32) * 0.9, 0, 255)
    fly_photo = fly_true * (1 - fringe_mix) + bg * fringe_mix
    put(fly, fly_true, 1.0, photo_col=fly_photo)

    return targets


def _m1_studio_teal(r):
    W, H = _M1_PW, _M1_PH
    xx, yy = coords(W, H)
    d = np.clip(np.hypot(xx - 820, yy - 850) / 1400, 0, 1)
    img = np.array((112, 188, 192), F32) * (1.05 - 0.4 * d)[..., None]
    return np.ascontiguousarray(img, dtype=F32)


def m1_curly_hair_portrait():
    name = "l03-curly-hair-portrait.jpg"
    r = rng(name)
    photo, _, _ = _m1_portrait("m1-sitter", _m1_studio_teal(r), (58, 36, 24), (128, 86, 52),
                               (176, 84, 58), 0.3)
    add_noise(photo, 2.0, r)
    save_jpg(photo, 1, name)


def m1_hair_busy_background():
    name = "l03-hair-busy-background.jpg"
    r = rng(name)
    W, H = _M1_PW, _M1_PH
    bg = vgrad(W, H, [(0, (92, 120, 60)), (1, (58, 84, 44))])
    for _ in range(170):                                          # out-of-focus foliage + light
        cx, cy, rad = r.uniform(0, W), r.uniform(0, H), r.uniform(25, 150)
        c = Canvas((cx - rad, cy - rad, cx + rad, cy + rad), ss=1, pad=30)
        c.circle(cx, cy, rad)
        col = [(70, 110, 45), (120, 150, 60), (40, 70, 35), (210, 215, 150), (160, 120, 70)][r.integers(0, 5)]
        paint(bg, c.mask(blur=r.uniform(4, 14)), rand_color_near(r, col, 15), r.uniform(0.5, 0.9))
    photo, _, _ = _m1_portrait("m1-sitter", bg, (132, 62, 30), (214, 132, 72), (70, 88, 140), 0.3)
    add_noise(photo, 2.0, r)
    save_jpg(photo, 1, name)


def m1_new_background():
    name = "l03-new-background.jpg"
    r = rng(name)
    W, H = _M1_PW, _M1_PH
    img = vgrad(W, H, [(0, (70, 52, 60)), (0.6, (150, 98, 74)), (1, (96, 64, 52))])
    for _ in range(90):                                           # warm evening bokeh
        cx, cy, rad = r.uniform(0, W), r.uniform(0, H * 0.8), r.uniform(20, 90)
        c = Canvas((cx - rad, cy - rad, cx + rad, cy + rad), ss=2, pad=10)
        c.circle(cx, cy, rad)
        col = [(255, 200, 120), (255, 170, 90), (255, 225, 170), (200, 150, 255)][r.integers(0, 4)]
        paint(img, c.mask(blur=r.uniform(2, 6)), col, r.uniform(0.15, 0.45))
    img = blur_img(img, 3)
    add_noise(img, 1.8, r)
    save_jpg(img, 1, name)


def m1_hair_cutout_reference():
    name = "l03-hair-cutout-reference.png"
    W, H = _M1_PW, _M1_PH
    r = rng(name)
    _, ob, ow = _m1_portrait("m1-sitter", _m1_studio_teal(r), (58, 36, 24), (128, 86, 52),
                             (176, 84, 58), 0.3)
    a = np.clip(1 - (ow - ob).mean(axis=2) / 255.0, 0, 1)
    rgb = np.clip(ob / np.maximum(a, 1e-4)[..., None], 0, 255)
    rgb *= (a > 0.002)[..., None]
    out = np.dstack([rgb, a * 255])
    save_png(Image.fromarray(to_u8(out), "RGBA"), 1, name, folder="instructor")


# ======================================================================================
# Module 2: Color & Tone, Deep
# ======================================================================================

# ======================================================================================
# MODULE 2: Color & Tone, Deep  (L04 color management, L05 grading + LUTs,
#                                L06 match / split-tone / soft-proof)
# ======================================================================================
#
# Special formats made here:
#   * an ICC v2 matrix/TRC profile with the published Adobe RGB (1998) primaries,
#     white point and 563/256 gamma, built byte by byte (Pillow's ImageCms can only
#     create sRGB/Lab/XYZ). It is named "Adobe RGB (1998) compatible" so nobody
#     mistakes it for Adobe's own file; colorimetrically it is the same space.
#   * a 16-bit/channel RGB TIFF (ZIP/Deflate + horizontal predictor), written by hand
#     because Pillow cannot save 16-bit RGB.
#   * a 3D LUT (.cube) as an instructor-only fallback.

_M2_GAMMA = 563 / 256          # Adobe RGB (1998) TRC, u8Fixed8 = 2.19921875


def _m2_xy_to_xyz(x, y):
    return np.array([x / y, 1.0, (1 - x - y) / y])


_M2_BRADFORD = np.array([[0.8951, 0.2664, -0.1614],
                         [-0.7502, 1.7135, 0.0367],
                         [0.0389, -0.0685, 1.0296]])
_M2_D65 = _m2_xy_to_xyz(0.3127, 0.3290)
_M2_D50 = np.array([0.9642, 1.0, 0.8249])


def _m2_rgb_to_xyz(prims, white):
    """Columns = XYZ of the R, G, B primaries at full intensity (white-point scaled)."""
    P = np.stack([_m2_xy_to_xyz(*p) for p in prims], 1)
    S = np.linalg.solve(P, white)
    return P * S


_M2_SRGB_M = _m2_rgb_to_xyz([(0.64, 0.33), (0.30, 0.60), (0.15, 0.06)], _M2_D65)
_M2_ARGB_M = _m2_rgb_to_xyz([(0.64, 0.33), (0.21, 0.71), (0.15, 0.06)], _M2_D65)
_M2_SRGB_TO_ARGB = np.linalg.solve(_M2_ARGB_M, _M2_SRGB_M)      # linear sRGB -> linear aRGB


def _m2_srgb_lin(v8):
    v = np.clip(np.asarray(v8, np.float64) / 255.0, 0, 1)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def _m2_argb_encode(lin):
    """Linear Adobe-RGB (0..1, may exceed) -> 0..1 encoded with the 563/256 gamma."""
    return np.clip(lin, 0, 1) ** (1 / _M2_GAMMA)


def _m2_srgb8_to_argb(img8):
    """Float sRGB image (0..255) -> float Adobe-RGB-encoded image (0..1), same look."""
    lin = _m2_srgb_lin(img8) @ _M2_SRGB_TO_ARGB.T
    return _m2_argb_encode(lin)


def _m2_s15(v):
    return int(round(v * 65536)).to_bytes(4, "big", signed=True)


def _m2_build_icc(name: str) -> bytes:
    """A minimal ICC v2.1 RGB display profile: matrix/TRC with Adobe RGB (1998) values."""
    # D50-adapted colorants (Bradford), as the ICC spec requires for the PCS.
    ms, md = _M2_BRADFORD @ _M2_D65, _M2_BRADFORD @ _M2_D50
    cat = np.linalg.inv(_M2_BRADFORD) @ np.diag(md / ms) @ _M2_BRADFORD
    cols = cat @ _M2_ARGB_M

    def xyz_tag(v):
        return b"XYZ " + bytes(4) + b"".join(_m2_s15(c) for c in v)

    def text_desc(s):
        a = s.encode("ascii") + b"\0"
        return (b"desc" + bytes(4) + len(a).to_bytes(4, "big") + a
                + bytes(8) + bytes(3) + bytes(67))

    curv = b"curv" + bytes(4) + (1).to_bytes(4, "big") + (563).to_bytes(2, "big") + bytes(2)
    cprt = b"text" + bytes(4) + b"No copyright, use freely (course practice profile)\0"
    tags = [(b"desc", text_desc(name)), (b"cprt", cprt), (b"wtpt", xyz_tag(_M2_D65)),
            (b"rXYZ", xyz_tag(cols[:, 0])), (b"gXYZ", xyz_tag(cols[:, 1])),
            (b"bXYZ", xyz_tag(cols[:, 2])), (b"rTRC", curv), (b"gTRC", curv), (b"bTRC", curv)]
    table_len = 4 + 12 * len(tags)
    off = 128 + table_len
    data, entries, seen = b"", [], {}
    for sig, body in tags:
        if body in seen:                      # the three TRCs share one curve
            entries.append((sig, seen[body], len(body)))
            continue
        while (off + len(data)) % 4:
            data += b"\0"
        seen[body] = off + len(data)
        entries.append((sig, off + len(data), len(body)))
        data += body
    while len(data) % 4:
        data += b"\0"
    table = len(tags).to_bytes(4, "big") + b"".join(
        s + o.to_bytes(4, "big") + n.to_bytes(4, "big") for s, o, n in entries)
    size = 128 + len(table) + len(data)
    hdr = (size.to_bytes(4, "big") + bytes(4) + bytes.fromhex("02100000") + b"mntr" + b"RGB "
           + b"XYZ " + bytes.fromhex("07ea00010001000000000000") + b"acsp" + bytes(4)
           + bytes(4) + bytes(4) + bytes(4) + bytes(8) + bytes(4)
           + b"".join(_m2_s15(c) for c in _M2_D50) + bytes(4) + bytes(16) + bytes(28))
    assert len(hdr) == 128
    return hdr + table + data


_M2_ARGB_ICC = _m2_build_icc("Adobe RGB (1998) compatible")


def _m2_save_jpg_icc(img, name, icc, quality=90, folder="practice"):
    """JPEG with a caller-chosen ICC profile (icc=None -> untagged)."""
    if isinstance(img, np.ndarray):
        img = Image.fromarray(to_u8(img))
    p = out_path(2, name, folder)
    kw = dict(quality=quality, dpi=(72, 72), optimize=True, subsampling=0)
    if icc is not None:
        kw["icc_profile"] = icc
    img.save(p, "JPEG", **kw)
    _record(p)


def _m2_save_tiff16(arr01, name, icc, dpi=300):
    """Write a 16-bit/channel RGB TIFF (little-endian, Deflate + horizontal predictor,
    ICC embedded). arr01: (h, w, 3) float in 0..1. Photoshop opens it as 16 Bits/Channel."""
    h, w = arr01.shape[:2]
    a = np.clip(np.rint(arr01 * 65535), 0, 65535).astype("<u2")
    rows = 32
    strips = []
    for y in range(0, h, rows):
        blk = a[y:y + rows].astype(np.int32)
        d = blk.copy()
        d[:, 1:, :] = blk[:, 1:, :] - blk[:, :-1, :]          # predictor 2, per sample
        strips.append(zlib.compress((d & 0xFFFF).astype("<u2").tobytes(), 9))
    n = len(strips)
    # layout: header | strip data | extra values | IFD
    out = bytearray(b"II*\0" + bytes(4))
    offs = []
    for s in strips:
        offs.append(len(out))
        out += s
        if len(out) % 2:
            out += b"\0"

    def put(b):
        nonlocal out
        if len(out) % 2:
            out += b"\0"
        o = len(out)
        out += b
        return o

    bps = put(b"".join((16).to_bytes(2, "little") for _ in range(3)))
    so = put(b"".join(o.to_bytes(4, "little") for o in offs))
    sc = put(b"".join(len(s).to_bytes(4, "little") for s in strips))
    xres = put(dpi.to_bytes(4, "little") + (1).to_bytes(4, "little"))
    yres = put(dpi.to_bytes(4, "little") + (1).to_bytes(4, "little"))
    iccp = put(icc)
    SHORT, LONG, RAT, UND = 3, 4, 5, 7

    def val(typ, v):          # inline value, left-justified in the 4-byte field
        return (v.to_bytes(2, "little") + bytes(2)) if typ == SHORT else v.to_bytes(4, "little")

    entries = [
        (256, LONG, 1, val(LONG, w)), (257, LONG, 1, val(LONG, h)),
        (258, SHORT, 3, bps.to_bytes(4, "little")), (259, SHORT, 1, val(SHORT, 8)),
        (262, SHORT, 1, val(SHORT, 2)),
        (273, LONG, n, so.to_bytes(4, "little") if n > 1 else val(LONG, offs[0])),
        (277, SHORT, 1, val(SHORT, 3)), (278, LONG, 1, val(LONG, rows)),
        (279, LONG, n, sc.to_bytes(4, "little") if n > 1 else val(LONG, len(strips[0]))),
        (282, RAT, 1, xres.to_bytes(4, "little")), (283, RAT, 1, yres.to_bytes(4, "little")),
        (284, SHORT, 1, val(SHORT, 1)), (296, SHORT, 1, val(SHORT, 2)),
        (317, SHORT, 1, val(SHORT, 2)), (34675, UND, len(icc), iccp.to_bytes(4, "little")),
    ]
    if len(out) % 2:
        out += b"\0"
    ifd = len(out)
    out += len(entries).to_bytes(2, "little")
    for tag, typ, cnt, v in entries:
        out += tag.to_bytes(2, "little") + typ.to_bytes(2, "little") + cnt.to_bytes(4, "little") + v
    out += bytes(4)
    out[4:8] = ifd.to_bytes(4, "little")
    p = out_path(2, name)
    p.write_bytes(bytes(out))
    _record(p)


# --------------------------------------------------------------------------------------
# L04 (Lesson 2.1): the container
# --------------------------------------------------------------------------------------

def m2_smooth_sky_16bit():
    """A gentle dusk-sky gradient with a hill silhouette, stored 16-bit, Adobe-RGB-tagged.
    No noise on purpose: nothing dithers the gradient, so a hard Curves move on an 8-bit
    copy breaks into clean bands while the 16-bit original stays smooth."""
    name = "l04-smooth-sky-16bit.tif"
    W, H = 2400, 1600
    xx, yy = coords(W, H)
    t = yy / H
    # sky, in 0..1 floating point (encoded values), narrow tonal range = easy to band
    top, mid, low = np.array((0.36, 0.45, 0.62)), np.array((0.55, 0.58, 0.68)), np.array((0.80, 0.70, 0.62))
    sky = np.where(t[..., None] < 0.45,
                   top + (mid - top) * (t[..., None] / 0.45),
                   mid + (low - mid) * np.clip((t[..., None] - 0.45) / 0.35, 0, 1))
    # a broad, soft sun glow low on the right
    d = np.hypot((xx - 1700) / 900, (yy - 1180) / 520)
    sky = sky + np.exp(-d ** 2 * 2.2)[..., None] * np.array((0.10, 0.06, 0.01))
    img = sky.astype(np.float64)
    # dark hill silhouette with an anti-aliased ridge
    ridge = 1240 + 60 * np.sin(xx[0] / 310) + 35 * np.sin(xx[0] / 97 + 1.3) - 90 * np.exp(-((xx[0] - 700) / 380) ** 2)
    cov = np.clip(yy - ridge[None, :] + 0.5, 0, 1)[..., None]
    hill = np.array((0.10, 0.10, 0.13)) + 0.04 * (1 - t[..., None])
    img = img * (1 - cov) + hill * cov
    _m2_save_tiff16(np.clip(img, 0, 1), name, _M2_ARGB_ICC)


def _m2_scene(W, H, r, snow=False):
    """A simple full-range landscape in 8-bit sRGB floats (the histogram drills)."""
    hz = int(H * 0.46)
    img = np.empty((H, W, 3), F32)
    if snow:
        img[:hz] = vgrad(W, hz, [(0, (196, 212, 230)), (1, (236, 240, 246))])
        img[hz:] = vgrad(W, H - hz, [(0, (238, 241, 245)), (1, (226, 231, 238))])
    else:
        img[:hz] = vgrad(W, hz, [(0, (60, 110, 185)), (1, (205, 222, 238))])
        img[hz:] = vgrad(W, H - hz, [(0, (110, 150, 80)), (1, (48, 92, 42))])
    for k in range(4):
        c = Canvas((0, 0, W, hz), ss=2, pad=10)
        soft_blob(c, r, r.uniform(0.1, 0.9) * W, r.uniform(0.15, 0.55) * hz, W * 0.16, hz * 0.18)
        paint(img, c.mask(blur=14), (250, 250, 252), 0.85)
    ys = hz - 40 - 70 * np.abs(np.sin(np.linspace(0, 5, 40)))
    c = Canvas((0, hz - 150, W, hz + 5), ss=2)
    c.poly([(0, hz + 2)] + list(zip(np.linspace(0, W, 40), ys)) + [(W, hz + 2)])
    paint(img, c.mask(), (230, 236, 244) if snow else (92, 112, 135))
    # a barn: bright wall + near-black open door + dark roof
    bx, by = int(W * 0.58), int(H * 0.50)
    img[by:by + 150, bx:bx + 230] = (150, 40, 35) if not snow else (160, 45, 38)
    img[by + 60:by + 150, bx + 85:bx + 145] = 10
    c = Canvas((bx - 30, by - 110, bx + 260, by + 2), ss=3)
    c.poly([(bx - 20, by), (bx + 250, by), (bx + 115, by - 100)])
    paint(img, c.mask(), (40, 38, 40) if not snow else (250, 250, 252))
    # dark trees
    for k in range(7):
        tx, ty = r.uniform(0.05, 0.45) * W, r.uniform(0.52, 0.75) * H
        c = Canvas((tx - 70, ty - 260, tx + 70, ty + 10), ss=2)
        c.poly([(tx - 60, ty), (tx + 60, ty), (tx, ty - 250)])
        paint(img, c.mask(), (22, 45, 30))
    # a white fence line
    fy = int(H * 0.82)
    img[fy:fy + 10, :] = 244
    for x in range(20, W, 70):
        img[fy - 40:fy + 60, x:x + 10] = 244
    add_noise(img, 3, r, mono=True)
    return img


_M2_HISTO = {   # letter: (problem, how the pixels were made)
    "a": ("flat / low contrast", "narrow histogram in the middle, empty at both ends"),
    "b": ("high-key snow scene, correctly exposed", "piled to the right but NOT slammed "
          "against the right wall; the trap: bright subject, not overexposure"),
    "c": ("underexposed", "crammed into the left half, nothing in the right third"),
    "d": ("overexposed with clipped highlights", "tall spike against the right wall"),
    "e": ("crushed / clipped shadows", "tall spike against the left wall"),
}


def m2_histogram_drills():
    W, H = 1200, 800
    for key in "abcde":
        name = f"l04-histogram-{key}.jpg"
        r = rng(name)
        img = _m2_scene(W, H, r, snow=(key == "b"))
        if key == "a":
            img = 72 + img * 0.42
        elif key == "c":
            img = img * 0.40
        elif key == "d":
            img = img * 1.45 + 30
        elif key == "e":
            img = (img - 70) * 1.35
        np.clip(img, 0, 255, out=img)
        save_jpg(img, 2, name, quality=88, subsampling=0)
    lines = ["Lesson 2.1 histogram drills: ANSWERS (instructor only)",
             "Have learners read Window > Histogram BEFORE naming a fix.", ""]
    for key, (prob, look) in _M2_HISTO.items():
        lines.append(f"l04-histogram-{key}.jpg  ->  {prob}")
        lines.append(f"    histogram: {look}")
    lines += ["", "One-sentence edit plans (examples):",
              "a: stretch the tones: set a black and white point / S-curve.",
              "b: leave the exposure alone; at most a gentle mid lift. A bright scene should read bright.",
              "c: lift exposure/midtones; watch noise in the shadows.",
              "d: the sky and white fence are gone (clipped); recover what little is left, re-shoot if possible.",
              "e: the trees and barn door are solid black; lift shadows, accept lost detail."]
    p = out_path(2, "l04-histogram-answers.txt", "instructor")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    _record(p)


def _m2_lagoon_argb():
    """A tropical lagoon authored directly in Adobe-RGB-encoded values (0..1), with
    cyans, greens and a parrot that sit OUTSIDE sRGB. Returns float (H, W, 3)."""
    W, H = 2000, 1333
    r = rng("l04-lagoon")
    xx, yy = coords(W, H)
    base8 = np.empty((H, W, 3), F32)                    # neutral-ish parts, authored in sRGB
    hz = int(H * 0.40)
    base8[:hz] = vgrad(W, hz, [(0, (70, 140, 215)), (1, (190, 222, 240))])
    base8[hz:] = vgrad(W, H - hz, [(0, (40, 150, 170)), (1, (230, 215, 175))])
    for k in range(3):
        c = Canvas((0, 0, W, hz), ss=2, pad=10)
        soft_blob(c, r, r.uniform(0.1, 0.9) * W, r.uniform(0.2, 0.6) * hz, 360, 90)
        paint(base8, c.mask(blur=12), (250, 250, 252), 0.9)
    img = _m2_srgb8_to_argb(base8).astype(np.float64)
    # water: a band of very saturated turquoise (outside sRGB) over the shallows
    wt = np.clip((yy - hz) / (H * 0.40), 0, 1)
    band = np.exp(-((wt - 0.35) / 0.28) ** 2) * (yy > hz)
    turq = np.array((0.02, 0.72, 0.66))
    img = img * (1 - 0.85 * band[..., None]) + turq * 0.85 * band[..., None]
    # sand (lower right) stays in gamut
    sand = np.clip((yy - H * 0.70) / 80 + (xx - W * 0.35) / 900, 0, 1)
    img = img * (1 - sand[..., None]) + np.array((0.86, 0.80, 0.63)) * sand[..., None]
    # palm fronds: saturated green (outside sRGB)
    for cx, cy, ang in ((260, 180, 0.3), (180, 320, -0.2), (420, 140, 0.8)):
        c = Canvas((0, 0, 900, 760), ss=2)
        for k in range(9):
            a = ang + k * 0.35 - 1.3
            ex, ey = cx + 420 * math.cos(a), cy + 280 * math.sin(a) + 120
            c.line(quad_bezier((cx, cy), ((cx + ex) / 2, min(cy, ey) - 60), (ex, ey), 30), 34, round_caps=True)
        m = c.mask(blur=1.2)
        fm = full_mask(m, W, H)[..., None]
        img = img * (1 - fm) + np.array((0.10, 0.62, 0.12)) * fm
    c = Canvas((0, 0, 700, H), ss=2)
    c.line(quad_bezier((300, 200), (380, 700), (240, H + 20), 60), 40)
    fm = full_mask(c.mask(blur=1), W, H)[..., None]
    img = img * (1 - fm) + np.array((0.36, 0.28, 0.19)) * fm
    # a parrot on a branch, right side: saturated red, green, cyan
    px, py = 1560, 560
    c = Canvas((1300, 350, 1850, 1000), ss=3, mode="RGBA")
    c.line([(1320, 900), (1840, 860)], 26, fill=(90, 70, 50))
    c.ellipse(px, py + 120, 95, 170, fill=(230, 15, 30))          # body
    c.circle(px + 10, py - 40, 70, fill=(230, 15, 30))            # head
    c.poly([(px + 70, py - 55), (px + 118, py - 25), (px + 72, py - 5)], fill=(235, 225, 200))
    c.circle(px + 30, py - 55, 11, fill=(255, 255, 255))
    c.circle(px + 32, py - 55, 6, fill=(10, 10, 10))
    c.poly([(px - 80, py + 60), (px - 10, py + 230), (px - 130, py + 330)], fill=(20, 200, 40))   # wing
    c.poly([(px - 60, py + 250), (px + 20, py + 260), (px - 40, py + 470)], fill=(0, 170, 235))    # tail
    L = c.layer()
    s = _slices(img.shape, L.x, L.y, L.a.shape)
    sb, sm = s
    a = L.a[sm][..., None]
    img[sb] = img[sb] * (1 - a) + (L.rgb[sm] / 255.0) * a     # drawn colors ARE Adobe-RGB values
    # a labelled swatch strip, bottom-left: in sRGB gamut / outside it
    sw = [((0.5, 0.5, 0.5), "gray"), ((0.72, 0.52, 0.42), "skin"), ((0.0, 0.85, 0.0), "green"),
          ((0.0, 0.80, 0.80), "cyan"), ((0.90, 0.0, 0.10), "red"), ((0.05, 0.25, 0.85), "blue")]
    for k, (col, lab) in enumerate(sw):
        x0, y0 = 60 + k * 150, H - 200
        img[y0:y0 + 120, x0:x0 + 130] = col
        c = Canvas((x0, y0 + 124, x0 + 130, y0 + 160), ss=3)
        c.text(x0 + 65, y0 + 142, lab, 24, bold=True, anchor="mm")
        fm = full_mask(c.mask(), W, H)[..., None]
        img = img * (1 - fm) + np.array((0.05, 0.05, 0.05)) * fm
    add = r.standard_normal((H, W, 1)) * (1.4 / 255)
    return np.clip(img + add, 0, 1)


def m2_lagoon_adobergb():
    img = _m2_lagoon_argb()
    _m2_save_jpg_icc(img * 255, "l04-lagoon-adobergb.jpg", _M2_ARGB_ICC, quality=92)


def m2_lagoon_untagged():
    img = _m2_lagoon_argb()
    _m2_save_jpg_icc(img * 255, "l04-lagoon-untagged.jpg", None, quality=92)


# --------------------------------------------------------------------------------------
# Shared studio portrait (L05 grade + L06 split-tone / match), adapted from the intro kit
# --------------------------------------------------------------------------------------

_M2_FW, _M2_FH = 2000, 2500
_M2_SKIN = (222, 176, 148)


def _m2_fc(box, ss=2):
    return Canvas(box, ss=ss, resample=Image.LANCZOS)


def _m2_mk(c, blur=0.0):
    m = c.mask(blur)
    return Mask(m.x, m.y, np.clip(m.a, 0, 1))


def _m2_hairline(x):
    t = (np.asarray(x, float) - 1000) / 360
    return 700 + 250 * t ** 2 + 10 * np.sin(np.asarray(x, float) / 45)


@lru_cache(maxsize=None)
def _m2_portrait_clean():
    """A neutral, well-lit studio portrait in sRGB floats, with real shadows (hair,
    jacket, the shadow side of the face) and real highlights (lit cheek, forehead,
    backdrop hot spot) so shadows/highlights zones are distinct for split-toning."""
    W, H = _M2_FW, _M2_FH
    r = rng("m2-portrait")
    xx, yy = coords(W, H)
    # gray seamless backdrop: hot spot behind the head, falling off to the corners
    d = np.hypot((xx - 820) / 1500, (yy - 900) / 1700)
    bg = 150 - 95 * np.clip(d, 0, 1.2) ** 1.4
    img = np.repeat(bg[..., None], 3, axis=2).astype(F32)

    skin = np.array(_M2_SKIN, F32)
    hair_col = np.array((48, 36, 28), F32)
    c = _m2_fc((460, 420, 1540, 1560))
    c.ellipse(1000, 990, 500, 560)
    hair_back = _m2_mk(c)
    paint(img, hair_back, hair_col)
    c = _m2_fc((830, 1500, 1170, 2050))
    c.rect(850, 1500, 1150, 2040)
    neck = _m2_mk(c)
    paint(img, neck, skin * 0.86)
    c = _m2_fc((0, 1880, W, H))
    c.ellipse(1000, 2620, 1000, 720)
    jacket = _m2_mk(c)
    paint(img, jacket, (38, 42, 50))
    c = _m2_fc((820, 1880, 1180, 2200))
    c.poly([(870, 1900), (1130, 1900), (1000, 2150)])
    paint(img, _m2_mk(c), (232, 230, 226))                      # white shirt V: a near-white
    c = _m2_fc((540, 1030, 1460, 1260))
    c.ellipse(600, 1140, 45, 95)
    c.ellipse(1400, 1140, 45, 95)
    ears = _m2_mk(c)
    paint(img, ears, skin * 0.93)
    c = _m2_fc((590, 640, 1410, 1720))
    c.ellipse(1000, 1180, 400, 530)
    face = _m2_mk(c)
    paint(img, face, skin)
    xs = np.arange(520, 1481, 4)
    c = _m2_fc((460, 420, 1540, 1560))
    c.poly([(520, 420)] + list(zip(xs, np.minimum(_m2_hairline(xs), 1150))) + [(1480, 420)])
    front = _m2_mk(c)
    front = Mask(front.x, front.y, front.a * hair_back.a)
    paint(img, front, hair_col)
    # hair sheen strands
    for k in range(40):
        x0 = r.uniform(560, 1440)
        c = Canvas((x0 - 140, 420, x0 + 140, 1000), ss=2, pad=4)
        c.line(quad_bezier((x0, 470 + r.uniform(0, 60)), (x0 + r.uniform(-90, 90), 640),
                           (x0 + r.uniform(-120, 120), 820 + r.uniform(0, 120)), 40), r.uniform(2, 4))
        m = c.mask(blur=0.8)
        m = Mask(m.x, m.y, m.a * full_mask(front, W, H)[m.y:m.y + m.a.shape[0], m.x:m.x + m.a.shape[1]])
        paint(img, m, (120, 95, 75), 0.45)
    skin_m = np.maximum.reduce([full_mask(face, W, H), full_mask(ears, W, H), full_mask(neck, W, H)])
    skin_m *= 1 - full_mask(front, W, H)
    skin_m *= 1 - full_mask(jacket, W, H)
    # features
    c = _m2_fc((990, 1050, 1080, 1290))
    c.line([(1025, 1070), (1045, 1270)], 8, round_caps=True)
    darken(img, _m2_mk(c, blur=4), 0.15)
    c = _m2_fc((940, 1280, 1060, 1310))
    c.ellipse(970, 1295, 13, 7)
    c.ellipse(1030, 1295, 13, 7)
    darken(img, _m2_mk(c), 0.4)
    c = _m2_fc((740, 920, 1260, 990))
    for x0, x1 in ((760, 920), (1080, 1240)):
        c.line(quad_bezier((x0, 975), ((x0 + x1) / 2, 940), (x1, 973), 30), 14, round_caps=True)
    paint(img, _m2_mk(c), (62, 45, 36))
    for ex in (840, 1160):
        top = quad_bezier((ex - 75, 1060), (ex, 994), (ex + 75, 1060), 40)
        bot = quad_bezier((ex + 75, 1060), (ex, 1126), (ex - 75, 1060), 40)
        c = _m2_fc((ex - 85, 1015, ex + 85, 1105))
        c.poly(top + bot)
        ew = _m2_mk(c)
        paint(img, ew, (232, 229, 222))
        for rad, col in ((32, (80, 95, 70)), (14, (12, 12, 12))):
            c = _m2_fc((ex - 85, 1015, ex + 85, 1105))
            c.circle(ex, 1060, rad)
            paint(img, Mask(ew.x, ew.y, _m2_mk(c).a * ew.a), col)
        c = _m2_fc((ex - 85, 1015, ex + 85, 1105))
        c.circle(ex - 9, 1051, 5)
        paint(img, _m2_mk(c), (255, 255, 255))
        c = _m2_fc((ex - 85, 1015, ex + 85, 1105))
        c.line(top, 4)
        paint(img, _m2_mk(c), (40, 28, 22))
        skin_m *= 1 - full_mask(ew, W, H)
    c = _m2_fc((880, 1360, 1120, 1470))
    c.poly(quad_bezier((890, 1405), (1000, 1365), (1110, 1405), 40) +
           quad_bezier((1110, 1405), (1000, 1480), (890, 1405), 40))
    lips = _m2_mk(c)
    paint(img, lips, (176, 92, 90))
    skin_m *= 1 - full_mask(lips, W, H)
    # skin texture
    n = r.standard_normal((H, W), dtype=F32) * 4
    img += (n * skin_m)[..., None]
    # key light from camera left: lit side brighter, shadow side and under-chin darker
    light = np.interp(xx[0], [560, 1000, 1450], [1.12, 1.0, 0.62]).astype(F32)
    person = np.maximum.reduce([skin_m, full_mask(hair_back, W, H), full_mask(front, W, H)])
    img *= (1 + (light[None, :] - 1) * person)[..., None]
    c = Canvas((830, 1690, 1170, 1800), ss=2, pad=60)
    c.ellipse(1000, 1735, 170, 55)
    darken(img, _m2_mk(c, blur=30), 0.35)
    # specular-ish highlights on the lit cheek, forehead and nose bridge
    for cx, cy, rad, amt in ((780, 1200, 150, 26), (930, 830, 170, 20), (1015, 1150, 60, 18)):
        sig = rad / 2
        g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sig * sig)) * skin_m
        img += (g * amt)[..., None]
    add_noise(img, 2.2, r, mono=True)
    return np.clip(img, 0, 255)


def _m2_gray_card(img, x0, y0, x1, y1, label=True):
    w = (x1 - x0) / 3
    for k, v in enumerate((12, 118, 245)):
        img[y0:y1, int(round(x0 + k * w)):int(round(x0 + (k + 1) * w))] = v
    if label:
        c = Canvas((x0, y0 - 44, x1, y0 - 4), ss=3)
        c.text((x0 + x1) / 2, y0 - 24, "GRAY CARD", 28, bold=True, anchor="mm")
        paint(img, c.mask(), (235, 235, 235))


def _m2_down(img, W, H):
    return np.asarray(Image.fromarray(to_u8(img)).resize((W, H), Image.LANCZOS), F32)


def m2_portrait_studio():
    """L05 main file: the portrait with a mild warm/yellow cast and ~2/3 stop under,
    so learners correct to a neutral base before grading."""
    name = "l05-portrait-studio.jpg"
    img = _m2_portrait_clean().copy()
    _m2_gray_card(img, 1480, 2280, 1900, 2420)
    img[..., 0] = img[..., 0] * 1.03 + 6
    img[..., 1] = img[..., 1] * 1.00 + 3
    img[..., 2] = img[..., 2] * 0.86
    img *= 0.80
    img = _m2_down(np.clip(img, 0, 255), 1600, 2000)
    save_jpg(img, 2, name, quality=91, subsampling=0)


def m2_companion_portrait():
    """L06 match file: same sitter, tighter crop, 'window light': cool/blue-magenta cast,
    brighter and lower contrast than the L05 file. Gray card in a different place."""
    name = "l06-companion-portrait.jpg"
    img = _m2_portrait_clean()[250:2350, 150:1830].copy()           # 1680 x 2100 crop
    _m2_gray_card(img, 90, 1900, 510, 2040)
    img[..., 0] = img[..., 0] * 0.86
    img[..., 1] = img[..., 1] * 0.93 + 2
    img[..., 2] = img[..., 2] * 1.06 + 14
    img = 38 + img * 0.80
    img = _m2_down(np.clip(img, 0, 255), 1440, 1800)
    save_jpg(img, 2, name, quality=91, subsampling=0)


# --------------------------------------------------------------------------------------
# L05 (Lesson 2.2): grading targets
# --------------------------------------------------------------------------------------

def m2_pier_dusk():
    """The 'different photo' a LUT is poured onto (and a landscape to grade): a pier at
    sunset, straight-out-of-camera flat and neutral."""
    name = "l05-pier-dusk.jpg"
    W, H = 2400, 1600
    r = rng(name)
    xx, yy = coords(W, H)
    hz = 760
    img = np.empty((H, W, 3), F32)
    img[:hz] = vgrad(W, hz, [(0, (78, 98, 138)), (0.55, (170, 150, 150)), (1, (236, 190, 150))])
    d = np.hypot((xx - 1650) / 600, (yy - hz) / 260)
    img += (np.exp(-d ** 2 * 3) * (yy < hz))[..., None] * np.array((40, 30, 10), F32)
    c = Canvas((1560, hz - 90, 1740, hz + 5), ss=3)
    c.circle(1650, hz - 20, 70)
    paint(img, c.mask(blur=2), (252, 232, 190))
    img[hz:hz + 3] = (190, 160, 140)
    # sea: reflected sky + horizontal ripples
    t = (yy[hz:] - hz) / (H - hz)
    sea = vgrad(W, H - hz, [(0, (160, 140, 140)), (0.3, (92, 100, 118)), (1, (40, 52, 68))])
    rip = r.standard_normal((H - hz, W // 24), dtype=F32)
    rip = np.asarray(Image.fromarray(rip).resize((W, H - hz), Image.BILINEAR), F32)
    sea += (rip * (6 + 10 * t))[..., None]
    glit = np.exp(-((xx[hz:] - 1650) / (60 + 260 * t)) ** 2) * (rip > 0.6) * (1 - t) * 90
    sea += glit[..., None] * np.array((1, 0.85, 0.6), F32)
    img[hz:] = sea
    # the pier: deck converging to a vanishing point near the sun, with posts and a lamp
    vp = (1500, hz)
    c = Canvas((0, hz - 10, W, H), ss=2)
    c.poly([(-200, H), (1100, H), (vp[0] + 8, vp[1] + 6), (vp[0] - 8, vp[1] + 6)])
    paint(img, c.mask(), (70, 55, 45))
    for k in range(18):
        f = (k / 17) ** 1.8
        yk = vp[1] + 6 + (H - vp[1] - 6) * f
        xl = vp[0] + (-200 - vp[0]) * f
        xr = vp[0] + (1100 - vp[0]) * f
        img[int(yk):int(yk) + max(1, int(3 * f + 1)), max(0, int(xl)):int(xr)] *= 0.6
        pw, ph = 4 + 30 * f, 20 + 260 * f
        c = Canvas((xl - pw - 2, yk - ph, xr + pw + 2, yk + 4), ss=2)
        c.rect(xl - pw, yk - ph, xl, yk)
        c.rect(xr, yk - ph, xr + pw, yk)
        paint(img, c.mask(), (46, 38, 34))
    c = Canvas((680, 380, 760, 1290), ss=3)
    c.rect(712, 420, 726, 1280)
    c.rect(690, 390, 748, 430)
    paint(img, c.mask(), (35, 32, 32))
    c = Canvas((620, 330, 820, 490), pad=10)
    c.circle(719, 410, 55)
    paint(img, c.mask(blur=18), (255, 225, 170), 0.55)
    # flatten: a neutral, lifted "straight out of camera" rendering
    img = 22 + img * 0.84
    add_noise(img, 2.5, r, mono=True)
    save_jpg(img, 2, name, quality=90, subsampling=0)


def m2_grade_test_chart():
    """Tones and colors in, colors out: a gray ramp, 11 gray steps, a hue x lightness
    field and memory-color patches. Drop a Gradient Map or Color Lookup on it and every
    remap is visible at a glance."""
    name = "l05-grade-test-chart.png"
    W, H = 2000, 1300
    img = np.full((H, W, 3), 128, F32)
    ramp = np.linspace(0, 255, W - 160, dtype=F32)
    img[80:230, 80:W - 80] = ramp[None, :, None]
    step_w = (W - 160) / 11
    for k in range(11):
        v = round(k * 25.5)
        img[260:400, int(80 + k * step_w):int(80 + (k + 1) * step_w)] = v
    img[256:260, 76:W - 76] = 20                                  # frame so the 50% step shows
    img[400:404, 76:W - 76] = 20
    img[256:404, 76:80] = 20
    img[256:404, W - 80:W - 76] = 20
    for k in range(1, 11):
        x = int(80 + k * step_w)
        img[260:400, x - 1:x + 1] = 20
    # hue x lightness field
    fx0, fy0, fw, fh = 80, 440, W - 160, 520
    hx = np.linspace(0, 1, fw, endpoint=False)
    ly = np.linspace(0.9, 0.1, fh)
    Hh, Ll = np.meshgrid(hx, ly)
    S = 0.75
    Cc = (1 - np.abs(2 * Ll - 1)) * S
    Hp = Hh * 6
    X = Cc * (1 - np.abs(Hp % 2 - 1))
    z = np.zeros_like(Hp)
    idx = np.floor(Hp).astype(int) % 6
    rgb = np.select([idx[..., None] == i for i in range(6)],
                    [np.stack(v, -1) for v in ((Cc, X, z), (X, Cc, z), (z, Cc, X),
                                               (z, X, Cc), (X, z, Cc), (Cc, z, X))])
    rgb += (Ll - Cc / 2)[..., None]
    img[fy0:fy0 + fh, fx0:fx0 + fw] = rgb * 255
    patches = [("dark skin", (115, 80, 64)), ("light skin", (196, 150, 128)), ("sky", (94, 122, 157)),
               ("foliage", (88, 108, 66)), ("teal", (40, 128, 130)), ("gold", (215, 170, 70)),
               ("neutral 8", (200, 200, 200)), ("neutral 3.5", (52, 52, 52))]
    pw = (W - 160) / len(patches)
    for k, (lab, col) in enumerate(patches):
        x0 = int(80 + k * pw) + 6
        img[1000:1170, x0:int(x0 + pw - 12)] = col
        c = Canvas((x0, 1180, x0 + pw, 1230), ss=3)
        c.text(x0 + (pw - 12) / 2, 1205, lab, 26, bold=True, anchor="mm")
        paint(img, c.mask(), (20, 20, 20))
    c = Canvas((0, 0, W, 80), ss=3)
    c.text(80, 42, "GRADE TEST CHART  ·  gray ramp  ·  11 steps  ·  hue × lightness  ·  memory colors",
           30, bold=True, anchor="lm")
    paint(img, c.mask(), (15, 15, 15))
    save_png(img, 2, name)


def m2_fallback_lut():
    """Instructor-only 17-point .cube: a gentle S-curve with teal shadows and warm
    highlights, for anyone whose own LUT export fails before the transfer test."""
    name = "l05-teal-gold-fallback.cube"
    N = 17
    v = np.linspace(0, 1, N)

    def s_curve(x):                            # monotonic S: darker shadows, brighter highlights
        return x - 0.08 * np.sin(2 * np.pi * x)

    lines = ['TITLE "Teal-Gold fallback (course practice)"',
             "# Photoshop Intermediate instructor kit, Module 2 (Lesson 2.2). Free to use.",
             f"LUT_3D_SIZE {N}", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    for b in v:
        for g in v:
            for rr in v:                       # red changes fastest (.cube convention)
                rgb = np.array([rr, g, b])
                y = rgb @ np.array([0.2126, 0.7152, 0.0722])
                out = s_curve(rgb)
                sh = (1 - y) ** 2.2                   # shadow weight
                hi = y ** 2.2                          # highlight weight
                out = out + sh * np.array((-0.045, 0.012, 0.050)) + hi * np.array((0.035, 0.010, -0.055))
                out = np.clip(out, 0, 1)
                lines.append(f"{out[0]:.6f} {out[1]:.6f} {out[2]:.6f}")
    p = out_path(2, name, "instructor")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    _record(p)


# --------------------------------------------------------------------------------------
# L06 (Lesson 2.3): a set to match, and a print-killer to soft-proof
# --------------------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _m2_still_life():
    """Neutral daylight still life: mug, lemon, linen, wooden board, gray card."""
    W, H = 1800, 1200
    r = rng("m2-still-life")
    img = vgrad(W, H, [(0, (196, 192, 186)), (0.58, (172, 168, 162)), (0.6, (150, 110, 78)), (1, (118, 84, 58))])
    tb = int(H * 0.6)
    for y in range(tb + 8, H, 22):                              # board grain
        img[y:y + 2] *= 0.9
    add_noise(img[tb:], 6, r, mono=True)
    c = Canvas((60, 700, 760, 1080), ss=2)                      # folded linen
    c.poly([(80, 1060), (140, 760), (720, 740), (740, 1040)])
    paint(img, c.mask(blur=1), (236, 232, 222))
    c = Canvas((60, 700, 760, 1080), ss=2)
    c.line([(150, 880), (720, 865)], 5)
    darken(img, c.mask(blur=3), 0.12)
    c = Canvas((820, 360, 1300, 960), ss=3)                     # mug: body + handle, then rim
    c.rect(880, 460, 1160, 900)
    c.ellipse(1020, 900, 140, 30)
    c.d.arc(c.B(1070, 520, 1250, 780), 270, 90, fill=255, width=34 * 3)
    mug = c.mask()
    paint(img, mug, (60, 92, 140))
    shade = np.interp(np.arange(W), [880, 1300], [1.15, 0.68]).astype(F32)
    mm = full_mask(mug, W, H)
    img *= (1 + (shade[None, :] - 1) * mm)[..., None]
    c = Canvas((820, 360, 1300, 960), ss=3)
    c.ellipse(1020, 460, 140, 32)
    paint(img, c.mask(), (40, 62, 98))
    c = Canvas((1300, 760, 1640, 1000), ss=3)                   # lemon
    c.ellipse(1470, 880, 150, 100)
    paint(img, c.mask(blur=1), (235, 200, 40))
    c = Canvas((1300, 760, 1640, 1000), ss=3)
    c.ellipse(1430, 850, 60, 30)
    paint(img, c.mask(blur=12), (255, 245, 170), 0.7)
    c = Canvas((780, 880, 1720, 1060), pad=20)                  # contact shadows
    c.ellipse(1020, 915, 170, 26)
    c.ellipse(1480, 985, 150, 22)
    darken(img, c.mask(blur=14), 0.45)
    _m2_gray_card(img, 1250, 1060, 1650, 1170, label=False)
    add_noise(img, 2, r, mono=True)
    return np.clip(img, 0, 255)


def m2_match_set():
    """Three frames of one set in three lights: a = daylight reference, b = tungsten
    (warm, dark), c = open shade (blue, flat). Match b and c to a."""
    looks = {
        "l06-set-a-daylight.jpg": ((1.0, 0), (1.0, 0), (1.0, 0), 1.0, 0),
        "l06-set-b-tungsten.jpg": ((1.08, 10), (0.94, 0), (0.66, 0), 0.78, 0),
        "l06-set-c-shade.jpg": ((0.88, 0), (0.97, 0), (1.10, 12), 0.72, 52),
    }
    for name, (rr, gg, bb, gain, lift) in looks.items():
        img = _m2_still_life().copy()
        for ch, (m, a) in enumerate((rr, gg, bb)):
            img[..., ch] = img[..., ch] * m + a
        img = lift + img * gain
        save_jpg(np.clip(img, 0, 255), 2, name, quality=90, subsampling=0)


def m2_neon_proof():
    """A night street with neon in sRGB's most saturated corners (pure blue, magenta,
    acid green, orange-red) next to muted, printable areas: the Gamut Warning lights up
    the neon and leaves the brick, wood and skin-tone poster alone."""
    name = "l06-neon-proof.jpg"
    W, H = 2000, 1334
    r = rng(name)
    img = np.empty((H, W, 3), F32)
    wall_h = 980
    img[:wall_h] = (78, 44, 38)                                  # brick wall
    for y in range(0, wall_h, 44):
        off = 0 if (y // 44) % 2 else 48
        img[y:y + 5] = (52, 46, 44)
        for x in range(off, W, 96):
            img[y:y + 44, x:x + 5] = (52, 46, 44)
            img[y + 5:y + 44, x + 5:x + 96] *= r.uniform(0.85, 1.15)
    img[wall_h:] = vgrad(W, H - wall_h, [(0, (40, 40, 46)), (1, (22, 22, 26))])   # wet pavement
    add_noise(img, 6, r, mono=True)
    # a wooden door and a muted poster (printable colors)
    img[420:wall_h, 1560:1800] = (96, 66, 44)
    img[430:wall_h, 1575:1785] *= 0.9
    img[150:520, 120:420] = (206, 178, 150)
    img[190:400, 170:370] = (170, 120, 100)
    c = Canvas((120, 410, 420, 510), ss=3)
    c.text(270, 460, "JAZZ · FRI", 44, bold=True, anchor="mm")
    paint(img, c.mask(), (60, 50, 50))
    glow = np.zeros_like(img)

    def neon(draw, col, width, blur_r=26):
        c = Canvas((0, 0, W, wall_h), ss=2)
        draw(c, width)
        core = full_mask(c.mask(blur=1.0), W, H)
        halo = full_mask(Canvas.mask(c, blur=blur_r), W, H)
        glow[...] += halo[..., None] * np.array(col, F32) * 0.9
        return core, col

    tubes = [
        neon(lambda c, w: c.text(980, 330, "OPEN", 260, bold=True, anchor="mm"), (255, 0, 190), 0),
        neon(lambda c, w: c.line([(620, 560), (1300, 560), (1250, 510), (1300, 560), (1250, 610)], 16, round_caps=True),
             (20, 70, 255), 16),
        neon(lambda c, w: c.line(quad_bezier((640, 820), (980, 640), (1320, 820), 60), 16, round_caps=True),
             (40, 255, 60), 16),
        neon(lambda c, w: c.line([(1400, 130), (1400, 880)], 14, round_caps=True), (255, 70, 0), 14),
    ]
    img += glow * 0.8
    for core, col in tubes:
        img = img * (1 - core[..., None]) + np.array(col, F32) * core[..., None]
    # a hot white-ish tube center on OPEN keeps it believable
    # reflections in the wet pavement
    refl = np.flipud(img[wall_h - (H - wall_h):wall_h]) * 0.35
    refl = blur_img(refl, 6)
    img[wall_h:] = np.clip(img[wall_h:] * 0.7 + refl, 0, 255)
    save_jpg(np.clip(img, 0, 255), 2, name, quality=92, subsampling=0)


# ======================================================================================
# Module 3: High-End Retouching
# ======================================================================================

# ======================================================================================
# MODULE 3: High-End Retouching        (one illustrated face, drawn at any scale/offset)
# ======================================================================================
#
# Every portrait file is the same face drawn through a transform (design coordinates are
# a 2000 x 2500 head-and-shoulders frame; face centre (1000, 1230)). Skin gets real
# multi-scale pore texture drawn at FINAL pixel size (pore size in px is a parameter, so
# the close-up, the standard portrait and the candid need different blur radii), plus
# optional low-frequency blotches, high-frequency blemishes, flat window light from the
# viewer's left, dull eyes, yellowed teeth, flyaway hairs and a thin gap in the hair.

_M3_SKIN = np.array((222, 176, 150), F32)
_M3_HAIR = np.array((58, 42, 32), F32)
_M3_EYES = (835, 1165)
_M3_EYE_Y = 1110

# low-frequency tone patches: (cx, cy, radius, (dR, dG, dB), label)
_M3_TONE = [
    (1000, 1330, 85, (26, -10, -6), "redness, nose"),
    (790, 1330, 150, (20, -8, -6), "redness, cheek"),
    (1210, 1330, 150, (20, -8, -6), "redness, cheek"),
    (1080, 820, 120, (14, -4, -2), "uneven forehead"),
    (1000, 1790, 100, (16, -5, -2), "redness, chin"),
    (835, 1190, 70, (-16, -20, -8), "muddy under-eye"),
    (1165, 1190, 70, (-16, -20, -8), "muddy under-eye"),
    (620, 1000, 100, (0, 6, -12), "sallow temple"),
    (1330, 1640, 90, (-6, -16, 6), "purplish jaw"),
]
# high-frequency blemishes: (x, y, radius, whitehead)
_M3_BLEM = [(1130, 760, 9, False), (900, 860, 7, True), (690, 1240, 10, False),
            (760, 1450, 8, False), (1265, 1455, 11, True), (1330, 1400, 7, False),
            (1180, 1700, 9, False), (930, 1760, 8, False), (1110, 1215, 6, False),
            (640, 1540, 9, False)]
_M3_FRECKLES = (1000, 1250, 300, 95)
_M3_MOLE = (800, 1600)
# sculpting map for this face (light from the viewer's left): (cx, cy, rx, ry, amount)
_M3_DODGE = [(1000, 790, 170, 120, .07), (990, 1240, 26, 150, .06), (770, 1215, 120, 60, .07),
             (1225, 1215, 100, 55, .045), (1000, 1805, 85, 60, .05), (830, 1030, 80, 30, .05),
             (1170, 1030, 75, 28, .035)]
_M3_BURN = [(560, 960, 90, 180, .06), (1445, 960, 90, 180, .08), (745, 1345, 110, 55, .05),
            (1262, 1345, 110, 55, .07), (610, 1600, 110, 170, .05), (1395, 1600, 110, 170, .07),
            (908, 1080, 38, 45, .05), (1092, 1080, 38, 45, .06), (955, 1300, 26, 80, .04),
            (1048, 1300, 26, 80, .05), (1000, 1945, 230, 60, .08)]


class _M3T:
    """Design coords -> pixels: X = ox + s * x."""

    def __init__(self, s=1.0, ox=0.0, oy=0.0):
        self.s, self.ox, self.oy = float(s), float(ox), float(oy)

    def p(self, x, y):
        return (self.ox + self.s * x, self.oy + self.s * y)

    def pts(self, pts):
        return [self.p(x, y) for x, y in pts]

    def box(self, x0, y0, x1, y1):
        a, b = self.p(x0, y0), self.p(x1, y1)
        return (a[0], a[1], b[0], b[1])


def _m3_cv(t, box, ss=2, pad=6):
    return Canvas(t.box(*box), ss=ss, resample=Image.LANCZOS, pad=pad)


def _m3_full(c, W, H, blur=0.0):
    m = c.mask(blur)
    return full_mask(Mask(m.x, m.y, np.clip(m.a, 0, 1)), W, H)


def _m3_gblur(a, sigma):
    """Separable Gaussian blur of a 2-D float array (small sigmas)."""
    rad = max(1, int(math.ceil(3 * sigma)))
    k = np.exp(-(np.arange(-rad, rad + 1) ** 2) / (2 * sigma * sigma)).astype(F32)
    k /= k.sum()
    for ax in (0, 1):
        out = np.zeros_like(a)
        for i, w in zip(range(-rad, rad + 1), k):
            out += w * np.roll(a, i, axis=ax)
        a = out
    return a


def _m3_noise(r, W, H, scale):
    """Unit-variance noise with feature size ~scale px."""
    if scale <= 1.05:
        return r.standard_normal((H, W), dtype=F32)
    h, w = int(H / scale) + 3, int(W / scale) + 3
    n = Image.fromarray(r.standard_normal((h, w), dtype=F32), "F")
    n = np.asarray(n.resize((int(w * scale), int(h * scale)), Image.BICUBIC), F32)[:H, :W]
    return (n - n.mean()) / (n.std() + 1e-6)


def _m3_gauss(shape, t, cx, cy, rx, ry=None):
    """Local window + Gaussian (sigma = radius / 2), for adding into an (H, W[, 3]) array."""
    ry = rx if ry is None else ry
    H, W = shape[:2]
    px, py = t.p(cx, cy)
    sx, sy = max(rx * t.s / 2, 0.5), max(ry * t.s / 2, 0.5)
    x0, x1 = int(max(px - 4 * sx, 0)), int(min(px + 4 * sx, W))
    y0, y1 = int(max(py - 4 * sy, 0)), int(min(py + 4 * sy, H))
    if x0 >= x1 or y0 >= y1:
        return None
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(F32)
    g = np.exp(-((xx + .5 - px) ** 2 / (2 * sx * sx) + (yy + .5 - py) ** 2 / (2 * sy * sy)))
    return (slice(y0, y1), slice(x0, x1)), g


def _m3_pores(img, skin_m, r, p, amp, zone):
    """Multi-scale skin texture at pore size p (px): grain + mottling + lit pore pits."""
    H, W = skin_m.shape
    g = _m3_noise(r, W, H, max(p * 0.45, 1.0)) * 0.55 + _m3_noise(r, W, H, p * 2.2) * 0.3
    k = int(W * H / (p * p * 7))
    ys, xs = r.integers(0, H, k), r.integers(0, W, k)
    imp = np.zeros((H, W), F32)
    np.add.at(imp, (ys, xs), r.uniform(0.5, 1.0, k).astype(F32))
    sig = max(p * 0.38, 0.55)
    pit = _m3_gblur(imp, sig) * F32(2 * np.pi * sig * sig)
    sh = max(1, int(round(p * 0.35)))
    rim = np.roll(np.roll(pit, sh, 0), sh, 1)                    # far wall catches the light
    n = (g * 0.6 - pit * 2.2 + rim * 0.7) * amp * zone
    img += (n * skin_m)[..., None] * np.array((1.0, 0.97, 0.95), F32)
    np.clip(img, 0, 255, out=img)


def _m3_curve(img, t, W, H, p0, p1, p2, width, color, opacity=1.0, blur=0.35):
    xs, ys = zip(p0, p1, p2)
    c = _m3_cv(t, (min(xs), min(ys), max(xs), max(ys)), ss=3, pad=8)
    c.line(t.pts(quad_bezier(p0, p1, p2, 90)), max(width * t.s, 0.8))
    paint(img, c.mask(blur=blur * max(t.s, .6)), color, opacity)


def _m3_blemish(img, skin_m, t, x, y, rad, white):
    H, W = skin_m.shape
    px, py = t.p(x, y)
    R = rad * t.s * 2.0
    x0, x1, y0, y1 = int(px - R - 3), int(px + R + 4), int(py - R - 3), int(py + R + 4)
    if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H:
        return
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(F32)
    d = np.hypot(xx + .5 - px, yy + .5 - py)
    sm = skin_m[y0:y1, x0:x1]
    a = (np.clip(1 - d / R, 0, 1) ** 1.2 * 0.85 * sm)[..., None]
    reg = img[y0:y1, x0:x1]
    reg[:] = reg * (1 - a) + np.array((198, 104, 96), F32) * a
    s = 0.3 * R
    hl = np.exp(-(((xx + .5 - (px - .35 * R)) ** 2 + (yy + .5 - (py - .35 * R)) ** 2) / (2 * s * s)))
    shd = np.exp(-(((xx + .5 - (px + .35 * R)) ** 2 + (yy + .5 - (py + .35 * R)) ** 2) / (2 * s * s)))
    reg += ((18 * hl - 14 * shd) * sm)[..., None]
    if white:
        s = max(0.2 * rad * t.s, 0.6)
        wh = (np.exp(-((xx + .5 - px) ** 2 + (yy + .5 - py) ** 2) / (2 * s * s)) * 0.9 * sm)[..., None]
        reg[:] = reg * (1 - wh) + np.array((240, 226, 204), F32) * wh
    np.clip(reg, 0, 255, out=reg)


def _m3_freckles(r, n):
    cx, cy, rx, ry = _M3_FRECKLES
    avoid = [(x, y, rr * 1.8) for x, y, rr, _ in _M3_BLEM]
    pts = []
    while len(pts) < n:
        x, y = cx + r.uniform(-rx, rx), cy + r.uniform(-ry, ry)
        if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 > 1:
            continue
        if any(abs(x - ex) < 110 and abs(y - _M3_EYE_Y) < 60 for ex in _M3_EYES):
            continue
        rad = float(r.uniform(3, 5.5))
        if any(math.hypot(x - ax, y - ay) < 14 + ar + rad for ax, ay, ar in avoid):
            continue
        if any(math.hypot(x - px, y - py) < 14 for px, py, _ in pts):
            continue
        pts.append((x, y, rad))
    return pts


def _m3_face(W, H, t, r, *, tone=1.0, blemish=True, sculpt=False, pore=2.2, bg=None, info=None):
    """Draw the portrait. Returns the float RGB image. `info` (dict) receives flaw positions."""
    full_px = (W, H)
    X, Y = coords(W, H)
    xd, yd = (X - t.ox) / t.s, (Y - t.oy) / t.s                   # design coordinates
    if bg is None:
        bg = hgrad(W, H, [(0, (202, 209, 218)), (1, (136, 145, 160))])
        bg *= np.interp(yd, [0, 2500], [1.02, 0.94])[..., None]
    img = bg.copy()

    lat = np.interp(xd, [440, 1560], [1.035, 0.955]).astype(F32)       # soft window light, left
    d = np.sqrt(((xd - 1000) / 520) ** 2 + ((yd - 1230) / 680) ** 2)
    edge = 1 - 0.09 * np.clip((d - 0.7) / 0.3, 0, 1) ** 1.5
    under_chin = np.interp(yd, [1860, 1990], [0.84, 0.97]).astype(F32)
    skin_arr = _M3_SKIN * (lat * edge)[..., None]

    # ---- hair (back mass + strands) -----------------------------------------------------
    hb = (300, 220, 1700, 2070)
    c = _m3_cv(t, hb)
    c.ellipse(*t.p(1000, 1060), 700 * t.s, 820 * t.s)
    c.rrect(*t.box(320, 1000, 1680, 2050), 260 * t.s)
    hair_back = _m3_full(c, W, H)
    c = Canvas(t.box(*hb), ss=1, pad=6)
    for side in (-1, 1):
        for _ in range(260 if side < 0 else 300):
            sx = 880 + r.uniform(-8, 8)
            sy = r.uniform(300, 640)
            ex = 1000 + side * r.uniform(420, 690)
            ey = r.uniform(1250, 2060)
            cx = 1000 + side * r.uniform(520, 760)
            cy = r.uniform(420, 900)
            c.line(t.pts(quad_bezier((sx, sy), (cx, cy), (ex, ey), 50)), max(2.2 * t.s, 1),
                   fill=int(r.integers(70, 256)))
    strands = full_mask(c.mask(blur=0.5 * max(t.s, .6)), W, H)
    hlat = np.interp(xd, [320, 1680], [1.14, 0.9]).astype(F32)
    hair_arr = _M3_HAIR * ((0.7 + 0.6 * strands) * hlat)[..., None]
    paint(img, Mask(0, 0, hair_back), hair_arr)
    # a thin gap in the hair mass (background shows through), viewer's right
    gap_pts = [(1598, 1150), (1625, 1300), (1612, 1470)]
    c = _m3_cv(t, (1560, 1120, 1660, 1500))
    c.line(t.pts(quad_bezier(*gap_pts, 60)), 11 * t.s, round_caps=True)
    paint(img, Mask(0, 0, _m3_full(c, W, H, blur=3 * t.s) * hair_back), bg * 0.9, 0.8)

    # ---- neck, clothing, face --------------------------------------------------------------
    c = _m3_cv(t, (790, 1650, 1210, 2300))
    c.rect(*t.box(790, 1650, 1210, 2300))
    neck = _m3_full(c, W, H)
    paint(img, Mask(0, 0, neck), skin_arr * under_chin[..., None] * 0.97)
    c = _m3_cv(t, (-100, 2040, 2100, 3500))
    c.ellipse(*t.p(1000, 2780), 1080 * t.s, 720 * t.s)
    cloth = _m3_full(c, W, H)
    paint(img, Mask(0, 0, cloth), np.array((58, 72, 96), F32) * np.interp(xd, [0, 2000], [1.15, .85])[..., None])
    th = np.linspace(0, 2 * np.pi, 240, endpoint=False)
    face_pts = [(1000 + 520 * math.cos(a) * (1 - 0.17 * max(math.sin(a), 0) ** 2), 1230 + 680 * math.sin(a)) for a in th]
    c = _m3_cv(t, (470, 540, 1530, 1920))
    c.poly(t.pts(face_pts))
    face = _m3_full(c, W, H)
    paint(img, Mask(0, 0, face), skin_arr)

    # fringe with a side part at x = 880
    xs = np.arange(400, 1601, 8, dtype=float)
    hy = np.where(xs < 880, 600 + 300 * (np.clip(880 - xs, 0, None) / 460) ** 1.6,
                  600 + 380 * (np.clip(xs - 880, 0, None) / 700) ** 1.3) + 8 * np.sin(xs / 37)
    c = _m3_cv(t, (380, 200, 1620, 1100))
    c.poly(t.pts([(380, 200)] + list(zip(xs, np.minimum(hy, 1080))) + [(1620, 200)]))
    fringe = _m3_full(c, W, H) * hair_back
    paint(img, Mask(0, 0, fringe), hair_arr)

    skin_m = np.maximum(face, neck) * (1 - fringe) * (1 - cloth)

    # ---- low-frequency tone ---------------------------------------------------------------
    if tone:
        for cx, cy, rad, dv, _ in _M3_TONE:
            w = _m3_gauss(img.shape, t, cx, cy, rad)
            if w:
                sl, g = w
                img[sl] += (g * skin_m[sl])[..., None] * (np.array(dv, F32) * tone)

    # ---- permanent features: freckles, mole, laugh lines -------------------------------------
    for x, y, rad in _m3_freckles(r, 36):
        c = _m3_cv(t, (x - rad, y - rad, x + rad, y + rad), ss=4, pad=4)
        c.circle(*t.p(x, y), rad * t.s)
        paint(img, c.mask(blur=0.6 * t.s), (168, 116, 92), float(r.uniform(.5, .75)))
    c = _m3_cv(t, (_M3_MOLE[0] - 10, _M3_MOLE[1] - 10, _M3_MOLE[0] + 10, _M3_MOLE[1] + 10), ss=4)
    c.circle(*t.p(*_M3_MOLE), 9 * t.s)
    paint(img, c.mask(blur=0.5 * t.s), (92, 58, 44))
    c = _m3_cv(t, (820, 1430, 1180, 1680), ss=3, pad=10)
    for p in (((905, 1450), (858, 1530), (880, 1645)), ((1095, 1450), (1142, 1530), (1120, 1645))):
        c.line(t.pts(quad_bezier(*p, 40)), 5 * t.s)
    darken(img, c.mask(blur=4 * t.s), 0.10)

    # ---- nose ---------------------------------------------------------------------------
    c = _m3_cv(t, (1010, 1120, 1080, 1390))
    c.line(t.pts([(1035, 1140), (1058, 1370)]), 10 * t.s, round_caps=True)
    darken(img, c.mask(blur=6 * t.s), 0.08)
    c = _m3_cv(t, (930, 1390, 1070, 1420))
    c.ellipse(*t.p(962, 1405), 18 * t.s, 9 * t.s)
    c.ellipse(*t.p(1038, 1405), 18 * t.s, 9 * t.s)
    darken(img, c.mask(blur=1.2 * t.s), 0.45)
    c = _m3_cv(t, (920, 1340, 1080, 1420), ss=3)
    c.line(t.pts(quad_bezier((935, 1360), (925, 1395), (948, 1412), 20)), 4 * t.s)
    c.line(t.pts(quad_bezier((1065, 1360), (1075, 1395), (1052, 1412), 20)), 4 * t.s)
    darken(img, c.mask(blur=3 * t.s), 0.10)

    # ---- eyebrows (hair strokes) ------------------------------------------------------------
    c = _m3_cv(t, (700, 940, 1300, 1060), ss=3)
    for ex in _M3_EYES:
        sgn = -1 if ex < 1000 else 1
        arc = quad_bezier((ex - sgn * 100, 1020), (ex - sgn * 10, 975), (ex + sgn * 105, 1012), 70)
        for i in range(170):
            k = int(r.integers(4, 66))
            (x0, y0), (x1, y1) = arc[k - 2], arc[k + 2]
            ox, oy = r.uniform(-4, 4), r.uniform(-9, 9) * (1 - abs(k - 35) / 50)
            c.line(t.pts([(x0 + ox, y0 + oy + 4), (x1 + ox, y1 + oy - 3)]), 1.7 * t.s)
    paint(img, c.mask(blur=0.4 * t.s), (72, 52, 40), 0.9)

    # ---- eyes (dull whites, textured iris, sacred catchlight) --------------------------------
    feat = np.zeros((H, W), F32)
    ey = _M3_EYE_Y
    for ex in _M3_EYES:
        top = quad_bezier((ex - 95, ey), (ex, ey - 72), (ex + 95, ey - 2), 50)
        bot = quad_bezier((ex + 95, ey - 2), (ex, ey + 58), (ex - 95, ey), 50)
        box = (ex - 110, ey - 80, ex + 110, ey + 70)
        c = _m3_cv(t, box)
        c.poly(t.pts(top + bot))
        ew = _m3_full(c, W, H)
        inner = 1 if ex < 1000 else -1                             # toward the nose
        paint(img, Mask(0, 0, ew), (206, 198, 188))
        w = _m3_gauss(img.shape, t, ex + inner * 80, ey, 40, 30)
        if w:
            sl, g = w
            img[sl] += (g * ew[sl])[..., None] * np.array((8, -10, -8), F32)
        c = _m3_cv(t, box, ss=3)
        for _ in range(3):
            y0 = ey + r.uniform(-12, 12)
            for side in (-1, 1):
                x0 = ex + side * 92
                c.line(t.pts(quad_bezier((x0, y0), (x0 - side * 25, y0 + r.uniform(-12, 12)),
                                         (x0 - side * r.uniform(40, 60), y0 + r.uniform(-15, 15)), 20)), 1.3 * t.s)
        paint(img, Mask(0, 0, _m3_full(c, W, H, blur=.4 * t.s) * ew), (176, 96, 92), 0.35)
        # iris
        c = _m3_cv(t, box)
        c.circle(*t.p(ex, ey - 4), 41 * t.s)
        iris = _m3_full(c, W, H) * ew
        paint(img, Mask(0, 0, iris), (104, 76, 50))
        c = _m3_cv(t, box, ss=3)
        for i in range(80):
            a = 2 * np.pi * i / 80 + r.uniform(-.03, .03)
            r0, r1 = 17 + r.uniform(0, 4), 36 + r.uniform(-4, 3)
            c.line(t.pts([(ex + r0 * math.cos(a), ey - 4 + r0 * math.sin(a)),
                          (ex + r1 * math.cos(a), ey - 4 + r1 * math.sin(a))]),
                   1.4 * t.s, fill=int(r.integers(0, 256)))
        stri = _m3_full(c, W, H, blur=.3 * t.s)
        img += ((stri - .45) * 38 * iris)[..., None] * np.array((1, .85, .6), F32)
        c = _m3_cv(t, box)
        c.circle(*t.p(ex, ey - 4), 41 * t.s)
        c.circle(*t.p(ex, ey - 4), 35 * t.s, fill=0)
        paint(img, Mask(0, 0, _m3_full(c, W, H, blur=1.5 * t.s) * iris), (44, 30, 22), 0.8)
        c = _m3_cv(t, box)
        c.circle(*t.p(ex, ey - 4), 16 * t.s)
        paint(img, Mask(0, 0, _m3_full(c, W, H, blur=.5 * t.s) * ew), (14, 11, 10))
        # upper-lid shadow over the eyeball
        lid = np.clip(1 - (yd - (ey - 58)) / 45, 0, 1) * ew
        img *= (1 - 0.28 * lid)[..., None]
        c = _m3_cv(t, box, ss=4)
        c.ellipse(*t.p(ex - 14, ey - 18), 7 * t.s, 6 * t.s)
        paint(img, c.mask(blur=.4 * t.s), (252, 252, 250))
        # lid line, lashes, lower lid, crease
        c = _m3_cv(t, (ex - 120, ey - 110, ex + 120, ey + 70), ss=3)
        c.line(t.pts(top), 5 * t.s)
        for i in range(5, 48, 2):
            x0, y0 = top[i]
            L = 9 + 6 * math.sin(math.pi * i / 50) + r.uniform(-1.5, 1.5)
            c.line(t.pts(quad_bezier((x0, y0), (x0 + (x0 - ex) * .06, y0 - L * .7),
                                     (x0 + (x0 - ex) * .16 + L * .1, y0 - L), 8)), 1.3 * t.s)
        paint(img, c.mask(blur=.35 * t.s), (38, 27, 22))
        c = _m3_cv(t, (ex - 110, ey - 130, ex + 110, ey + 70), ss=2)
        c.line(t.pts(bot), 2.5 * t.s)
        darken(img, c.mask(blur=1.5 * t.s), 0.15)
        c = _m3_cv(t, (ex - 110, ey - 130, ex + 110, ey), ss=2)
        c.line(t.pts(quad_bezier((ex - 85, ey - 38), (ex, ey - 100), (ex + 88, ey - 40), 40)), 4 * t.s)
        darken(img, c.mask(blur=4 * t.s), 0.10)
        feat = np.maximum(feat, ew)
        if info is not None:
            info.setdefault("eyes", []).append((ex, ey))

    # ---- mouth: lips, yellowed teeth, gum line ----------------------------------------------
    mb = (850, 1490, 1150, 1680)
    ou = quad_bezier((868, 1562), (930, 1506), (1000, 1530), 30) + quad_bezier((1000, 1530), (1070, 1506), (1132, 1562), 30)
    iu = quad_bezier((1132, 1562), (1000, 1546), (868, 1562), 40)
    il = quad_bezier((868, 1562), (1000, 1612), (1132, 1562), 40)
    ol = quad_bezier((1132, 1562), (1000, 1668), (868, 1562), 40)
    c = _m3_cv(t, mb)
    c.poly(t.pts(iu[::-1] + ol))
    lower = _m3_full(c, W, H)
    paint(img, Mask(0, 0, lower), (186, 102, 100))
    c = _m3_cv(t, mb)
    c.poly(t.pts(ou + iu))
    upper = _m3_full(c, W, H)
    paint(img, Mask(0, 0, upper), (170, 88, 88))
    c = _m3_cv(t, mb)
    c.poly(t.pts(iu + il))
    opening = _m3_full(c, W, H)
    paint(img, Mask(0, 0, opening), (58, 28, 28))
    c = _m3_cv(t, mb)
    c.rrect(*t.box(902, 1540, 1098, 1594), 12 * t.s)
    teeth = _m3_full(c, W, H) * opening
    tshade = np.clip(1 - 0.25 * np.abs(xd - 1000) / 98, .7, 1)[..., None]
    paint(img, Mask(0, 0, teeth), np.array((226, 204, 152), F32) * tshade)
    c = _m3_cv(t, mb, ss=3)
    for gx in (1000, 968, 1032, 938, 1062, 915, 1085):
        c.line(t.pts([(gx, 1548), (gx + (gx - 1000) * .03, 1592)]), 2.2 * t.s)
    paint(img, Mask(0, 0, _m3_full(c, W, H, blur=.6 * t.s) * teeth), (150, 120, 90), 0.55)
    c = _m3_cv(t, mb)
    c.poly(t.pts(quad_bezier((890, 1556), (1000, 1542), (1110, 1556), 30) +
                 quad_bezier((1110, 1562), (1000, 1553), (890, 1562), 30)))
    paint(img, Mask(0, 0, _m3_full(c, W, H, blur=1 * t.s) * opening), (192, 112, 112), 0.8)
    mouth = np.maximum.reduce([lower, upper, opening])
    add = r.standard_normal((H, W), dtype=F32) * 3
    img += (add * mouth)[..., None]
    feat = np.maximum(feat, mouth)
    skin_m *= 1 - feat

    # ---- sculpted light (catch-up file for Lesson 3.3) --------------------------------------
    if sculpt:
        F = np.ones((H, W), F32)
        for lst, sgn in ((_M3_DODGE, 1), (_M3_BURN, -1)):
            for cx, cy, rx, ry, amt in lst:
                w = _m3_gauss((H, W), t, cx, cy, rx, ry)
                if w:
                    F[w[0]] += sgn * amt * w[1]
        sk = np.maximum(skin_m, 0.6 * feat * np.maximum(face, neck))
        img *= (1 + (F - 1) * sk)[..., None]

    # ---- texture, blemishes -------------------------------------------------------------------
    zone = np.full((H, W), 0.8, F32)
    for cx, cy, rx, ry in ((1000, 1300, 90, 160), (790, 1320, 150, 110), (1210, 1320, 150, 110)):
        w = _m3_gauss((H, W), t, cx, cy, rx, ry)
        if w:
            zone[w[0]] += 0.45 * w[1]
    if blemish:
        for x, y, rad, wh in _M3_BLEM:
            _m3_blemish(img, skin_m, t, x, y, rad, wh)
    _m3_pores(img, skin_m, r, pore, 11.0, zone)
    hair_n = _m3_noise(r, W, H, max(t.s, 1)) * 4
    img += (hair_n * np.maximum(hair_back, fringe) * (1 - face * (1 - fringe)))[..., None]

    # ---- flyaways: against the background, plus two strays over the temple -------------------
    fly = []
    for a in np.linspace(math.radians(200), math.radians(340), 11):
        a += r.uniform(-.05, .05)
        bx, by = 1000 + 700 * math.cos(a), 1060 + 820 * math.sin(a)
        nx, ny = math.cos(a), math.sin(a)
        L = r.uniform(70, 190)
        p0 = (1000 + 660 * math.cos(a), 1060 + 780 * math.sin(a))
        p2 = (bx + nx * L + r.uniform(-60, 60), by + ny * L * .8)
        p1 = ((p0[0] + p2[0]) / 2 - ny * r.uniform(-50, 50), (p0[1] + p2[1]) / 2 + nx * r.uniform(-50, 50))
        fly.append((p0, p1, p2))
    for side in (-1, 1):
        for yy in (1250, 1560, 1820):
            ex = 1000 + side * 680
            p0 = (ex, yy + r.uniform(-40, 40))
            p2 = (ex + side * r.uniform(60, 150), p0[1] + r.uniform(60, 180))
            p1 = ((p0[0] + p2[0]) / 2 + side * r.uniform(10, 50), (p0[1] + p2[1]) / 2 - r.uniform(0, 40))
            fly.append((p0, p1, p2))
    for p0, p1, p2 in fly:
        _m3_curve(img, t, W, H, p0, p1, p2, 1.6, (74, 56, 44), 0.9)
    strays = [((600, 820), (560, 960), (610, 1090)), ((1300, 900), (1370, 1010), (1355, 1130))]
    for p0, p1, p2 in strays:
        _m3_curve(img, t, W, H, p0, p1, p2, 1.5, (60, 44, 34), 0.85)
    np.clip(img, 0, 255, out=img)
    if info is not None:
        info.update(fly=fly, strays=strays, gap=gap_pts, skin_m=skin_m)
    return img


def _m3_save(img, name, quality=90):
    save_jpg(img, 3, name, quality=quality, subsampling=0)


@lru_cache(maxsize=None)
def _m3_main():
    info = {}
    img = _m3_face(2000, 2500, _M3T(), rng("l07-portrait-retouch.jpg"), info=info)
    return img, info


def m3_portrait_retouch():
    _m3_save(_m3_main()[0], "l07-portrait-retouch.jpg")


def m3_beauty_closeup():
    name = "l07-beauty-closeup.jpg"
    t = _M3T(2.1, 1000 - 2.1 * 1000, 1250 - 2.1 * 1230)
    _m3_save(_m3_face(2000, 2500, t, rng(name), pore=4.6), name)


def m3_candid_distance():
    name = "l07-candid-distance.jpg"
    r = rng(name)
    W, H = 2400, 1600
    bg = vgrad(W, H, [(0, (200, 214, 226)), (.3, (170, 190, 170)), (.62, (96, 124, 84)), (.75, (150, 140, 118)), (1, (126, 116, 98))])
    c = Canvas((0, 0, W, H), ss=1)
    for _ in range(40):
        c.ellipse(r.uniform(0, W), r.uniform(380, 900), r.uniform(80, 220), r.uniform(60, 160),
                  fill=int(r.integers(80, 256)))
    blobs = np.asarray(c.mask(blur=40).a, F32)[:H, :W]
    bg = bg * (1 - 0.35 * blobs[..., None]) + np.array((70, 104, 60), F32) * 0.35 * blobs[..., None]
    add_noise(bg, 1.5, r, mono=True)
    s = 0.5
    t = _M3T(s, 1620 - s * 1000, 700 - s * 1230)
    _m3_save(_m3_face(W, H, t, r, pore=1.1, bg=bg), name)


def m3_portrait_clean_flat():
    name = "l08-portrait-clean-flat.jpg"
    _m3_save(_m3_face(2000, 2500, _M3T(), rng(name), tone=0.22, blemish=False), name)


def m3_portrait_sculpted():
    name = "l09-portrait-sculpted.jpg"
    _m3_save(_m3_face(2000, 2500, _M3T(), rng(name), tone=0.22, blemish=False, sculpt=True), name)


def m3_apple_flat():
    """A flatly lit apple for the 'sculpt something that is not a face' variation."""
    name = "l08-apple-flat.jpg"
    r = rng(name)
    W = H = 1600
    img = vgrad(W, H, [(0, (218, 214, 208)), (.66, (200, 196, 190)), (1, (182, 178, 172))])
    img *= np.interp(np.arange(W), [0, W], [1.04, .95]).astype(F32)[None, :, None]
    t = _M3T()
    c = Canvas((770, 1245, 1530, 1335), ss=2, pad=90)
    c.ellipse(1150, 1290, 380, 45)
    darken(img, c.mask(blur=28), 0.22)
    cx, cy = 800, 860
    th = np.linspace(0, 2 * np.pi, 300, endpoint=False)
    rr = 470 * (1 + 0.05 * np.cos(2 * th) - 0.06 * np.clip(-np.sin(th), 0, 1) ** 8 + 0.03 * np.sin(th))
    pts = [(cx + a * math.cos(b) * 1.04, cy + a * math.sin(b)) for a, b in zip(rr, th)]
    c = Canvas((250, 340, 1350, 1380), ss=3, pad=4)
    c.poly(pts)
    am = full_mask(c.mask(), W, H)
    X, Y = coords(W, H)
    streak = _m3_noise(r, W, H, 1)
    streak = np.asarray(Image.fromarray(streak, "F").resize((W, H // 50), Image.BILINEAR).resize((W, H), Image.BICUBIC), F32)
    streak = (streak - streak.mean()) / (streak.std() + 1e-6)
    d = np.hypot((X - cx) / 490, (Y - cy) / 470)
    shade = 1 - 0.07 * np.clip((d - .75) / .25, 0, 1)
    col = np.array((176, 34, 38), F32) + streak[..., None] * np.array((9, 6, 1), F32)
    col = col * shade[..., None]
    paint(img, Mask(0, 0, am), col)
    for _ in range(420):
        x, y = r.uniform(360, 1260), r.uniform(420, 1320)
        if am[int(y), int(x)] < 1:
            continue
        cc = Canvas((x - 3, y - 3, x + 3, y + 3), ss=4, pad=2)
        cc.circle(x, y, r.uniform(1.2, 2.4))
        paint(img, cc.mask(blur=.5), (214, 150, 110), .55)
    c = Canvas((735, 467, 875, 523), ss=3, pad=50)
    c.ellipse(805, 492, 70, 26)
    darken(img, c.mask(blur=14), 0.25)
    c = Canvas((780, 300, 880, 510), ss=3, pad=6)
    c.line(quad_bezier((808, 495), (812, 400), (850, 330), 30), 16, round_caps=True)
    paint(img, c.mask(blur=.6), (84, 58, 36))
    c = Canvas((840, 300, 1080, 420), ss=3, pad=6)
    c.poly(quad_bezier((842, 360), (930, 280), (1060, 322), 30) + quad_bezier((1060, 322), (960, 420), (842, 360), 30))
    paint(img, c.mask(blur=.6), (88, 128, 58))
    add_noise(img, 2.5, r, mono=True)
    _m3_save(img, name)


def _m3_ring(c, x, y, rad, col, width=3, dashed=False):
    if dashed:
        for a0 in range(0, 360, 20):
            c.d.arc(c.B(x - rad, y - rad, x + rad, y + rad), a0, a0 + 11, fill=col, width=int(width * c.ss))
    else:
        c.d.ellipse(c.B(x - rad, y - rad, x + rad, y + rad), outline=col, width=int(width * c.ss))


def m3_flaw_map():
    img, info = _m3_main()
    s = 0.5
    im = Image.fromarray(to_u8(img)).resize((1000, 1250), Image.LANCZOS)
    c = Canvas((0, 0, 1000, 1250), ss=3, mode="RGBA")
    red, orange, blue = (225, 30, 30, 255), (235, 130, 0, 255), (20, 90, 220, 255)
    green, purple = (20, 150, 60, 255), (150, 50, 190, 255)
    for i, (x, y, rad, _) in enumerate(_M3_BLEM, start=1):
        x, y, rr = x * s, y * s, max(rad * 1.8 * s + 6, 11)
        _m3_ring(c, x, y, rr, red)
        c.circle(x + rr * .8 + 8, y - rr * .8 - 8, 10, red)
        c.text(x + rr * .8 + 8, y - rr * .8 - 8, str(i), 13, bold=True, fill=(255, 255, 255), anchor="mm")
    for i, (x, y, rad, _, _) in enumerate(_M3_TONE):
        _m3_ring(c, x * s, y * s, rad * s * .9, orange, 2.5, dashed=True)
        c.text(x * s, y * s + rad * s * .9 + 4, chr(65 + i), 14, bold=True, fill=orange, anchor="mt")
    for p0, p1, p2 in info["fly"] + info["strays"]:
        mx, my = quad_bezier(p0, p1, p2, 3)[1]
        _m3_ring(c, mx * s, my * s, 22, blue, 2.5)
    gx, gy = info["gap"][1]
    _m3_ring(c, gx * s, gy * s, 34, blue, 3.5)
    c.text(gx * s - 40, gy * s, "gap", 15, bold=True, fill=blue, anchor="rm")
    for ex, ey in info["eyes"]:
        c.d.ellipse(c.B(ex * s - 56, ey * s - 32, ex * s + 56, ey * s + 30), outline=purple, width=3 * c.ss)
    c.d.ellipse(c.B(890 * s, 1530 * s, 1110 * s, 1610 * s), outline=purple, width=3 * c.ss)
    _m3_ring(c, _M3_MOLE[0] * s, _M3_MOLE[1] * s, 13, green)
    fx, fy, frx, fry = _M3_FRECKLES
    for a0 in range(0, 360, 12):
        c.d.arc(c.B((fx - frx) * s - 6, (fy - fry) * s - 6, (fx + frx) * s + 6, (fy + fry) * s + 6),
                a0, a0 + 7, fill=green, width=3 * c.ss)
    for x in (880, 1120):
        c.d.ellipse(c.B(x * s - 18, 1445 * s, x * s + 18, 1650 * s), outline=green, width=2 * c.ss)
    c.rect(0, 0, 1000, 70, (255, 255, 255, 235))
    c.text(14, 18, "RED 1-10 = blemishes (heal on HIGH, L07)", 15, bold=True, fill=red, anchor="lm")
    c.text(470, 18, "ORANGE A-I = tone patches (even on LOW, L07)", 15, bold=True, fill=orange, anchor="lm")
    c.text(14, 50, "BLUE = flyaways + gap (L09)", 15, bold=True, fill=blue, anchor="lm")
    c.text(290, 50, "PURPLE = eyes, teeth (L09)", 15, bold=True, fill=purple, anchor="lm")
    c.text(540, 50, "GREEN = permanent (keep)", 15, bold=True, fill=green, anchor="lm")
    c.text(986, 50, "instructor only", 13, fill=(60, 60, 60, 255), anchor="rm")
    base = np.asarray(im, F32).copy()
    over(base, c.layer())
    save_png(base, 3, "l07-flaw-map-INSTRUCTOR.png", folder="instructor")


def m3_light_map():
    name = "l08-light-map-INSTRUCTOR.png"
    img = _m3_face(1000, 1250, _M3T(0.5), rng(name), tone=0.22, blemish=False, pore=1.1)
    c = Canvas((0, 0, 1000, 1250), ss=3, mode="RGBA")
    for cx, cy, rx, ry, amt in _M3_BURN:
        a = int(70 + 900 * amt)
        c.ellipse(cx * .5, cy * .5, rx * .5, ry * .5, (0, 70, 80, a))
    for cx, cy, rx, ry, amt in _M3_DODGE:
        a = int(70 + 1300 * amt)
        c.ellipse(cx * .5, cy * .5, rx * .5, ry * .5, (255, 255, 255, a))
    base = img.copy()
    over(base, c.layer(blur=6))
    c = Canvas((0, 0, 1000, 1250), ss=3, mode="RGBA")
    for y in (420, 470, 520):
        c.line([(30, y), (150, y + 10)], 5, (255, 190, 0, 255))
        c.poly([(150, y + 10 - 12), (178, y + 13), (146, y + 10 + 14)], (255, 190, 0, 255))
    c.text(30, 390, "window light", 16, bold=True, fill=(120, 80, 0, 255), anchor="ls")
    c.rect(0, 0, 1000, 70, (255, 255, 255, 235))
    c.text(14, 20, "WHITE = dodge (bring forward)    TEAL = burn (push back)", 17, bold=True,
           fill=(20, 40, 60, 255), anchor="lm")
    c.text(14, 50, "Light comes from the viewer's left: dodge the left planes more, burn the right more.",
           14, fill=(40, 40, 40, 255), anchor="lm")
    c.text(986, 20, "instructor only", 13, fill=(60, 60, 60, 255), anchor="rm")
    over(base, c.layer())
    save_png(base, 3, name, folder="instructor")


# ======================================================================================
# Module 4: Commercial Compositing
# ======================================================================================

# --------------------------------------------------------------------------------------
# Module 4 · Commercial Compositing (L10 perspective, L11 light & shadow, L12 atmosphere)
# --------------------------------------------------------------------------------------
# The main scene (l10-plaza-background.jpg) is rendered analytically with a real pinhole
# camera: a level camera 1.6 m above a tiled plaza, so the horizon sits exactly at the
# eye level of every standing person in the shot, and every receding edge (tile grout,
# window rows, lamp-post line) converges on one vanishing point on that horizon. The sun
# is high on the right, so every shadow falls to the LEFT, crisp at the contact point and
# softening toward its tip. That one file carries the whole 4.1 -> 4.2 -> 4.3 save chain.

_M4_W, _M4_H = 2400, 1600
_M4_PLAZA = dict(F=1400.0, cx=1260.0, h0=700.0, hc=1.6)
# shadow direction on the ground (X right, Z away from camera): left and slightly away
_M4_SUN = dict(dx=-0.944, dz=0.33, cot=0.84)
_M4_HAZE = np.array((204, 212, 224), F32)


def _m4_P(cam, X, Y, Z):
    """Project a world point (metres; Y up, Z away) through a level pinhole camera."""
    return (cam["cx"] + cam["F"] * X / Z, cam["h0"] + cam["F"] * (cam["hc"] - Y) / Z)


def _m4_shadow_pt(X, Y, Z, sun=_M4_SUN):
    k = Y * sun["cot"]
    return (X + k * sun["dx"], Z + k * sun["dz"])


def _m4_box(x0, x1, y0, y1, z0, z1):
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def _m4_shadow_layer(cam, parts, W, H, sun=_M4_SUN, near=1.2, far=7.0, ss=2):
    """Ground shadow of a set of world-space boxes (each a list of 3D points).

    Returns (mask, base_xy): a full-frame float mask whose edge is crisp near the object's
    base and progressively softer toward the tip, like a real sun shadow (penumbra grows
    with distance from the contact point)."""
    hulls, allpts = [], []
    for pts in parts:
        ground = [(p[0], p[2]) for p in pts if p[1] <= 0.001]
        cast = [_m4_shadow_pt(*p, sun=sun) for p in pts]
        hull = convex_hull(ground + cast)
        img = [_m4_P(cam, x, 0.0, max(z, 0.3)) for x, z in hull]
        hulls.append(img)
        allpts += img
    xs = [p[0] for p in allpts]
    ys = [p[1] for p in allpts]
    box = (max(min(xs), -50), max(min(ys), -50), min(max(xs), W + 50), min(max(ys), H + 50))
    c = Canvas(box, ss=ss, mode="L", pad=int(far * 3) + 4)
    for poly in hulls:
        if len(poly) >= 3:
            c.poly(poly, 255)
    sharp = c.mask(blur=near)
    soft = c.mask(blur=far)
    # distance-based blend from the base (lowest point of the first part = feet/base)
    base = parts[0]
    bx = float(np.mean([p[0] for p in base]))
    bz = float(np.mean([p[2] for p in base]))
    top = max(p[1] for pp in parts for p in pp)
    b_img = _m4_P(cam, bx, 0.0, bz)
    t_img = _m4_P(cam, *(lambda s: (s[0], 0.0, s[1]))(_m4_shadow_pt(bx, top, bz, sun)))
    L = max(8.0, math.hypot(t_img[0] - b_img[0], t_img[1] - b_img[1]))
    hh, ww = sharp.a.shape
    yy, xx = np.mgrid[0:hh, 0:ww].astype(F32)
    d = np.hypot(xx + sharp.x - b_img[0], yy + sharp.y - b_img[1]) / L
    t = np.clip(d, 0, 1)
    a = sharp.a * (1 - t) + soft.a * t
    a *= (1.0 - 0.25 * t)                       # a little paler toward the tip
    return full_mask(Mask(sharp.x, sharp.y, a), W, H), b_img


def _m4_apply_shadow(img, m, strength=0.55):
    """Multiply-style shadow that leans cool (outdoor shadows are lit by the blue sky)."""
    k = (m * strength)[..., None]
    img *= (1 - k)
    img += k * np.array((-4.0, 2.0, 16.0), F32)
    np.clip(img, 0, 255, out=img)


def _m4_contact(img, cx, cy, rx, ry, strength=0.6, blur=2.0):
    c = Canvas((cx - rx, cy - ry, cx + rx, cy + ry), ss=3, mode="L", pad=int(blur * 3) + 2)
    c.ellipse(cx, cy, rx, ry, 255)
    darken(img, c.mask(blur=blur), strength)


# ---- people --------------------------------------------------------------------------

_M4_PERSON_PARTS = [  # world boxes relative to feet centre (x, y up, z depth): for shadows
    (-0.17, 0.17, 0.0, 0.88, -0.10, 0.10),
    (-0.24, 0.24, 0.82, 1.47, -0.12, 0.12),
    (-0.31, 0.31, 0.84, 1.44, -0.06, 0.06),
    (-0.09, 0.09, 1.44, 1.72, -0.09, 0.09),
]


def _m4_person_layer(s, col, light=1.0, noise=0.0, r=None):
    """A stylized standing person, `s` px per metre, feet centre at local (0, 0).

    col: dict(skin, hair, top, arm, pants, shoe). light=+1 lit from the right, -1 left.
    Returns a Layer in local coordinates (add the feet position to x/y to place it)."""
    def X(m):
        return m * s

    def Y(m):
        return -m * s

    c = Canvas((-0.36 * s, -1.78 * s, 0.36 * s, 0.06 * s), ss=3, mode="RGBA", pad=3)
    for sx in (-1, 1):
        c.ellipse(X(sx * 0.10), Y(0.035), 0.08 * s, 0.037 * s, col["shoe"])
    c.rrect(X(-0.165), Y(0.90), X(-0.018), Y(0.045), 0.03 * s, col["pants"])
    c.rrect(X(0.018), Y(0.90), X(0.165), Y(0.045), 0.03 * s, col["pants"])
    c.rrect(X(-0.305), Y(1.44), X(-0.195), Y(0.83), 0.045 * s, col["arm"])
    c.rrect(X(0.195), Y(1.44), X(0.305), Y(0.83), 0.045 * s, col["arm"])
    for sx in (-1, 1):
        c.circle(X(sx * 0.25), Y(0.815), 0.047 * s, col["skin"])
    c.rrect(X(-0.235), Y(1.48), X(0.235), Y(0.80), 0.075 * s, col["top"])
    c.rect(X(-0.045), Y(1.53), X(0.045), Y(1.45), col["skin"])
    c.ellipse(X(0.0), Y(1.645), 0.094 * s, 0.088 * s, col["hair"])
    c.ellipse(X(0.0), Y(1.598), 0.082 * s, 0.100 * s, col["skin"])
    c.ellipse(X(0.0), Y(1.675), 0.086 * s, 0.05 * s, col["hair"])
    L = c.layer()
    h, w = L.a.shape
    xs = (np.arange(w, dtype=F32) + L.x) / s          # metres from centre line
    ys = -(np.arange(h, dtype=F32) + L.y) / s         # metres above the feet
    f = 1.0 + 0.30 * light * np.clip(xs / 0.30, -1, 1)[None, :]
    f = f * (0.86 + 0.14 * np.clip(ys / 1.7, 0, 1))[:, None]
    rgb = L.rgb * f[..., None]
    if noise and r is not None:
        rgb += r.standard_normal((h, w, 1), dtype=F32) * noise
    return Layer(L.x, L.y, np.clip(rgb, 0, 255), L.a)


def _m4_blur_layer(L, radius):
    """Gaussian-blur a Layer (premultiplied, so edges do not go dark)."""
    pre = L.rgb * L.a[..., None]
    pb = blur_img(np.clip(pre, 0, 255), radius)
    ab = blur_img(np.repeat(L.a[..., None] * 255, 3, 2), radius)[..., 0] / 255
    rgb = pb / np.clip(ab, 1e-3, None)[..., None]
    return Layer(L.x, L.y, np.clip(rgb, 0, 255), ab)


def _m4_place(L, px, py):
    return Layer(int(round(L.x + px)), int(round(L.y + py)), L.rgb, L.a)


def _m4_hazed(L, amount, haze=_M4_HAZE, contrast=1.0):
    rgb = L.rgb
    if contrast != 1.0:
        m = rgb.mean()
        rgb = m + (rgb - m) * contrast
    return Layer(L.x, L.y, rgb * (1 - amount) + haze * amount, L.a)


# ---- the plaza (the Module 4 key-visual background) ----------------------------------

_M4_PLAZA_PEOPLE = [  # (X, Z, colours) already in the "photo"
    (-2.8, 7.5, dict(skin="#c9906c", hair="#2a1d16", top="#a8322c", arm="#962b26",
                     pants="#2c3040", shoe="#1b1b1e")),
    (2.3, 13.0, dict(skin="#e3b48f", hair="#6b4a2c", top="#2d3e63", arm="#27365a",
                     pants="#565a60", shoe="#222222")),
    (-0.7, 26.0, dict(skin="#b07d5a", hair="#1c1512", top="#4f7a44", arm="#476e3d",
                      pants="#35322e", shoe="#1c1c1c")),
]


def _m4_plaza_surfaces(y0, y1, ss=2):
    """Analytic render of the static surfaces for output rows y0..y1 (supersampled)."""
    cam = _M4_PLAZA
    F, CX, H0, HC = cam["F"], cam["cx"], cam["h0"], cam["hc"]
    W = _M4_W
    ys = (np.arange(y0 * ss, y1 * ss, dtype=F32) + 0.5) / ss
    xs = (np.arange(W * ss, dtype=F32) + 0.5) / ss
    xx, yy = np.meshgrid(xs, ys)
    INF = F32(1e9)
    dy = yy - H0
    dx = xx - CX
    # candidate hits
    with np.errstate(divide="ignore", invalid="ignore"):
        zg = np.where(dy > 0, F * HC / dy, INF)
        Xg = dx * zg / F
        zf = np.where(dx < 0, -7.0 * F / dx, INF)
        Yf = HC - dy * zf / F
        zw = np.where(dx > 0, 5.0 * F / dx, INF)
        Yw = HC - dy * zw / F
        zt = np.where(dy > 0, F * (HC - 0.6) / dy, INF)
        Xt = dx * zt / F
    zend = F32(92.0)
    Xe = dx * zend / F
    Ye = HC - dy * zend / F
    blocks = [(-60, -31, 8.5), (-31, -18, 11.5), (-18, -9, 7.0), (-9, -2.5, 9.5), (-2.5, 3.6, 6.5)]
    he = np.full_like(xx, -1.0)
    for a, b, hgt in blocks:
        he = np.where((Xe >= a) & (Xe < b), hgt, he)
    fac = (zf < INF) & (Yf >= 0) & (Yf <= 14.0) & (zf <= 88.0)
    wal = (zw < INF) & (Yw >= 0) & (Yw <= 0.6) & (zw <= 88.0)
    top = (zt < INF) & (Xt >= 5.0) & (Xt <= 5.35) & (zt <= 88.0)
    end = (Ye >= 0) & (Ye <= he)
    gnd = (zg < INF) & (Xg >= -7.0)
    Z = np.stack([np.where(fac, zf, INF), np.where(wal, zw, INF), np.where(top, zt, INF),
                  np.where(end, zend, INF), np.where(gnd, zg, INF)])
    which = np.argmin(Z, axis=0)
    zmin = np.min(Z, axis=0)
    hit = zmin < INF
    out = np.zeros(xx.shape + (3,), F32)

    # sky + distant hills (no hit)
    t = np.clip(yy / H0, 0, 1)[..., None]
    sky = np.array((88, 138, 202), F32) * (1 - t) + np.array((232, 226, 212), F32) * t
    ridge1 = H0 - 70 - 22 * np.sin(xx / 260.0 + 0.7) - 14 * np.sin(xx / 97.0)
    ridge2 = H0 - 34 - 14 * np.sin(xx / 180.0 + 2.1) - 8 * np.sin(xx / 61.0 + 1.0)
    sky = np.where((yy > ridge1)[..., None], np.array((178, 192, 208), F32), sky)
    sky = np.where((yy > ridge2)[..., None], np.array((150, 172, 168), F32), sky)
    sky = np.where((yy > H0)[..., None], np.array((150, 172, 150), F32), sky)
    out[:] = sky

    # ground: tiles, crossing street, wall shadow strip, lawn
    fpz = np.where(gnd, zg * zg / (F * HC) / ss, 1.0)
    fpx = np.where(gnd, zg / F / ss, 1.0)
    ix = np.floor(Xg + 7.0)
    iz = np.floor(zg)
    hsh = np.sin(ix * 12.9898 + iz * 78.233) * 43758.5453
    var = (hsh - np.floor(hsh) - 0.5) * 0.10
    tile = np.array((212, 194, 168), F32) * (1 + var)[..., None]
    gz = np.abs(zg - np.round(zg))
    gx = np.abs(Xg - np.round(Xg))
    w = 0.018
    cz = np.clip((w - gz) / np.maximum(fpz, 1e-4) + 0.5, 0, 1)
    cx_ = np.clip((w - gx) / np.maximum(fpx, 1e-4) + 0.5, 0, 1)
    fade = np.clip(1.2 - fpz / 0.35, 0, 1)
    grout = np.maximum(cz * fade, cx_ * np.clip(1.2 - fpx / 0.05, 0, 1))
    tile = tile * (1 - 0.42 * grout)[..., None]
    street = np.array((96, 94, 96), F32)
    tile = np.where((zg > 88.0)[..., None], street, tile)
    lawn = np.array((112, 150, 72), F32) * (1 + var * 0.8)[..., None]
    g = np.where((Xg > 5.35)[..., None], lawn, tile)
    # the planter wall's own shadow on the tiles (left of it)
    wall_sh = ((Xg > 4.50) & (Xg < 5.0) & (zg < 88)).astype(F32)
    g = g * (1 - 0.42 * wall_sh)[..., None]
    g[..., 2] += wall_sh * 6
    sel = hit & (which == 4)
    out[sel] = g[sel]

    # facade (lit, facing +X): sandstone, windows in rows receding to the VP
    zz = zf
    fcol = np.array((226, 198, 158), F32)
    shop = Yf < 3.8
    pil = (np.mod(zz, 6.0) < 0.7)
    win = (~shop) & (np.mod(zz, 3.0) > 0.9) & (np.mod(zz, 3.0) < 2.3) & \
          (np.mod(Yf - 4.6, 2.9) < 1.7) & (Yf < 12.6)
    corn = (Yf > 13.2)
    fcv = np.broadcast_to(fcol, xx.shape + (3,)).copy()
    fcv[corn] = (240, 220, 186)
    wy = np.clip((np.mod(Yf - 4.6, 2.9)) / 1.7, 0, 1)[..., None]
    wcol = np.array((70, 88, 112), F32) * (1 - wy) + np.array((138, 160, 186), F32) * wy
    fcv = np.where(win[..., None], wcol, fcv)
    sh = shop & ~pil
    fcv = np.where(sh[..., None], np.array((52, 58, 66), F32) * (0.8 + 0.5 * np.clip(Yf / 3.8, 0, 1))[..., None], fcv)
    fcv = np.where((shop & (Yf > 3.3))[..., None], np.array((150, 60, 48), F32), fcv)  # awning band
    sel = hit & (which == 0)
    out[sel] = fcv[sel]

    # planter wall face (faces the street, away from the sun: in shade) and lit top
    wcolr = np.array((128, 126, 132), F32)
    sel = hit & (which == 1)
    out[sel] = wcolr
    sel = hit & (which == 2)
    out[sel] = (224, 214, 194)

    # buildings closing the street
    ecol = np.array((196, 176, 150), F32)
    ew = (np.mod(Xe, 2.2) > 0.8) & (np.mod(Ye - 1.2, 2.6) < 1.3) & (Ye > 1.0)
    ecv = np.where(ew[..., None], np.array((96, 108, 124), F32), ecol)
    sel = hit & (which == 3)
    out[sel] = ecv[sel]

    # distance haze on everything that was hit
    hz = np.where(hit, 1 - np.exp(-zmin / 320.0), 0.0)[..., None]
    out = out * (1 - hz) + _M4_HAZE * hz
    # downsample
    h, w_ = out.shape[:2]
    out = out.reshape(h // ss, ss, w_ // ss, ss, 3).mean(axis=(1, 3))
    return out.astype(F32)


def _m4_tree_layer(s, r):
    c = Canvas((-2.6 * s, -7.2 * s, 2.6 * s, 0.1 * s), ss=3, mode="RGBA", pad=2)
    c.rect(-0.16 * s, -3.0 * s, 0.16 * s, 0, "#4a3a2c")
    for _ in range(9):
        ex = r.uniform(-1.4, 1.4) * s
        ey = -r.uniform(3.4, 5.8) * s
        rr = r.uniform(0.9, 1.5) * s
        c.circle(ex, ey, rr, rand_color_near(r, (74, 112, 52), 10))
    L = c.layer()
    h, w = L.a.shape
    xs = (np.arange(w, dtype=F32) + L.x) / s
    f = 1.0 + 0.28 * np.clip(xs / 2.0, -1, 1)[None, :]
    return Layer(L.x, L.y, np.clip(L.rgb * f[..., None], 0, 255), L.a)


def _m4_render_plaza(extra=None, name="l10-plaza-background.jpg", far=None):
    """Render the plaza. `extra` = list of (X, Z, colours) people to add (used by the
    instructor-only finished reference, which 'composites' the practice figure in)."""
    r = rng(name)
    cam = _M4_PLAZA
    W, H = _M4_W, _M4_H
    img = np.zeros((H, W, 3), F32)
    for y0 in range(0, H, 100):
        img[y0:y0 + 100] = _m4_plaza_surfaces(y0, min(y0 + 100, H))

    if far is not None:                      # a far element, behind every object
        over(img, far)
    objs = []  # (Z, kind, X, extra)
    for z in range(6, 88, 8):
        objs.append((float(z), "lamp", 4.55, None))
    tr = rng("m4-trees")
    for X, Z in [(9, 18), (14, 30), (8.5, 42), (19, 24), (12, 56), (23, 48), (16, 72), (10, 80)]:
        objs.append((float(Z), "tree", float(X), tr))
    people = list(_M4_PLAZA_PEOPLE) + list(extra or [])
    for X, Z, col in people:
        objs.append((float(Z), "person", float(X), col))

    # shadows first (they lie on the ground under everything)
    for Z, kind, X, ex in objs:
        if kind == "lamp":
            parts = [_m4_box(X - 0.06, X + 0.06, 0, 4.2, Z - 0.06, Z + 0.06),
                     _m4_box(X - 0.25, X + 0.05, 4.0, 4.25, Z - 0.1, Z + 0.1)]
            m, _ = _m4_shadow_layer(cam, parts, W, H, near=0.8, far=3.0)
            _m4_apply_shadow(img, m, 0.50)
        elif kind == "tree":
            parts = [_m4_box(X - 0.16, X + 0.16, 0, 3.0, Z - 0.16, Z + 0.16),
                     _m4_box(X - 1.9, X + 1.9, 3.2, 6.8, Z - 1.4, Z + 1.4)]
            m, _ = _m4_shadow_layer(cam, parts, W, H, near=1.5, far=6.0)
            _m4_apply_shadow(img, m, 0.40)
        else:
            parts = [_m4_box(X + a, X + b, c0, c1, Z + d0, Z + d1)
                     for a, b, c0, c1, d0, d1 in _M4_PERSON_PARTS]
            m, _ = _m4_shadow_layer(cam, parts, W, H, near=1.0, far=5.0)
            _m4_apply_shadow(img, m, 0.55)

    for Z, kind, X, ex in sorted(objs, key=lambda o: -o[0]):
        s = cam["F"] / Z
        fx, fy = _m4_P(cam, X, 0.0, Z)
        hz = 1 - math.exp(-Z / 320.0)
        if kind == "lamp":
            c = Canvas((fx - 0.4 * s, fy - 4.4 * s, fx + 0.2 * s, fy + 2), ss=3, mode="RGBA", pad=2)
            c.rect(fx - 0.06 * s, fy - 4.2 * s, fx + 0.06 * s, fy, (58, 62, 66))
            c.rect(fx - 0.26 * s, fy - 4.25 * s, fx + 0.06 * s, fy - 4.12 * s, (50, 54, 58))
            c.ellipse(fx - 0.2 * s, fy - 4.08 * s, 0.07 * s, 0.05 * s, (236, 228, 200))
            L = c.layer()
            xs = (np.arange(L.a.shape[1], dtype=F32) + L.x - fx) / s
            f = 1.0 + 0.9 * np.clip(xs / 0.06, -1, 1)[None, :] * 0.5
            over(img, _m4_hazed(Layer(L.x, L.y, np.clip(L.rgb * f[..., None], 0, 255), L.a), hz))
        elif kind == "tree":
            L = _m4_place(_m4_tree_layer(s, ex), fx, fy)
            over(img, _m4_hazed(L, hz))
        else:
            _m4_contact(img, fx, fy, 0.26 * s, 0.045 * s, 0.55, max(0.6, 0.012 * s))
            L = _m4_place(_m4_person_layer(s, ex, light=1.0), fx, fy)
            over(img, _m4_hazed(L, hz))

    # a gentle warm late-sun cast, lens falloff and sensor noise
    img *= np.array((1.03, 1.0, 0.95), F32)
    xx, yy = coords(W, H)
    v = 1 - 0.18 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
    img *= v[..., None]
    add_noise(img, 2.2, r, mono=True)
    return img


def m4_plaza_background():
    save_jpg(_m4_render_plaza(), 4, "l10-plaza-background.jpg", quality=88)


# ---- L10 cut-out elements ------------------------------------------------------------

_M4_HERO = dict(skin="#e2b48e", hair="#3b2618", top="#e8e6df", arm="#dcdad2",
                pants="#26324a", shoe="#141416")


def m4_figure_cutout():
    """A full-length person, cut out (RGBA), photographed far larger than they will
    appear in the plaza, lit from the LEFT with cool studio light."""
    r = rng("l10-figure-cutout.png")
    s = 820.0
    L = _m4_person_layer(s, _M4_HERO, light=-1.0, noise=2.0, r=r)
    rgb = L.rgb * np.array((0.93, 0.98, 1.07), F32)
    h, w = L.a.shape
    pad = 40
    out = np.zeros((h + 2 * pad, w + 2 * pad, 4), F32)
    out[pad:pad + h, pad:pad + w, :3] = rgb
    out[pad:pad + h, pad:pad + w, 3] = L.a * 255
    save_png(Image.fromarray(to_u8(out), "RGBA"), 4, "l10-figure-cutout.png")


def _m4_rot(p, yaw, pitch):
    x, y, z = p
    cy, sy = math.cos(yaw), math.sin(yaw)
    x, z = x * cy + z * sy, -x * sy + z * cy
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = y * cp - z * sp, y * sp + z * cp
    return x, y, z


def m4_product_box_cutout():
    """A product carton (RGBA) shot from a HIGH angle and rotated ~34 degrees: its own
    vanishing lines disagree with the plaza, so it needs Perspective Warp."""
    W = H = 1400
    yaw, pitch, dist, F = math.radians(34), math.radians(-30), 2.1, 2300.0
    bw, bh, bd = 0.42, 0.52, 0.30

    def cam_pt(p):
        x, y, z = _m4_rot((p[0], p[1] - bh / 2, p[2]), yaw, pitch)
        return x, y, z + dist

    def proj(p):
        x, y, z = cam_pt(p)
        return (W / 2 + F * x / z, H / 2 - F * y / z)

    x0, x1, z0, z1 = -bw / 2, bw / 2, -bd / 2, bd / 2
    # face: (outward normal, origin, u-axis, v-axis); v runs top->bottom on side faces
    faces = {
        "front": ((0, 0, -1), (x0, bh, z0), (bw, 0, 0), (0, -bh, 0)),
        "back": ((0, 0, 1), (x1, bh, z1), (-bw, 0, 0), (0, -bh, 0)),
        "left": ((-1, 0, 0), (x0, bh, z1), (0, 0, -bd), (0, -bh, 0)),
        "right": ((1, 0, 0), (x1, bh, z0), (0, 0, bd), (0, -bh, 0)),
        "top": ((0, 1, 0), (x0, bh, z1), (bw, 0, 0), (0, 0, -bd)),
    }
    light = np.array((-0.6, 0.7, -0.4))
    light /= np.linalg.norm(light)
    vis = []
    for name, (n, o, u, v) in faces.items():
        cen = tuple(o[i] + 0.5 * u[i] + 0.5 * v[i] for i in range(3))
        nr = _m4_rot(n, yaw, pitch)
        cc = cam_pt(cen)
        if nr[0] * cc[0] + nr[1] * cc[1] + nr[2] * cc[2] < 0:
            k = 0.55 + 0.6 * max(0.0, float(np.dot(n, light)))
            vis.append((cc[2], name, k))
    c = Canvas((0, 0, W, H), ss=3, mode="RGBA")
    for _, name, k in sorted(vis, reverse=True):
        n, o, u, v = faces[name]

        def fp(uu, vv):
            return proj(tuple(o[i] + uu * u[i] + vv * v[i] for i in range(3)))

        def quad(u0, v0, u1, v1, col):
            c.poly([fp(u0, v0), fp(u1, v0), fp(u1, v1), fp(u0, v1)],
                   tuple(min(255, int(ch * k)) for ch in col))

        quad(0, 0, 1, 1, (18, 118, 128))
        if name == "top":
            quad(0.08, 0.35, 0.92, 0.65, (238, 234, 222))
        else:
            quad(0, 0.40, 1, 0.66, (238, 234, 222))
            quad(0, 0.66, 1, 0.70, (232, 150, 40))
            c.poly([fp(0.5 + 0.12 * math.cos(t), 0.53 + 0.09 * math.sin(t)) for t in np.linspace(0, 6.283, 64)],
                   tuple(min(255, int(ch * k)) for ch in (232, 150, 40)))
            quad(0.1, 0.82, 0.9, 0.86, (200, 232, 232))
    L = c.layer()
    r = rng("l10-product-box-cutout.png")
    h, w = L.a.shape
    rgb = L.rgb * np.array((0.95, 0.99, 1.06), F32)
    rgb += r.standard_normal((h, w, 1), dtype=F32) * 1.6
    out = np.dstack([np.clip(rgb, 0, 255), L.a * 255])
    save_png(Image.fromarray(to_u8(out), "RGBA"), 4, "l10-product-box-cutout.png")


# ---- L10 horizon drill sheet (+ instructor answers) ----------------------------------

def _m4_drill_panels():
    """Five small level-camera scenes. Each: (title, horizon_y, [vps], [segments], [fills])
    in panel-local coords (700 x 460). Segments are drawn only on the part AWAY from
    the vanishing point, so learners must extend them."""
    P = []
    # 1 corridor, one-point, VP off-centre
    vp, hy = (410, 190), 190
    segs, fills = [], []
    for (ex, ey) in [(0, 0), (700, 0), (0, 460), (700, 460), (0, 120), (0, 330)]:
        t0 = 0.55
        segs.append(((vp[0] + (ex - vp[0]) * t0, vp[1] + (ey - vp[1]) * t0), (ex, ey)))
    for k in range(4):
        x = 700 - k * 60
        segs.append(((x, 40 + k * 26), (x, 460 - k * 30)))
    P.append(("1 · Corridor", hy, [vp], segs, fills))
    # 2 road across fields, VP right
    vp, hy = (520, 250), 250
    segs = [((vp[0] + (x - vp[0]) * 0.5, vp[1] + (460 - vp[1]) * 0.5), (x, 460)) for x in (60, 330, 600)]
    segs += [((vp[0] + (0 - vp[0]) * 0.6, vp[1] + (330 - vp[1]) * 0.6), (0, 330))]
    fills = [("poly", [(0, 0), (700, 0), (700, 262), (0, 262)], (206, 222, 238))]
    P.append(("2 · Road", hy, [vp], segs, fills))
    # 3 tabletop box, two-point (VPs off-panel)
    hy = 110
    vl, vr = (-260.0, 110.0), (980.0, 110.0)

    def toward(p, v, t):
        return (p[0] + (v[0] - p[0]) * t, p[1] + (v[1] - p[1]) * t)

    def at_x(p, v, x):
        t = (x - p[0]) / (v[0] - p[0])
        return toward(p, v, t)

    A, D = (300.0, 400.0), (300.0, 260.0)            # near vertical edge (bottom, top)
    B = toward(A, vl, 0.26)
    C = toward(A, vr, 0.34)
    Bt, Ct = at_x(D, vl, B[0]), at_x(D, vr, C[0])
    segs = [(A, B), (A, C), (D, A), (Bt, B), (Ct, C), (D, Bt), (D, Ct)]
    segs += [(toward(Bt, vr, 0.0), at_x(Bt, vr, 470.0)), (at_x(Ct, vl, 150.0), Ct)]
    P.append(("3 · Box on a table", hy, [vl, vr], segs, []))
    # 4 building corner, two-point, low horizon
    hy = 380
    vl, vr = (-420, 380), (1100, 380)
    segs = []
    for yv in (60, 140, 220, 300):
        t = 0.45
        segs.append(((330, yv + (hy - yv) * 0.0), (330 + (vl[0] - 330) * t, yv + (hy - yv) * t)))
        segs.append(((330, yv), (330 + (vr[0] - 330) * t, yv + (hy - yv) * t)))
    segs.append(((330, 20), (330, 440)))
    P.append(("4 · Building corner", hy, [vl, vr], segs, []))
    # 5 railway, horizon low, VP centre-left
    vp, hy = (300, 330), 330
    segs = []
    for x in (180, 250, 420, 500):
        segs.append(((vp[0] + (x - vp[0]) * 0.45, vp[1] + (460 - vp[1]) * 0.45), (x + (x - vp[0]) * 0.8, 460 + 130 * 0.8)))
    for k in range(5):
        yk = 380 + k * 18
        segs.append(((vp[0] - (yk - hy) * 2.4, yk), (vp[0] + (yk - hy) * 2.4, yk)))
    fills = [("poly", [(0, 0), (700, 0), (700, 342), (0, 342)], (214, 226, 238))]
    P.append(("5 · Railway", hy, [vp], segs, fills))
    return P


def _m4_drill_sheet(answers):
    W, H = 2200, 1560
    im = Image.new("RGB", (W, H), (250, 250, 247))
    d = ImageDraw.Draw(im)
    d.text((60, 40), "Find the horizon: extend the lines to their vanishing point(s), then draw the eye-level line.",
           font=font(34, True), fill=(30, 36, 48))
    d.text((60, 90), "Photoshop Intermediate · Lesson 4.1 drill" + ("   ·   INSTRUCTOR ANSWERS" if answers else ""),
           font=font(24), fill=(90, 98, 112))
    pw, ph = 700, 460
    slots = [(60, 160), (760 + 0, 160), (1460, 160), (60, 760), (760, 760), (1460, 760)]
    for i, (title, hy, vps, segs, fills) in enumerate(_m4_drill_panels()):
        ox, oy = slots[i]
        pan = Image.new("RGB", (pw, ph), (255, 255, 255))
        pd = ImageDraw.Draw(pan)
        for kind, pts, col in fills:
            pd.polygon(pts, fill=col)
        for a, b in segs:
            pd.line([a, b], fill=(40, 44, 52), width=4)
        if answers:
            for a, b in segs:
                ax, ay = a
                bx, by = b
                for vp in vps:
                    # extend the segment toward the VP it points at (if near-collinear)
                    cr = (bx - ax) * (vp[1] - ay) - (by - ay) * (vp[0] - ax)
                    if abs(cr) / max(1.0, math.hypot(bx - ax, by - ay)) < 6:
                        pd.line([a, vp], fill=(20, 140, 200), width=2)
            pd.line([(0, hy), (pw, hy)], fill=(220, 40, 40), width=4)
            for vp in vps:
                if 0 <= vp[0] <= pw:
                    pd.ellipse([vp[0] - 9, vp[1] - 9, vp[0] + 9, vp[1] + 9], outline=(220, 40, 40), width=4)
            pd.text((12, hy - 34), "horizon = eye level", font=font(22, True), fill=(220, 40, 40))
        pd.rectangle([0, 0, pw - 1, ph - 1], outline=(150, 156, 166), width=2)
        im.paste(pan, (ox, oy + 40))
        d.text((ox, oy), title, font=font(28, True), fill=(30, 36, 48))
    ox, oy = slots[5]
    d.rectangle([ox, oy + 40, ox + pw - 1, oy + 40 + ph - 1], outline=(150, 156, 166), width=2)
    d.text((ox, oy), "6 · Your own photo", font=font(28, True), fill=(30, 36, 48))
    lines = ["Paste one of your five homework photos here", "(or sketch it), then mark:",
             "• two receding edges, extended", "• the vanishing point", "• the horizon line",
             "• where it crosses any person"]
    for k, t in enumerate(lines):
        d.text((ox + 30, oy + 80 + k * 44), t, font=font(26), fill=(90, 98, 112))
    if answers:
        d.text((60, H - 70), "Panels 3 and 4 are two-point scenes: both vanishing points sit off the panel, "
               "but still on the same horizontal line.", font=font(24), fill=(180, 40, 40))
    return im


def m4_horizon_sheet():
    im = _m4_drill_sheet(False)
    save_jpg(im, 4, "l10-horizon-practice-sheet.jpg", quality=90)


def _m4_save_jpg_folder(img, name, folder, quality=88):
    if isinstance(img, np.ndarray):
        img = Image.fromarray(to_u8(img))
    p = out_path(4, name, folder)
    img.save(p, "JPEG", quality=quality, dpi=(72, 72), optimize=True, icc_profile=SRGB_ICC)
    _record(p)


def m4_horizon_answers():
    _m4_save_jpg_folder(_m4_drill_sheet(True), "l10-horizon-practice-answers.jpg", "instructor", 90)


def m4_plaza_answer_overlay():
    """Instructor-only: the plaza with its horizon, vanishing point, extended edges and
    ghost outlines of the practice figure at three correct distances (the 'same person
    walking away' solo variation)."""
    img = _m4_render_plaza()
    cam = _M4_PLAZA
    im = Image.fromarray(to_u8(img))
    d = ImageDraw.Draw(im, "RGBA")
    H0, CX, F = cam["h0"], cam["cx"], cam["F"]
    for X, Y in [(-7, 14), (-7, 3.8), (-7, 0), (5, 0), (4.55, 4.2), (-7, 7.5), (-7, 10.4)]:
        a = _m4_P(cam, X, Y, 4.0 if X < 0 else 7.0)
        d.line([a, (CX, H0)], fill=(40, 190, 255, 230), width=3)
    d.line([(0, H0), (_M4_W, H0)], fill=(235, 40, 40, 255), width=5)
    d.ellipse([CX - 14, H0 - 14, CX + 14, H0 + 14], outline=(235, 40, 40, 255), width=5)
    d.text((40, H0 - 52), "HORIZON = camera eye level (y = 700)", font=font(38, True), fill=(235, 40, 40, 255))
    d.text((CX - 330, H0 + 16), "vanishing point", font=font(32, True), fill=(235, 40, 40, 255))
    for X, Z in [(1.2, 8.0), (1.2, 16.0), (1.2, 32.0)]:
        s = F / Z
        fx, fy = _m4_P(cam, X, 0, Z)
        top = fy - 1.72 * s
        d.rectangle([fx - 0.3 * s, top, fx + 0.3 * s, fy], outline=(40, 230, 180, 255), width=4)
        d.line([(fx - 0.5 * s, fy), (fx + 0.5 * s, fy)], fill=(40, 230, 180, 255), width=4)
        d.text((fx + 0.36 * s, top), f"Z={Z:.0f} m: {1.72 * s:.0f} px tall", font=font(28, True),
               fill=(40, 230, 180, 255))
    for (x0, y0) in [(760, 1250), (1560, 1120)]:
        d.line([(x0, y0), (x0 - 260, y0 - 40)], fill=(255, 210, 60, 255), width=6)
        d.polygon([(x0 - 260, y0 - 40), (x0 - 228, y0 - 58), (x0 - 232, y0 - 22)], fill=(255, 210, 60, 255))
    d.text((360, 1270), "sun high right: every shadow falls LEFT", font=font(34, True), fill=(255, 210, 60, 255))
    _m4_save_jpg_folder(im, "l10-plaza-answer-overlay.jpg", "instructor", 88)


# ---- L11 light references (hard sun / overcast) --------------------------------------

_M4_REF = dict(F=1500.0, cx=1200.0, h0=520.0, hc=1.2)


def _m4_ref_scene(hard, name):
    r = rng(name)
    cam = _M4_REF
    W, H = _M4_W, _M4_H
    F, CX, H0, HC = cam["F"], cam["cx"], cam["h0"], cam["hc"]
    xx, yy = coords(W, H)
    if hard:
        sky = vgrad(W, H, [(0, "#5e9ad8"), (1, "#d6e6f4")], 0, H0)
        gcol_n, gcol_f = np.array((222, 206, 176), F32), np.array((206, 200, 186), F32)
    else:
        sky = vgrad(W, H, [(0, "#a3adb8"), (1, "#c6ccd2")], 0, H0)
        gcol_n, gcol_f = np.array((168, 166, 160), F32), np.array((176, 178, 178), F32)
    img = sky.copy()
    dy = yy - H0
    with np.errstate(divide="ignore", invalid="ignore"):
        zg = np.where(dy > 0, F * HC / dy, 1e9)
    t = np.clip((zg - 3) / 40, 0, 1)[..., None]
    g = gcol_n * (1 - t) + gcol_f * t
    tex = blur_img(np.repeat(r.normal(128, 30, (H, W, 1)).astype(F32), 3, 2), 1.2)[..., :1] - 128
    g = g + tex * 0.10 * (1 - t)
    img = np.where((dy > 0)[..., None], g, img)
    # far tree line on the horizon (hazy)
    tl = H0 - 26 - 16 * np.abs(np.sin(xx / 53.0)) - 10 * np.sin(xx / 170.0)
    tree_col = np.array((150, 170, 160) if hard else (150, 158, 158), F32)
    img = np.where(((yy > tl) & (yy <= H0 + 2))[..., None], tree_col, img)

    sun = dict(dx=-0.944, dz=0.33, cot=0.84)
    objs = [  # kind, X, Z, size
        ("cube", -1.05, 4.6, 0.55), ("sphere", 0.35, 4.0, 0.30),
        ("cyl", 1.35, 5.4, 0.20), ("pole", -0.15, 7.6, 1.7),
    ]
    # shadows
    for kind, X, Z, s_ in objs:
        if kind == "cube":
            parts = [_m4_box(X - s_ / 2, X + s_ / 2, 0, s_, Z - s_ / 2, Z + s_ / 2)]
        elif kind == "sphere":
            pts = [(X + s_ * math.cos(a) * math.sin(b), s_ + s_ * math.cos(b), Z + s_ * math.sin(a) * math.sin(b))
                   for a in np.linspace(0, 2 * math.pi, 16) for b in np.linspace(0, math.pi, 9)]
            parts = [[(X, 0.0, Z)] + pts]
        elif kind == "cyl":
            pts = [(X + s_ * math.cos(a), y, Z + s_ * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 24)
                   for y in (0.0, 0.75)]
            parts = [pts]
        else:
            parts = [_m4_box(X - 0.03, X + 0.03, 0, s_, Z - 0.03, Z + 0.03)]
        if hard:
            m, _ = _m4_shadow_layer(cam, parts, W, H, sun=sun, near=0.9, far=4.5)
            _m4_apply_shadow(img, m, 0.58)
        # contact / occlusion pool (tight in hard light, broad in overcast)
        fx, fy = _m4_P(cam, X, 0, Z)
        sc = F / Z
        rad = {"cube": s_ * 0.62, "sphere": s_ * 0.55, "cyl": s_ * 1.05, "pole": 0.06}[kind]
        if hard:
            _m4_contact(img, fx, fy, rad * sc, rad * sc * 0.22, 0.55, 2.0)
        else:
            _m4_contact(img, fx, fy, rad * sc * 1.9, rad * sc * 0.55, 0.30, 26.0)
            _m4_contact(img, fx, fy, rad * sc * 1.05, rad * sc * 0.25, 0.35, 5.0)
    # objects (far to near)
    Lh = np.array((0.944 * 0.77, 0.64, -0.33 * 0.77))   # toward the sun (X, Y, Z-away)
    Lh = Lh / np.linalg.norm(Lh)
    amb, key = (0.42, 0.72) if hard else (0.78, 0.22)
    for kind, X, Z, s_ in sorted(objs, key=lambda o: -o[2]):
        sc = F / Z
        if kind == "cube":
            h2 = s_ / 2
            faces = {  # normal, quad in world
                "front": ((0, 0, -1), [(X - h2, 0, Z - h2), (X + h2, 0, Z - h2), (X + h2, s_, Z - h2), (X - h2, s_, Z - h2)]),
                "right": ((1, 0, 0), [(X + h2, 0, Z - h2), (X + h2, 0, Z + h2), (X + h2, s_, Z + h2), (X + h2, s_, Z - h2)]),
                "top": ((0, 1, 0), [(X - h2, s_, Z - h2), (X + h2, s_, Z - h2), (X + h2, s_, Z + h2), (X - h2, s_, Z + h2)]),
            }
            base = np.array((196, 84, 60), F32)
            for fname in ("right", "top", "front"):
                n, q = faces[fname]
                if fname == "right" and X + h2 > 0:
                    continue
                lam = amb + key * max(0.0, float(np.dot(n, Lh)))
                if not hard:
                    lam = amb + 0.22 * (1.0 if fname == "top" else 0.55)
                c = Canvas((0, 0, W, H), ss=3, mode="L")
                c.poly([_m4_P(cam, *p) for p in q], 255)
                paint(img, c.mask(), np.clip(base * lam, 0, 255))
        elif kind == "sphere":
            cx_, cy_ = _m4_P(cam, X, s_, Z)
            rr = s_ * sc
            c = Canvas((cx_ - rr, cy_ - rr, cx_ + rr, cy_ + rr), ss=3, mode="L", pad=2)
            c.circle(cx_, cy_, rr, 255)
            m = c.mask()
            hh, ww = m.a.shape
            gy, gx = np.mgrid[0:hh, 0:ww].astype(F32)
            nx = (gx + m.x + 0.5 - cx_) / rr
            ny = -(gy + m.y + 0.5 - cy_) / rr
            nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
            lam = np.clip(nx * Lh[0] + ny * Lh[1] - nz * Lh[2], 0, 1)   # camera looks along +Z
            shade = amb + key * lam if hard else amb + key * (0.5 + 0.5 * ny)
            col = np.array((66, 120, 196), F32)[None, None, :] * shade[..., None]
            col[..., :] += (np.clip(lam, 0, 1) ** 30 * (70 if hard else 0))[..., None]
            full = np.zeros((H, W, 3), F32)
            sb = _slices(img.shape, m.x, m.y, m.a.shape)
            full[sb[0]] = col[sb[1]]
            paint(img, m, full)
        elif kind == "cyl":
            x0, _ = _m4_P(cam, X - s_, 0, Z)
            x1, yb = _m4_P(cam, X + s_, 0, Z)
            _, yt = _m4_P(cam, X, 0.75, Z)
            ery = s_ * sc * 0.18
            c = Canvas((x0, yt - ery, x1, yb + ery), ss=3, mode="L", pad=2)
            c.rect(x0, yt, x1, yb, 255)
            c.ellipse((x0 + x1) / 2, yb, (x1 - x0) / 2, ery, 255)
            m = c.mask()
            hh, ww = m.a.shape
            u = np.clip(((np.arange(ww, dtype=F32) + m.x) - (x0 + x1) / 2) / ((x1 - x0) / 2), -1, 1)
            lam = np.clip(u * 0.944 + np.sqrt(1 - u * u) * 0.33, 0, 1) if hard else 0.5 + 0.2 * u
            shade = (amb + key * lam) if hard else (amb + 0.1 * lam)
            col = np.array((236, 200, 70), F32)[None, None, :] * np.broadcast_to(shade[None, :], (hh, ww))[..., None]
            full = np.zeros((H, W, 3), F32)
            sb = _slices(img.shape, m.x, m.y, m.a.shape)
            full[sb[0]] = col[sb[1]]
            paint(img, m, full)
            c2 = Canvas((x0, yt - ery, x1, yt + ery), ss=3, mode="L", pad=1)
            c2.ellipse((x0 + x1) / 2, yt, (x1 - x0) / 2, ery, 255)
            paint(img, c2.mask(), np.clip(np.array((236, 200, 70), F32) * (amb + key * 0.64 if hard else amb + 0.2), 0, 255))
        else:
            x0, yb = _m4_P(cam, X - 0.03, 0, Z)
            x1, yt = _m4_P(cam, X + 0.03, s_, Z)
            c = Canvas((x0, yt, x1, yb), ss=3, mode="L", pad=1)
            c.rect(x0, yt, x1, yb, 255)
            paint(img, c.mask(), (90, 92, 96))
            c = Canvas((x0, yt, x1, yb), ss=3, mode="L", pad=1)
            c.rect((x0 + x1) / 2, yt, x1, yb, 255)
            paint(img, c.mask(), (170, 168, 160) if hard else (112, 114, 118))
    if hard:
        img *= np.array((1.04, 1.0, 0.94), F32)
    else:
        img *= np.array((0.98, 1.0, 1.03), F32)
        m = img.mean()
        img = m + (img - m) * 0.85
    add_noise(img, 2.0, r, mono=True)
    return img


def m4_light_hard():
    save_jpg(_m4_ref_scene(True, "l11-light-reference-hard-sun.jpg"), 4, "l11-light-reference-hard-sun.jpg", quality=88)


def m4_light_overcast():
    save_jpg(_m4_ref_scene(False, "l11-light-reference-overcast.jpg"), 4, "l11-light-reference-overcast.jpg", quality=88)


# ---- L11 glossy showroom floor (reflections) -----------------------------------------

_M4_SHOW = dict(F=1300.0, cx=1200.0, h0=640.0, hc=1.5)


def m4_glossy_floor():
    r = rng("l11-glossy-floor-scene.jpg")
    cam = _M4_SHOW
    W, H = _M4_W, _M4_H
    F, CX, H0, HC = cam["F"], cam["cx"], cam["h0"], cam["hc"]
    xx, yy = coords(W, H)
    dx, dy = xx - CX, yy - H0
    ZB = 14.0
    with np.errstate(divide="ignore", invalid="ignore"):
        zg = np.where(dy > 0, F * HC / dy, 1e9)
        Xg = dx * zg / F
        zl = np.where(dx < 0, -5.0 * F / dx, 1e9)
        zr = np.where(dx > 0, 5.0 * F / dx, 1e9)
    Yl = HC - dy * zl / F
    Yr = HC - dy * zr / F
    Xb = dx * ZB / F
    Yb = HC - dy * ZB / F
    img = np.zeros((H, W, 3), F32)
    # back wall with a warm-white panel grid and a magenta neon strip
    back = np.array((58, 56, 64), F32) * (1 + 0.25 * np.clip(Yb / 4.0, 0, 1))[..., None]
    back = back * np.where((np.mod(Xb, 2.0) < 0.03)[..., None], 0.7, 1.0)
    neon = np.exp(-((Yb - 2.7) / 0.05) ** 2) * (np.abs(Xb) < 3.4)
    glow = np.exp(-((Yb - 2.7) / 0.55) ** 2) * np.clip(1 - (np.abs(Xb) - 3.4) / 1.5, 0, 1)
    back = back + neon[..., None] * np.array((255, 120, 230), F32) + glow[..., None] * np.array((90, 20, 80), F32)
    img[:] = back
    # left wall: tall daylight windows (the key light), right wall dark
    lw = np.array((70, 68, 74), F32)
    winm = (np.mod(zl, 3.0) > 0.6) & (Yl > 0.5) & (Yl < 3.6)
    lwv = np.where(winm[..., None], np.array((236, 240, 246), F32), lw)
    sel = (zl < ZB) & (Yl >= 0) & (Yl <= 4.2)
    img[sel] = lwv[sel]
    sel = (zr < ZB) & (Yr >= 0) & (Yr <= 4.2)
    img[sel] = np.array((44, 42, 48), F32)
    # ceiling above 4.2 m
    with np.errstate(divide="ignore", invalid="ignore"):
        zc = np.where(dy < 0, F * (HC - 4.2) / dy, 1e9)
    sel = (dy < 0) & (zc < ZB) & (np.abs(dx * zc / F) < 5.0)
    img[sel] = np.array((34, 34, 38), F32)
    # floor: polished dark stone, 1.2 m tiles, sun patches from the windows
    fsel = (dy > 0) & (zg < ZB) & (np.abs(Xg) < 5.0)
    fl = np.array((30, 30, 34), F32) * np.ones_like(img)
    gz = np.abs(zg / 1.2 - np.round(zg / 1.2)) * 1.2
    gx = np.abs(Xg / 1.2 - np.round(Xg / 1.2)) * 1.2
    fp = np.clip(zg * zg / (F * HC), 1e-4, None)
    seam = np.maximum(np.clip((0.01 - gz) / fp + 0.5, 0, 1) * np.clip(1.2 - fp / 0.2, 0, 1),
                      np.clip((0.01 - gx) / np.clip(zg / F, 1e-4, None) + 0.5, 0, 1))
    fl = fl * (1 - 0.35 * seam)[..., None] + (seam * 6)[..., None]
    patch = (np.mod(zg + 0.9 * (Xg + 5.0), 3.0) > 0.7) & (Xg < -1.2) & (Xg > -5)
    patchf = blur_img(patch.astype(F32)[..., None].repeat(3, 2) * 255, 8)[..., 0] / 255
    fl = fl + patchf[..., None] * np.array((60, 58, 52), F32) * np.clip(1 - (Xg + 5) / 4, 0, 1)[..., None]
    img[fsel] = fl[fsel]
    # mirror of the back wall on the glossy floor (flipped about the wall/floor line)
    yb_line = H0 + F * HC / ZB
    ys_src = (2 * yb_line - yy).astype(int).clip(0, H - 1)
    mir = img[ys_src, np.arange(W)[None, :].repeat(H, 0)]
    dist = np.clip((yy - yb_line) / 500.0, 0, 1)
    refl_ok = fsel & (np.abs(Xb) < 7.0)
    mir_b = blur_img(mir, 5)
    mix = (0.42 * (1 - dist) ** 1.5 * refl_ok)[..., None]
    img = img * (1 - mix) + np.maximum(img, mir_b) * mix
    # objects: pedestal + vase, chrome sphere; each with its own reflection
    objs = []
    # pedestal
    Xp, Zp = -1.3, 6.4
    c = Canvas((0, 0, W, H), ss=3, mode="RGBA")
    q = [(Xp - 0.35, 0, Zp - 0.35), (Xp + 0.35, 0, Zp - 0.35), (Xp + 0.35, 0.95, Zp - 0.35), (Xp - 0.35, 0.95, Zp - 0.35)]
    c.poly([_m4_P(cam, *p) for p in q], (214, 212, 206))
    q = [(Xp + 0.35, 0, Zp - 0.35), (Xp + 0.35, 0, Zp + 0.35), (Xp + 0.35, 0.95, Zp + 0.35), (Xp + 0.35, 0.95, Zp - 0.35)]
    c.poly([_m4_P(cam, *p) for p in q], (150, 148, 150))
    q = [(Xp - 0.35, 0.95, Zp - 0.35), (Xp + 0.35, 0.95, Zp - 0.35), (Xp + 0.35, 0.95, Zp + 0.35), (Xp - 0.35, 0.95, Zp + 0.35)]
    c.poly([_m4_P(cam, *p) for p in q], (236, 234, 228))
    vx, vy = _m4_P(cam, Xp, 0.95, Zp)
    s = F / Zp
    c.ellipse(vx, vy - 0.20 * s, 0.17 * s, 0.20 * s, (40, 104, 150))
    c.rect(vx - 0.05 * s, vy - 0.52 * s, vx + 0.05 * s, vy - 0.34 * s, (40, 104, 150))
    c.ellipse(vx, vy - 0.52 * s, 0.075 * s, 0.02 * s, (30, 80, 118))
    objs.append((c.layer(), _m4_P(cam, Xp, 0, Zp - 0.35)[1]))
    # sphere
    Xs, Zs, rs = 1.6, 8.2, 0.45
    cx_, cy_ = _m4_P(cam, Xs, rs, Zs)
    rr = rs * F / Zs
    c = Canvas((cx_ - rr, cy_ - rr, cx_ + rr, cy_ + rr), ss=3, mode="L", pad=2)
    c.circle(cx_, cy_, rr, 255)
    m = c.mask()
    hh, ww = m.a.shape
    gy, gx_ = np.mgrid[0:hh, 0:ww].astype(F32)
    nx = (gx_ + m.x + 0.5 - cx_) / rr
    ny = -(gy + m.y + 0.5 - cy_) / rr
    lam = np.clip(-nx * 0.8 + ny * 0.3 + 0.3, 0, 1)
    col = np.array((200, 60, 44), F32)[None, None] * (0.25 + 0.85 * lam)[..., None]
    col += (np.clip(lam, 0, 1) ** 25 * 120)[..., None]
    col += (np.clip(nx, 0, 1) ** 4 * 60)[..., None] * np.array((1, 0.4, 0.9), F32)  # neon rim, right
    objs.append((Layer(m.x, m.y, col, m.a), _m4_P(cam, Xs, 0, Zs)[1]))
    for L, ybase in objs:
        # reflection: flip about the object's own base line, fade + blur with distance
        h, w = L.a.shape
        rgb_f = L.rgb[::-1]
        a_f = L.a[::-1]
        ry0 = int(round(2 * ybase - (L.y + h)))
        dd = np.clip((np.arange(h, dtype=F32) + ry0 - ybase) / (h * 0.8), 0, 1)
        a_f = a_f * (0.38 * (1 - dd))[:, None]
        sharp = Layer(L.x, ry0, rgb_f, a_f)
        soft = _m4_blur_layer(sharp, 7)
        t = dd[:, None]
        blend = Layer(L.x, ry0, sharp.rgb * (1 - t[..., None]) + soft.rgb * t[..., None],
                      sharp.a * (1 - t) + soft.a * t)
        over(img, blend)
        # a tight contact shadow where the object meets the floor
        cols = np.where(L.a.max(axis=0) > 0.5)[0]
        bx = L.x + (cols[0] + cols[-1]) / 2
        bw_ = (cols[-1] - cols[0]) * 0.46
        _m4_contact(img, bx, ybase, bw_, max(3.0, bw_ * 0.07), 0.6, 2.5)
    for L, ybase in objs:
        over(img, L)
    add_noise(img, 1.8, r, mono=True)
    save_jpg(img, 4, "l11-glossy-floor-scene.jpg", quality=88)


# ---- L12 far element + depth-bands scene ---------------------------------------------

def m4_far_clocktower():
    """A crisp, saturated, high-contrast distant element (RGBA). Dropped at the far end of
    the plaza it looks pasted forward until it gets atmosphere."""
    r = rng("l12-far-clocktower-cutout.png")
    W, H = 520, 1500
    c = Canvas((0, 0, W, H), ss=3, mode="RGBA")
    c.rect(110, 420, 410, 1490, (178, 64, 40))
    for yv in (560, 860, 1160):
        c.rect(100, yv, 420, yv + 26, (246, 240, 228))
    for yv in (640, 940, 1240):
        c.rrect(222, yv, 298, yv + 150, 36, (34, 30, 36))
    c.rect(96, 380, 424, 430, (246, 240, 228))
    c.rect(130, 190, 390, 390, (190, 70, 44))
    c.circle(260, 290, 86, (250, 248, 240))
    c.circle(260, 290, 86 - 8, (252, 250, 244))
    c.line([(260, 290), (260, 222)], 9, (20, 20, 24))
    c.line([(260, 290), (306, 312)], 9, (20, 20, 24))
    c.poly([(116, 196), (404, 196), (260, 8)], (26, 92, 96))
    c.rect(100, 1440, 420, 1500, (120, 110, 100))
    L = c.layer()
    h, w = L.a.shape
    xs = np.arange(w, dtype=F32) / w
    f = (0.72 + 0.56 * xs)[None, :]                       # lit from the right, hard
    rgb = L.rgb * f[..., None]
    rgb += r.standard_normal((h, w, 1), dtype=F32) * 1.5
    out = np.dstack([np.clip(rgb, 0, 255), L.a * 255])
    save_png(Image.fromarray(to_u8(out), "RGBA"), 4, "l12-far-clocktower-cutout.png")


def m4_depth_bands():
    """Five depth bands (sky, mountains, hills, tree line, foreground rocks) rendered with
    NO atmospheric perspective: every band has the same contrast and saturation, so the
    learner must build the depth with contrast and haze alone."""
    r = rng("l12-depth-bands-flat.jpg")
    W, H = _M4_W, _M4_H
    xx, yy = coords(W, H)
    img = vgrad(W, H, [(0, "#3f7fd0"), (1, "#8fb8e6")], 0, 760)
    bands = [  # base y, amp, colour, texture scale
        (520, 150, (52, 88, 120), 60),
        (700, 90, (58, 110, 70), 40),
        (860, 60, (40, 96, 44), 22),
        (1120, 80, (120, 96, 70), 14),
    ]
    for k, (by, amp, col, ts) in enumerate(bands):
        ph = r.uniform(0, 6.28)
        top = by - amp * (0.6 * np.sin(xx / (170 + 90 * k) + ph) + 0.4 * np.sin(xx / (61 + 17 * k) + 2 * ph))
        if k == 2:
            top = top - 30 * np.abs(np.sin(xx / 24.0 + ph))
        m = yy > top
        n = r.normal(0, 1, (H // 4 + 1, W // 4 + 1)).astype(F32)
        n = np.asarray(Image.fromarray(to_u8(n * 40 + 128)).resize((W, H), Image.BICUBIC), F32)[:H, :W] - 128
        shade = 1 + n / 128 * 0.9                         # full-contrast texture in every band
        ridge = np.clip((yy - top) / (ts * 3), 0, 1)
        shade = shade * (0.65 + 0.45 * ridge)
        colr = np.array(col, F32)[None, None] * shade[..., None]
        img = np.where(m[..., None], colr, img)
    add_noise(img, 2.0, r, mono=True)
    save_jpg(img, 4, "l12-depth-bands-flat.jpg", quality=88)


def m4_key_visual_reference():
    """Instructor-only: the finished Module 4 key visual, built from the practice files the
    way the lessons describe (placed on the horizon, relit, two shadows, far element hazed,
    one grade on top, vignette + grain)."""
    hero = (0.9, 9.5, dict(_M4_HERO, top="#f1e2cc", arm="#e6d5bd"))  # relit warm
    tw = Image.open(out_path(4, "l12-far-clocktower-cutout.png")).convert("RGBA")
    tw = tw.resize((int(520 * 0.15), int(1500 * 0.15)), Image.LANCZOS)
    a = np.asarray(tw, F32)
    L = Layer(1335, 700 - 22 - a.shape[0], a[..., :3], a[..., 3] / 255)
    img = _m4_render_plaza(extra=[hero], name="l12-key-visual-reference.jpg",
                           far=_m4_hazed(L, 0.55, contrast=0.6))
    # unifying grade: gentle S, cool shadows, warm highlights
    lum = img.mean(axis=2, keepdims=True) / 255
    s_ = lum + 0.10 * np.sin((lum - 0.5) * math.pi) * 0.5 * 2
    img = img * (s_ / np.clip(lum, 1e-3, None))
    img += (1 - lum) * np.array((-6, 2, 12), F32) + lum * np.array((12, 4, -10), F32)
    xx, yy = coords(_M4_W, _M4_H)
    v = 1 - 0.32 * np.clip(((xx - 1200) / 1300) ** 2 + ((yy - 820) / 900) ** 2, 0, 1.4)
    img *= v[..., None]
    add_noise(img, 3.2, rng("m4-grain"), mono=True)
    _m4_save_jpg_folder(np.clip(img, 0, 255), "l12-key-visual-reference.jpg", "instructor", 86)


# ======================================================================================
# Module 5: Design Systems & Type
# ======================================================================================

# ======================================================================================
# Module 5 · Design Systems & Type (L13–L15)
# ======================================================================================
# One running brand ("Northwind · Coastal Coffee Roasters", the example from Lesson 5.1)
# ties the three labs together: a copy deck and a "ransom-note" before-file for the type
# system (L13), a blank-poster wall and a tote bag to mock up, four swappable designs and
# a logo in two versions for linked-asset updates (L14), and key art, two swappable
# backgrounds, campaign copy and safe-zone overlays for the multi-artboard campaign (L15).

_M5_EXTRA_DIRS = [
    "/usr/share/fonts/truetype/ubuntu", "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/liberation2", "/usr/share/fonts/truetype/freefont",
    "/System/Library/Fonts", "/Library/Fonts",
]

_M5_FACES = {
    "sans": ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf", "Helvetica.ttf", "LiberationSans-Regular.ttf"],
    "sans_bold": ["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf", "LiberationSans-Bold.ttf"],
    "serif": ["DejaVuSerif.ttf", "Georgia.ttf", "georgia.ttf", "Times New Roman.ttf", "times.ttf",
              "LiberationSerif-Regular.ttf"],
    "serif_bold": ["DejaVuSerif-Bold.ttf", "Georgia Bold.ttf", "georgiab.ttf", "Times New Roman Bold.ttf",
                   "timesbd.ttf", "LiberationSerif-Bold.ttf"],
    "mono": ["DejaVuSansMono.ttf", "Courier New.ttf", "cour.ttf", "LiberationMono-Regular.ttf"],
    "mono_bold": ["DejaVuSansMono-Bold.ttf", "Courier New Bold.ttf", "courbd.ttf", "LiberationMono-Bold.ttf"],
    "condensed": ["Ubuntu-C.ttf", "DejaVuSansCondensed.ttf", "arialn.ttf", "Arial Narrow.ttf",
                  "LiberationSansNarrow-Regular.ttf"],
    "light": ["Ubuntu-L.ttf", "DejaVuSans-ExtraLight.ttf", "Arial.ttf", "arial.ttf"],
}


@lru_cache(maxsize=None)
def _m5_font(size, face="sans"):
    for n in _M5_FACES[face]:
        for cand in [n] + [f"{d}/{n}" for d in _FONT_DIRS + _M5_EXTRA_DIRS]:
            try:
                return ImageFont.truetype(cand, int(size))
            except OSError:
                continue
    return font(int(size), bold=face.endswith("bold"))


def _m5_tlen(s, f, track):
    return sum(f.getlength(ch) for ch in s) + track * max(len(s) - 1, 0)


class _M5Sheet:
    """A supersampled flat-graphics sheet (RGB or RGBA), coordinates in final pixels."""

    def __init__(self, w, h, bg, ss=2, mode="RGB"):
        self.w, self.h, self.ss = w, h, ss
        if isinstance(bg, str):
            bg = hexc(bg)
        self.im = Image.new(mode, (w * ss, h * ss), bg)
        self.d = ImageDraw.Draw(self.im)

    def _c(self, c):
        if isinstance(c, str):
            return hexc(c)
        return tuple(int(v) for v in c)

    def P(self, pts):
        return [(x * self.ss, y * self.ss) for x, y in pts]

    def rect(self, x0, y0, x1, y1, fill, outline=None, width=0):
        self.d.rectangle([x0 * self.ss, y0 * self.ss, x1 * self.ss - 1, y1 * self.ss - 1],
                         fill=None if fill is None else self._c(fill),
                         outline=None if outline is None else self._c(outline), width=int(width * self.ss))

    def rrect(self, x0, y0, x1, y1, r, fill):
        self.d.rounded_rectangle([x0 * self.ss, y0 * self.ss, x1 * self.ss, y1 * self.ss],
                                 radius=r * self.ss, fill=self._c(fill))

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=0):
        self.d.ellipse([(cx - rx) * self.ss, (cy - ry) * self.ss, (cx + rx) * self.ss, (cy + ry) * self.ss],
                       fill=None if fill is None else self._c(fill),
                       outline=None if outline is None else self._c(outline), width=int(width * self.ss))

    def poly(self, pts, fill):
        self.d.polygon(self.P(pts), fill=self._c(fill))

    def line(self, pts, width, fill, caps=False):
        self.d.line(self.P(pts), fill=self._c(fill), width=int(width * self.ss), joint="curve")
        if caps:
            for x, y in (pts[0], pts[-1]):
                self.ellipse(x, y, width / 2, width / 2, fill)

    def arc(self, cx, cy, rx, ry, a0, a1, width, fill):
        self.d.arc([(cx - rx) * self.ss, (cy - ry) * self.ss, (cx + rx) * self.ss, (cy + ry) * self.ss],
                   a0, a1, fill=self._c(fill), width=int(width * self.ss))

    def text(self, x, y, s, size, face, fill, anchor="ls", track=0, stroke=0):
        f = _m5_font(round(size * self.ss), face)
        fill = self._c(fill)
        if track:
            tr = track * self.ss
            ln = _m5_tlen(s, f, tr)
            X = x * self.ss - (ln / 2 if anchor[0] == "m" else ln if anchor[0] == "r" else 0)
            for ch in s:
                self.d.text((X, y * self.ss), ch, font=f, fill=fill, anchor="l" + anchor[1],
                            stroke_width=int(stroke * self.ss), stroke_fill=fill)
                X += f.getlength(ch) + tr
        else:
            self.d.text((x * self.ss, y * self.ss), s, font=f, fill=fill, anchor=anchor,
                        stroke_width=int(stroke * self.ss), stroke_fill=fill)

    def length(self, s, size, face, track=0):
        return _m5_tlen(s, _m5_font(round(size * self.ss), face), track * self.ss) / self.ss

    def wrap(self, s, size, face, width):
        words, lines, cur = s.split(), [], ""
        for w_ in words:
            t = (cur + " " + w_).strip()
            if self.length(t, size, face) <= width or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w_
        if cur:
            lines.append(cur)
        return lines

    def done(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def _m5_wave_pts(x0, x1, y, amp, period, phase=0.0, n=160):
    xs = np.linspace(x0, x1, n)
    return [(float(x), float(y + amp * math.sin(2 * math.pi * (x - x0) / period + phase))) for x in xs]


def _m5_persp_coeffs(dst, src):
    """PIL PERSPECTIVE coefficients mapping output points dst[i] -> input points src[i]."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return np.linalg.solve(np.array(A, float), np.array(b, float)).tolist()


def _m5_lowfreq(w, h, r, cell, amp):
    """Smooth random variation (+/- amp), e.g. plaster or fabric unevenness."""
    small = r.standard_normal((h // cell + 2, w // cell + 2)).astype(F32)
    im = Image.fromarray(small).resize((w, h), Image.BICUBIC)
    a = np.asarray(im, F32)
    return a / (np.abs(a).max() + 1e-6) * amp


# ---- the Northwind logo (two versions, identical canvas) -----------------------------

def _m5_logo(version):
    W, H = 1600, 600
    sh = _M5Sheet(W, H, (0, 0, 0, 0), ss=3, mode="RGBA")
    if version == 1:
        ink, accent = "#1d3557", "#e76f51"
    else:
        ink, accent = "#1f6f66", "#d9a441"
    cx, cy, R = 300, 300, 230
    sh.ellipse(cx, cy, R, R, outline=ink, width=22)
    if version == 1:
        # sun rising over three waves
        sh.d.pieslice([(cx - 120) * 3, (cy - 120 + 10) * 3, (cx + 120) * 3, (cy + 120 + 10) * 3],
                      180, 360, fill=hexc(accent))
        for k, yy in enumerate((cy + 40, cy + 85, cy + 130)):
            half = [185, 170, 140][k]
            sh.line(_m5_wave_pts(cx - half, cx + half, yy, 12, 90), 16, ink, caps=True)
    else:
        # coffee bean with steam
        sh.ellipse(cx, cy + 40, 95, 130, fill=accent)
        sh.line([(cx + 5 + 30 * math.sin(t / 10.0 * math.pi), cy - 80 + t * 24)
                 for t in range(11)], 16, ink)
        for dx in (-45, 0, 45):
            sh.line([(cx + dx + 14 * math.sin(t / 3.0), cy - 110 - t * 9) for t in range(9)], 12, ink, caps=True)
    sh.text(590, 320, "NORTHWIND", 128, "serif_bold", ink)
    sh.text(594, 395, "COASTAL COFFEE ROASTERS", 34, "sans_bold", accent, track=6)
    if version == 2:
        sh.text(594, 450, "EST. 2019 · PORTLAND", 26, "sans", ink, track=5)
    return sh.done()


# ======================================================================================
# L13 · Type Systems, Styles & Grids
# ======================================================================================

def m5_layout_copy():
    text = """NORTHWIND · COASTAL COFFEE ROASTERS
Copy deck for the Lesson 5.1 (L13) type-system layout
=====================================================

Set every line below with a named Paragraph Style. Do not freehand a size.
Keep the words exactly as written; the exercise is the SYSTEM, not the copy.

ROLE (lesson scale, 16 px base x 1.25)   TEXT
----------------------------------------------------------------------------
Display   39 px    Northwind
H1        31 px    Slow-roasted, small batch
Subhead   20 px    COASTAL COFFEE ROASTERS            (tracked caps)
H2        25 px    Single estate
Body      16 px    Sourced from single estates and roasted the morning we
                   ship. Every bag carries its roast date, its farm, and the
                   name of the person who roasted it.
H2        25 px    Roasted to order
Body      16 px    We roast on Mondays and Thursdays, in small batches, and
                   only what has been ordered. Brew it within three weeks
                   and taste the difference.
CTA       20 px    Order a sample box                 (Subhead style +
                                                        an Emphasis Character Style)
Caption   13 px    EST. 2019 · PORTLAND
Caption   13 px    northwindroasters.example
Tagline   (use H2) Tasted, not guessed.

Numbers on the Lesson 5.1 scale: 13 / 16 / 20 / 25 / 31 / 39.
Body leading and document grid ("Gridline Every"): 24 px, Subdivisions 1.

PRACTICE DOCUMENT (optional, for a poster-sized page)
----------------------------------------------------------------------------
The lesson's 16 px base is sized for a small page. For an 1800 x 2400 px practice
poster, multiply every number by 3 (the ratio does not change):
  Caption 39 · Body 48 · Subhead 60 · H2 75 · H1 93 · Display 117
  Body leading and document grid: 72 px, Subdivisions 1.
  Columns: View > Guides > New Guide Layout, 6 columns, gutter 48 px,
  margins 144 top / 120 left / 144 bottom / 120 right.

Fonts: two families only, one display face and one text face (Adobe Fonts).
Real Bold and Italic weights only; never the Faux Bold / Faux Italic buttons.
Standard Ligatures and Oldstyle Figures on for the Body style.

Before-file to diagnose: l13-ransom-note-before.png (same words, no system).
"""
    save_txt(text, 5, "l13-layout-copy.txt")


def m5_ransom_note():
    """Same Northwind copy set with no system: six faces, random sizes, faux styling."""
    W, H = 1800, 2400
    sh = _M5Sheet(W, H, "#f2eee6", ss=2)
    sh.text(900, 300, "Northwind", 170, "serif_bold", "#7b2d26", anchor="ms")
    sh.text(1660, 450, "COFFEE", 112, "mono_bold", "#1d6fb8", anchor="rs")
    # horizontally stretched "COASTAL" (distorted type)
    tmp = _M5Sheet(360, 120, "#f2eee6", ss=2)
    tmp.text(0, 95, "COASTAL", 92, "condensed", "#6a4c93")
    st = tmp.im.resize((int(tmp.im.width * 1.7), tmp.im.height), Image.BICUBIC)
    sh.im.paste(st, (150 * 2, 360 * 2))
    # faux italic subhead: a regular condensed face sheared
    tmp = _M5Sheet(1300, 150, "#f2eee6", ss=2)
    tmp.text(20, 110, "Slow-roasted, small batch", 88, "condensed", "#2f7d32")
    sheared = tmp.im.transform(tmp.im.size, Image.AFFINE, (1, 0.32, -0.32 * tmp.im.height, 0, 1, 0),
                               resample=Image.BICUBIC, fillcolor=hexc("#f2eee6"))
    sh.im.paste(sheared, (260 * 2, 600 * 2))
    # body: faux bold (stroke), inconsistent line spacing, centered
    for s_, y_ in (("Sourced from single estates", 900), ("and roasted the morning", 985),
                   ("we ship. Every bag carries its", 1098), ("roast date and its farm.", 1170)):
        sh.text(900, y_, s_, 54, "sans", "#3a3a3a", anchor="ms", stroke=1.6)
    # "Tasted!" in a light face, faux-italic, rotated
    tmp = _M5Sheet(900, 300, "#f2eee6", ss=2)
    tmp.text(30, 230, "Tasted!", 210, "light", "#e0a100")
    t2 = tmp.im.transform(tmp.im.size, Image.AFFINE, (1, 0.28, -0.28 * tmp.im.height, 0, 1, 0),
                          resample=Image.BICUBIC, fillcolor=hexc("#f2eee6"))
    t2 = t2.rotate(7, resample=Image.BICUBIC, expand=True, fillcolor=hexc("#f2eee6"))
    sh.im.paste(t2, (950 * 2, 1250 * 2))
    # CTA: shouting, underlined, off to one side
    sh.text(160, 1720, "ORDER NOW!!!", 104, "serif_bold", "#d62828")
    ln = sh.length("ORDER NOW!!!", 104, "serif_bold")
    sh.rect(160, 1740, 160 + ln, 1750, "#d62828")
    sh.text(1080, 1880, "northwindroasters.example", 44, "mono", "#1d6fb8", anchor="ms")
    sh.text(1500, 2270, "EST 2019 portland", 30, "sans", "#8a8a8a", anchor="ms")
    sh.text(260, 2100, "Tasted, not guessed.", 58, "light", "#2f7d32")
    save_png(sh.done(), 5, "l13-ransom-note-before.png")


def m5_system_layout_instructor():
    """INSTRUCTOR reference: the same copy rebuilt on a x3 scale, 6 columns, 72 px grid."""
    W, H = 1800, 2400
    sh = _M5Sheet(W, H, "#f6f3ee", ss=2)
    G, ML, MR, MT = 72, 120, 120, 144
    gut, ncol = 48, 6
    colw = (W - ML - MR - gut * (ncol - 1)) / ncol
    # skeleton: baseline grid + columns (shown faintly on purpose)
    for y in range(0, H, G):
        sh.rect(0, y, W, y + 1, "#cfe0ee")
    for k in range(ncol):
        x0 = ML + k * (colw + gut)
        sh.rect(x0, 0, x0 + colw, H, None, outline="#9fd3e6", width=1)
    ink, accent, soft = "#1d3557", "#e76f51", "#5b6b7d"
    notes = []

    def note(y, s):
        notes.append((y, s))

    sh.text(ML, 3 * G, "COASTAL COFFEE ROASTERS", 60, "sans_bold", accent, track=10); note(3 * G, "Subhead 60 · tracked")
    sh.text(ML, 5 * G, "Northwind", 117, "serif_bold", ink); note(5 * G, "Display 117")
    sh.text(ML, 7 * G, "Slow-roasted, small batch", 93, "serif_bold", ink); note(7 * G, "H1 93")
    # image band: rows 8..18 (a flat sunrise stand-in for the photo)
    y0, y1 = 8 * G, 19 * G - 24
    band = _M5Sheet(W - ML - MR, y1 - y0, "#fbd3b0", ss=1)
    for k, c in enumerate(["#cfe3ee", "#dce7ea", "#e9e3dc", "#f6dcc6", "#fbd3b0"]):
        band.rect(0, k * (y1 - y0) * 0.12, band.w, (k + 1) * (y1 - y0) * 0.12, c)
    band.ellipse(band.w / 2, (y1 - y0) * 0.62, 180, 180, fill="#f4a261")
    band.rect(0, (y1 - y0) * 0.62, band.w, y1 - y0, "#5f9bb3")
    for k in range(5):
        band.line(_m5_wave_pts(0, band.w, (y1 - y0) * (0.68 + k * 0.065), 8, 160, k), 6, "#3d7a93")
    sh.im.paste(band.im.resize(((W - ML - MR) * 2, (y1 - y0) * 2)), (ML * 2, y0 * 2))
    # two feature blocks, each 3 columns wide
    bw = 3 * colw + 2 * gut
    feats = [("Single estate", "Sourced from single estates and roasted the morning we ship. "
              "Every bag carries its roast date, its farm, and the name of the person who roasted it."),
             ("Roasted to order", "We roast on Mondays and Thursdays, in small batches, and only "
              "what has been ordered. Brew it within three weeks and taste the difference.")]
    for k, (h2, body) in enumerate(feats):
        x = ML + k * (bw + gut)
        sh.text(x, 21 * G, h2, 75, "serif_bold", ink)
        for i, ln in enumerate(sh.wrap(body, 48, "sans", bw)):
            sh.text(x, (22 + i) * G, ln, 48, "sans", "#2b2b2b")
    note(21 * G, "H2 75"); note(22 * G, "Body 48 / 72")
    sh.text(ML, 29 * G, "Tasted, not guessed.", 75, "serif_bold", accent); note(29 * G, "H2 75 (tagline)")
    sh.text(ML, 31 * G, "Order a sample box  →", 60, "sans_bold", ink); note(31 * G, "Subhead 60 + Emphasis")
    sh.text(ML, 32 * G, "EST. 2019 · PORTLAND", 39, "sans", soft, track=6); note(32 * G, "Caption 39")
    sh.text(ML + 3 * (colw + gut), 32 * G, "northwindroasters.example", 39, "sans", soft)
    for y, s in notes:
        sh.text(W - 8, y - 6, s, 20, "mono", "#2f8fbf", anchor="rs")
    sh.text(ML, H - 20, "INSTRUCTOR REFERENCE · lesson scale ×3 · 6 columns, gutter 48 · grid 72 px · every baseline on a gridline",
            22, "mono", "#2f8fbf")
    save_png(sh.done(), 5, "l13-system-layout-INSTRUCTOR.png", folder="instructor")


# ======================================================================================
# L14 · Smart-Object Templates & Linked Assets
# ======================================================================================

def m5_mockup_poster_wall():
    """A blank, folded poster on a plaster wall, in perspective, lit from a window at left."""
    W, H = 2400, 1600
    r = rng("l14-mockup-poster-wall.jpg")
    xx, yy = coords(W, H)
    img = solid(W, H, "#c9c2b8")
    light = 1.14 - 0.36 * (xx / W) - 0.06 * ((yy / H - 0.4) ** 2)
    img *= light[..., None]
    img += _m5_lowfreq(W, H, r, 60, 7)[..., None]
    # baseboard + wooden floor
    fl = 1390
    img[fl - 26:fl] = np.array(hexc("#e7e3dc"), F32) * light[fl - 26:fl, :, None]
    floor = vgrad(W, H - fl, [(0, "#7a5a3c"), (1, "#5b4029")])
    for k in range(0, W, 230):
        floor[:, k:k + 3] *= 0.8
    floor *= (1.1 - 0.3 * (xx[fl:] / W))[..., None]
    img[fl:] = floor
    # poster in perspective (built flat at 1200 x 1800, then projected; 2x for clean edges)
    quad = [(930, 250), (1530, 290), (1522, 1172), (940, 1216)]
    pw, ph = 1200, 1800
    paper = np.ones((ph, pw, 3), F32) * np.array(hexc("#efece6"), F32)
    px, py = coords(pw, ph)
    paper *= (1.0 - 0.05 * (py / ph))[..., None]
    for fy in (ph / 3, 2 * ph / 3):                     # horizontal folds: dark crease, lit ridge
        d = py - fy
        paper *= (1 - 0.16 * np.exp(-(d / 5) ** 2) - 0.06 * np.exp(-((d + 26) / 22) ** 2)
                  + 0.05 * np.exp(-((d - 24) / 20) ** 2))[..., None]
    d = px - pw / 2                                      # a softer vertical fold
    paper *= (1 - 0.08 * np.exp(-(d / 5) ** 2) + 0.03 * np.exp(-((d - 30) / 30) ** 2))[..., None]
    curl = np.clip((px / pw + py / ph - 1.72) / 0.28, 0, 1)   # bottom-right corner lifts
    paper *= (1 - 0.14 * curl)[..., None]
    alpha = np.full((ph, pw, 1), 255, F32)
    rgba = Image.fromarray(to_u8(np.concatenate([paper, alpha], -1)), "RGBA")
    S = 2
    co = _m5_persp_coeffs([(x * S, y * S) for x, y in quad], [(0, 0), (pw, 0), (pw, ph), (0, ph)])
    big = rgba.transform((W * S, H * S), Image.PERSPECTIVE, co, resample=Image.BICUBIC)
    proj = np.asarray(big.resize((W, H), Image.BOX), F32)
    pa = proj[..., 3] / 255.0
    # cast shadow of the poster on the wall
    sh_m = Canvas((0, 0, W, H), ss=1, pad=0)
    sh_m.poly([(x + 16, y + 22) for x, y in quad], 255)
    darken(img, sh_m.mask(blur=22), 0.38)
    prgb = proj[..., :3] * light[..., None] / 1.0
    img = img * (1 - pa[..., None]) + prgb * pa[..., None]
    # a soft window-mullion shadow falling across wall and poster
    band = Canvas((0, 0, W, H), ss=1)
    for off in (0, 330):
        band.poly([(500 + off, 0), (590 + off, 0), (1250 + off, H), (1160 + off, H)], 255)
    darken(img, band.mask(blur=26), 0.2)
    add_noise(img, 2.4, r, mono=True)
    save_jpg(img, 5, "l14-mockup-poster-wall.jpg")


def m5_mockup_tote_bag():
    """A plain canvas tote with fabric texture, soft folds and a crease (print area blank)."""
    W, H = 1600, 2000
    r = rng("l14-mockup-tote-bag.jpg")
    xx, yy = coords(W, H)
    img = vgrad(W, H, [(0, "#ece9e4"), (0.8, "#dcd7d0"), (1, "#cfc9c1")])
    # floor shadow
    fs = Canvas((0, 0, W, H), ss=1)
    fs.ellipse(800, 1815, 560, 60, 255)
    darken(img, fs.mask(blur=40), 0.35)
    # handles (back handle darker, front handle lighter)
    for (cy_top, shade) in ((170, 0.78), (235, 1.0)):
        hc = Canvas((0, 0, W, H), ss=2)
        hc.ellipse(800, 640, 290, 640 - cy_top, 255)
        hm = hc.mask()
        hc2 = Canvas((0, 0, W, H), ss=2)
        hc2.ellipse(800, 640, 230, 640 - cy_top - 58, 255)
        ring = hm.a - hc2.mask().a
        ring[int(640 - hm.y):, :] = 0
        col = np.array(hexc("#d9cbb0"), F32) * shade
        paint(img, Mask(hm.x, hm.y, np.clip(ring, 0, 1)), col)
    # bag body with slightly bowed sides
    left = quad_bezier((330, 620), (300, 1200), (300, 1790), 60)
    right = quad_bezier((1300, 1790), (1300, 1200), (1270, 620), 60)
    bc = Canvas((0, 0, W, H), ss=3)
    bc.poly(left + right, 255)
    bm = bc.mask()
    fabric = solid(W, H, "#e4d7bf")
    weave = 1 + 0.025 * np.sin(xx * 1.9) * np.sin(yy * 1.9)
    folds = (1 + 0.045 * np.sin(xx / 95 + 0.6) + 0.03 * np.sin(xx / 41 + 2.0)
             - 0.10 * np.exp(-((xx - 560) / 14) ** 2) * np.clip((yy - 700) / 260, 0, 1)
             - 0.07 * np.exp(-((xx - 1060) / 18) ** 2) * np.clip((yy - 900) / 300, 0, 1))
    diag = (xx - 330) * 0.42 + 1350 - yy                      # diagonal crease low on the bag
    folds -= 0.09 * np.exp(-(diag / 10) ** 2) * np.clip((yy - 1150) / 220, 0, 1)
    folds += 0.05 * np.exp(-((diag - 22) / 18) ** 2) * np.clip((yy - 1150) / 220, 0, 1)
    edge = np.clip(np.minimum(xx - 300, 1300 - xx) / 110, 0, 1)
    shade = folds * weave * (0.8 + 0.2 * edge) * (1.04 - 0.1 * (yy - 620) / 1170)
    fabric *= shade[..., None]
    fabric += _m5_lowfreq(W, H, r, 40, 4)[..., None]
    paint(img, bm, fabric)
    # top hem with stitching
    hem = Canvas((0, 0, W, H), ss=2)
    hem.poly([(330, 620), (1270, 620), (1271, 690), (329, 690)], 255)
    darken(img, hem.mask(), 0.06)
    st = Canvas((0, 0, W, H), ss=2)
    for x in range(345, 1255, 26):
        st.rect(x, 676, x + 14, 680, 255)
    darken(img, st.mask(), 0.3)
    add_noise(img, 3.0, r, mono=True)
    save_jpg(img, 5, "l14-mockup-tote-bag.jpg")


def m5_art_a_sunrise():
    W, H = 1200, 1800
    sh = _M5Sheet(W, H, "#fbd3b0", ss=2)
    for k, c in enumerate(["#bcd8e6", "#cfe0e6", "#e2e4de", "#f1dccb", "#f8d4b6", "#fbcba0"]):
        sh.rect(0, k * 170, W, (k + 1) * 170, c)
    sh.ellipse(600, 1020, 260, 260, fill="#e76f51")
    sh.rect(0, 1020, W, H, "#2a6f8f")
    for k, c in enumerate(["#3d85a3", "#2f7496", "#23607f", "#1d4e6b", "#173f58"]):
        y = 1040 + k * 80
        sh.poly(_m5_wave_pts(0, W, y, 16, 240, k * 1.3) + [(W, H), (0, H)], c)
    sh.rect(0, 1470, W, H, "#132f45")
    sh.text(600, 1620, "NORTHWIND", 124, "serif_bold", "#f6efe4", anchor="ms")
    sh.text(600, 1705, "SUNRISE BLEND", 46, "sans_bold", "#f4a261", anchor="ms", track=12)
    save_png(sh.done(), 5, "l14-art-a-sunrise-1200x1800.png")


def m5_art_b_geometric():
    W, H = 1200, 1800
    sh = _M5Sheet(W, H, "#264653", ss=2)
    sh.ellipse(600, 620, 420, 420, fill="#e9c46a")
    sh.d.pieslice([180 * 2, 200 * 2, 1020 * 2, 1040 * 2], 90, 180, fill=hexc("#2a9d8f"))
    sh.poly([(600, 620), (1080, 1180), (120, 1180)], "#e76f51")
    sh.rect(120, 1180, 1080, 1250, "#f6efe4")
    sh.ellipse(840, 400, 90, 90, fill="#f6efe4")
    sh.text(120, 1470, "SMALL", 150, "sans_bold", "#f6efe4")
    sh.text(120, 1610, "BATCH", 150, "sans_bold", "#e9c46a")
    sh.text(1080, 1610, "NO. 02", 44, "mono_bold", "#f6efe4", anchor="rs")
    save_png(sh.done(), 5, "l14-art-b-geometric-1200x1800.png")


def m5_art_c_typographic():
    W, H = 1200, 1800
    sh = _M5Sheet(W, H, "#e76f51", ss=2)
    sh.text(90, 500, "SLOW", 250, "serif_bold", "#f6efe4")
    sh.text(90, 830, "ROAST", 250, "serif_bold", "#1d3557")
    sh.text(90, 1160, "ED.", 250, "serif_bold", "#f6efe4")
    sh.rect(90, 1320, 1110, 1330, "#1d3557")
    sh.text(90, 1420, "Tasted, not guessed.", 62, "serif", "#1d3557")
    sh.text(90, 1690, "NORTHWIND · EST. 2019", 38, "sans_bold", "#f6efe4", track=8)
    save_png(sh.done(), 5, "l14-art-c-typographic-1200x1800.png")


def m5_art_d_landscape():
    """Deliberately the WRONG shape for the 2:3 placeholder (the Replace Contents size trap)."""
    W, H = 1800, 1200
    sh = _M5Sheet(W, H, "#1d3557", ss=2)
    r = rng("l14-art-d-landscape-1800x1200.png")
    for k in range(9):
        x, y, s = r.uniform(1300, 1660), r.uniform(160, 1040), r.uniform(80, 140)
        a = r.uniform(0, math.pi / 2)
        pts = [(x + s * math.cos(a + j * math.pi / 2), y + s * math.sin(a + j * math.pi / 2)) for j in range(4)]
        sh.poly(pts, ["#a8dadc", "#cfe9ea", "#8cc9cc"][k % 3])
    sh.text(120, 520, "COLD BREW", 140, "serif_bold", "#f6efe4")
    sh.text(120, 700, "SEASON", 140, "serif_bold", "#a8dadc")
    sh.text(124, 860, "Steeped 18 hours. Poured over ice.", 54, "sans", "#f6efe4")
    sh.text(124, 1060, "NORTHWIND", 44, "sans_bold", "#e76f51", track=10)
    save_png(sh.done(), 5, "l14-art-d-landscape-1800x1200.png")


def m5_logo_v1():
    save_png(_m5_logo(1), 5, "l14-logo-v1.png")


def m5_logo_v2():
    save_png(_m5_logo(2), 5, "l14-logo-v2.png")


# ======================================================================================
# L15 · Campaign from One Master
# ======================================================================================

def _m5_key_art():
    """Coffee cup on a saucer, steam, and a sun disk behind: a transparent 2400 x 2400 hero."""
    W = H = 2400
    rgb = np.zeros((H, W, 3), F32)          # premultiplied
    al = np.zeros((H, W, 1), F32)

    def put(m, color, op=1.0):
        paint(rgb, m, color, op)
        paint(al, m, (255.0,), op)

    c = Canvas((300, 150, 2100, 1750), ss=2)
    c.circle(1200, 950, 780, 255)
    put(c.mask(), "#f4a261")
    c = Canvas((520, 270, 1880, 1630), ss=2)
    c.circle(1200, 950, 640, 255)
    put(c.mask(), "#f7b27a")
    # saucer
    c = Canvas((330, 1880, 2070, 2230), ss=3)
    c.ellipse(1200, 2050, 860, 160, 255)
    xx, yy = coords(W, H)
    sauc = np.ones((H, W, 3), F32) * np.array(hexc("#efe6d8"), F32)
    sauc *= (0.78 + 0.25 * np.clip(1 - np.abs(xx - 1000) / 1100, 0, 1))[..., None]
    put(c.mask(), sauc)
    c = Canvas((600, 1960, 1800, 2130), ss=3)
    c.ellipse(1200, 2030, 560, 80, 255)
    put(c.mask(blur=6), "#c9bba6", 0.9)
    # handle (a thick ring on the right)
    c = Canvas((1600, 1250, 2080, 1850), ss=3)
    c.ellipse(1790, 1540, 250, 230, 255)
    hm = c.mask()
    c2 = Canvas((1600, 1250, 2080, 1850), ss=3)
    c2.ellipse(1790, 1540, 170, 150, 255)
    ring = np.clip(hm.a - c2.mask().a, 0, 1)
    put(Mask(hm.x, hm.y, ring), np.array(hexc("#e8dccb"), F32) * 0.92)
    # cup body
    left = quad_bezier((640, 1200), (660, 1850), (900, 2010), 60)
    right = quad_bezier((1500, 2010), (1740, 1850), (1760, 1200), 60)
    c = Canvas((600, 1080, 1800, 2030), ss=3)
    c.poly(left + right, 255)
    c.ellipse(1200, 1200, 560, 115, 255)
    body = np.ones((H, W, 3), F32) * np.array(hexc("#f6efe4"), F32)
    t = (xx - 640) / 1120
    body *= (0.74 + 0.34 * np.exp(-((t - 0.32) / 0.28) ** 2) - 0.1 * np.clip(t - 0.7, 0, 1))[..., None]
    put(c.mask(), body)
    # coffee surface + crema
    c = Canvas((680, 1110, 1720, 1290), ss=3)
    c.ellipse(1200, 1205, 500, 85, 255)
    put(c.mask(), "#b07a4f")
    c = Canvas((700, 1120, 1700, 1290), ss=3)
    c.ellipse(1205, 1212, 455, 70, 255)
    put(c.mask(), "#5a3521")
    # steam: three soft ribbons
    for k, x0 in enumerate((1060, 1210, 1350)):
        c = Canvas((700, 250, 1700, 1180), ss=2)
        pts = [(x0 + 70 * math.sin(yv / 150.0 + k * 1.7), yv) for yv in range(1130, 380 + k * 60, -12)]
        c.line(pts, 46, 255, round_caps=True)
        put(c.mask(blur=16), "#ffffff", 0.75)
    a = al[..., 0] / 255.0
    out = np.where(a[..., None] > 0, rgb / np.maximum(a[..., None], 1e-6), 0)
    return Image.fromarray(to_u8(np.concatenate([out, al], -1)), "RGBA")


def m5_key_art():
    save_png(_m5_key_art(), 5, "l15-key-art.png")


def _m5_background(dark):
    W, H = 1950, 3000
    r = rng("l15-background-dark.jpg" if dark else "l15-background-light.jpg")
    hz = 1900
    if dark:
        sky = [(0, "#08131f"), (0.7, "#15304b"), (1, "#27496b")]
        sea = [(0, "#1a3550"), (1, "#050d16")]
        streak = (150, 190, 220)
    else:
        sky = [(0, "#bcd8e6"), (0.55, "#e7e1d8"), (1, "#fbd0a8")]
        sea = [(0, "#7fb3c8"), (1, "#2f6680")]
        streak = (235, 245, 250)
    img = np.concatenate([vgrad(W, hz, sky), vgrad(W, H - hz, sea)], 0)
    st = Canvas((0, hz, W, H), ss=1)
    for k in range(26):
        y = hz + 30 + (k ** 1.35) * 14 + r.uniform(-8, 8)
        x0 = r.uniform(-200, W * 0.6)
        st.rect(x0, y, x0 + r.uniform(300, 1100), y + r.uniform(3, 7), 255)
    paint(img, st.mask(blur=3), streak, 0.35 if dark else 0.45)
    add_noise(img, 2.0, r, mono=True)
    return img


def m5_background_light():
    save_jpg(_m5_background(False), 5, "l15-background-light.jpg")


def m5_background_dark():
    save_jpg(_m5_background(True), 5, "l15-background-dark.jpg")


def m5_campaign_copy():
    text = """NORTHWIND · SUNRISE BLEND LAUNCH
Campaign brief for Lesson 5.3 (L15), the Module 5 deliverable
=============================================================

One master PSD, four artboards, shared art and type. Build the poster first.

ARTBOARDS (New document, RGB, Artboard on)
  Poster      3300 x 5100 px    (print; design this one first, at full size)
  IG square   1080 x 1080 px
  Story       1080 x 1920 px    (keep text clear of the top and bottom UI overlays)
  Banner      1500 x  500 px    (keep text clear of the crop edges)

SHARED ART (File > Place Linked; keep these files in ONE project folder, never move them)
  Logo        logo.png          (a copy of l14-logo-v1.png, or your own logo from L14)
  Key art     l15-key-art.png   (transparent hero: cup, steam, sun) or your Module 4 composite
  Background  l15-background-light.jpg   (swap for l15-background-dark.jpg for the dark set)

SHARED TYPE (your Lesson 5.1 Paragraph Styles; copy a styled text layer in to bring them)
  Headline (H1 / Display)   Sunrise Blend
  Subhead                   Slow-roasted, small batch
  Tagline (H2)              Tasted, not guessed.
  CTA (Subhead + Emphasis)  Order a sample box
  Caption                   northwindroasters.example

  Use fewer words on smaller sizes. The banner usually needs only the logo,
  the headline and the CTA; the story and the square can drop the caption.

RECOMPOSE, DON'T SQUASH
  Poster  (portrait)   stack: key art large, headline, subhead, CTA, logo low
  Square  (1:1)        center the key art; headline above or below it
  Story   (9:16)       stack vertically; everything inside the safe zone
  Banner  (3:1)        spread horizontally: key art one side, headline + CTA the other

OPTIONAL SHARED GRADE
  The same adjustment layer (or a Color Lookup layer with your Module 4 LUT) at the
  top of each artboard. Adjustment layers cannot be linked: update each copy.

EXPORT
  File > Export > Export As, all artboards, PNG or JPG, 1x.
  (File > Export > Artboards to Files is the batch alternative.)

PROVE IT
  Open logo.png, make a visible change (or paste in l14-logo-v2.png), save.
  Every artboard updates (else Layer > Smart Objects > Update All Modified Content).
  Re-export the whole set.

Safe-zone overlays (guides only, delete before export):
  l15-safe-zones-story.png, l15-safe-zones-banner.png
"""
    save_txt(text, 5, "l15-campaign-copy.txt")


def m5_safe_zones_story():
    W, H = 1080, 1920
    sh = _M5Sheet(W, H, (0, 0, 0, 0), ss=2, mode="RGBA")
    red = (224, 49, 49, 70)
    sh.rect(0, 0, W, 250, red)
    sh.rect(0, H - 340, W, H, red)
    sh.rect(64, 250, W - 64, H - 340, None, outline=(49, 168, 255, 230), width=4)
    sh.text(W / 2, 140, "UI OVERLAY ZONE (profile, progress bar)", 34, "sans_bold", (160, 20, 20, 255), anchor="ms")
    sh.text(W / 2, H - 170, "UI OVERLAY ZONE (reply bar, buttons)", 34, "sans_bold", (160, 20, 20, 255), anchor="ms")
    sh.text(W / 2, 300, "TEXT-SAFE AREA", 30, "mono_bold", (20, 110, 190, 255), anchor="ms")
    sh.text(W / 2, H - 290, "rule of thumb: top 250 px, bottom 340 px, sides 64 px", 24, "mono",
            (20, 110, 190, 255), anchor="ms")
    save_png(sh.done(), 5, "l15-safe-zones-story.png")


def m5_safe_zones_banner():
    W, H = 1500, 500
    sh = _M5Sheet(W, H, (0, 0, 0, 0), ss=2, mode="RGBA")
    red = (224, 49, 49, 70)
    sh.rect(0, 0, W, 60, red)
    sh.rect(0, H - 60, W, H, red)
    sh.rect(0, 60, 60, H - 60, red)
    sh.rect(W - 60, 60, W, H - 60, red)
    sh.rect(60, 60, W - 60, H - 60, None, outline=(49, 168, 255, 230), width=4)
    sh.text(W / 2, 42, "MAY BE CROPPED ON SOME SCREENS", 26, "sans_bold", (160, 20, 20, 255), anchor="ms")
    sh.text(W / 2, H - 20, "rule of thumb: 60 px on every edge; check the platform's current spec", 22,
            "mono", (160, 20, 20, 255), anchor="ms")
    sh.text(W / 2, 100, "TEXT-SAFE AREA", 26, "mono_bold", (20, 110, 190, 255), anchor="ms")
    save_png(sh.done(), 5, "l15-safe-zones-banner.png")


def _m5_cover(im, w, h, fy=0.6):
    s = max(w / im.width, h / im.height)
    r_ = im.resize((max(w, round(im.width * s)), max(h, round(im.height * s))), Image.LANCZOS)
    x0 = (r_.width - w) // 2
    y0 = int(np.clip(fy * r_.height - h * fy, 0, r_.height - h))
    return r_.crop((x0, y0, x0 + w, y0 + h))


def m5_campaign_reference_instructor():
    """INSTRUCTOR model result: the four artboards recomposed from the same assets."""
    bg = Image.fromarray(to_u8(_m5_background(False)))
    art = _m5_key_art()
    logo = _m5_logo(1)
    W, H = 2200, 900
    sheet = Image.new("RGB", (W, H), hexc("#e9edf2"))
    d = ImageDraw.Draw(sheet)
    ink, accent = hexc("#1d3557"), hexc("#e76f51")

    def board(w, h, layout):
        b = _m5_cover(bg, w, h).convert("RGBA")
        dd = ImageDraw.Draw(b)
        for kind, x, y, size, anchor in layout:
            if kind == "art":
                a = art.resize((size, size), Image.LANCZOS)
                b.alpha_composite(a, (int(x - size / 2), int(y - size / 2)))
            elif kind == "logo":
                lg = logo.resize((size, size * 3 // 8), Image.LANCZOS)
                b.alpha_composite(lg, (int(x - (size / 2 if anchor == "m" else 0)), int(y)))
            else:
                face, col, s = {"head": ("serif_bold", ink, "Sunrise Blend"),
                                "sub": ("sans", ink, "Slow-roasted, small batch"),
                                "cta": ("sans_bold", accent, "Order a sample box →")}[kind]
                dd.text((x, y), s, font=_m5_font(size, face), fill=ink if kind != "cta" else (150, 45, 25),
                        anchor=anchor + "s")
        return b.convert("RGB")

    k = 0.11  # poster at 11 %
    pw, ph = round(3300 * k), round(5100 * k)
    poster = board(pw, ph, [("art", pw / 2, ph * 0.36, int(pw * 0.86), "m"),
                            ("head", pw / 2, ph * 0.72, 44, "m"), ("sub", pw / 2, ph * 0.77, 19, "m"),
                            ("cta", pw / 2, ph * 0.83, 20, "m"), ("logo", pw / 2, ph * 0.87, 200, "m")])
    s = 0.36
    sq = round(1080 * s)
    square = board(sq, sq, [("art", sq / 2, sq * 0.42, int(sq * 0.7), "m"),
                            ("head", sq / 2, sq * 0.86, 34, "m"), ("cta", sq / 2, sq * 0.94, 15, "m")])
    sw, shh = round(1080 * s), round(1920 * s)
    story = board(sw, shh, [("art", sw / 2, shh * 0.40, int(sw * 0.9), "m"),
                            ("head", sw / 2, shh * 0.68, 36, "m"), ("sub", sw / 2, shh * 0.72, 15, "m"),
                            ("cta", sw / 2, shh * 0.78, 16, "m"), ("logo", sw / 2, shh * 0.135, 200, "m")])
    bw, bh = round(1500 * s), round(500 * s)
    banner = board(bw, bh, [("art", bw * 0.2, bh * 0.52, int(bh * 1.0), "m"),
                            ("head", bw * 0.4, bh * 0.52, 34, "l"), ("cta", bw * 0.4, bh * 0.72, 15, "l")])
    items = [(poster, "Poster 3300 × 5100 (11 %)"), (square, "IG square 1080 × 1080 (36 %)"),
             (story, "Story 1080 × 1920 (36 %)"), (banner, "Banner 1500 × 500 (36 %)")]
    x = 60
    for im, label in items:
        y = 140
        sheet.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(150, 160, 175))
        d.text((x, y - 18), label, font=_m5_font(22, "mono"), fill=(40, 60, 90))
        x += max(im.width, 330) + 60
    d.text((60, 70), "INSTRUCTOR REFERENCE · one master, four recomposed artboards: same key art, logo, "
           "background and type styles", font=_m5_font(28, "sans_bold"), fill=(29, 53, 87))
    d.text((60, H - 36), "Poster: stacked · Square: centered · Story: stacked inside the safe zone · "
           "Banner: spread horizontally", font=_m5_font(24, "sans"), fill=(60, 70, 90))
    save_png(sheet, 5, "l15-campaign-reference-INSTRUCTOR.png", folder="instructor")


# ======================================================================================
# Module 6: Generative + Automation, Advanced
# ======================================================================================

# ======================================================================================
# Module 6: Generative + Automation, Advanced  (L16 generative compositing, L17 conditional
# Actions + Batch, L18 Variables / Data Sets + a first script)
# ======================================================================================

_M6_SKIN = "#e2b894"
_M6_HAIR = "#3b2a20"


def _m6_save_text(text: str, name: str, folder: str = "practice", bom: bool = False) -> None:
    """Write a UTF-8 text file (CSV / .jsx) into practice/ or instructor/."""
    p = out_path(6, name, folder)
    p.write_text(("﻿" if bom else "") + text, encoding="utf-8", newline="\n")
    _record(p)


def _m6_save_jpg_to(img, name: str, folder: str, quality: int = 90) -> None:
    """save_jpg() always writes to practice/; this one takes a folder (instructor/)."""
    if isinstance(img, np.ndarray):
        img = Image.fromarray(to_u8(img))
    p = out_path(6, name, folder)
    img.save(p, "JPEG", quality=quality, dpi=(72, 72), optimize=True, icc_profile=SRGB_ICC)
    _record(p)


def _m6_rgba(L: Layer) -> Image.Image:
    rgba = np.dstack([to_u8(L.rgb), to_u8(L.a * 255)])
    return Image.fromarray(rgba, "RGBA")


def _m6_ground_speckles(img, r, y0, y1, n, lo=2.0, hi=9.0, x0=0, x1=None):
    """Gravel: small light/dark pebbles whose size grows toward the viewer."""
    H, W = img.shape[:2]
    x1 = W if x1 is None else x1
    c_dark = Canvas((x0, y0, x1, y1), ss=2)
    c_lite = Canvas((x0, y0, x1, y1), ss=2)
    for _ in range(n):
        y = y0 + (y1 - y0) * r.random() ** 0.8
        t = (y - y0) / max(1, (y1 - y0))
        s = lo + (hi - lo) * t
        x = r.uniform(x0, x1)
        cv = c_dark if r.random() < 0.55 else c_lite
        cv.ellipse(x, y, s * r.uniform(0.8, 1.4), s * r.uniform(0.45, 0.8), int(r.uniform(90, 200)))
    darken(img, c_dark.mask(blur=0.6), 0.28)
    paint(img, c_lite.mask(blur=0.6), "#f4e2c4", 0.35)


def _m6_cast_shadow(img, base_x0, base_x1, base_y, height, dx, amount=0.42, blur=6):
    """A soft shadow falling from an upright object's base toward the lower left."""
    c = Canvas((base_x0 + dx - 40, base_y - 20, base_x1 + 40, base_y + height * 0.35 + 40), ss=2, pad=blur * 3)
    c.poly([(base_x0, base_y), (base_x1, base_y),
            (base_x1 + dx, base_y + height * 0.28), (base_x0 + dx - 10, base_y + height * 0.30)])
    darken(img, c.mask(blur=blur), amount)


# --------------------------------------------------------------------------------------
# L16: the cramped plaza scene + a mismatched pasted subject
# --------------------------------------------------------------------------------------

_M6_SCENE_W, _M6_SCENE_H = 1500, 1200
_M6_HORIZON = 610
_M6_SUBJ_W, _M6_SUBJ_H = 340, 880
_M6_SUBJ_POS = (1135, 262)          # where the subject sits in the "cramped" composite


def _m6_plaza_scene() -> np.ndarray:
    """Warm late-afternoon plaza, sun from the right, framed too tight, with a SALE sign."""
    W, H = _M6_SCENE_W, _M6_SCENE_H
    r = rng("m6-plaza-scene")
    hz = _M6_HORIZON
    img = vgrad(W, H, [(0, "#86acd4"), (0.72, "#e9c9a0"), (1, "#f3d6aa")], 0, hz)
    # sun glow bleeding in from off-frame right
    xx, yy = coords(W, H)
    glow = np.exp(-(((xx - W - 60) / 520) ** 2 + ((yy - 140) / 360) ** 2)).astype(F32)
    img += (np.array(hexc("#fff0cc"), F32) - img) * (0.75 * glow)[..., None]
    # distant buildings, running off both edges
    c_far = Canvas((0, 300, W, hz + 5), ss=2)
    c_win = Canvas((0, 300, W, hz + 5), ss=2)
    x = -60.0
    while x < W + 40:
        bw = r.uniform(120, 230)
        top = r.uniform(360, 470)
        c_far.rect(x, top, x + bw - 6, hz + 5)
        for wy in np.arange(top + 22, hz - 30, 34):
            for wx in np.arange(x + 16, x + bw - 30, 30):
                if r.random() < 0.8:
                    c_win.rect(wx, wy, wx + 12, wy + 18)
        x += bw
    paint(img, c_far.mask(), "#c9a283")
    paint(img, c_win.mask(), "#8e6f5c", 0.55)
    # warm light on the right-hand faces: a gentle ramp over the whole skyline
    ramp = np.clip((xx - 200) / (W - 200), 0, 1)[..., None]
    band = full_mask(c_far.mask(), W, H)[..., None]
    img += band * ramp * np.array([26, 14, 2], F32)
    # low stone wall across the plaza (cut by both edges)
    wall_top, wall_bot = hz - 10, hz + 70
    img[wall_top:wall_bot] = vgrad(W, wall_bot - wall_top, [(0, "#c7a684"), (1, "#a8876a")])
    img[wall_top:wall_top + 10] = np.array(hexc("#dcc0a0"), F32)
    for bx in np.arange(-20, W, 95):
        img[wall_top + 10:wall_bot, int(max(bx, 0)):int(max(bx + 3, 0))] *= 0.8
    # gravel plaza
    g = vgrad(W, H - wall_bot, [(0, "#bfa688"), (1, "#d7bf9c")])
    img[wall_bot:] = g
    add_noise(img[wall_bot:], 7, r, mono=True)
    _m6_ground_speckles(img, r, wall_bot, H, 5200, 1.6, 8.5)
    # lamppost jammed against the left edge (cramped framing), shadow to the lower left
    c = Canvas((0, 180, 80, 1010), ss=3)
    c.rect(18, 250, 38, 1000, 255)
    c.rrect(0, 180, 64, 262, 10, 255)
    paint(img, c.mask(), "#2f2a28")
    _m6_cast_shadow(img, 14, 42, 1000, 820, -260, 0.40)
    # the distraction: a SALE sign on a post, left of where the subject will stand
    _m6_cast_shadow(img, 955, 985, 905, 520, -250, 0.40)
    c = Canvas((850, 500, 1100, 910), ss=3, mode="RGBA")
    c.rect(958, 640, 982, 905, "#5b4636")
    c.rect(850, 505, 1090, 655, "#c0392b")
    c.rect(862, 517, 1078, 643, "#fbf5ea")
    c.text(970, 582, "SALE", 66, bold=True, fill="#c0392b", anchor="mm")
    over(img, c.layer())
    # warm grade + photographic noise
    img *= np.array([1.03, 1.0, 0.94], F32)
    add_noise(img, 2.6, r, mono=True)
    return img


def _m6_subject_layer() -> Layer:
    """A standing figure lit COOL and from the LEFT, crisp-edged, with no shadow:
    everything about its light disagrees with the warm, right-lit plaza."""
    W, H = _M6_SUBJ_W, _M6_SUBJ_H
    c = Canvas((0, 0, W, H), ss=3, mode="RGBA")
    c.rrect(98, 480, 166, 840, 20, "#3a5a8c")           # legs
    c.rrect(174, 480, 242, 840, 20, "#3a5a8c")
    c.ellipse(128, 850, 44, 20, "#242424")              # shoes
    c.ellipse(214, 850, 44, 20, "#242424")
    for x0, x1, hx in ((40, 92, 64), (248, 300, 276)):  # arms + hands
        c.circle(hx, 482, 24, _M6_SKIN)
        c.rrect(x0, 160, x1, 478, 24, "#d9793a")
    c.rect(150, 110, 190, 160, _M6_SKIN)                # neck
    c.rrect(84, 150, 256, 500, 36, "#d9793a")           # jacket
    c.rect(166, 160, 174, 490, "#b5612c")               # zip line
    c.ellipse(170, 64, 60, 60, _M6_HAIR)                # hair cap
    c.ellipse(170, 78, 50, 60, _M6_SKIN)                # face
    c.d.chord(c.B(170 - 58, 70 - 64, 170 + 58, 70 + 64), 190, 350, fill=c._f(_M6_HAIR))
    L = c.layer()
    rgb = L.rgb.copy()
    xs = (np.arange(rgb.shape[1], dtype=F32) + L.x) / W
    shade = (1.32 - 0.78 * xs)[None, :, None]           # bright on the LEFT, dark on the right
    rgb = rgb * shade
    rgb = rgb * np.array([0.80, 0.93, 1.18], F32) + np.array([0, 6, 20], F32)   # cold cast
    rgb = (rgb - 110) * 1.18 + 110                      # a punchier, studio-flash contrast
    return Layer(L.x, L.y, np.clip(rgb, 0, 255), L.a)


def m6_cramped_scene():
    save_jpg(_m6_plaza_scene(), 6, "l16-cramped-scene.jpg", quality=90)


def m6_pasted_subject():
    L = _m6_subject_layer()
    im = Image.new("RGBA", (_M6_SUBJ_W, _M6_SUBJ_H), (0, 0, 0, 0))
    im.paste(_m6_rgba(L), (L.x, L.y))
    save_png(im, 6, "l16-pasted-subject.png")


def m6_cramped_composite_preview():
    img = _m6_plaza_scene()
    L = _m6_subject_layer()
    over(img, Layer(L.x + _M6_SUBJ_POS[0], L.y + _M6_SUBJ_POS[1], L.rgb, L.a))
    save_jpg(img, 6, "l16-cramped-composite-preview.jpg", quality=88)


def m6_three_distractions():
    """Now You: a sign (easy), a person (harder), a shadow across the subject (hardest)."""
    name = "l16-three-distractions.jpg"
    r = rng(name)
    W, H = 1800, 1200
    img = vgrad(W, H, [(0, "#9cc4e8"), (1, "#dcebf6")], 0, 230)
    wall_top, ground = 230, 860
    img[wall_top:ground] = vgrad(W, ground - wall_top, [(0, "#efe2c8"), (1, "#e2d0ae")])
    add_noise(img[wall_top:ground], 5, r, mono=True)
    img[wall_top:ground] = blur_img(img[wall_top:ground], 1.2)
    img[wall_top:wall_top + 14] = np.array(hexc("#cdb996"), F32)
    img[ground:] = vgrad(W, H - ground, [(0, "#9a958c"), (1, "#b5afa4")])
    add_noise(img[ground:], 6, r, mono=True)
    for px in np.arange(-40, W, 160):                                    # paving joints
        img[ground:, int(max(px, 0)):int(max(px + 3, 0))] *= 0.86
    img[ground:ground + 3] *= 0.8
    # 1. sign on the wall (right)
    c = Canvas((1380, 360, 1620, 560), ss=3, mode="RGBA")
    c.rrect(1390, 370, 1610, 550, 12, "#1f5fa8")
    c.text(1500, 432, "NOTICE", 40, bold=True, fill="#ffffff", anchor="mm")
    c.rect(1420, 470, 1580, 482, "#cfe0f5")
    c.rect(1420, 500, 1550, 512, "#cfe0f5")
    over(img, c.layer())
    # the subject: a red bicycle leaning against the wall (center)
    c = Canvas((620, 700, 1240, 1160), ss=3, mode="RGBA")
    for wx in (760, 1090):
        c.circle(wx, 1010, 128, "#2b2b2b")
        c.circle(wx, 1010, 114, (0, 0, 0, 0))
        c.circle(wx, 1010, 16, "#8a8a8a")
    c.line([(760, 1010), (900, 1010), (1040, 850), (860, 850), (760, 1010)], 16, "#c0392b")
    c.line([(900, 1010), (850, 820)], 16, "#c0392b")
    c.line([(1040, 850), (1090, 1010)], 14, "#c0392b")
    c.line([(1040, 850), (1030, 790), (1090, 780)], 12, "#2b2b2b")
    c.rrect(815, 800, 900, 822, 8, "#2b2b2b")
    over(img, c.layer())
    # 2. a passer-by (left)
    c = Canvas((170, 470, 360, 1130), ss=3)
    c.circle(262, 520, 42)
    c.rrect(208, 565, 318, 860, 34)
    c.line([(236, 850), (206, 1110)], 36, round_caps=True)
    c.line([(290, 850), (322, 1105)], 36, round_caps=True)
    c.line([(214, 600), (186, 820)], 26, round_caps=True)
    paint(img, c.mask(blur=0.7), "#3a3d4a")
    _m6_cast_shadow(img, 190, 340, 1115, 300, -120, 0.30, 8)
    # 3. a hard diagonal shadow (a pole out of frame) across wall AND bicycle
    c = Canvas((500, wall_top, 1500, H), ss=2, pad=30)
    c.poly([(1111, wall_top), (1191, wall_top), (820, H), (730, H)])
    m = c.mask(blur=5)
    m = Mask(m.x, m.y, m.a * (np.arange(m.a.shape[0])[:, None] + m.y >= wall_top))  # not on the sky
    darken(img, m, 0.42)
    add_noise(img, 2.2, r, mono=True)
    save_jpg(img, 6, name, quality=90)


# --------------------------------------------------------------------------------------
# L17: a mixed-orientation delivery folder + watermark
# --------------------------------------------------------------------------------------

_M6_BATCH = [
    # (size, sky top, sky horizon, hill near, hill far)
    ((2400, 1600), "#3d7cc9", "#bfe0f5", "#4f8a4c", "#7fae78"),
    ((1600, 2400), "#6a4fa8", "#f2c1c9", "#6b5a86", "#9c86b8"),
    ((2000, 2000), "#1f8a7a", "#cdefe6", "#2f6b52", "#5f9d7e"),
    ((3000, 2000), "#c86a2b", "#fbe0b0", "#7a4a2c", "#b37c52"),
    ((1800, 2400), "#2c3e50", "#aab7c4", "#34495e", "#5d6d7e"),
    ((2400, 1350), "#b03a2e", "#f7c6b8", "#6e2c24", "#a3584b"),
    ((2000, 3000), "#1e6fa8", "#d6ecfa", "#2e6e8e", "#6aa0bd"),
    ((2400, 1800), "#7a8a2a", "#eef0c4", "#55621d", "#8b9a45"),
]


def _m6_orientation(w, h):
    return "LANDSCAPE" if w > h else ("PORTRAIT" if h > w else "SQUARE")


def _m6_batch_image(i: int) -> np.ndarray:
    (W, H), top, hor, near, far = _M6_BATCH[i]
    r = rng(f"l17-delivery-{i + 1:02d}")
    s = min(W, H)
    hz = int(H * 0.62)
    img = vgrad(W, H, [(0, top), (1, hor)], 0, hz)
    img[hz:] = np.array(hexc(near), F32)
    # a round sun: it must stay round after Fit Image (nothing stretched)
    c = Canvas((0, 0, W, H), ss=2)
    c.circle(W * 0.74, H * 0.2, s * 0.07)
    paint(img, c.mask(blur=2), "#fff6d8", 0.95)
    xs = np.arange(W, dtype=float)
    for base, amp, col, ph in ((hz - s * 0.06, s * 0.05, far, 0.0), (hz + s * 0.02, s * 0.04, near, 1.7)):
        ys = smooth_wave(xs, base, amp, [(W * 0.9, 1.0, 0.3), (W * 0.37, 0.5, 1.1)], ph + i)
        c = Canvas((0, 0, W, H), ss=1)
        c.poly([(0, H)] + list(zip(xs[::8], ys[::8])) + [(W, ys[-1]), (W, H)])
        paint(img, c.mask(blur=1), col)
    # a centered tree as "the subject"
    c = Canvas((0, 0, W, H), ss=2, mode="RGBA")
    tx, ty = W * 0.5, hz + s * 0.03
    c.rect(tx - s * 0.012, ty - s * 0.16, tx + s * 0.012, ty, "#3b2b20")
    for dx, dy, rr in ((0, -0.22, 0.085), (-0.06, -0.17, 0.06), (0.06, -0.17, 0.06)):
        c.circle(tx + dx * s, ty + dy * s, rr * s, "#2f5a2c")
    over(img, c.layer(blur=1))
    add_noise(img, 1.4, r, mono=True)
    # the label plate: number + orientation + pixel size (keep it central so crops don't cut it)
    c = Canvas((0, 0, W, H), ss=2, mode="RGBA")
    pw, ph = s * 0.46, s * 0.2
    cx, cy = W * 0.5, H * 0.42
    c.rrect(cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2, s * 0.02, (15, 22, 36, 170))
    c.text(cx, cy - ph * 0.12, f"{i + 1:02d}", s * 0.1, bold=True, fill="#ffffff", anchor="mm")
    c.text(cx, cy + ph * 0.3, f"{_m6_orientation(W, H)} · {W} × {H}", s * 0.028, bold=True,
           fill="#cfe3ff", anchor="mm")
    over(img, c.layer())
    # a thin white keyline: shows at a glance which edges a crop removed
    k = max(10, int(s * 0.006))
    img[:k], img[-k:], img[:, :k], img[:, -k:] = 255, 255, 255, 255
    return img


def m6_delivery_inputs():
    for i in range(len(_M6_BATCH)):
        save_jpg(_m6_batch_image(i), 6, f"l17-input/l17-delivery-{i + 1:02d}.jpg", quality=86)


def m6_watermark():
    W, H = 700, 170
    c = Canvas((0, 0, W, H), ss=3, mode="RGBA")
    for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)):
        c.text(W / 2 + ox, H / 2 + oy, "© PRACTICE", 96, bold=True, fill=(0, 0, 0, 120), anchor="mm")
    c.text(W / 2, H / 2, "© PRACTICE", 96, bold=True, fill=(255, 255, 255, 150), anchor="mm")
    save_png(_m6_rgba(c.layer()), 6, "l17-watermark.png")


# --------------------------------------------------------------------------------------
# L18: card template parts, six "photos" whose names match the CSV, the CSVs, the script
# --------------------------------------------------------------------------------------

_M6_PEOPLE = [
    # name, backdrop, shirt, hair, sale, vip, tint
    ("Ana", "#f5b041", "#1f618d", "#3b2a20", "true", "false", "false"),
    ("Ben", "#48c9b0", "#943126", "#1c1c1c", "false", "true", "false"),
    ("Cy", "#af7ac5", "#f4d03f", "#7b4a2a", "true", "false", "true"),
    ("Dee", "#5dade2", "#e67e22", "#2e1f16", "false", "false", "false"),
    ("Eli", "#ec7063", "#1e8449", "#c9a15a", "false", "true", "true"),
    ("Fay", "#58d68d", "#6c3483", "#4a2a18", "true", "true", "false"),
]
_M6_CARD_W, _M6_CARD_H = 1080, 1350
_M6_PHOTO_BOX = (140, 150, 940, 950)     # 800 x 800 photo window on the card


def _m6_person_photo(i: int) -> np.ndarray:
    name, bg, shirt, hair, *_ = _M6_PEOPLE[i]
    r = rng(f"l18-{name.lower()}")
    S = 800
    b = np.array(hexc(bg), F32)
    img = vgrad(S, S, [(0, tuple(np.clip(b * 1.12, 0, 255))), (1, tuple(b * 0.8))])
    skin = ["#e2b894", "#8d5a3b", "#f1cfae", "#b07850", "#d9a57e", "#6b4430"][i]
    c = Canvas((0, 0, S, S), ss=3, mode="RGBA")
    c.ellipse(400, 860, 300, 250, shirt)                     # shoulders
    c.rect(362, 470, 438, 640, skin)                         # neck
    hr = [150, 140, 175, 120, 150, 185][i]                   # hair volume varies per person
    c.ellipse(400, 330, hr, hr + 10, hair)
    c.ellipse(400, 360, 118, 145, skin)                      # face
    c.d.chord(c.B(400 - 125, 350 - 160, 400 + 125, 350 + 160), 190, 350, fill=c._f(hair))
    for ex in (358, 442):
        c.ellipse(ex, 372, 10, 8, "#2a1d16")
    c.line([(372, 440), (400, 452), (428, 440)], 6, "#8a4f45")
    over(img, c.layer(blur=0.6))
    # studio light from the upper left
    xx, yy = coords(S, S)
    img *= (1.08 - 0.16 * (xx + yy) / (2 * S))[..., None]
    add_noise(img, 2.0, r, mono=True)
    # the name tag makes proofing easy: the photo must match the row's name
    c = Canvas((0, 0, S, S), ss=3, mode="RGBA")
    c.rrect(560, 716, 776, 776, 30, (15, 22, 36, 190))
    c.text(668, 746, name.upper(), 34, bold=True, fill="#ffffff", anchor="mm")
    over(img, c.layer())
    return np.clip(img, 0, 255)


def m6_person_photos():
    for i, p in enumerate(_M6_PEOPLE):
        save_jpg(_m6_person_photo(i), 6, f"l18-data/l18-{p[0].lower()}.jpg", quality=88)


def _m6_card_background() -> np.ndarray:
    W, H = _M6_CARD_W, _M6_CARD_H
    img = vgrad(W, H, [(0, "#0f2a4a"), (1, "#1473E6")])
    xx, yy = coords(W, H)
    img += (np.exp(-(((xx - 900) / 500) ** 2 + ((yy - 120) / 400) ** 2)) * 50)[..., None]
    x0, y0, x1, y1 = _M6_PHOTO_BOX
    c = Canvas((0, 0, W, H), ss=3, mode="RGBA")
    c.rrect(x0 - 24, y0 - 24, x1 + 24, y1 + 24, 28, "#ffffff")          # photo mount
    c.rect(x0, y0, x1, y1, "#d6dee9")                                  # empty window
    c.rrect(90, 1010, 990, 1170, 24, (255, 255, 255, 36))             # name band
    c.text(W / 2, 1255, "PRACTICE STUDIO  ·  SPRING MEETUP 2026", 30, bold=True,
           fill="#cfe3ff", anchor="mm")
    over(img, c.layer())
    return np.clip(img, 0, 255)


def m6_card_background():
    save_jpg(_m6_card_background(), 6, "l18-data/l18-card-background.jpg", quality=90)


def _m6_badge_layer() -> Layer:
    S = 300
    c = Canvas((0, 0, S, S), ss=3, mode="RGBA")
    pts = []
    for k in range(32):
        rad = 146 if k % 2 == 0 else 120
        a = math.pi * 2 * k / 32 - math.pi / 2
        pts.append((150 + rad * math.cos(a), 150 + rad * math.sin(a)))
    c.poly(pts, "#c0392b")
    c.circle(150, 150, 104, "#e74c3c")
    c.text(150, 152, "SALE", 64, bold=True, fill="#ffffff", anchor="mm")
    return c.layer()


def m6_sale_badge():
    save_png(_m6_rgba(_m6_badge_layer()), 6, "l18-data/l18-sale-badge.png")


def m6_vip_ribbon():
    W, H = 420, 130
    c = Canvas((0, 0, W, H), ss=3, mode="RGBA")
    c.poly([(0, 20), (60, 20), (60, 110), (0, 110), (26, 65)], "#b7892b")
    c.poly([(W, 20), (W - 60, 20), (W - 60, 110), (W, 110), (W - 26, 65)], "#b7892b")
    c.rect(40, 8, W - 40, 100, "#f1c40f")
    c.rect(40, 8, W - 40, 20, "#f7dc6f")
    c.text(W / 2, 56, "VIP", 64, bold=True, fill="#5b3a00", anchor="mm")
    save_png(_m6_rgba(c.layer()), 6, "l18-data/l18-vip-ribbon.png")


def m6_cards_csv():
    rows = ["name,photo,sale"] + [f"{n},l18-{n.lower()}.jpg,{s}" for n, _, _, _, s, _, _ in _M6_PEOPLE]
    _m6_save_text("\n".join(rows) + "\n", "l18-data/l18-cards.csv")


def m6_cards_vip_csv():
    rows = ["name,photo,sale,vip,tint"] + [f"{n},l18-{n.lower()}.jpg,{s},{v},{t}"
                                           for n, _, _, _, s, v, t in _M6_PEOPLE]
    _m6_save_text("\n".join(rows) + "\n", "l18-data/l18-cards-vip.csv")


def m6_cards_broken_csv():
    """Instructor-only: three deliberate faults for the 'why didn't it bind?' demo:
    header 'Name' (capital N, no longer matches the variable), 'yes'/'no' instead of
    true/false, and a photo name that does not exist (l18-benn.jpg)."""
    rows = ["Name,photo,sale", "Ana,l18-ana.jpg,yes", "Ben,l18-benn.jpg,no", "Cy,l18-cy.jpg,yes"]
    _m6_save_text("\n".join(rows) + "\n", "l18-cards-broken.csv", folder="instructor")


def m6_card_reference():
    """Instructor-only: what row 1 (Ana, sale = true) should look like once bound."""
    img = _m6_card_background()
    photo = _m6_person_photo(0)
    x0, y0, x1, y1 = _M6_PHOTO_BOX
    img[y0:y1, x0:x1] = photo
    c = Canvas((0, 0, _M6_CARD_W, _M6_CARD_H), ss=3, mode="RGBA")
    c.text(_M6_CARD_W / 2, 1090, "Ana", 96, bold=True, fill="#ffffff", anchor="mm")
    over(img, c.layer())
    B = _m6_badge_layer()
    over(img, Layer(B.x + 770, B.y + 40, B.rgb, B.a))
    _m6_save_jpg_to(img, "l18-card-reference-ana.jpg", "instructor", quality=88)


_M6_JSX = """// resize-folder.jsx  —  File ▸ Scripts ▸ Browse to run
var inputFolder  = Folder.selectDialog("Choose a folder of images");
if (!inputFolder) { throw new Error("No folder chosen."); }
var files = inputFolder.getFiles(/\\.(jpg|jpeg|png)$/i);

for (var i = 0; i < files.length; i++) {
    var doc = app.open(files[i]);
    var longEdge = 2000;
    var scale = longEdge / Math.max(doc.width.value, doc.height.value);
    doc.resizeImage(doc.width * scale, doc.height * scale);

    var out = new File(inputFolder + "/web_" + doc.name.replace(/\\.[^.]+$/, ".jpg"));
    var opt = new JPEGSaveOptions();
    opt.quality = 10;
    doc.saveAs(out, opt, true);
    doc.close(SaveOptions.DONOTSAVECHANGES);
}
alert("Done: " + files.length + " images resized.");
"""


def m6_resize_script():
    """The lesson's ExtendScript, verbatim (UTF-8 with BOM so ExtendScript reads the
    em dash and the menu arrow in the comment correctly)."""
    _m6_save_text(_M6_JSX, "l18-resize-folder.jsx", bom=True)


# ======================================================================================
# Module 7: Multi-Shot Techniques
# ======================================================================================

# ======================================================================================
# Module 7: Multi-Shot Techniques (Session 7)
#   L19 (7.1) Panoramas, HDR & Focus Stacking: overlapping pano frames, a 3-shot
#             exposure bracket, a 4-frame focus series
#   L20 (7.2) Timeline Animation & Export: layered pieces for a looping social post,
#             plus six cinemagraph frames (steam loop)
# ======================================================================================

from PIL import TiffImagePlugin as _m7_Tiff

_M7_F = 1800.0                    # pano "lens" focal length in px (53 deg horizontal FOV)
_M7_FW, _M7_FH = 1800, 1200       # pano / stack / HDR frame size
_M7_HALF = math.atan(_M7_FW / 2 / _M7_F)
_M7_STEP = 0.65 * 2 * _M7_HALF    # 35 % overlap between neighbouring pano frames
_M7_TMIN = -_M7_HALF - 0.05
_M7_PW = int(math.ceil((3 * _M7_STEP + _M7_HALF + 0.05 - _M7_TMIN) * _M7_F))
_M7_PH, _M7_HC = 1320, 660        # cylinder height and optical-center row
_M7_HZ = _M7_HC + 70              # far shore (horizon) row on the cylinder


def _m7_sample(img, xs, ys):
    """Bilinear sample img (h, w, 3) at float coords; edges clamp."""
    h, w = img.shape[:2]
    xs = np.clip(xs, 0, w - 1.001)
    ys = np.clip(ys, 0, h - 1.001)
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    fx = (xs - x0)[..., None].astype(F32)
    fy = (ys - y0)[..., None].astype(F32)
    a = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    b = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy


def _m7_down(img, factor):
    """Box-downsample a float RGB array by an integer factor."""
    h, w = img.shape[:2]
    return img.reshape(h // factor, factor, w // factor, factor, 3).mean(axis=(1, 3))


def _m7_exif(exposure, bias):
    ex = Image.Exif()
    ex[0x010F] = "Synthetic"
    ex[0x0110] = "Practice Bracket (generated)"
    ifd = ex.get_ifd(0x8769)
    ifd[0x829A] = _m7_Tiff.IFDRational(*exposure)          # ExposureTime
    ifd[0x829D] = _m7_Tiff.IFDRational(8, 1)                # FNumber f/8
    ifd[0x8827] = 100                                        # ISO
    ifd[0x9204] = _m7_Tiff.IFDRational(bias, 1)             # ExposureBiasValue
    return ex.tobytes()


def _m7_save_jpg_exif(arr, name, exif, quality=90):
    p = out_path(7, name)
    Image.fromarray(to_u8(arr)).save(p, "JPEG", quality=quality, dpi=(72, 72), optimize=True,
                                     icc_profile=SRGB_ICC, exif=exif)
    _record(p)


def _m7_save_inst_jpg(arr, name, quality=85):
    p = out_path(7, name, "instructor")
    Image.fromarray(to_u8(arr)).save(p, "JPEG", quality=quality, dpi=(72, 72), optimize=True,
                                     icc_profile=SRGB_ICC)
    _record(p)


# ---------------------------------------------------------------------------------------
# L19 panorama: one wide cylindrical lake scene, re-projected into four rectilinear frames
# ---------------------------------------------------------------------------------------

def _m7_ridge(xs, base, amp, parts, seed):
    return smooth_wave(xs, base, amp, parts, phase=seed)


def _m7_pano_scene():
    W, H = _M7_PW, _M7_PH
    r = rng("m7-pano-scene")
    xs = np.arange(W, dtype=float)
    img = vgrad(W, H, [(0, "#3f78b8"), (0.45, "#8fbfe6"), (1, "#d9ecf7")], 0, _M7_HZ)
    X, Y = coords(W, H)
    # sun glow, off-center so frames 2-3 are a little brighter up top
    sx, sy = W * 0.63, _M7_HC - 430
    d = np.hypot(X - sx, Y - sy)
    img += (np.exp(-(d / 420) ** 2) * 55)[..., None] * np.array([1, 0.9, 0.65], F32)
    c = Canvas((sx - 60, sy - 60, sx + 60, sy + 60), ss=3)
    c.circle(sx, sy, 46)
    paint(img, c.mask(blur=3), "#fff6dc")
    # distinctive cumulus clouds (anchors for Auto-Align in the sky)
    for cx, cy, cw, ch in [(380, 250, 520, 150), (1150, 170, 380, 110), (1780, 300, 620, 170),
                           (2600, 210, 300, 90), (3350, 330, 560, 150), (4150, 190, 440, 130),
                           (4800, 290, 360, 120)]:
        cm = Canvas((cx - cw, cy - ch, cx + cw, cy + ch), ss=2)
        soft_blob(cm, r, cx, cy, cw, ch, n=(6, 9))
        m = cm.mask(blur=10)
        paint(img, Mask(m.x, m.y + 18, m.a), "#a9bfd6", 0.55)       # shaded base
        paint(img, m, "#f7fbff", 0.92)
    # far mountains with snow and slope shading
    ridge = _m7_ridge(xs, _M7_HC - 150, 170, [(1900, 1.0, 0.3), (830, 0.7, 1.1), (370, 0.35, 2.0),
                                               (150, 0.12, 0.4)], 0.0)
    ridge -= 150 * np.exp(-((xs - W * 0.47) / 260) ** 2)               # one signature peak
    slope = np.convolve(np.gradient(ridge), np.ones(121) / 121, mode="same")
    mt = (Y >= ridge[None, :]) & (Y < _M7_HZ)
    depth = np.clip((Y - ridge[None, :]) / 220, 0, 1)
    shade = np.clip(0.5 + slope[None, :] * 1.8, 0, 1)
    base = np.stack([lerp(hexc("#5c7394"), hexc("#8ea3bd"), t) for t in (0, 1)])
    col = base[0][None, None, :] * (1 - shade[..., None]) + base[1][None, None, :] * shade[..., None]
    snowline = np.clip((_M7_HC - 210 - ridge) / 70, 0, 1)[None, :] * np.clip(1 - depth * 3.2, 0, 1)
    col = col * (1 - snowline[..., None]) + np.array(hexc("#f2f6fb"), F32) * snowline[..., None] * (0.8 + 0.2 * shade[..., None])
    haze = np.clip(depth, 0, 1)[..., None] * 0.35
    col = col * (1 - haze) + np.array(hexc("#b8cde2"), F32) * haze
    img = np.where(mt[..., None], col, img)
    # near forested hills
    hill = _m7_ridge(xs, _M7_HZ - 55, 45, [(1300, 1.0, 2.2), (520, 0.6, 0.7), (190, 0.25, 1.4)], 0.0)
    hm = (Y >= hill[None, :]) & (Y < _M7_HZ)
    img = np.where(hm[..., None], np.array(hexc("#2f5a3a"), F32) * (0.85 + 0.15 * np.sin(X / 37)[..., None]), img)
    trees = Canvas((0, _M7_HZ - 200, W, _M7_HZ + 2), ss=2)
    for tx in np.sort(r.uniform(0, W, 260)):
        ty = hill[int(tx)] + 6
        th = r.uniform(35, 80)
        trees.poly([(tx - th * 0.22, ty), (tx, ty - th), (tx + th * 0.22, ty)])
    paint(img, trees.mask(), "#1f4029")
    # the far shore: cabin (overlap 1), lighthouse point (overlap 2)
    ov = [int(((i + 0.5) * _M7_STEP - _M7_TMIN) * _M7_F) for i in range(3)]
    feat = Canvas((0, _M7_HZ - 320, W, _M7_HZ + 60), ss=3, mode="RGBA")
    cx0 = ov[0] - 40
    feat.rect(cx0, _M7_HZ - 70, cx0 + 120, _M7_HZ, "#b3322b")
    feat.poly([(cx0 - 12, _M7_HZ - 70), (cx0 + 60, _M7_HZ - 118), (cx0 + 132, _M7_HZ - 70)], "#3a2d2a")
    feat.rect(cx0 + 18, _M7_HZ - 50, cx0 + 40, _M7_HZ - 28, "#f4ead2")
    feat.rect(cx0 + 80, _M7_HZ - 50, cx0 + 102, _M7_HZ - 28, "#f4ead2")
    feat.rect(cx0 + 52, _M7_HZ - 44, cx0 + 68, _M7_HZ, "#f4ead2")
    lx = ov[1] + 30
    feat.poly([(lx - 230, _M7_HZ + 2), (lx - 120, _M7_HZ - 28), (lx - 20, _M7_HZ - 40),
               (lx + 60, _M7_HZ - 30), (lx + 170, _M7_HZ + 2)], "#5b5750")
    tw0, tw1, tb, tt = 30, 20, _M7_HZ - 34, _M7_HZ - 270
    feat.poly([(lx - tw0, tb), (lx - tw1, tt), (lx + tw1, tt), (lx + tw0, tb)], "#f3f1ea")
    for k in range(3):
        y0 = tb - (k * 2 + 1) * (tb - tt) / 6.5
        y1 = y0 - (tb - tt) / 6.5
        wl = tw0 + (tw1 - tw0) * (tb - y0) / (tb - tt)
        wu = tw0 + (tw1 - tw0) * (tb - y1) / (tb - tt)
        feat.poly([(lx - wl, y0), (lx - wu, y1), (lx + wu, y1), (lx + wl, y0)], "#c0392b")
    feat.rect(lx - 26, tt - 8, lx + 26, tt, "#2b2b2b")
    feat.rect(lx - 16, tt - 40, lx + 16, tt - 8, "#ffe9a6")
    feat.poly([(lx - 22, tt - 40), (lx, tt - 62), (lx + 22, tt - 40)], "#2b2b2b")
    fl = feat.layer()
    over(img, fl)
    # lake with reflections
    shore = _m7_ridge(xs, H - 190, 45, [(900, 1.0, 0.5), (340, 0.5, 2.1)], 0.0)
    ly = np.arange(_M7_HZ, H)
    src_y = np.clip(2 * _M7_HZ - ly - 1, 0, H - 1).astype(F32)
    LX, LY = np.meshgrid(xs.astype(F32), src_y)
    wob = (3.5 * np.sin(np.arange(_M7_HZ, H)[:, None] * 0.35) * np.sin(LX / 23)).astype(F32)
    refl = _m7_sample(img, LX + wob, LY)
    water = vgrad(W, H - _M7_HZ, [(0, "#5f8fb6"), (1, "#27577f")])
    t = np.clip((ly - _M7_HZ) / (H - _M7_HZ), 0, 1)[:, None, None]
    lake = refl * (0.62 - 0.3 * t) + water * (0.38 + 0.3 * t)
    img[_M7_HZ:] = lake
    for _ in range(420):
        yy = int(r.uniform(_M7_HZ + 8, H - 150))
        x0 = r.uniform(0, W)
        ln = r.uniform(20, 160) * (0.4 + (yy - _M7_HZ) / 400)
        img[yy:yy + 2, int(x0):int(min(W, x0 + ln))] += 18
    # pier and sailboat (overlap 3)
    px = ov[2] + 60
    pier = Canvas((px - 300, _M7_HZ, px + 300, H), ss=3, mode="RGBA")
    pier.poly([(px - 20, _M7_HZ + 150), (px + 20, _M7_HZ + 150), (px + 190, H), (px - 70, H)], "#7a5a3c")
    for k in range(14):
        yy = _M7_HZ + 150 + k * (H - _M7_HZ - 150) / 14
        tl = (yy - _M7_HZ - 150) / (H - _M7_HZ - 150)
        pier.line([(px - 20 - 50 * tl, yy), (px + 20 + 170 * tl, yy)], 2 + 3 * tl, "#4b3524")
    for k in range(5):
        tl = k / 4
        yy = _M7_HZ + 150 + tl * (H - _M7_HZ - 190)
        pier.rect(px - 26 - 50 * tl, yy, px - 18 - 50 * tl + 8 * tl, yy + 25 + 50 * tl, "#3a2a1c")
    over(img, pier.layer())
    bx, by = ov[2] - 330, _M7_HZ + 120
    boat = Canvas((bx - 90, by - 170, bx + 90, by + 30), ss=3, mode="RGBA")
    boat.poly([(bx - 70, by - 18), (bx + 75, by - 18), (bx + 55, by + 4), (bx - 55, by + 4)], "#f0f0ea")
    boat.poly([(bx - 4, by - 26), (bx - 4, by - 160), (bx - 70, by - 30)], "#fdfbf4")
    boat.poly([(bx + 4, by - 26), (bx + 4, by - 130), (bx + 52, by - 30)], "#e8c14a")
    boat.line([(bx, by - 18), (bx, by - 165)], 3, "#444444")
    over(img, boat.layer())
    # foreground shore: grass, rocks, and boulders (distinct low anchors)
    fg = Y >= shore[None, :]
    gt = r.standard_normal((H // 4 + 1, W // 4 + 1)).astype(F32)
    gt = np.asarray(Image.fromarray(to_u8(128 + 40 * gt)).resize((W, H), Image.BICUBIC), F32)[:H, :W] / 128
    grass = np.array(hexc("#5f7d3a"), F32) * (0.75 + 0.25 * gt)[..., None]
    img = np.where(fg[..., None], grass, img)
    rocks = Canvas((0, H - 280, W, H), ss=2, mode="RGBA")
    for bxx in list(np.sort(r.uniform(0, W, 38))) + [ov[0] + 200, ov[1] - 120, 350, W - 400]:
        bw = r.uniform(40, 150)
        byy = shore[int(min(W - 1, bxx))] + r.uniform(20, 120)
        g = int(r.uniform(95, 150))
        rocks.ellipse(bxx, byy, bw, bw * 0.55, (g, g - 4, g - 12))
        rocks.ellipse(bxx - bw * 0.25, byy - bw * 0.2, bw * 0.45, bw * 0.22, (g + 35, g + 30, g + 22))
    over(img, rocks.layer())
    add_noise(img, 3, r, mono=True)
    return img


def _m7_project(scene, i, gain, vig, roll_deg, dy, tint):
    W, H = _M7_FW, _M7_FH
    u, v = coords(W, H)
    xn, yn = u - W / 2, v - H / 2
    a = math.radians(roll_deg)
    xr = xn * math.cos(a) - yn * math.sin(a)
    yr = xn * math.sin(a) + yn * math.cos(a)
    theta = i * _M7_STEP + np.arctan2(xr, _M7_F)
    cx = (theta - _M7_TMIN) * _M7_F
    cy = yr * _M7_F / np.sqrt(_M7_F ** 2 + xr ** 2) + _M7_HC + dy
    fr = _m7_sample(scene, cx, cy)
    rr = np.hypot(xn / (W / 2), yn / (H / 2)) / math.sqrt(2)
    fr *= ((1 - vig * rr ** 2) * gain)[..., None]
    fr *= np.array(tint, F32)
    add_noise(fr, 2.2, rng(f"m7-pano-noise-{i}"), mono=True)
    return fr


def m7_panorama():
    scene = _m7_pano_scene()
    params = [(1.00, 0.24, 0.0, 0, (1.0, 1.0, 1.0)),
              (0.93, 0.30, 0.35, 12, (0.99, 1.0, 1.02)),
              (1.07, 0.22, -0.25, -9, (1.02, 1.0, 0.98)),
              (0.96, 0.27, 0.15, 5, (1.0, 1.0, 1.01))]
    for i, (g, vg, rot, dy, tint) in enumerate(params):
        fr = _m7_project(scene, i, g, vg, rot, dy, tint)
        save_jpg(fr, 7, f"l19-pano/l19-pano-0{i + 1}.jpg", quality=88)
    ref = Image.fromarray(to_u8(scene)).resize((2400, int(2400 * _M7_PH / _M7_PW)), Image.LANCZOS)
    _m7_save_inst_jpg(np.asarray(ref, F32), "l19-pano-reference.jpg")


# ---------------------------------------------------------------------------------------
# L19 HDR: a dark room with a sunlit window, rendered in linear light, bracketed -2/0/+2
# ---------------------------------------------------------------------------------------

def _m7_hdr_radiance():
    W, H = _M7_FW + 16, _M7_FH + 16          # 8 px margin for the hand-held shift
    r = rng("m7-hdr-radiance")
    X, Y = coords(W, H)
    L = np.zeros((H, W, 3), F32)
    # walls: warm, darker toward the corners
    corner = 1 - 0.55 * (np.abs(X - W * 0.45) / W) ** 1.2 - 0.25 * (Y / H) ** 2
    L[:] = (np.array([0.052, 0.044, 0.036], F32) * corner[..., None])
    # floor (wood planks) below y 900
    fy = 900
    planks = (0.030 + 0.006 * np.sin(Y / 3.3 + np.floor(X / 180) * 1.7)
              + 0.004 * np.sin(X / 41)).astype(F32)
    floor = np.stack([planks * 1.25, planks * 0.95, planks * 0.7], -1)
    floor[(np.mod(X, 180) < 3)] *= 0.45
    L[Y >= fy] = floor[Y >= fy]
    L[(Y >= fy) & (Y < fy + 10)] = np.array([0.018, 0.014, 0.011], F32)   # skirting shadow
    # window opening
    wx0, wx1, wy0, wy1 = 470, 1170, 150, 780
    win = (X >= wx0) & (X < wx1) & (Y >= wy0) & (Y < wy1)
    t = np.clip((Y - wy0) / (wy1 - wy0), 0, 1)
    sky = np.stack([0.95 + 0.55 * t, 1.18 + 0.5 * t, 1.62 + 0.25 * t], -1).astype(F32)
    out = sky.copy()
    cl = Canvas((wx0, wy0, wx1, wy1), ss=2)
    for cxx, cyy, cw, chh in [(640, 250, 170, 60), (930, 330, 220, 70), (1080, 215, 110, 40)]:
        soft_blob(cl, r, cxx, cyy, cw, chh, n=(5, 7))
    cm = full_mask(cl.mask(blur=6), W, H)
    out = out * (1 - cm[..., None]) + np.array([2.05, 2.02, 1.96], F32) * cm[..., None]
    hills = smooth_wave(np.arange(W, dtype=float), 610, 45, [(420, 1, 0.3), (160, 0.4, 1.2)])
    hm = Y >= hills[None, :].astype(F32)
    field = np.stack([0.42 + 0.1 * np.sin(X / 13), 0.62 + 0.12 * np.sin(X / 13), 0.22 + 0 * X], -1)
    field *= (0.9 + 0.25 * np.clip((Y - 600) / 180, 0, 1))[..., None]
    out = np.where(hm[..., None], field.astype(F32), out)
    trees = Canvas((wx0, 520, wx1, 700), ss=2)
    for txx in (560, 610, 700, 1010, 1060, 1120):
        tyy = hills[txx] + 10
        th = r.uniform(70, 110)
        trees.poly([(txx - th * 0.3, tyy), (txx, tyy - th), (txx + th * 0.3, tyy)])
    tm = full_mask(trees.mask(), W, H)
    out = out * (1 - tm[..., None]) + np.array([0.09, 0.16, 0.07], F32) * tm[..., None]
    L = np.where(win[..., None], out, L)
    # window frame and mullions (dark, backlit)
    frame = Canvas((wx0 - 40, wy0 - 40, wx1 + 40, wy1 + 60), ss=2)
    frame.rect(wx0 - 30, wy0 - 30, wx1 + 30, wy0)
    frame.rect(wx0 - 30, wy1, wx1 + 30, wy1 + 45)            # sill
    frame.rect(wx0 - 30, wy0 - 30, wx0, wy1 + 45)
    frame.rect(wx1, wy0 - 30, wx1 + 30, wy1 + 45)
    frame.rect((wx0 + wx1) / 2 - 9, wy0, (wx0 + wx1) / 2 + 9, wy1)
    frame.rect(wx0, (wy0 + wy1) / 2 - 8, wx1, (wy0 + wy1) / 2 + 8)
    fm = full_mask(frame.mask(), W, H)
    L = L * (1 - fm[..., None]) + np.array([0.03, 0.028, 0.026], F32) * fm[..., None]
    # sunbeam on the floor (window shape, sheared), with mullion shadows
    beam = Canvas((300, fy, 1500, H), ss=2)
    beam.poly([(560, fy + 40), (1080, fy + 40), (1330, H - 30), (640, H - 30)])
    bm = full_mask(beam.mask(blur=8), W, H)
    mull = Canvas((300, fy, 1500, H), ss=2)
    mull.poly([(812, fy + 40), (828, fy + 40), (1000, H - 30), (975, H - 30)])
    mull.rect(560, (fy + 40 + H - 30) / 2 - 10, 1400, (fy + 40 + H - 30) / 2 + 10)
    bm *= 1 - full_mask(mull.mask(blur=5), W, H)
    L += np.array([0.62, 0.52, 0.36], F32) * bm[..., None]
    # interior things only the +2 frame shows well
    shelf = Canvas((1330, 200, W, 900), ss=2, mode="RGBA")
    shelf.rect(1350, 220, 1760, 880, (40, 30, 22))
    for k in range(4):
        yb = 360 + k * 160
        shelf.rect(1360, yb, 1750, yb + 14, (70, 52, 36))
        xb = 1370
        while xb < 1720:
            bw = r.uniform(18, 44)
            col = [(150, 40, 35), (40, 70, 130), (200, 160, 60), (60, 110, 70), (120, 90, 150)][int(r.integers(0, 5))]
            shelf.rect(xb, yb - r.uniform(95, 130), xb + bw, yb, col)
            xb += bw + 3
    sl = shelf.layer()
    sl = Layer(sl.x, sl.y, sl.rgb / 255.0 * 0.11, sl.a)
    over(L, sl)
    art = Canvas((80, 260, 420, 620), ss=2, mode="RGBA")
    art.rect(100, 280, 400, 600, (60, 45, 30))
    art.rect(122, 302, 378, 578, (190, 170, 130))
    art.circle(250, 400, 60, (200, 90, 50))
    art.poly([(122, 578), (220, 470), (300, 520), (378, 440), (378, 578)], (70, 100, 80))
    al = art.layer()
    over(L, Layer(al.x, al.y, al.rgb / 255.0 * 0.12, al.a))
    chair = Canvas((200, 700, 700, H), ss=2, mode="RGBA")
    chair.rrect(240, 760, 560, 1040, 40, (150, 40, 40))
    chair.rrect(220, 900, 600, 1110, 30, (170, 48, 46))
    chair.rect(250, 1100, 275, 1180, (40, 25, 15))
    chair.rect(545, 1100, 570, 1180, (40, 25, 15))
    cl2 = chair.layer()
    over(L, Layer(cl2.x, cl2.y, cl2.rgb / 255.0 * 0.10, cl2.a))
    plant = Canvas((wx0 + 40, wy1 - 260, wx0 + 300, wy1 + 10), ss=2)
    plant.rect(wx0 + 110, wy1 - 70, wx0 + 200, wy1)
    for k in range(9):
        ang = -math.pi / 2 + (k - 4) * 0.28
        L0 = r.uniform(120, 200)
        ex = wx0 + 155 + math.cos(ang) * L0
        ey = wy1 - 70 + math.sin(ang) * L0
        plant.line([(wx0 + 155, wy1 - 70), (ex, ey)], 14, round_caps=True)
    pm = full_mask(plant.mask(), W, H)
    L = L * (1 - pm[..., None]) + np.array([0.02, 0.03, 0.015], F32) * pm[..., None]
    return L


def _m7_camera(lin):
    """Linear light -> 8-bit-ish sRGB values with a soft film shoulder, clipped."""
    x = np.maximum(lin, 0)
    k = 0.78
    x = np.where(x > k, k + (1 - k) * np.tanh((x - k) / (1 - k)), x)
    x = np.clip(x, 0, 1)
    s = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return s * 255


def m7_hdr_bracket():
    L = _m7_hdr_radiance()
    shots = [("l19-hdr/l19-hdr-1-minus2ev.jpg", 0.45, (1, 250), -2, (0, 0), 700),
             ("l19-hdr/l19-hdr-2-0ev.jpg", 1.80, (1, 60), 0, (2, -1), 760),
             ("l19-hdr/l19-hdr-3-plus2ev.jpg", 7.20, (1, 15), 2, (-1, 2), 820)]
    for name, s, expo, bias, (dx, dy), bird_x in shots:
        lin = L.copy()
        b = Canvas((bird_x - 40, 330, bird_x + 40, 370), ss=3)       # a bird crossing the window
        b.line(quad_bezier((bird_x - 30, 340), (bird_x - 14, 332), (bird_x, 350)), 4)
        b.line(quad_bezier((bird_x, 350), (bird_x + 14, 332), (bird_x + 30, 340)), 4)
        bm = full_mask(b.mask(), lin.shape[1], lin.shape[0])
        lin = lin * (1 - bm[..., None]) + 0.04 * bm[..., None]
        lin = lin * s
        rr = rng(name)
        noise = rr.standard_normal(lin.shape[:2], dtype=F32)[..., None]
        lin = lin + noise * (0.0015 + 0.008 * np.sqrt(np.maximum(lin, 0)))
        out = _m7_camera(lin)[8 + dy:8 + dy + _M7_FH, 8 + dx:8 + dx + _M7_FW]
        _m7_save_jpg_exif(out, name, _m7_exif(expo, bias), quality=90)


# ---------------------------------------------------------------------------------------
# L19 focus stack: a tabletop receding from the lens, four frames focused near -> far
# ---------------------------------------------------------------------------------------

_M7_VH = -250.0          # vanishing line of the table plane (above the frame)
_M7_WALL = 380           # row where the table meets the back wall
_M7_WNEAR, _M7_WFAR = 1450.0, _M7_WALL - _M7_VH    # inverse-depth range (v - VH)


def _m7_depth_for_row(v):
    return (_M7_WNEAR - (v - _M7_VH)) / (_M7_WNEAR - _M7_WFAR)


def _m7_row_for_depth(d):
    return _M7_WNEAR - d * (_M7_WNEAR - _M7_WFAR) + _M7_VH


def _m7_mat_texture():
    ppc = 50                                  # texture px per cm
    x0, x1, z0, z1 = -46.0, 46.0, 28.0, 72.0
    tw, th = int((x1 - x0) * ppc), int((z1 - z0) * ppc)
    im = Image.new("RGB", (tw, th), hexc("#2f6b58"))
    d = ImageDraw.Draw(im)
    for cm in range(int(x0), int(x1) + 1):
        x = (cm - x0) * ppc
        d.line([(x, 0), (x, th)], fill=hexc("#8cc7b2") if cm % 5 else hexc("#d9f2e8"), width=3 if cm % 5 else 5)
    for cm in range(int(z0), int(z1) + 1):
        y = th - (cm - z0) * ppc
        d.line([(0, y), (tw, y)], fill=hexc("#8cc7b2") if cm % 5 else hexc("#d9f2e8"), width=3 if cm % 5 else 5)
    # a steel ruler lying along the depth axis, numbered every centimeter
    rx0, rx1 = (-17 - x0) * ppc, (-12 - x0) * ppc
    d.rectangle([rx0, 0, rx1, th], fill=hexc("#d8dadc"), outline=hexc("#6f7478"), width=6)
    f = font(58, True)
    for cm in range(int(z0), int(z1) + 1):
        for mm in range(10):
            y = th - (cm - z0 + mm / 10) * ppc
            ln = 90 if mm == 0 else (60 if mm == 5 else 34)
            d.line([(rx0, y), (rx0 + ln, y)], fill=hexc("#1c1c1c"), width=4)
        y = th - (cm - z0) * ppc
        d.text((rx0 + 110, y), str(cm), font=f, fill=hexc("#1c1c1c"), anchor="lm")
    # printed lettering on the mat at three depths
    for zc, txt, sz in [(31, "FOCUS STACK PRACTICE MAT", 110), (46, "sharp here? check the 1 mm ticks", 80),
                        (64, "FAR ZONE · FINE PRINT TEST · 0123456789", 70)]:
        d.text(((6 - x0) * ppc, th - (zc - z0) * ppc), txt, font=font(sz, True), fill=hexc("#e9f7f1"), anchor="lm")
    return np.asarray(im, F32), (x0, z0, ppc, th)


def _m7_stack_sharp():
    """All-in-focus background (table + wall) at 1x, rendered at 2x then downsampled."""
    S = 2
    W, H = _M7_FW * S, _M7_FH * S
    tex, (x0, z0, ppc, th) = _m7_mat_texture()
    u, v = coords(W, H)
    u, v = u / S, v / S
    f, C = 1500.0, 1450.0 * 30.0
    Z = C / np.maximum(v - _M7_VH, 1)
    Xp = (u - _M7_FW / 2) * Z / f
    tx = (Xp - x0) * ppc
    ty = th - (Z - z0) * ppc
    img = _m7_sample(tex, tx, ty)
    fall = np.clip(1.08 - 0.25 * (v - _M7_WALL) / (_M7_FH - _M7_WALL), 0.8, 1.1)
    img *= fall[..., None]
    # back wall: striped wallpaper with small type (the far sharpness target)
    wall = (v < _M7_WALL)
    stripes = np.where(np.mod(u, 36) < 18, 1.0, 0.9)[..., None] * np.array(hexc("#d9cdb6"), F32)
    img = np.where(wall[..., None], stripes, img)
    im = Image.fromarray(to_u8(img))
    d = ImageDraw.Draw(im)
    d.rectangle([140 * S, 60 * S, 700 * S, 330 * S], fill=hexc("#f7f3ea"), outline=hexc("#3b3b3b"), width=6 * S)
    d.text((170 * S, 90 * S), "WALL CHART", font=font(40 * S, True), fill=hexc("#222222"))
    for k, line in enumerate(["E  F P  T O Z  L P E D", "P E C F D  E D F C Z P",
                              "F E L O P Z D  D E F P O T E C", "fine print: if you can read this, the far frame is in focus"]):
        d.text((170 * S, (150 + k * 42) * S), line, font=font((30 - k * 4) * S, k < 3), fill=hexc("#333333"))
    d.rectangle([0, (_M7_WALL - 6) * S, W, _M7_WALL * S], fill=hexc("#6b5a45"))
    img = _m7_down(np.asarray(im, F32), S)
    # contact shadows under the objects
    for cx, cy, rx, ry in [(390, 1150, 170, 34), (1415, 975, 70, 16), (800, 815, 120, 24), (1370, 462, 150, 18)]:
        c = Canvas((cx - rx, cy - ry, cx + rx, cy + ry), ss=2)
        c.ellipse(cx, cy, rx, ry)
        darken(img, c.mask(blur=ry * 0.6), 0.55)
    depth = np.clip(_m7_depth_for_row(coords(_M7_FW, _M7_FH)[1]), 0, 1.05).astype(F32)
    depth[: _M7_WALL] = 1.05
    return img, depth


def _m7_stack_objects():
    """Objects as (Layer, depth): near die, flower, mid mug, far books."""
    objs = []
    # near: a big red die in three-quarter view (d ~ 0.08)
    c = Canvas((180, 830, 620, 1180), ss=3, mode="RGBA")
    c.poly([(230, 930), (500, 930), (500, 1160), (230, 1160)], "#c62828")
    c.poly([(230, 930), (330, 860), (590, 860), (500, 930)], "#e25b4f")
    c.poly([(500, 930), (590, 860), (590, 1080), (500, 1160)], "#8e1b1b")
    for px, py in [(290, 990), (365, 1045), (440, 1100), (290, 1100), (440, 990)]:
        c.circle(px, py, 20, "#fdf6ec")
    for px, py in [(415, 895)]:
        c.ellipse(px, py, 26, 12, "#fdf6ec")
    for px, py in [(530, 945), (560, 1030)]:
        c.ellipse(px, py, 10, 18, "#f1e2d2")
    objs.append((c.layer(), 0.08))
    # near-mid: a daisy in a small glass (d ~ 0.30)
    c = Canvas((1300, 640, 1540, 990), ss=3, mode="RGBA")
    c.rrect(1375, 880, 1455, 975, 10, (200, 225, 235, 200))
    c.line([(1415, 880), (1410, 760), (1420, 700)], 7, "#3f7d2e")
    c.ellipse(1440, 800, 28, 11, "#4f9a3a")
    for k in range(16):
        a = k * math.pi / 8
        c.ellipse(1420 + math.cos(a) * 34, 700 + math.sin(a) * 34, 22, 22, "#fbfbf5")
    c.circle(1420, 700, 22, "#f2b01e")
    for k in range(10):
        a = k * 2.4
        c.circle(1420 + math.cos(a) * 12, 700 + math.sin(a) * 12, 3, "#b7770f")
    objs.append((c.layer(), 0.30))
    # mid: a blue mug with a printed label (d ~ 0.55)
    c = Canvas((650, 520, 990, 840), ss=3, mode="RGBA")
    c.line(quad_bezier((890, 610), (985, 620), (890, 760), n=18), 22, "#1f4f8f")
    c.rrect(690, 560, 900, 820, 18, "#2a64b0")
    c.ellipse(795, 562, 105, 20, "#1b3f70")
    c.rrect(720, 640, 870, 740, 8, "#f7f3ea")
    c.text(795, 668, "MID", 44, True, "#1b3f70", anchor="mm")
    c.text(795, 712, "zone 3 of 4", 18, False, "#333333", anchor="mm")
    objs.append((c.layer(), 0.55))
    # far: three books stacked against the wall (d ~ 0.92)
    c = Canvas((1180, 250, 1580, 480), ss=3, mode="RGBA")
    for k, (col, txt) in enumerate([("#6d2c3a", "ATLAS OF LIGHT"), ("#2f4f3f", "FIELD NOTES"), ("#c79a3a", "PHOTO YEAR")]):
        y1 = 462 - k * 58
        c.rect(1225 - k * 8, y1 - 54, 1520 - k * 12, y1, col)
        c.rect(1225 - k * 8, y1 - 54, 1520 - k * 12, y1 - 46, "#f1e9d6")
        c.text(1372 - k * 10, y1 - 22, txt, 22, True, "#f7f0dd", anchor="mm")
    objs.append((c.layer(), 0.92))
    return objs


def _m7_blur_layer(L: Layer, radius):
    if radius < 0.3:
        return L
    pad = int(radius * 3) + 2
    h, w = L.a.shape
    rgba = np.zeros((h + 2 * pad, w + 2 * pad, 4), F32)
    rgba[pad:pad + h, pad:pad + w, :3] = L.rgb * L.a[..., None]
    rgba[pad:pad + h, pad:pad + w, 3] = L.a * 255
    ch = [np.asarray(Image.fromarray(np.clip(rgba[..., k], 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius)), F32) for k in range(4)]
    a = ch[3] / 255.0
    rgb = np.stack(ch[:3], -1) / np.maximum(a, 1e-4)[..., None]
    return Layer(L.x - pad, L.y - pad, np.clip(rgb, 0, 255), a)


def m7_focus_stack():
    sharp, depth = _m7_stack_sharp()
    objs = _m7_stack_objects()
    K = 12.0
    radii = [0, 1, 2, 3.5, 5.5, 8, 11, 14]
    levels = [sharp if rr == 0 else blur_img(sharp, rr) for rr in radii]
    focus = [(0.10, "near"), (0.37, "midnear"), (0.64, "midfar"), (0.92, "far")]
    for i, (df, tag) in enumerate(focus):
        need = np.clip(K * np.abs(depth - df), 0, radii[-1])
        out = np.zeros_like(sharp)
        for j, rr in enumerate(radii):
            lo = radii[j - 1] if j else None
            hi = radii[j + 1] if j + 1 < len(radii) else None
            w = np.zeros_like(need)
            if lo is not None:
                m = (need >= lo) & (need <= rr)
                w[m] = (need[m] - lo) / (rr - lo)
            if hi is not None:
                m = (need >= rr) & (need < hi)
                w[m] = (hi - need[m]) / (hi - rr)
            else:
                w[need >= rr] = 1
            if j == 0:
                w[need == 0] = 1
            out += levels[j] * w[..., None]
        for L, d in sorted(objs, key=lambda o: -o[1]):
            over(out, _m7_blur_layer(L, K * abs(d - df)))
        # focus breathing: the image scales a hair as focus moves
        s = 1 + 0.004 * i
        im = Image.fromarray(to_u8(out))
        cx, cy = _M7_FW / 2, _M7_FH / 2
        im = im.transform(im.size, Image.AFFINE, (1 / s, 0, cx - cx / s, 0, 1 / s, cy - cy / s), Image.BICUBIC)
        fr = np.asarray(im, F32).copy()
        add_noise(fr, 2.0, rng(f"m7-stack-{i}"), mono=True)
        save_jpg(fr, 7, f"l19-stack/l19-stack-{i + 1}-{tag}.jpg", quality=90)
        if i == 0:
            ref = sharp.copy()
            for L, d in sorted(objs, key=lambda o: -o[1]):
                over(ref, L)
            _m7_save_inst_jpg(ref, "l19-stack-reference.jpg")


# ---------------------------------------------------------------------------------------
# L20: layered pieces for a looping social post, and six cinemagraph frames
# ---------------------------------------------------------------------------------------

_M7_AS = 1080


def _m7_anim_background():
    S = _M7_AS
    r = rng("m7-anim-bg")
    img = vgrad(S, S, [(0, "#2a1a14"), (0.55, "#5a3322"), (1, "#c96a2c")])
    X, Y = coords(S, S)
    for cx, cy, rad, col, op in [(180, 820, 420, "#e08a3c", 0.35), (900, 980, 300, "#f2b35a", 0.25),
                                 (300, 180, 220, "#7a4a30", 0.4)]:
        c = Canvas((cx - rad, cy - rad, cx + rad, cy + rad), ss=2, pad=130)
        c.circle(cx, cy, rad)
        paint(img, c.mask(blur=40), col, op)
    c = Canvas((0, 0, S, S), ss=2)
    c.rect(36, 36, S - 36, 40)
    c.rect(36, S - 40, S - 36, S - 36)
    c.rect(36, 36, 40, S - 36)
    c.rect(S - 40, 36, S - 36, S - 36)
    paint(img, c.mask(), "#f3dcc0", 0.6)
    c = Canvas((60, 60, 600, 140), ss=3)
    c.text(76, 76, "NORTHSIDE COFFEE CO.", 34, True)
    paint(img, c.mask(), "#f3dcc0", 0.9)
    add_noise(img, 3, r, mono=True)
    return img


def _m7_badge_layer():
    S = _M7_AS
    c = Canvas((0, 0, S, S), ss=3, mode="RGBA")
    cx, cy, R = 800, 300, 175
    pts = []
    for k in range(32):
        a = k * math.pi / 16 - math.pi / 2
        rr = R if k % 2 == 0 else R * 0.84
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    c.poly(pts, "#f5b83d")
    c.circle(cx, cy, R * 0.72, "#fff3d6")
    c.circle(cx, cy, R * 0.66, "#d9462b")
    c.text(cx, cy - 16, "NEW", 74, True, "#fff3d6", anchor="mm")
    c.text(cx, cy + 50, "HOUSE BLEND", 21, True, "#fff3d6", anchor="mm")
    return c.layer()


def _m7_headline_layer():
    S = _M7_AS
    c = Canvas((0, 0, S, S), ss=3, mode="RGBA")
    c.text(80, 800, "FRESH ROAST", 118, True, "#fff1dc")
    c.rect(84, 945, 380, 953, "#f5b83d")
    c.text(84, 975, "every Saturday · 8 AM", 44, False, "#f3dcc0")
    return c.layer()


def _m7_save_rgba(L: Layer, name):
    S = _M7_AS
    rgba = np.zeros((S, S, 4), F32)
    s = _slices((S, S), L.x, L.y, L.a.shape)
    rgba[s[0]][..., :3] = L.rgb[s[1]]
    rgba[s[0]][..., 3] = L.a[s[1]] * 255
    p = out_path(7, name)
    Image.fromarray(to_u8(rgba), "RGBA").save(p, "PNG", optimize=True, dpi=(72, 72), icc_profile=SRGB_ICC)
    _record(p)


def m7_anim_pieces():
    bg = _m7_anim_background()
    badge, head = _m7_badge_layer(), _m7_headline_layer()
    save_jpg(bg, 7, "l20-anim/l20-anim-1-background.jpg", quality=90)
    _m7_save_rgba(badge, "l20-anim/l20-anim-2-badge.png")
    _m7_save_rgba(head, "l20-anim/l20-anim-3-headline.png")
    # instructor reference: the target 3-second loop at 12 fps, half size
    frames = []
    n = 36
    small = Image.fromarray(to_u8(bg)).resize((540, 540), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))

    def key(t, pts):
        return float(np.interp(t, [p[0] for p in pts], [p[1] for p in pts]))

    for k in range(n):
        t = k / 12.0
        sc = key(t, [(0, 0.2), (0.7, 0.95), (0.9, 1.0), (2.2, 1.0), (2.9, 0.2), (3.0, 0.2)])
        op = key(t, [(0, 0), (0.4, 0), (1.0, 1), (2.2, 1), (2.8, 0), (3.0, 0)])
        dy = key(t, [(0, 40), (0.4, 40), (0.9, 4), (1.1, 0), (2.2, 0), (2.8, 40), (3.0, 40)])
        fr = np.asarray(small, F32).copy()
        b = _m7_blur_layer(badge, 0)
        bi = Image.fromarray(to_u8(np.dstack([b.rgb, b.a * 255])), "RGBA").resize((540, 540), Image.LANCZOS)
        bw = max(2, int(540 * sc))
        bi = bi.resize((bw, bw), Image.LANCZOS)
        ox, oy = int(400 - 400 * sc), int(150 - 150 * sc)
        ba = np.asarray(bi, F32)
        over(fr, Layer(ox, oy, ba[..., :3], ba[..., 3] / 255.0))
        hi = Image.fromarray(to_u8(np.dstack([head.rgb, head.a * 255])), "RGBA").resize((540, 540), Image.LANCZOS)
        ha = np.asarray(hi, F32)
        over(fr, Layer(0, int(dy / 2), ha[..., :3], ha[..., 3] / 255.0), op)
        frames.append(Image.fromarray(to_u8(fr)).quantize(64, dither=Image.Dither.NONE))
    p = out_path(7, "l20-reference-loop.gif", "instructor")
    frames[0].save(p, save_all=True, append_images=frames[1:], duration=83, loop=0, optimize=True)
    _record(p)


def m7_cinemagraph():
    W, H = 960, 720
    r = rng("m7-cinemagraph")
    base = vgrad(W, H, [(0, "#1a1512"), (0.62, "#2b211b"), (0.62, "#6b4a33"), (1, "#4a3222")])
    X, Y = coords(W, H)
    glow = np.exp(-((X - 120) / 380) ** 2 - ((Y - 260) / 300) ** 2)
    base += (glow * 45)[..., None] * np.array([1, 0.85, 0.6], F32)
    c = Canvas((300, 380, 700, 640), ss=3, mode="RGBA")
    c.ellipse(480, 610, 190, 26, (20, 14, 10, 150))                 # shadow
    c.line(quad_bezier((590, 470), (690, 490), (590, 575), n=18), 20, "#ece6dc")
    c.poly([(360, 450), (600, 450), (580, 590), (380, 590)], "#f1ebe1")
    c.ellipse(480, 590, 100, 16, "#d9d0c2")
    c.ellipse(480, 450, 120, 24, "#e6dfd4")
    c.ellipse(480, 452, 104, 18, "#3b2416")
    c.ellipse(470, 449, 50, 7, "#6b4630")
    over(base, c.layer())
    shade = np.clip((X - 420) / 180, 0, 1) * ((Y > 450) & (Y < 592) & (X > 360) & (X < 600))
    base *= (1 - 0.25 * shade)[..., None]
    add_noise(base, 2.5, r, mono=True)            # identical grain in every frame
    n = 6
    for k in range(n):
        ph = 2 * math.pi * k / n
        steam = np.zeros((H, W), F32)
        for j, (x0, amp, lam, wid) in enumerate([(455, 16, 150, 16), (495, 20, 190, 20), (475, 12, 120, 12)]):
            yy = Y[:, 0]
            up = np.clip((440 - yy) / 330, 0, 1)
            cxl = x0 + amp * (0.4 + up) * np.sin(2 * math.pi * yy / lam + ph * (1 + 0 * j) + j * 2.1)
            wl = wid * (1 + 2.2 * up)
            inten = np.clip(up * 6, 0, 1) * np.clip(1 - up, 0, 1) ** 1.3
            steam += (np.exp(-((X - cxl[:, None]) / wl[:, None]) ** 2) * inten[:, None] * 0.32).astype(F32)
        steam = np.asarray(Image.fromarray(to_u8(np.clip(steam, 0, 1) * 255)).filter(ImageFilter.GaussianBlur(4)), F32) / 255
        fr = base.copy()
        fr = fr * (1 - steam[..., None]) + np.array(hexc("#efe8df"), F32) * steam[..., None]
        save_jpg(fr, 7, f"l20-steam/l20-steam-0{k + 1}.jpg", quality=90)


# ======================================================================================
# Module 8: Capstone
# ======================================================================================

# ======================================================================================
# MODULE 8: Capstone (L21 The Brief & the Plan, L22 Studio Session, L23 Present & Case Study)
# ======================================================================================
# Backup briefs and assets for learners who arrive with little built, three presentation
# mockups (wall frame, phone feed, record sleeve), and the planning / case-study text
# templates. Every pixel is drawn from scratch; nothing comes from the course images/.

_M8_GRAY = "#9a9a9a"            # flat placeholder where learners place their art


def _m8_txt(text: str, name: str, folder: str = "practice") -> None:
    p = out_path(8, name, folder)
    p.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")
    _record(p)


# ---- text files -----------------------------------------------------------------------

def m8_vague_brief():
    _m8_txt("""
L21 WARM-UP: THE STICKY-NOTE BRIEF
Photoshop Intermediate: From Practitioner to Pro · Module 8 · Lesson 8.1

A (fictional) cafe owner left these notes on your desk. Nothing here can be checked,
so nothing here can ever be "done." Your job: pin every vague phrase to a spec,
a named constraint, or a reference image. Rewrite it as the six parts of a brief.

    - "Something for the new cold brew, for online."
    - "Make it pop."
    - "Modern vibe, but not cold."
    - "Clean but bold."
    - "Young people should like it."
    - "Our colors, I guess?"
    - "Soon-ish."
    - "You'll know it when you see it."

Rewrite as:
  1. Objective ............ one sentence: what must it achieve, and why?
  2. Audience ............. who, their context, what should make them stop?
  3. Deliverables + specs . exact outputs, pixel sizes, formats, where they live
  4. Constraints .......... brand rules, colors, fonts, budget, deadline
  5. Success criteria ..... a checklist someone else could grade
  6. References .......... which images give "bold" and "modern" a picture?

Test: could a stranger build against your version and know when it is finished?
Mantra: if you can't check it, it isn't in the brief.
""", "l21-vague-brief.txt")


def m8_vague_brief_fixed():
    _m8_txt("""
INSTRUCTOR ONLY: ONE GOOD ANSWER TO l21-vague-brief.txt
(There are many good answers. Accept any version where every line is checkable.)

1. OBJECTIVE
   Launch Halden Cold Brew (a fictional cafe brand) online: one hero image that makes a
   phone-scrolling customer stop and read the product name.

2. AUDIENCE
   Local 20-35-year-old commuters who follow the cafe on social media; they see it on a
   phone, in a feed, for about one second.
   ("Young people should like it" -> a named group, a device, a viewing time.)

3. DELIVERABLES + SPECS
   - Web hero banner 3000 x 2000 px, sRGB JPG
   - Feed post 1080 x 1350 px (4:5), sRGB JPG
   - Story 1080 x 1920 px (9:16), sRGB JPG, key content inside the safe zone
   - Layered master .psd with artboards
   ("Something for online" -> three named sizes, one color space, one master.)

4. CONSTRAINTS
   - Brand colors: deep green #1F4D3F, cream #F3E9DC; one accent allowed
   - One type family, two weights at most
   - Use the supplied logo file; do not redraw it
   - Final files due Friday, 5 p.m.
   ("Our colors, I guess?" -> hex values. "Soon-ish" -> a date and a time.)

5. SUCCESS CRITERIA (a checklist)
   [ ] Product name readable on a phone-sized thumbnail (about 300 px wide)
   [ ] One focal point: the can; it survives the squint test
   [ ] Light direction on the can matches the scene (window light from the left)
   [ ] Contact shadow present; nothing floats
   [ ] Warm grade: no pure-blue shadows anywhere
   [ ] All three sizes exported at spec from one master
   ("Make it pop" -> readable at thumbnail size + one focal point.
    "You'll know it when you see it" -> this list.)

6. REFERENCES / MOODBOARD (6-12, each annotated)
   - Morning-window light on a counter  -> the light direction and warmth
   - An editorial food photo with lots of negative space -> "clean"
   - A poster with one heavy sans headline -> "bold"
   - A matte, low-contrast color grade -> "modern, but not cold"
   ("Clean but bold", "modern vibe, but not cold" -> pictures, each with a reason.)
""", "l21-vague-brief-fixed.txt", folder="instructor")


def m8_brief_template():
    _m8_txt("""
CAPSTONE BRIEF (ONE PAGE) · Lesson 8.1
Photoshop Intermediate: From Practitioner to Pro

Name: ____________________    Project: ____________________    Date: __________

Keep it to one page. Force every adjective to a spec or a reference.
Mantra: if you can't check it, it isn't in the brief.

1. OBJECTIVE (one sentence: what this must achieve, and why)
   ______________________________________________________________________

2. AUDIENCE (who it is for; their context; what should make them stop)
   ______________________________________________________________________

3. DELIVERABLES + SPECS (exact outputs, sizes, formats, and where they will live)
   - ________  ____ x ____ px / in   ___ ppi   color: ______   format: ______
   - ________  ____ x ____ px / in   ___ ppi   color: ______   format: ______
   - Layered master: ______________________.psd

4. CONSTRAINTS (brand rules, colors, fonts, budget, and the deadline)
   Colors: ____________   Fonts: ____________   Deadline: ____________
   Other: ______________________________________________________________

5. SUCCESS CRITERIA (a checklist you could hand to someone else to grade)
   [ ] ________________________________________________
   [ ] ________________________________________________
   [ ] ________________________________________________
   [ ] ________________________________________________
   [ ] ________________________________________________

6. REFERENCES / MOODBOARD (6-12 images; the one thing you take from each)
   1. ______________ -> ______________     7. ______________ -> ______________
   2. ______________ -> ______________     8. ______________ -> ______________
   3. ______________ -> ______________     9. ______________ -> ______________
   4. ______________ -> ______________    10. ______________ -> ______________
   5. ______________ -> ______________    11. ______________ -> ______________
   6. ______________ -> ______________    12. ______________ -> ______________

THE PLAN (stages -> module skills)
   Stage                         Module skill                  Assets to source/shoot
   Assets & cutouts ............ Module 1 · masking            ______________________
   Color base .................. Module 2 · grade/space        ______________________
   Subject retouch ............. Module 3                      ______________________
   Composite ................... Module 4 · light/shadow/atmos ______________________
   Type & system ............... Module 5                      ______________________
   Automate & export ........... Module 6 · maybe 7            ______________________
   Present ..................... Module 8.3                    ______________________
   (Not every project needs every stage. Cross out the ones yours does not.)

   Assets I did not shoot: license and credit terms checked?  [ ] yes

MILESTONES (two or three, and a realistic finish date)
   1. ______________________  by ________
   2. ______________________  by ________
   3. ______________________  by ________
   Finish date: ________

STRETCH GOALS (optional; each must be cuttable without breaking the deliverable)
   - ______________________________________________
   - ______________________________________________
""", "l21-brief-template.txt")


def m8_backup_briefs():
    _m8_txt("""
READY-MADE BACKUP BRIEFS · Lesson 8.1
Use one of these only if you have no project of your own, or you arrive at Session 8
with little built. The assets named below are in this practice folder. Both brands and
the film are fictional. You may still add your own photos.

=====================================================================================
BRIEF A · KEY ART POSTER: "THE SALT ROAD" (a film that does not exist)
Touches Modules 1, 3, 4, 5.
=====================================================================================
1. Objective   A one-sheet key art poster that sells a quiet, tense road-movie thriller.
2. Audience    Festival-goers scrolling a program page or passing a lobby wall.
3. Deliverables + specs
               - Poster 24 x 36 in, 300 ppi (build smaller if your machine struggles,
                 e.g. 2400 x 3600 px), print PDF to the printer's spec
               - Screen version 1080 x 1620 px, sRGB JPG
               - Layered master .psd
4. Constraints Title "THE SALT ROAD"; a credit block at the bottom; one type family;
               palette of dusk orange, salt white and deep blue; deadline: Session 8.
5. Success criteria
               [ ] The figure stands on the road at the right scale for the horizon
               [ ] Light on the figure comes from the left, like the low sun
               [ ] A contact shadow and a long cast shadow to the right
               [ ] Haze makes the distant hills lighter than the foreground
               [ ] Title readable at a phone-sized thumbnail
               [ ] One unifying grade over the whole composite
6. References   Find 6-12 of your own: dusk road photography, thriller one-sheets,
               heavy condensed title type.
Assets: l21-backup-keyart-plate.jpg (the road at dusk, horizon at y 1900 of 3000,
        sun low on the left), l21-backup-keyart-figure.jpg (a figure on gray, lit from
        the left, with wind-blown hair for a Select & Mask cutout).

=====================================================================================
BRIEF B · PRODUCT CAMPAIGN: "HALDEN COLD BREW" (a fictional brand)
Touches Modules 2, 4, 5, 6.
=====================================================================================
1. Objective   Launch the product online with one hero and a sized social set,
               all from one master.
2. Audience    Local commuters who follow the cafe on social media, on a phone.
3. Deliverables + specs
               - Web hero 3000 x 2000 px, sRGB JPG
               - Feed post 1080 x 1350 px (4:5) and story 1080 x 1920 px (9:16),
                 sRGB JPG, key content inside the safe zone
               - Layered master .psd with artboards
4. Constraints Brand green #1F4D3F and cream #F3E9DC plus one accent; use the supplied
               logo (do not redraw it); one type family; deadline: Session 8.
5. Success criteria
               [ ] Clean cutout of the can, no fringe at 100%
               [ ] Light direction on the can matches the window light (from the left)
               [ ] Contact shadow where the can meets the counter
               [ ] Product name readable at a phone-sized thumbnail
               [ ] All sizes exported at spec from one master (an Action is a bonus)
6. References   Find 6-12 of your own: window-lit product shots, editorial food
               photography, minimal packaging ads.
Assets: l21-backup-product.jpg (the can on seamless gray, lit from the left),
        l21-backup-product-surface.jpg (counter and wall with window light from the
        left), l21-backup-brand-logo.png (transparent logo).

=====================================================================================
EDITORIAL PORTRAIT?
=====================================================================================
There is no synthetic portrait for this brief here. Reuse your Module 3 retouching
practice portrait (labs/module-3/practice/) or, better, a portrait you shot yourself
of someone who has agreed to have it retouched and shown in class.
""", "l21-backup-briefs.txt")


def m8_case_study_outline():
    _m8_txt("""
CASE-STUDY OUTLINE · Lesson 8.3
Lay it out top to bottom like a story. Lead with the outcome or the idea, not the tools.
Mantra: show that you think like a professional, not just that you can push pixels.

PAGE ORDER (top to bottom)
  1. HERO SHOT ...... the finished piece, big, first. Earn the scroll.
  2. THE BRIEF ...... the challenge and who it was for, in a line (from your 8.1 brief).
  3. APPROACH ....... your strategy in a sentence or two: the key idea that solved it.
  4. PROCESS ........ 3-5 progress shots or a before/after that reveal how it was built.
  5. DETAILS ........ a few close crops of craft you're proud of
                      (a clean cutout, the grade, the type).
  6. RESULT ......... deliverables in context/mockups, plus any outcome you can claim.
  7. REFLECTION ..... one honest paragraph on what you learned.

THE FIVE BEATS (keep each tight: a few sentences)
  Challenge  : what needed solving? ___________________________________________
  Approach   : your strategy, and why? ________________________________________
  Process    : how you built it (the 3 or 4 moments that show judgment) _______
  Result     : the finished work in context ___________________________________
  Reflection : what worked, what you would change ____________________________

  Outcome-first:  "A warm, editorial key art that reads on mobile"
  beats           "I used Curves and Generative Fill."

HONESTY
  - Real "before", real steps. A fabricated before costs all your credibility.
  - Used Generative Fill or Expand? Say so in the process section. Content Credentials
    can be attached on export as well.

EXPORT
  - Web-sized images: File > Export > Export As
  - PDF: File > Save a Copy > Photoshop PDF
    (or File > Export > Artboards to PDF if you laid it out on several artboards)

30-SECOND SPOKEN VERSION ("Tell me about this piece.")
  ______________________________________________________________________________
""", "l23-case-study-outline.txt")


# ---- backup key art: the road plate and the figure -----------------------------------

def m8_keyart_plate():
    name = "l21-backup-keyart-plate.jpg"
    r = rng(name)
    W, H = 2000, 3000
    hy = 1900                                                     # horizon
    vx = 1120                                                     # vanishing point x
    sunx, suny = 430, 1830
    img = np.empty((H, W, 3), F32)
    img[:hy] = vgrad(W, hy, [(0, "#101a3a"), (0.45, "#2c3a6e"), (0.78, "#b7616a"),
                             (0.93, "#ee9a5e"), (1, "#f7c27a")])
    X, Y = coords(W, hy)
    d = np.hypot((X - sunx) / 900, (Y - suny) / 520)
    glow = (np.clip(1 - d, 0, 1) ** 2.2)[..., None]
    img[:hy] = img[:hy] * (1 - glow * 0.7) + np.array(hexc("#ffd79a"), F32) * glow * 0.7
    c = Canvas((sunx - 60, suny - 60, sunx + 60, suny + 60), ss=3, pad=40)
    c.circle(sunx, suny, 46)
    paint(img, c.mask(blur=3), "#fff1cf")
    # distant hills (two ridges, the far one lighter from haze)
    for k, (base, amp, col) in enumerate(((hy - 70, 60, "#9b6f7e"), (hy - 25, 40, "#6d4f66"))):
        xs = np.linspace(-20, W + 20, 90)
        ys = smooth_wave(xs, base, amp, [(700, 1, r.uniform(0, 6)), (260, .5, r.uniform(0, 6)),
                                         (95, .2, r.uniform(0, 6))])
        c = Canvas((0, base - amp - 20, W, hy + 2), ss=2)
        c.poly(list(zip(xs, ys)) + [(W + 20, hy + 2), (-20, hy + 2)])
        paint(img, c.mask(), col)
    # salt flat: pale, warm near the horizon, cooler and darker toward the viewer
    g = vgrad(W, H - hy, [(0, "#e8c9a6"), (0.25, "#cdb7a4"), (1, "#7f7f93")])
    X, Y = coords(W, H - hy)
    tex = np.sin(X / 7 + np.sin(Y / 11) * 2) * 0.5 + 0.5
    comp = (Y / (H - hy)) ** 1.5
    g *= (1 - 0.05 * tex * comp)[..., None]
    img[hy:] = g
    for _ in range(60):                                           # salt crust streaks
        t = r.random() ** 2
        y = hy + 6 + t * (H - hy - 10)
        ln = 80 + 900 * t
        x = r.uniform(-100, W)
        c = Canvas((x, y - 6, x + ln, y + 6), ss=2)
        c.line([(x, y), (x + ln, y + r.uniform(-2, 2))], 1 + 5 * t)
        paint(img, c.mask(blur=1 + 2 * t), "#f4e6d4", 0.35)
    # the road, converging on the vanishing point
    c = Canvas((0, hy, W, H), ss=3)
    c.poly([(vx - 6, hy), (vx + 6, hy), (1780, H), (420, H)])
    road = c.mask()
    paint(img, road, vgrad(W, H, [(0, "#5a5058"), (1, "#2c2a33")], hy, H))
    c = Canvas((0, hy, W, H), ss=3)
    for k in range(14):                                           # dashed centre line
        t0, t1 = (k / 14) ** 2.2, ((k + 0.45) / 14) ** 2.2
        y0, y1 = hy + t0 * (H - hy), hy + t1 * (H - hy)
        w0, w1 = 1 + t0 * 22, 1 + t1 * 22
        x0, x1 = vx + (1100 - vx) * t0, vx + (1100 - vx) * t1
        c.poly([(x0 - w0, y0), (x0 + w0, y0), (x1 + w1, y1), (x1 - w1, y1)])
    paint(img, c.mask(), "#e9d9a8", 0.85)
    # telephone poles on the left verge: scale cues shrinking toward the horizon
    for k in range(6):
        t = 0.95 * (0.62 ** k)                                    # 0 = horizon, 1 = bottom
        by = hy + t * (H - hy)
        bx = vx + (180 - vx) * t
        ph = 40 + 1500 * t
        pw = 3 + 26 * t
        c = Canvas((bx - pw - 2 * ph, by - ph - 10, bx + 2 * ph, by + 20), ss=2, pad=10)
        c.poly([(bx, by - 2), (bx + pw * 0.6, by + pw * 0.2), (bx + 1.9 * ph, by + 0.30 * ph),
                (bx + 1.9 * ph - pw, by + 0.30 * ph - pw * 0.4)])   # long shadow to the right
        paint(img, c.mask(blur=1 + 3 * t), "#2d2a3c", 0.45)
        c = Canvas((bx - pw - 2 * ph, by - ph - 10, bx + 2 * ph, by + 20), ss=2, pad=10)
        c.rect(bx - pw / 2, by - ph, bx + pw / 2, by)
        c.rect(bx - pw * 3, by - ph * 0.93, bx + pw * 3, by - ph * 0.93 + pw * 0.8)
        paint(img, c.mask(), "#2a2230")
        c = Canvas((bx - pw - 2 * ph, by - ph - 10, bx + 2 * ph, by + 20), ss=2, pad=10)
        c.rect(bx - pw / 2, by - ph, bx - pw / 6, by)             # sunlit left edge
        paint(img, c.mask(), "#b86a4e", 0.8)
    # atmosphere: haze band on the horizon, a touch of vignette
    Yf = np.arange(H, dtype=F32)[:, None, None]
    haze = np.exp(-((Yf - hy) / 140) ** 2) * 0.35
    img = img * (1 - haze) + np.array(hexc("#f0b98a"), F32) * haze
    X, Y = coords(W, H)
    vig = 1 - 0.28 * np.clip(np.hypot((X - W / 2) / (W * 0.75), (Y - H * 0.6) / (H * 0.7)), 0, 1) ** 2
    img *= vig[..., None]
    add_noise(img, 3, r, mono=True)
    save_jpg(img, 8, name, quality=90)


_M8_COAT, _M8_TROUSER, _M8_BOOT = "#3b4a52", "#2c2c33", "#1e1a18"
_M8_SKIN, _M8_HAIR, _M8_SCARF = "#c99b7c", "#2b1d16", "#9b3b2c"


def m8_keyart_figure():
    name = "l21-backup-keyart-figure.jpg"
    r = rng(name)
    W, H = 1600, 2400
    X, Y = coords(W, H)
    img = vgrad(W, H, [(0, "#a3a8ae"), (0.7, "#8e949a"), (1, "#7b8187")])
    vig = 1 - 0.22 * np.clip(np.hypot((X - 620) / 1100, (Y - 1000) / 1500), 0, 1) ** 2
    img *= vig[..., None]
    # contact + cast shadow on the seamless floor, falling to the right (light from left)
    c = Canvas((520, 2150, 1500, 2300), ss=1, pad=60)
    c.ellipse(800, 2238, 260, 26)
    darken(img, c.mask(blur=14), 0.55)
    c = Canvas((520, 2150, 1500, 2300), ss=1, pad=60)
    c.poly([(640, 2240), (960, 2228), (1460, 2190), (1440, 2262), (700, 2262)])
    darken(img, c.mask(blur=30), 0.28)

    box = (380, 360, 1300, 2290)
    c = Canvas(box, ss=3, mode="RGBA")
    c.rrect(650, 1700, 770, 2215, 20, _M8_TROUSER)               # legs
    c.rrect(830, 1700, 950, 2215, 20, _M8_TROUSER)
    c.rrect(630, 2180, 790, 2252, 30, _M8_BOOT)
    c.rrect(820, 2180, 990, 2252, 30, _M8_BOOT)
    hem = [(585, 1860)]                                           # coat, hem blown right
    for k in range(1, 12):
        t = k / 12
        hem.append((585 + 540 * t, 1860 + 45 * math.sin(t * 9) + 60 * t + r.uniform(-12, 12)))
    hem.append((1150, 1930))
    c.poly([(650, 860), (950, 860), (1030, 1300)] + hem[::-1] + [(590, 1300)], _M8_COAT)
    c.rrect(630, 800, 970, 1000, 90, _M8_COAT)                   # shoulders
    c.line([(655, 880), (600, 1180), (590, 1520)], 96, "#35434a", round_caps=True)   # sleeves
    c.line([(945, 880), (1000, 1180), (1010, 1520)], 96, "#35434a", round_caps=True)
    c.circle(592, 1590, 42, _M8_SKIN)
    c.circle(1010, 1590, 42, _M8_SKIN)
    c.line([(800, 900), (800, 1840)], 4, "#2a353b")               # coat opening
    c.rect(765, 700, 835, 830, _M8_SKIN)                          # neck
    c.poly([(690, 790), (910, 790), (955, 880), (645, 880)], _M8_SCARF)   # scarf
    c.poly([(900, 820), (1080, 900), (1170, 960), (1090, 990), (930, 880)], _M8_SCARF)
    c.ellipse(800, 590, 118, 140, _M8_HAIR)                       # hair cap
    c.ellipse(795, 608, 98, 128, _M8_SKIN)                        # face (three-quarter)
    c.d.chord(c.B(800 - 116, 588 - 140, 800 + 116, 588 + 140), 190, 350, fill=c._f(_M8_HAIR))
    c.ellipse(752, 610, 9, 7, "#3a2a22")
    c.ellipse(826, 610, 9, 7, "#3a2a22")
    L = c.layer()
    # light from the left: brighter on each shape's left side, plus a warm rim
    xs = np.arange(L.a.shape[1], dtype=F32) + L.x
    f = 1.22 - 0.5 * np.clip((xs - 520) / (1100 - 520), 0, 1)
    rgb = np.clip(L.rgb * f[None, :, None], 0, 255)
    solid_a = (L.a > 0.5).astype(F32)
    shifted = np.zeros_like(solid_a)
    shifted[:, 9:] = solid_a[:, :-9]
    rim = np.clip(solid_a - shifted, 0, 1)
    rim = np.asarray(Image.fromarray(to_u8(rim * 255)).filter(ImageFilter.GaussianBlur(2.5)), F32) / 255
    rim = (rim * solid_a)[..., None] * 0.55
    rgb = rgb * (1 - rim) + np.array(hexc("#f3c89a"), F32) * rim
    over(img, Layer(L.x, L.y, rgb, L.a))
    # wind-blown hair: fine strands streaming to the right (the Select & Mask test)
    cs = Canvas(box, ss=3)
    for _ in range(520):
        t = r.uniform(-0.55 * math.pi, 0.45 * math.pi)            # mostly top and right
        px, py = 800 + 112 * math.cos(t), 588 + 132 * math.sin(t)
        ln = 60 + 230 * r.random() ** 1.6
        ex = px + ln * r.uniform(0.8, 1.0)
        ey = py + ln * r.uniform(-0.25, 0.35)
        mx = (px + ex) / 2 + r.uniform(-20, 20)
        my = (py + ey) / 2 - r.uniform(10, 50)
        cs.line(quad_bezier((px, py), (mx, my), (ex, ey), 16), r.uniform(1, 1.8),
                r.uniform(0.35, 0.85) * 255)
    paint(img, cs.mask(blur=0.4), "#3a2a20")
    add_noise(img, 2.5, r)
    save_jpg(img, 8, name, quality=92)


# ---- backup product campaign: the can, the counter, the logo ---------------------------

def _m8_logo_layer(w, h, scale=1.0, color="#1f4d3f", sub="COLD BREW CO."):
    """A fictional wordmark as an RGBA Layer at (0, 0): a leaf-in-circle mark + HALDEN."""
    c = Canvas((0, 0, w, h), ss=3, mode="RGBA")
    s = scale
    cx, cy = 0.17 * w, 0.5 * h
    c.circle(cx, cy, 150 * s, color)
    c.circle(cx, cy, 128 * s, (0, 0, 0, 0))
    c.ellipse(cx, cy, 58 * s, 100 * s, color)                    # a bean
    c.line([(cx - 8 * s, cy - 92 * s), (cx + 14 * s, cy - 10 * s), (cx - 10 * s, cy + 92 * s)],
           10 * s, (0, 0, 0, 0))
    c.text(0.32 * w, 0.46 * h, "HALDEN", 165 * s, bold=True, fill=color, anchor="lm")
    c.text(0.325 * w, 0.46 * h + 120 * s, sub, 50 * s, fill=color, anchor="lm")
    return c.layer()


def m8_brand_logo():
    name = "l21-backup-brand-logo.png"
    W, H = 1400, 480
    L = _m8_logo_layer(W, H)
    out = np.zeros((H, W, 4), F32)
    h, w = L.a.shape
    out[:h, :w, :3] = L.rgb
    out[:h, :w, 3] = L.a * 255
    save_png(Image.fromarray(to_u8(out), "RGBA"), 8, name)


def m8_product():
    name = "l21-backup-product.jpg"
    r = rng(name)
    W = H = 2000
    img = vgrad(W, H, [(0, "#d6d9dc"), (0.75, "#c4c8cc"), (1, "#b9bdc1")])
    X, Y = coords(W, H)
    img *= (1.04 - 0.1 * np.clip(X / W, 0, 1))[..., None]      # light from the left
    x0, x1, y0, y1 = 720, 1280, 470, 1600
    cw = x1 - x0
    # cast shadow to the right, then a tight contact shadow
    c = Canvas((x0, y1 - 80, 1900, y1 + 80), ss=1, pad=60)
    c.poly([(x0 + 60, y1 + 20), (x1, y1 - 30), (1840, y1 - 10), (1820, y1 + 50), (x0 + 120, y1 + 45)])
    darken(img, c.mask(blur=28), 0.30)
    c = Canvas((x0, y1 - 40, x1, y1 + 40), ss=2, pad=30)
    c.ellipse((x0 + x1) / 2 + 20, y1 + 8, cw / 2 + 10, 26)
    darken(img, c.mask(blur=9), 0.55)
    # can body with cylindrical shading (key light from the left)
    t = np.clip((X - x0) / cw, 0, 1)
    shade = 0.55 + 0.75 * np.exp(-((t - 0.24) / 0.16) ** 2) + 0.35 * (1 - t) - 0.1 * t
    shade += 0.25 * np.exp(-((t - 0.93) / 0.04) ** 2)            # a thin rim from the wall
    metal = np.array(hexc("#b9bec4"), F32)
    green = np.array(hexc("#1f4d3f"), F32)
    c = Canvas((x0, y0, x1, y1), ss=3, pad=4)
    c.rect(x0, y0 + 30, x1, y1 - 30)
    c.ellipse((x0 + x1) / 2, y1 - 30, cw / 2, 30)
    body = c.mask()
    paint(img, body, np.clip(metal * shade[..., None] * 0.85, 0, 255))
    ly0, ly1 = 690, 1400                                          # the label band
    c = Canvas((x0, ly0 - 40, x1, ly1 + 40), ss=3, pad=2)
    c.rect(x0, ly0, x1, ly1)
    c.ellipse((x0 + x1) / 2, ly1, cw / 2, 30)
    c.ellipse((x0 + x1) / 2, ly0, cw / 2, 30, 0)                 # curved like the can
    paint(img, c.mask(), np.clip(green * (0.35 + 0.8 * shade)[..., None], 0, 255))
    band = Canvas((x0, ly0, x1, ly1 + 40), ss=3, pad=2)           # cream stripe
    band.ellipse((x0 + x1) / 2, ly1 - 52, cw / 2, 30)
    band.ellipse((x0 + x1) / 2, ly1 - 70, cw / 2, 30, 0)
    paint(img, band.mask(), np.clip(np.array(hexc("#f3e9dc"), F32) * (0.45 + 0.6 * shade)[..., None], 0, 255))
    # the wordmark on the label, squeezed toward the edges like a cylinder
    lw, lh = 1400, 480
    Lg = _m8_logo_layer(lw, lh, color="#f3e9dc", sub="COLD BREW")
    crop = Image.fromarray(to_u8(np.dstack([Lg.rgb, Lg.a * 255])), "RGBA").crop((360, 60, 1400, 420))
    tw = int(cw * 0.78)
    crop = crop.resize((tw, int(crop.height * tw / crop.width)), Image.LANCZOS)
    arr = np.asarray(crop, F32)
    u = np.linspace(-1, 1, tw)
    src = ((np.arcsin(np.clip(u * 0.97, -1, 1)) / (math.pi / 2) * 0.5 + 0.5) * (tw - 1)).astype(int)
    arr = arr[:, src]
    ox, oy = int((x0 + x1) / 2 - tw / 2), 900
    sh = np.clip(0.45 + 0.6 * shade[oy:oy + arr.shape[0], ox:ox + tw], 0, 1.3)[..., None]
    over(img, Layer(ox, oy, np.clip(arr[..., :3] * sh, 0, 255), arr[..., 3] / 255))
    c = Canvas((x0, y0 - 40, x1, y0 + 60), ss=3, pad=4)           # lid
    c.ellipse((x0 + x1) / 2, y0 + 30, cw / 2, 34)
    paint(img, c.mask(), np.clip(metal * (0.6 + 0.5 * shade)[..., None], 0, 255))
    c = Canvas((x0, y0 - 40, x1, y0 + 60), ss=3, pad=4)
    c.ellipse((x0 + x1) / 2, y0 + 32, cw / 2 - 22, 24)
    paint(img, c.mask(), "#8d9298")
    c = Canvas((x0, y0 - 40, x1, y0 + 60), ss=3, pad=4)
    c.rrect(960, y0 + 18, 1080, y0 + 44, 12)                      # tab
    paint(img, c.mask(), "#c9ced3")
    add_noise(img, 2.5, r, mono=True)
    save_jpg(img, 8, name, quality=92)


def m8_product_surface():
    name = "l21-backup-product-surface.jpg"
    r = rng(name)
    W, H = 3000, 2000
    ey = 1160                                                     # back edge of the counter
    img = np.empty((H, W, 3), F32)
    img[:ey] = vgrad(W, ey, [(0, "#e6dccd"), (1, "#d6c8b4")])
    X, Y = coords(W, ey)
    # window light on the wall: a skewed pane with mullion shadows, from the left
    pane = np.zeros((ey, W), F32)
    c = Canvas((0, 0, W, ey), ss=1)
    c.poly([(250, 120), (1350, 260), (1450, 1080), (330, 1000)])
    pane = full_mask(c.mask(blur=18), W, ey)
    c = Canvas((0, 0, W, ey), ss=1)
    c.poly([(780, 180), (830, 186), (910, 1045), (860, 1040)])
    c.poly([(290, 560), (1400, 660), (1405, 700), (295, 600)])
    mull = full_mask(c.mask(blur=10), W, ey)
    light = (pane * (1 - mull) * 0.32)[..., None]
    img[:ey] = img[:ey] * (1 - light) + np.array(hexc("#fff4df"), F32) * light
    # counter: warm concrete with speckle, darker toward the front, and a front edge band
    g = vgrad(W, H - ey, [(0, "#b8ab9c"), (1, "#8e8273")])
    sp = r.standard_normal((H - ey, W)).astype(F32)
    sp = np.asarray(Image.fromarray(to_u8(sp * 30 + 128)).filter(ImageFilter.GaussianBlur(1.2)), F32) - 128
    g += sp[..., None] * 0.5
    img[ey:] = g
    Xc, Yc = coords(W, H - ey)
    pool = np.clip(1 - np.hypot((Xc - 900) / 1300, (Yc - 250) / 520), 0, 1) ** 2 * 0.22
    img[ey:] = img[ey:] * (1 - pool[..., None]) + np.array(hexc("#fff0d8"), F32) * pool[..., None]
    img[ey:ey + 5] *= 0.7                                         # occlusion at the wall
    img[1930:] = vgrad(W, 70, [(0, "#c5b8a8"), (1, "#9d9182")])
    f = np.linspace(1.06, 0.84, W, dtype=F32)                     # falloff left -> right
    img *= f[None, :, None]
    add_noise(img, 3, r, mono=True)
    save_jpg(img, 8, name, quality=90)


# ---- presentation mockups ----------------------------------------------------------

def m8_mockup_wall():
    """A framed-print mockup with a 2:3 portrait opening (800 x 1200) for a poster."""
    name = "l23-mockup-wall.jpg"
    r = rng(name)
    W, H = 3000, 2000
    fy = 1700
    img = np.empty((H, W, 3), F32)
    img[:fy] = vgrad(W, fy, [(0, "#e9e4dc"), (1, "#d6cfc3")])
    X, Y = coords(W, fy)
    d = np.hypot((X - 1400) / 1300, (Y - 450) / 900)
    pool = (np.clip(1 - d, 0, 1) ** 2 * 70 / 255)[..., None]
    img[:fy] = img[:fy] * (1 - pool) + 255 * pool
    img[fy:] = vgrad(W, H - fy, [(0, (150, 118, 88)), (1, "#8a6a4e")])
    img[fy:fy + 6] = hexc("#5e4a38")
    frame, opening = (1000, 160, 2000, 1560), (1100, 260, 1900, 1460)
    fx0, fy0, fx1, fy1 = frame
    c = Canvas(frame, ss=1, pad=90)
    c.rect(fx0 + 20, fy0 + 22, fx1 + 20, fy1 + 22)
    darken(img, c.mask(blur=30), 75 / 255)
    img[fy0:fy1, fx0:fx1] = hexc("#262626")
    img[fy0 + 30:fy1 - 30, fx0 + 30:fx1 - 30] = (248, 248, 245)
    ox0, oy0, ox1, oy1 = opening
    img[oy0 - 3:oy1 + 3, ox0 - 3:ox1 + 3] = (225, 224, 220)       # mat bevel
    img[oy0:oy1, ox0:ox1] = hexc(_M8_GRAY)
    # a low bench to the right for scale
    c = Canvas((2150, 1350, 2900, 1720), ss=2)
    c.rect(2180, 1480, 2880, 1540)
    c.rect(2220, 1540, 2260, 1700)
    c.rect(2800, 1540, 2840, 1700)
    paint(img, c.mask(), "#6b4f3a")
    add_noise(img, 2, r, mono=True)
    save_jpg(img, 8, name, quality=90)


def m8_mockup_phone():
    """A phone lying on a desk (rotated), showing a feed with a 4:5 post placeholder."""
    name = "l23-mockup-phone.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = hgrad(W, H, [(0, "#8b6446"), (1, "#6f4f37")])
    for k in range(40):                                           # wood grain, vertical
        x = r.uniform(0, W)
        xs = x + 6 * np.sin(np.linspace(0, 6, 80) + r.uniform(0, 6))
        c = Canvas((x - 20, 0, x + 20, H), ss=2)
        c.line(list(zip(xs, np.linspace(-10, H + 10, 80))), r.uniform(1, 3))
        paint(img, c.mask(), rand_color_near(r, hexc("#5e412c"), 12), 0.5)
    img *= np.linspace(1.08, 0.9, W, dtype=F32)[None, :, None]
    # a notebook corner for context
    c = Canvas((1650, 900, 2400, 1600), ss=2, pad=40)
    c.poly([(1760, 1000), (2450, 930), (2450, 1650), (1850, 1650)])
    paint(img, c.mask(blur=14), "#000000", 0.25)
    c = Canvas((1650, 900, 2400, 1600), ss=2)
    c.poly([(1740, 980), (2430, 910), (2430, 1640), (1830, 1640)])
    paint(img, c.mask(), "#ece6da")
    # the phone, drawn upright on an RGBA canvas, then rotated
    pw, ph = 600, 1220
    ph_img = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    ss = 3
    big = Image.new("RGBA", ((pw + 80) * ss, (ph + 80) * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    S = lambda *v: [q * ss for q in v]
    d.rounded_rectangle(S(40, 40, 40 + pw, 40 + ph), radius=80 * ss, fill=(20, 20, 22, 255))
    sx0, sy0, sx1, sy1 = 64, 64, 40 + pw - 24, 40 + ph - 24
    d.rounded_rectangle(S(sx0, sy0, sx1, sy1), radius=58 * ss, fill=(250, 250, 250, 255))
    d.rounded_rectangle(S(40 + pw / 2 - 60, 80, 40 + pw / 2 + 60, 110), radius=15 * ss, fill=(20, 20, 22, 255))
    d.ellipse(S(sx0 + 30, 160, sx0 + 90, 220), fill=(200, 200, 205, 255))      # avatar
    d.rounded_rectangle(S(sx0 + 110, 172, sx0 + 330, 190), radius=6 * ss, fill=(60, 60, 64, 255))
    d.rounded_rectangle(S(sx0 + 110, 198, sx0 + 250, 210), radius=5 * ss, fill=(170, 170, 176, 255))
    postw = sx1 - sx0
    posth = int(postw * 5 / 4)
    py0 = 240
    d.rectangle(S(sx0, py0, sx1, py0 + posth), fill=hexc(_M8_GRAY) + (255,))  # 4:5 post
    iy = py0 + posth + 24
    for k, ix in enumerate((sx0 + 30, sx0 + 100, sx0 + 170)):
        d.ellipse(S(ix, iy, ix + 44, iy + 44), outline=(40, 40, 44, 255), width=5 * ss)
    for k, lw in enumerate((360, 440, 300)):
        yy = iy + 70 + k * 30
        d.rounded_rectangle(S(sx0 + 30, yy, sx0 + 30 + lw, yy + 14), radius=6 * ss,
                            fill=(120, 120, 126, 255) if k else (40, 40, 44, 255))
    ph_img = big.resize((pw + 80, ph + 80), Image.BOX)
    rot = ph_img.rotate(-9, resample=Image.BICUBIC, expand=True)
    cx, cy = 1050, 800
    px, py = int(cx - rot.width / 2), int(cy - rot.height / 2)
    a = np.asarray(rot, F32)
    shadow = Image.fromarray(to_u8(a[..., 3])).filter(ImageFilter.GaussianBlur(22))
    darken(img, Mask(px + 24, py + 30, np.asarray(shadow, F32) / 255), 0.55)
    over(img, Layer(px, py, a[..., :3], a[..., 3] / 255))
    add_noise(img, 2, r, mono=True)
    save_jpg(img, 8, name, quality=90)


def m8_mockup_sleeve():
    """A square record sleeve on a shelf with the record peeking out."""
    name = "l23-mockup-sleeve.jpg"
    r = rng(name)
    W, H = 2400, 1600
    sy = 1340                                                     # shelf top
    img = np.empty((H, W, 3), F32)
    img[:sy] = vgrad(W, sy, [(0, "#3e4a57"), (1, "#56626e")])     # moody painted wall
    X, Y = coords(W, sy)
    pool = np.clip(1 - np.hypot((X - 950) / 1100, (Y - 500) / 800), 0, 1) ** 2 * 0.35
    img[:sy] = img[:sy] * (1 - pool[..., None]) + np.array(hexc("#c9d2da"), F32) * pool[..., None]
    img[sy:sy + 50] = vgrad(W, 50, [(0, "#b48a5f"), (1, "#8f6a47")])  # shelf lip
    img[sy + 50:] = vgrad(W, H - sy - 50, [(0, "#2a2724"), (1, "#1c1a18")])
    s0x, s0y, sz = 560, 400, 940                                  # sleeve square
    c = Canvas((s0x, s0y, s0x + sz, sy), ss=1, pad=80)
    c.rect(s0x + 30, s0y + 26, s0x + sz + 34, sy)
    darken(img, c.mask(blur=26), 0.5)
    # the record peeking out to the right
    rcx, rcy, rr = s0x + sz - 60 + 330, s0y + sz / 2 - 20, sz / 2 - 20
    c = Canvas((rcx - rr, rcy - rr, rcx + rr, rcy + rr), ss=3, pad=40)
    c.circle(rcx + 16, rcy + 18, rr)
    darken(img, c.mask(blur=16), 0.45)
    c = Canvas((rcx - rr, rcy - rr, rcx + rr, rcy + rr), ss=3)
    c.circle(rcx, rcy, rr)
    disc = c.mask()
    Xd, Yd = coords(W, H)
    rad = np.hypot(Xd - rcx, Yd - rcy)
    groove = 18 + 8 * (np.sin(rad / 3.1) > 0.6) + 22 * np.exp(-((np.arctan2(Yd - rcy, Xd - rcx) + 2.2) / 0.35) ** 2)
    paint(img, disc, np.dstack([groove] * 3).astype(F32))
    c = Canvas((rcx - 170, rcy - 170, rcx + 170, rcy + 170), ss=3)
    c.circle(rcx, rcy, 150)
    paint(img, c.mask(), "#c2553a")
    c = Canvas((rcx - 20, rcy - 20, rcx + 20, rcy + 20), ss=3)
    c.circle(rcx, rcy, 10)
    paint(img, c.mask(), "#1a1a1a")
    # the sleeve front: flat gray placeholder, slight paper edge
    img[s0y:s0y + sz, s0x:s0x + sz] = hexc("#d8d6d0")
    img[s0y + 4:s0y + sz - 4, s0x + 4:s0x + sz - 4] = hexc(_M8_GRAY)
    img[sy - 2:sy, s0x:s0x + sz] *= 0.7
    add_noise(img, 2, r, mono=True)
    save_jpg(img, 8, name, quality=90)


# ======================================================================================
# Registry and CLI
# ======================================================================================

MODULES = {
    1: [m1_high_contrast_landscape, m1_still_life_window_light, m1_bare_tree_sky,
        m1_new_sky, m1_grunge_texture, m1_fireworks_on_black, m1_curly_hair_portrait,
        m1_new_background, m1_hair_busy_background, m1_hair_cutout_reference],
    2: [m2_smooth_sky_16bit, m2_histogram_drills, m2_lagoon_adobergb, m2_lagoon_untagged,
        m2_portrait_studio, m2_pier_dusk, m2_grade_test_chart, m2_fallback_lut,
        m2_companion_portrait, m2_match_set, m2_neon_proof],
    3: [m3_portrait_retouch, m3_beauty_closeup, m3_candid_distance, m3_portrait_clean_flat,
        m3_apple_flat, m3_portrait_sculpted, m3_flaw_map, m3_light_map],
    4: [m4_plaza_background, m4_figure_cutout, m4_product_box_cutout, m4_horizon_sheet,
        m4_horizon_answers, m4_plaza_answer_overlay, m4_light_hard, m4_light_overcast,
        m4_glossy_floor, m4_far_clocktower, m4_depth_bands, m4_key_visual_reference],
    5: [m5_layout_copy, m5_ransom_note, m5_system_layout_instructor, m5_mockup_poster_wall,
        m5_mockup_tote_bag, m5_art_a_sunrise, m5_art_b_geometric, m5_art_c_typographic,
        m5_art_d_landscape, m5_logo_v1, m5_logo_v2, m5_key_art, m5_background_light,
        m5_background_dark, m5_campaign_copy, m5_safe_zones_story, m5_safe_zones_banner,
        m5_campaign_reference_instructor],
    6: [m6_cramped_scene, m6_pasted_subject, m6_cramped_composite_preview,
        m6_three_distractions, m6_delivery_inputs, m6_watermark, m6_person_photos,
        m6_card_background, m6_sale_badge, m6_vip_ribbon, m6_cards_csv, m6_cards_vip_csv,
        m6_cards_broken_csv, m6_card_reference, m6_resize_script],
    7: [m7_panorama, m7_hdr_bracket, m7_focus_stack, m7_anim_pieces, m7_cinemagraph],
    8: [m8_vague_brief, m8_vague_brief_fixed, m8_brief_template, m8_backup_briefs,
        m8_case_study_outline, m8_keyart_plate, m8_keyart_figure, m8_brand_logo,
        m8_product, m8_product_surface, m8_mockup_wall, m8_mockup_phone, m8_mockup_sleeve],
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--module", type=int, action="append", choices=sorted(MODULES),
                    help="build only this module (repeat for several)")
    args = ap.parse_args(argv)
    for mod in (args.module or sorted(MODULES)):
        print(f"Module {mod}:")
        for fn in MODULES[mod]:
            fn()
    total = sum(p.stat().st_size for p in WRITTEN)
    print(f"{len(WRITTEN)} files, {total / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
