#!/usr/bin/env python3
"""
DW SHIRT (@dw_shirt) — 365-Day Automated Luxury Creative Ad Factory for Instagram ($0)
Obsidian & Brushed Champagne Gold • Zero Catalog • 365 Unique Creative Ads (Full Year)
10 distinct Poster layouts + 8 distinct Reel cinema engines + 23 Studio Scenes + Custom Trend Mode.
"""
import os
import sys
import json
import time
import glob
import math
import wave
import argparse
import subprocess
from datetime import datetime, timezone

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, features
import imageio_ffmpeg

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
SCENES_DIR = os.path.join(ASSETS, "scenes")
FONTS_DIR = os.path.join(ASSETS, "fonts")
LOGO_PATH = os.path.join(ASSETS, "logo", "DW-Shirt-Gold-Logo.png")
BANK_PATH = os.path.join(ROOT, "ad_bank.json")
STATE_PATH = os.path.join(ROOT, "state", "history.json")
PUB_DIR = os.path.join(ROOT, "published")
PENDING_PATH = os.path.join(PUB_DIR, "pending.json")

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
HAS_RAQM = bool(features.check("raqm"))

OBSIDIAN = (9, 10, 12)
OBSIDIAN_CARD = (17, 19, 24)
GOLD = (224, 188, 118)
GOLD_BRIGHT = (244, 218, 158)
GOLD_DIM = (158, 130, 80)
WHITE = (248, 246, 242)
MUTED = (186, 182, 174)


# ==============================================================================
# TYPOGRAPHY & NATIVE HARFBUZZ ARABIC RENDERING
# ==============================================================================
def font_ar(sz: int, extra_bold: bool = True):
    fn = "Tajawal-ExtraBold.ttf" if extra_bold else "Tajawal-Bold.ttf"
    return ImageFont.truetype(os.path.join(FONTS_DIR, fn), sz)


def font_en(name: str, sz: int, weight: int = 600):
    f = ImageFont.truetype(os.path.join(FONTS_DIR, name), sz)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def _has_arabic(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def _shape_ar(text: str):
    if not _has_arabic(text):
        return text, {}
    if HAS_RAQM:
        return text, {"direction": "rtl", "language": "ar"}
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text)), {}


def fit_ar(text: str, max_w: int, start_sz: int, extra_bold: bool = True):
    shaped, kw = _shape_ar(text)
    sz = start_sz
    while sz >= 18:
        f = font_ar(sz, extra_bold)
        bb = f.getbbox(shaped, **kw)
        if (bb[2] - bb[0]) <= max_w:
            return f, shaped, kw
        sz -= 2
    return font_ar(18, extra_bold), shaped, kw


def draw_ar_center(d, cx: int, cy: int, text: str, max_w: int, start_sz: int, fill, extra_bold=True, shadow=True):
    f, shaped, kw = fit_ar(text, max_w, start_sz, extra_bold)
    bb = d.textbbox((0, 0), shaped, font=f, **kw)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x = cx - tw // 2 - bb[0]
    y = cy - th // 2 - bb[1]
    if shadow:
        a = fill[3] if len(fill) == 4 else 255
        d.text((x, y + 4), shaped, font=f, fill=(0, 0, 0, int(a * 0.78)), **kw)
    d.text((x, y), shaped, font=f, fill=fill, **kw)
    return tw, th


def draw_ar_right(d, rx: int, cy: int, text: str, max_w: int, start_sz: int, fill, extra_bold=True, shadow=True):
    f, shaped, kw = fit_ar(text, max_w, start_sz, extra_bold)
    bb = d.textbbox((0, 0), shaped, font=f, **kw)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x = rx - tw - bb[0]
    y = cy - th // 2 - bb[1]
    if shadow:
        a = fill[3] if len(fill) == 4 else 255
        d.text((x, y + 3), shaped, font=f, fill=(0, 0, 0, int(a * 0.72)), **kw)
    d.text((x, y), shaped, font=f, fill=fill, **kw)
    return tw, th


def draw_en_center(d, cx: int, cy: int, text: str, f, fill):
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw // 2 - bb[0], cy - th // 2 - bb[1]), text, font=f, fill=fill)


# ==============================================================================
# METALLIC GOLD DW SHIRT LOGO EXTRACTION (BAND-LOCKED, ZERO CLIPPING)
# ==============================================================================
def extract_gold_logo():
    raw = Image.open(LOGO_PATH).convert("RGBA")
    arr = np.array(raw).astype(np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    warm = (r - b)
    signal = np.maximum(lum - 28.0, warm * 1.45)
    alpha = np.clip((signal - 14.0) / 52.0, 0.0, 1.0) * 255.0
    alpha[alpha < 18] = 0.0
    out = np.zeros_like(arr, dtype=np.uint8)
    out[:, :, 0] = np.clip(r * 1.06, 0, 255).astype(np.uint8)
    out[:, :, 1] = np.clip(g * 1.04, 0, 255).astype(np.uint8)
    out[:, :, 2] = np.clip(b * 1.00, 0, 255).astype(np.uint8)
    out[:, :, 3] = alpha.astype(np.uint8)
    rgba = Image.fromarray(out, "RGBA")

    rs = (out[:, :, 3] > 35).sum(axis=1)
    bands = []
    in_b, st = False, 0
    for y in range(len(rs)):
        if rs[y] > 5 and not in_b:
            st, in_b = y, True
        elif rs[y] <= 5 and in_b:
            bands.append((st, y))
            in_b = False
    if in_b:
        bands.append((st, len(rs)))

    y_top, y_bot = bands[0][0], bands[-1][1]
    full_strip = rgba.crop((0, max(0, y_top - 6), rgba.size[0], min(rgba.size[1], y_bot + 6)))
    full_lockup = full_strip.crop(full_strip.getbbox())

    ey0, ey1 = bands[0]
    em_strip = rgba.crop((0, max(0, ey0 - 4), rgba.size[0], min(rgba.size[1], ey1 + 4)))
    emblem = em_strip.crop(em_strip.getbbox())
    return full_lockup, emblem


FULL_LOGO, EMBLEM = extract_gold_logo()


def paste_rgba(canvas: Image.Image, overlay: Image.Image, x: int, y: int, target_h: int, opacity: float = 1.0):
    ow, oh = overlay.size
    nw = max(1, int(ow * (target_h / oh)))
    im = overlay.resize((nw, target_h), Image.Resampling.LANCZOS)
    if opacity < 0.999:
        a = im.split()[3].point(lambda v: int(v * opacity))
        im.putalpha(a)
    canvas.paste(im, (x, y), im)
    return nw


def paste_corner_emblem(canvas: Image.Image, pos: str = "left", target_h: int = 70, pad_x: int = 62, pad_y: int = 54, opacity: float = 0.95):
    ow, oh = EMBLEM.size
    nw = max(1, int(ow * (target_h / oh)))
    x = pad_x if pos == "left" else (canvas.size[0] - pad_x - nw)
    paste_rgba(canvas, EMBLEM, x, pad_y, target_h=target_h, opacity=opacity)


def apply_fade(im: Image.Image, start_ratio: float = 0.56, strength: float = 0.97, top_strength: float = 0.28):
    w, h = im.size
    ys = np.linspace(0, 1, h)[:, None]
    alpha_bot = np.clip((ys - start_ratio) / max(0.01, (1.0 - start_ratio)), 0, 1) ** 1.35 * strength
    alpha_top = np.clip((0.18 - ys) / 0.18, 0, 1) ** 1.6 * top_strength
    alpha = np.clip(np.maximum(alpha_bot, alpha_top), 0, 1)
    arr = np.array(im).astype(np.float32)
    bg = np.array(OBSIDIAN, dtype=np.float32)[None, None, :]
    out = arr * (1.0 - alpha[:, :, None]) + bg * alpha[:, :, None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def draw_thin_brackets(d, cx: int, cy: int, bw: int, bh: int, arm: int = 24, color=(238, 205, 134, 210), width: int = 2):
    x1, y1, x2, y2 = cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2
    for seg in [
        (x1, y1, x1 + arm, y1), (x1, y1, x1, y1 + arm),
        (x2 - arm, y1, x2, y1), (x2, y1, x2, y1 + arm),
        (x1, y2 - arm, x1, y2), (x1, y2, x1 + arm, y2),
        (x2, y2 - arm, x2, y2), (x2 - arm, y2, x2, y2),
    ]:
        d.line(seg, fill=color, width=width)


def draw_minimal_footer(canvas: Image.Image, brand: dict, y_line: int = 1254, pad: int = 76):
    W, H = canvas.size
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.line((pad, y_line, W - pad, y_line), fill=(224, 188, 118, 72), width=1)
    f_en = font_en("Outfit-Var.ttf", 21, 500)
    d.text((pad, y_line + 24), f"{brand['handle']}   •   {brand['phone']}", font=f_en, fill=(196, 190, 180, 235))
    ar_txt = brand["location"]
    f_ar, shaped, kw = fit_ar(ar_txt, 460, 23, extra_bold=False)
    bb = d.textbbox((0, 0), shaped, font=f_ar, **kw)
    d.text((W - pad - (bb[2] - bb[0]) - bb[0], y_line + 20 - bb[1]), shaped, font=f_ar, fill=(224, 188, 118, 240), **kw)
    return Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")


def make_obsidian_spotlight(W: int, H: int, cx_r: float = 0.5, cy_r: float = 0.42, glow_r: float = 42.0):
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.sqrt(((xx - W * cx_r) / (W * 0.58)) ** 2 + ((yy - H * cy_r) / (H * 0.36)) ** 2)
    glow = np.clip(1.0 - dist, 0, 1) ** 2.4
    arr = np.zeros((H, W, 3), dtype=np.float32)
    arr[:, :, 0] = OBSIDIAN[0] + glow * glow_r
    arr[:, :, 1] = OBSIDIAN[1] + glow * (glow_r * 0.77)
    arr[:, :, 2] = OBSIDIAN[2] + glow * (glow_r * 0.36)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def load_scene(filename: str) -> Image.Image:
    return Image.open(os.path.join(SCENES_DIR, filename)).convert("RGB")


def cover_crop(im: Image.Image, tw: int, th: int, zoom: float = 1.0, pan_y: float = 0.0):
    sw, sh = im.size
    scale = max(tw / sw, th / sh) * zoom
    nw, nh = int(sw * scale), int(sh * scale)
    r = im.resize((nw, nh), Image.Resampling.BILINEAR)
    x0 = (nw - tw) // 2
    y0 = max(0, min(nh - th, int((nh - th) // 2 + pan_y)))
    return r.crop((x0, y0, x0 + tw, y0 + th))


# ==============================================================================
# PART 1: 10 DISTINCT CREATIVE AD POSTER RENDERERS (1080x1350)
# ==============================================================================
def render_poster(ad: dict, brand: dict, out_path: str):
    W, H = 1080, 1350
    style = ad.get("poster_style", "standard")
    pos = ad.get("emblem_pos", "left")

    if style == "apple_manifesto":
        canvas = make_obsidian_spotlight(W, H, cx_r=0.5, cy_r=0.40, glow_r=38.0)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.rectangle((46, 46, W - 46, H - 46), outline=(224, 188, 118, 55), width=1)
        lw = int(FULL_LOGO.size[0] * (230 / FULL_LOGO.size[1]))
        paste_rgba(canvas, FULL_LOGO, (W - lw) // 2, 165, target_h=230, opacity=0.96)
        d.line((W // 2 - 140, 465, W // 2 + 140, 465), fill=(224, 188, 118, 115), width=1)
        draw_en_center(d, W // 2, 520, ad.get("kicker", "DW SHIRT  •  CUSTOM PRINT STUDIO"), font_en("Outfit-Var.ttf", 22, 600), (224, 188, 118, 220))
        draw_ar_center(d, W // 2, 690, ad["headline"], 900, 82, WHITE, extra_bold=True)
        draw_ar_center(d, W // 2, 810, ad["punchline"], 900, 92, GOLD, extra_bold=True)
        draw_ar_center(d, W // 2, 955, ad["subline"], 860, 30, MUTED, extra_bold=False)
        d.rounded_rectangle((W // 2 - 270, 1055, W // 2 + 270, 1135), radius=40, fill=(224, 188, 118, 28), outline=(224, 188, 118, 220), width=2)
        draw_ar_center(d, W // 2, 1095, brand["cta_reel"], 500, 32, GOLD_BRIGHT, extra_bold=True, shadow=False)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")
        canvas = draw_minimal_footer(canvas, brand, y_line=1230, pad=84)

    elif style == "dm_mockup":
        bg = load_scene(ad["scene"]).resize((W, H), Image.Resampling.LANCZOS)
        bg = apply_fade(bg, start_ratio=0.18, strength=0.90, top_strength=0.60)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        cx1, cy1, cx2, cy2 = 108, 200, W - 108, 760
        d.rounded_rectangle((cx1, cy1, cx2, cy2), radius=34, fill=(13, 15, 20, 232), outline=(224, 188, 118, 130), width=2)
        d.line((cx1 + 36, cy1 + 88, cx2 - 36, cy1 + 88), fill=(224, 188, 118, 55), width=1)
        d.text((cx1 + 42, cy1 + 30), "Instagram Direct  •  @dw_shirt", font=font_en("Outfit-Var.ttf", 22, 600), fill=(224, 188, 118, 220))
        d.ellipse((cx2 - 58, cy1 + 36, cx2 - 42, cy1 + 52), fill=(86, 212, 132, 235))

        d.rounded_rectangle((cx1 + 110, cy1 + 132, cx2 - 38, cy1 + 292), radius=26, fill=(32, 36, 46, 245), outline=(255, 255, 255, 35), width=1)
        draw_ar_right(d, cx2 - 72, cy1 + 186, ad.get("dm_q", "سلام، نقدر نطبع فكرة من راسي عندكم؟"), 575, 30, WHITE, extra_bold=False, shadow=False)
        draw_ar_right(d, cx2 - 72, cy1 + 244, "زبون • الآن", 300, 21, (150, 154, 166, 210), extra_bold=False, shadow=False)

        d.rounded_rectangle((cx1 + 38, cy1 + 332, cx2 - 104, cy1 + 514), radius=26, fill=(224, 188, 118, 36), outline=(224, 188, 118, 185), width=2)
        draw_ar_right(d, cx2 - 138, cy1 + 394, ad.get("dm_a", "أكيد! ابعتها فالخاص، نوجدولك ماكيت مجانية تشوفها قبل الطباعة."), 575, 30, GOLD_BRIGHT, extra_bold=True, shadow=False)
        draw_ar_right(d, cx2 - 138, cy1 + 462, "DW SHIRT  •  رد فوري", 360, 21, (224, 188, 118, 220), extra_bold=False, shadow=False)

        draw_ar_center(d, W // 2, 955, ad["headline"], 920, 64, WHITE, extra_bold=True)
        draw_ar_center(d, W // 2, 1046, ad["punchline"], 920, 76, GOLD, extra_bold=True)
        draw_ar_center(d, W // 2, 1150, ad["subline"], 910, 28, MUTED, extra_bold=False)
        canvas = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
        paste_corner_emblem(canvas, pos=pos, target_h=68)
        canvas = draw_minimal_footer(canvas, brand)

    elif style == "woven_label":
        bg = load_scene(ad["scene"]).resize((W, H), Image.Resampling.LANCZOS)
        bg = apply_fade(bg, start_ratio=0.50, strength=0.97, top_strength=0.35)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        tx1, ty1, tx2, ty2 = W // 2 - 270, 230, W // 2 + 270, 690
        d.rounded_rectangle((tx1, ty1, tx2, ty2), radius=12, fill=(10, 11, 14, 240), outline=(224, 188, 118, 210), width=2)
        d.rounded_rectangle((tx1 + 14, ty1 + 14, tx2 - 14, ty2 - 14), radius=8, fill=None, outline=(224, 188, 118, 80), width=1)
        d.ellipse((W // 2 - 14, ty1 + 30, W // 2 + 14, ty1 + 58), fill=(26, 24, 22, 255), outline=(224, 188, 118, 220), width=2)
        draw_en_center(d, W // 2, ty1 + 298, ad.get("tag_code", "EDITION  01 / 01"), font_en("Syne-Var.ttf", 28, 800), GOLD_BRIGHT)
        d.line((tx1 + 70, ty1 + 336, tx2 - 70, ty1 + 336), fill=(224, 188, 118, 95), width=1)
        draw_ar_center(d, W // 2, ty1 + 388, ad.get("tag_ar", "صُنع خصيصاً لفكرتك أنت"), 460, 30, WHITE, extra_bold=True, shadow=False)

        draw_ar_center(d, W // 2, 975, ad["headline"], 920, 64, WHITE, extra_bold=True)
        draw_ar_center(d, W // 2, 1062, ad["punchline"], 920, 78, GOLD, extra_bold=True)
        draw_ar_center(d, W // 2, 1164, ad["subline"], 910, 28, MUTED, extra_bold=False)
        canvas = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
        ew = int(EMBLEM.size[0] * (135 / EMBLEM.size[1]))
        paste_rgba(canvas, EMBLEM, (W - ew) // 2, ty1 + 98, target_h=135, opacity=0.96)
        canvas = draw_minimal_footer(canvas, brand)

    elif style == "split_editorial":
        # Vogue / Balenciaga Luxury Split Editorial: Top 56% Crisp Photography | Gold Hairline | Bottom 44% Obsidian Typography Block
        split_y = 756
        top_im = cover_crop(load_scene(ad["scene"]), W, split_y, zoom=1.02)
        canvas = Image.new("RGB", (W, H), OBSIDIAN)
        canvas.paste(top_im, (0, 0))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.line((0, split_y, W, split_y), fill=(224, 188, 118, 210), width=3)
        # Centered diamond emblem divider on gold split line!
        draw_en_center(d, W // 2, split_y + 62, ad.get("kicker", "DW SHIRT  •  CUSTOM PRINT"), font_en("Outfit-Var.ttf", 20, 600), (224, 188, 118, 210))
        draw_ar_center(d, W // 2, split_y + 162, ad["headline"], 930, 64, WHITE, extra_bold=True, shadow=False)
        draw_ar_center(d, W // 2, split_y + 252, ad["punchline"], 930, 76, GOLD, extra_bold=True, shadow=False)
        draw_ar_center(d, W // 2, split_y + 356, ad["subline"], 900, 28, MUTED, extra_bold=False, shadow=False)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")
        paste_corner_emblem(canvas, pos=pos, target_h=68)
        canvas = draw_minimal_footer(canvas, brand, y_line=1254)

    elif style == "quote_card_gold":
        # High-Fashion Minimalist Quote Poster on Deep Moody Textured Fabric!
        bg = load_scene(ad["scene"]).resize((W, H), Image.Resampling.LANCZOS)
        bg = apply_fade(bg, start_ratio=0.04, strength=0.88, top_strength=0.72)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.rectangle((56, 56, W - 56, H - 56), outline=(224, 188, 118, 75), width=1)
        # Giant minimalist decorative quote mark in clean spacing above headline
        d.text((W // 2 - 48, 250), "“", font=font_en("Syne-Var.ttf", 175, 800), fill=(224, 188, 118, 115))
        draw_ar_center(d, W // 2, 540, ad["headline"], 880, 74, WHITE, extra_bold=True)
        draw_ar_center(d, W // 2, 650, ad["punchline"], 880, 84, GOLD, extra_bold=True)
        d.line((W // 2 - 120, 760, W // 2 + 120, 760), fill=(224, 188, 118, 150), width=2)
        draw_ar_center(d, W // 2, 842, ad["subline"], 840, 31, MUTED, extra_bold=False)
        # Sleek gold CTA outline
        d.rounded_rectangle((W // 2 - 260, 960, W // 2 + 260, 1036), radius=38, fill=(224, 188, 118, 26), outline=(224, 188, 118, 200), width=2)
        draw_ar_center(d, W // 2, 998, brand["cta_reel"], 460, 30, GOLD_BRIGHT, extra_bold=True, shadow=False)
        canvas = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
        ew = int(EMBLEM.size[0] * (88 / EMBLEM.size[1]))
        paste_rgba(canvas, EMBLEM, (W - ew) // 2, 112, target_h=88, opacity=0.95)
        canvas = draw_minimal_footer(canvas, brand, y_line=1216, pad=92)

    elif style == "checklist_minimal":
        # Ultra-clean 3-step luxury timeline over moody obsidian studio visual!
        bg = load_scene(ad["scene"]).resize((W, H), Image.Resampling.LANCZOS)
        bg = apply_fade(bg, start_ratio=0.30, strength=0.94, top_strength=0.35)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        draw_ar_center(d, W // 2, 540, ad["headline"], 920, 62, WHITE, extra_bold=True)
        draw_ar_center(d, W // 2, 624, ad["punchline"], 920, 72, GOLD, extra_bold=True)

        steps = ad.get("steps", [
            "ابعتلنا فكرتك ولا اللوغو في الخاص (DM)",
            "نوجدولك ماكيت مجانية تشوفها قبل الطباعة",
            "نطبعوهالك فليكس HD وتوصلك في 58 ولاية",
        ])
        y_start = 740
        for idx, stxt in enumerate(steps[:3]):
            yy = y_start + idx * 124
            d.rounded_rectangle((96, yy, W - 96, yy + 94), radius=18, fill=(14, 16, 21, 225), outline=(224, 188, 118, 110), width=1)
            # Crisp gold step number circle on the right (RTL natural reading!)
            d.rounded_rectangle((W - 186, yy + 20, W - 118, yy + 74), radius=12, fill=(224, 188, 118, 240))
            draw_en_center(d, W - 152, yy + 47, f"0{idx + 1}", font_en("Syne-Var.ttf", 24, 800), OBSIDIAN)
            draw_ar_right(d, W - 216, yy + 47, stxt, 640, 30, WHITE, extra_bold=True, shadow=False)

        draw_ar_center(d, W // 2, 1170, ad["subline"], 900, 27, GOLD_BRIGHT, extra_bold=False)
        canvas = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
        paste_corner_emblem(canvas, pos=pos, target_h=70)
        canvas = draw_minimal_footer(canvas, brand, y_line=1254)

    elif style == "side_vertical_bar":
        # Architectural Right-Aligned Editorial Poster with Brushed-Gold Vertical Accent Bar!
        bg = load_scene(ad["scene"]).resize((W, H), Image.Resampling.LANCZOS)
        bg = apply_fade(bg, start_ratio=0.50, strength=0.97, top_strength=0.28)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # Sleek gold vertical architectural rule on right side of bottom text block
        bar_x = W - 82
        d.rectangle((bar_x, 916, bar_x + 5, 1185), fill=(224, 188, 118, 235))
        draw_ar_right(d, bar_x - 32, 956, ad["headline"], 860, 62, WHITE, extra_bold=True)
        draw_ar_right(d, bar_x - 32, 1044, ad["punchline"], 860, 76, GOLD, extra_bold=True)
        draw_ar_right(d, bar_x - 32, 1142, ad["subline"], 860, 28, MUTED, extra_bold=False)
        canvas = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
        paste_corner_emblem(canvas, pos=pos, target_h=70)
        canvas = draw_minimal_footer(canvas, brand, y_line=1254)

    else:
        # "standard", "bracket_center", "b2b_bracket"
        im = load_scene(ad["scene"]).resize((W, H), Image.Resampling.LANCZOS)
        im = apply_fade(im, start_ratio=0.55, strength=0.98, top_strength=0.28)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        if style == "bracket_center":
            bx, by = int(W * 0.499), int(H * 0.361)
            draw_ar_center(d, bx, by - 14, ad.get("bracket_top", "فكرتك"), 165, 36, GOLD_BRIGHT, extra_bold=True)
            draw_ar_center(d, bx, by + 26, ad.get("bracket_bot", "هنا"), 165, 34, (245, 240, 232, 235), extra_bold=False)
        elif style == "b2b_bracket":
            ax, ay = 340, 705
            draw_thin_brackets(d, ax, ay, 182, 112, arm=20, color=(238, 205, 134, 195), width=2)
            draw_ar_center(d, ax, ay, ad.get("bracket_text", "لوقو محلك هنا"), 158, 23, GOLD_BRIGHT, extra_bold=True)

        draw_ar_center(d, W // 2, 990, ad["headline"], 930, 64, WHITE, extra_bold=True)
        draw_ar_center(d, W // 2, 1076, ad["punchline"], 930, 78, GOLD, extra_bold=True)
        draw_ar_center(d, W // 2, 1168, ad["subline"], 920, 28, MUTED, extra_bold=False)

        canvas = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
        paste_corner_emblem(canvas, pos=pos, target_h=70)
        canvas = draw_minimal_footer(canvas, brand)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path, "JPEG", quality=93, optimize=True)


# ==============================================================================
# PART 2: UNIQUE CINEMATIC AUDIO GENERATOR (8 STYLE-ADAPTIVE PROFILES!)
# ==============================================================================
def synth_commercial_audio(wav_path: str, dur: float, style: str, cut_times: list, tick_times: list = None, sr: int = 44100):
    n = int(dur * sr)
    t = np.linspace(0, dur, n, endpoint=False)
    sig = np.zeros(n, dtype=np.float64)

    roots = {
        "cinema_3beat":      (73.42, 110.00, 146.83, 0.75),
        "dm_to_reality":     (65.41,  98.00, 130.81, 0.70),
        "apple_kinetic":     (82.41, 123.47, 164.81, 0.60),
        "bracket_morph":     (69.30, 103.83, 138.59, 0.72),
        "split_contrast":    (77.78, 116.54, 155.56, 0.65),
        "spotlight_macro":   (61.74,  92.50, 123.47, 0.82),
        "flash_manifesto":   (87.31, 130.81, 174.61, 0.55),
        "zoom_reveal_quote": (58.27,  87.31, 116.54, 0.78),
    }
    f1, f2, f3, beat_step = roots.get(style, roots["cinema_3beat"])

    pad = (
        0.16 * np.sin(2 * np.pi * f1 * t) +
        0.09 * np.sin(2 * np.pi * f2 * t) +
        0.05 * np.sin(2 * np.pi * f3 * t + 0.4) +
        0.03 * np.sin(2 * np.pi * (f2 * 2) * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t))
    )
    env = np.minimum(1.0, t / 0.5) * np.minimum(1.0, (dur - t) / 1.0)
    sig += pad * env

    k = 0
    while k * beat_step < dur - 0.5:
        bt = k * beat_step
        i0 = int(bt * sr)
        blen = min(int(0.26 * sr), n - i0)
        tt = np.linspace(0, blen / sr, blen)
        fk = 48.0 + 78.0 * np.exp(-tt * 28.0)
        sig[i0:i0 + blen] += 0.27 * np.sin(2 * np.pi * np.cumsum(fk) / sr) * np.exp(-tt * 11.5)
        k += 1

    for ct in cut_times:
        if 0 < ct < dur - 0.1:
            i0 = int(ct * sr)
            clen = min(int(0.8 * sr), n - i0)
            tt = np.linspace(0, clen / sr, clen)
            shimmer = (
                0.13 * np.sin(2 * np.pi * (f3 * 4) * tt) +
                0.08 * np.sin(2 * np.pi * (f2 * 8) * tt)
            ) * np.exp(-tt * 4.6)
            boom = 0.26 * np.sin(2 * np.pi * 54.0 * tt) * np.exp(-tt * 5.8)
            sig[i0:i0 + clen] += shimmer + boom

    for wt in (tick_times or []):
        if 0 < wt < dur - 0.05:
            i0 = int(wt * sr)
            wlen = min(int(0.14 * sr), n - i0)
            tt = np.linspace(0, wlen / sr, wlen)
            sig[i0:i0 + wlen] += 0.09 * np.sin(2 * np.pi * 1318.5 * tt) * np.exp(-tt * 22.0)

    sig = np.tanh(sig * 1.15) * 0.85
    pcm = (sig * 32767).astype(np.int16)
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


# ==============================================================================
# PART 3: 8 DISTINCT LUXURY CREATIVE AD REEL ENGINES (1080x1920, 30fps)
# ==============================================================================
def ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1.0 - (1.0 - x) ** 3


def fit_blank_hoodie_916(im: Image.Image, tw: int, th: int, zoom: float = 1.0):
    canvas = Image.new("RGB", (tw, th), OBSIDIAN)
    sw, sh = im.size
    scale = (tw / sw) * zoom
    nw, nh = int(sw * scale), int(sh * scale)
    r = im.resize((nw, nh), Image.Resampling.BILINEAR)
    x0 = (tw - nw) // 2
    y0 = int((th - nh) // 2 - 140)
    arr = np.array(r).astype(np.float32)
    ys = np.linspace(0, 1, nh)[:, None]
    m = np.minimum(np.clip(ys / 0.10, 0, 1), np.clip((1.0 - ys) / 0.18, 0, 1))[:, :, None]
    bg = np.array(OBSIDIAN, dtype=np.float32)[None, None, :]
    feathered = Image.fromarray(np.clip(arr * m + bg * (1.0 - m), 0, 255).astype(np.uint8))
    canvas.paste(feathered, (x0, y0))
    return canvas, int(x0 + nw * 0.499), int(y0 + nh * 0.361)


def render_brand_outro_frame(end_bg: Image.Image, lt: float, ad: dict, brand: dict):
    W, H = end_bg.size
    p = ease_out(min(1.0, lt / 0.85))
    frame = end_bg.copy()
    logo_h = int(340 + 40 * p)
    lw = int(FULL_LOGO.size[0] * (logo_h / FULL_LOGO.size[1]))
    paste_rgba(frame, FULL_LOGO, (W - lw) // 2, 575 - int(18 * p), target_h=logo_h, opacity=min(1.0, lt / 0.45))

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = int(255 * ease_out(max(0.0, (lt - 0.30) / 0.55)))
    if a > 5:
        d.line((W // 2 - 220, 1085, W // 2 + 220, 1085), fill=(224, 188, 118, int(a * 0.55)), width=2)
        draw_ar_center(d, W // 2, 1175, ad.get("outro_line", "فكرتك. طبعتك. ستيلك."), 900, 56, (248, 246, 242, a), extra_bold=True)
        bw, bh = 640, 92
        cx1, cy1 = W // 2 - bw // 2, 1275
        d.rounded_rectangle((cx1, cy1, cx1 + bw, cy1 + bh), radius=46, fill=(224, 188, 118, int(a * 0.12)), outline=(224, 188, 118, a), width=2)
        draw_ar_center(d, W // 2, cy1 + bh // 2, brand["cta_reel"], 580, 38, (244, 218, 158, a), extra_bold=True, shadow=False)
        draw_ar_center(d, W // 2, 1445, "قسنطينة • توصيل متوفر لـ 58 ولاية", 860, 30, (195, 190, 180, a), extra_bold=False)
        draw_en_center(d, W // 2, 1515, f"{brand['handle']}   •   {brand['phone']}", font_en("Outfit-Var.ttf", 28, 600), (224, 188, 118, a))
    return Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")


def render_reel(ad: dict, brand: dict, out_path: str):
    W, H, FPS = 1080, 1920, 30
    style = ad.get("reel_style", "cinema_3beat")
    DUR = 13.5 if style in ("cinema_3beat", "dm_to_reality") else 12.0
    total_frames = int(FPS * DUR)
    end_bg = make_obsidian_spotlight(W, H, cx_r=0.5, cy_r=0.42, glow_r=44.0)
    scene_names = ad.get("scenes", ["s01_blank_canvas.jpg"])
    scenes = [load_scene(s) for s in scene_names]

    cut_map = {
        "cinema_3beat":      ([3.8, 7.8, 10.5],     [4.5, 5.3, 6.1, 6.9]),
        "dm_to_reality":     ([6.2, 10.5],          [0.6, 2.0, 3.4, 4.8]),
        "apple_kinetic":     ([1.8, 3.6, 5.4, 9.0], [1.8, 3.6]),
        "bracket_morph":     ([4.4, 9.0],           [1.0, 2.0, 3.0, 4.0]),
        "split_contrast":    ([4.5, 9.0],           [2.2, 4.5]),
        "spotlight_macro":   ([4.5, 9.0],           [4.5]),
        "flash_manifesto":   ([1.4, 2.8, 4.2, 5.6, 9.0], [1.4, 2.8, 4.2]),
        "zoom_reveal_quote": ([4.2, 9.0],           [4.2]),
    }
    cuts, ticks = cut_map.get(style, ([4.5, 9.0], []))
    wav_path = "/tmp/dw_factory_audio.wav"
    synth_commercial_audio(wav_path, dur=DUR, style=style, cut_times=cuts, tick_times=ticks)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [
        FFMPEG, "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
        out_path
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    for fi in range(total_frames):
        t = fi / FPS

        if style == "cinema_3beat":
            if t < 3.8:
                p = t / 3.8
                frame = cover_crop(scenes[0], W, H, zoom=1.02 + 0.10 * ease_out(p), pan_y=-40 + 40 * p)
                frame = apply_fade(frame, start_ratio=0.58, strength=0.97, top_strength=0.35)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                a1 = int(255 * ease_out(min(1.0, t / 0.55)))
                a2 = int(255 * ease_out(max(0.0, (t - 0.55) / 0.55)))
                draw_ar_center(d, W // 2, 1390, ad["s1_top"], 940, 62, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1484, ad["s1_gold"], 940, 76, (224, 188, 118, a2))
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            elif t < 7.8:
                lt = t - 3.8
                is_blank = (scene_names[min(1, len(scene_names) - 1)] == "s01_blank_canvas.jpg")
                s_idx = min(1, len(scenes) - 1)
                if is_blank:
                    frame, bx, by = fit_blank_hoodie_916(scenes[s_idx], W, H, zoom=1.0 + 0.08 * ease_out(lt / 4.0))
                else:
                    frame = cover_crop(scenes[s_idx], W, H, zoom=1.03 + 0.09 * ease_out(lt / 4.0))
                    frame = apply_fade(frame, start_ratio=0.55, strength=0.97, top_strength=0.30)
                    bx, by = W // 2, 760
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                words = ad.get("bracket_words", ["فكرتك هنا"])
                slot = min(len(words) - 1, int(lt / (4.0 / len(words))))
                if not is_blank:
                    draw_thin_brackets(d, bx, by, 300, 150, arm=28, color=(238, 205, 134, 210), width=3)
                draw_ar_center(d, bx, by, words[slot], 240 if not is_blank else 175, 38, GOLD_BRIGHT)
                a1 = int(255 * ease_out(min(1.0, lt / 0.5)))
                a2 = int(255 * ease_out(max(0.0, (lt - 0.5) / 0.5)))
                a3 = int(255 * ease_out(max(0.0, (lt - 1.0) / 0.5)))
                draw_ar_center(d, W // 2, 1400, ad["s2_top"], 920, 64, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1496, ad["s2_gold"], 920, 84, (224, 188, 118, a2))
                if a3 > 5:
                    draw_ar_center(d, W // 2, 1602, ad["s2_sub"], 900, 32, (195, 190, 182, a3), extra_bold=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            elif t < 10.5:
                lt = t - 7.8
                s_idx = min(2, len(scenes) - 1)
                frame = cover_crop(scenes[s_idx], W, H, zoom=1.04 + 0.08 * ease_out(lt / 2.7), pan_y=-50 + 50 * (lt / 2.7))
                frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                ab = int(225 * ease_out(min(1.0, lt / 0.5)))
                draw_thin_brackets(d, 355, 920, 224, 130, arm=22, color=(238, 205, 134, ab), width=2)
                draw_ar_center(d, 355, 920, ad.get("s3_tag", "فكرتك هنا"), 192, 27, (244, 218, 158, ab))
                a1 = int(255 * ease_out(min(1.0, lt / 0.45)))
                a2 = int(255 * ease_out(max(0.0, (lt - 0.45) / 0.45)))
                draw_ar_center(d, W // 2, 1410, ad["s3_gold"], 940, 44, (224, 188, 118, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1498, ad["s3_top"], 940, 62, (248, 246, 242, a2))
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "right", 70, 68, 128)
            else:
                frame = render_brand_outro_frame(end_bg, t - 10.5, ad, brand)

        elif style == "dm_to_reality":
            if t < 6.2:
                frame = end_bg.copy()
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                cx1, cy1, cx2, cy2 = 84, 340, W - 84, 1520
                d.rounded_rectangle((cx1, cy1, cx2, cy2), radius=42, fill=(13, 15, 20, 238), outline=(224, 188, 118, 145), width=2)
                d.line((cx1 + 40, cy1 + 112, cx2 - 40, cy1 + 112), fill=(224, 188, 118, 60), width=1)
                d.text((cx1 + 48, cy1 + 42), "Instagram Direct   •   @dw_shirt", font=font_en("Outfit-Var.ttf", 25, 600), fill=(224, 188, 118, 235))
                d.ellipse((cx2 - 64, cy1 + 48, cx2 - 46, cy1 + 66), fill=(86, 212, 132, 240))
                msgs = [
                    (0.4, True,  ad["dm_user_1"],  cy1 + 180),
                    (1.8, False, ad["dm_brand_1"], cy1 + 410),
                    (3.2, True,  ad["dm_user_2"],  cy1 + 650),
                    (4.5, False, ad["dm_brand_2"], cy1 + 880),
                ]
                for start_t, is_user, txt, y0 in msgs:
                    if t >= start_t:
                        ap = ease_out(min(1.0, (t - start_t) / 0.45))
                        al = int(255 * ap)
                        dy = int(26 * (1.0 - ap))
                        if is_user:
                            d.rounded_rectangle((cx1 + 120, y0 + dy, cx2 - 40, y0 + 175 + dy), radius=28, fill=(32, 36, 46, int(245 * ap)), outline=(255, 255, 255, int(40 * ap)), width=1)
                            draw_ar_right(d, cx2 - 76, y0 + 88 + dy, txt, 610, 31, (248, 246, 242, al), extra_bold=False, shadow=False)
                        else:
                            d.rounded_rectangle((cx1 + 40, y0 + dy, cx2 - 110, y0 + 175 + dy), radius=28, fill=(224, 188, 118, int(40 * ap)), outline=(224, 188, 118, int(195 * ap)), width=2)
                            draw_ar_right(d, cx2 - 146, y0 + 88 + dy, txt, 610, 31, (244, 218, 158, al), extra_bold=True, shadow=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            elif t < 10.5:
                lt = t - 6.2
                frame = cover_crop(scenes[0], W, H, zoom=1.02 + 0.10 * ease_out(lt / 4.3), pan_y=-40 + 40 * (lt / 4.3))
                frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                a1 = int(255 * ease_out(min(1.0, lt / 0.5)))
                a2 = int(255 * ease_out(max(0.0, (lt - 0.5) / 0.5)))
                a3 = int(255 * ease_out(max(0.0, (lt - 1.0) / 0.5)))
                draw_ar_center(d, W // 2, 1395, ad["reveal_top"], 920, 66, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1492, ad["reveal_gold"], 920, 86, (224, 188, 118, a2))
                if a3 > 5:
                    draw_ar_center(d, W // 2, 1598, ad["reveal_sub"], 900, 31, (195, 190, 182, a3), extra_bold=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "right", 70, 68, 128)
            else:
                frame = render_brand_outro_frame(end_bg, t - 10.5, ad, brand)

        elif style == "apple_kinetic":
            if t < 5.4:
                frame = end_bg.copy()
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                if t < 1.8:
                    p = ease_out(min(1.0, t / 0.45))
                    draw_ar_center(d, W // 2, 950 + int(30 * (1 - p)), ad["beat1"], 920, 80, (248, 246, 242, int(255 * p)))
                    lw_bar = int(280 * p)
                    d.line((W // 2 - lw_bar, 1050, W // 2 + lw_bar, 1050), fill=(224, 188, 118, 180), width=3)
                elif t < 3.6:
                    lt = t - 1.8
                    p = ease_out(min(1.0, lt / 0.45))
                    draw_ar_center(d, W // 2, 950 + int(30 * (1 - p)), ad["beat2"], 920, 80, (248, 246, 242, int(255 * p)))
                    lw_bar = int(340 * p)
                    d.line((W // 2 - lw_bar, 1050, W // 2 + lw_bar, 1050), fill=(224, 188, 118, 180), width=3)
                else:
                    lt = t - 3.6
                    p = ease_out(min(1.0, lt / 0.45))
                    draw_ar_center(d, W // 2, 950 + int(30 * (1 - p)), ad["beat3"], 940, 88, (224, 188, 118, int(255 * p)))
                    draw_thin_brackets(d, W // 2, 950, int(860 * p), 240, arm=36, color=(224, 188, 118, int(180 * p)), width=2)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            elif t < 9.0:
                lt = t - 5.4
                is_blank = (scene_names[0] == "s01_blank_canvas.jpg")
                if is_blank:
                    frame, bx, by = fit_blank_hoodie_916(scenes[0], W, H, zoom=1.0 + 0.08 * ease_out(lt / 3.6))
                else:
                    frame = cover_crop(scenes[0], W, H, zoom=1.03 + 0.10 * ease_out(lt / 3.6))
                    frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                if is_blank:
                    draw_ar_center(d, bx, by, ad.get("bracket_label", "فكرتك هنا"), 175, 36, GOLD_BRIGHT)
                a1 = int(255 * ease_out(min(1.0, lt / 0.45)))
                a2 = int(255 * ease_out(max(0.0, (lt - 0.45) / 0.45)))
                a3 = int(255 * ease_out(max(0.0, (lt - 0.95) / 0.45)))
                draw_ar_center(d, W // 2, 1395, ad["scene_top"], 920, 64, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1488, ad["scene_gold"], 920, 80, (224, 188, 118, a2))
                if a3 > 5:
                    draw_ar_center(d, W // 2, 1592, ad["scene_sub"], 900, 31, (195, 190, 182, a3), extra_bold=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            else:
                frame = render_brand_outro_frame(end_bg, t - 9.0, ad, brand)

        elif style == "bracket_morph":
            if t < 4.4:
                p = t / 4.4
                frame = cover_crop(scenes[0], W, H, zoom=1.02 + 0.10 * ease_out(p))
                frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                words = ad.get("bracket_words", ["فكرتك هنا"])
                slot = min(len(words) - 1, int(t / (4.4 / len(words))))
                pulse = int(10 * math.sin(t * 5.0))
                draw_thin_brackets(d, W // 2, 740, 340 + pulse, 164 + pulse // 2, arm=30, color=(238, 205, 134, 225), width=3)
                draw_ar_center(d, W // 2, 740, words[slot], 280, 40, GOLD_BRIGHT)
                a1 = int(255 * ease_out(min(1.0, t / 0.5)))
                a2 = int(255 * ease_out(max(0.0, (t - 0.55) / 0.5)))
                draw_ar_center(d, W // 2, 1395, ad["hook_top"], 920, 62, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1488, ad["hook_gold"], 920, 74, (224, 188, 118, a2))
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "right", 70, 68, 128)
            elif t < 9.0:
                lt = t - 4.4
                frame = cover_crop(scenes[min(1, len(scenes) - 1)], W, H, zoom=1.03 + 0.09 * ease_out(lt / 4.6))
                frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                a1 = int(255 * ease_out(min(1.0, lt / 0.5)))
                a2 = int(255 * ease_out(max(0.0, (lt - 0.5) / 0.5)))
                a3 = int(255 * ease_out(max(0.0, (lt - 1.0) / 0.5)))
                draw_ar_center(d, W // 2, 1395, ad["reveal_top"], 920, 62, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1488, ad["reveal_gold"], 920, 76, (224, 188, 118, a2))
                if a3 > 5:
                    draw_ar_center(d, W // 2, 1592, ad["reveal_sub"], 900, 31, (195, 190, 182, a3), extra_bold=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            else:
                frame = render_brand_outro_frame(end_bg, t - 9.0, ad, brand)

        elif style == "split_contrast":
            if t < 4.5:
                p = t / 4.5
                half = H // 2
                top_im = cover_crop(scenes[0], W, half, zoom=1.02 + 0.07 * ease_out(p))
                bot_im = cover_crop(scenes[min(1, len(scenes) - 1)], W, half, zoom=1.02 + 0.07 * ease_out(p))
                frame = Image.new("RGB", (W, H), OBSIDIAN)
                frame.paste(top_im, (0, 0))
                frame.paste(bot_im, (0, half))
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                d.rectangle((0, half - 4, W, half + 4), fill=(224, 188, 118, 240))
                d.rounded_rectangle((W // 2 - 270, half - 140, W // 2 + 270, half - 62), radius=39, fill=(10, 11, 14, 215), outline=(224, 188, 118, 170), width=2)
                draw_ar_center(d, W // 2, half - 101, ad["top_label"], 490, 32, WHITE, extra_bold=True, shadow=False)
                d.rounded_rectangle((W // 2 - 290, half + 62, W // 2 + 290, half + 140), radius=39, fill=(10, 11, 14, 225), outline=(224, 188, 118, 235), width=2)
                draw_ar_center(d, W // 2, half + 101, ad["bot_label"], 530, 32, GOLD_BRIGHT, extra_bold=True, shadow=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            elif t < 9.0:
                lt = t - 4.5
                frame = cover_crop(scenes[min(1, len(scenes) - 1)], W, H, zoom=1.03 + 0.09 * ease_out(lt / 4.5))
                frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                a1 = int(255 * ease_out(min(1.0, lt / 0.5)))
                a2 = int(255 * ease_out(max(0.0, (lt - 0.5) / 0.5)))
                a3 = int(255 * ease_out(max(0.0, (lt - 1.0) / 0.5)))
                draw_ar_center(d, W // 2, 1395, ad["mid_top"], 920, 62, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1488, ad["mid_gold"], 920, 78, (224, 188, 118, a2))
                if a3 > 5:
                    draw_ar_center(d, W // 2, 1592, ad["mid_sub"], 900, 31, (195, 190, 182, a3), extra_bold=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            else:
                frame = render_brand_outro_frame(end_bg, t - 9.0, ad, brand)

        elif style == "flash_manifesto":
            # 4 rapid numbered luxury beats (01..04) -> dramatic garment reveal -> Gold Logo Outro!
            if t < 5.6:
                frame = end_bg.copy()
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                beats = ad.get("beats", ["فكرتك في راسك", "ماكيت مجانية", "طباعة فليكس HD", "توصيل 58 ولاية"])
                idx = min(3, int(t / 1.4))
                lt = t - idx * 1.4
                p = ease_out(min(1.0, lt / 0.22))
                # Oversized translucent gold number watermark behind crisp white Darja line
                draw_en_center(d, W // 2, 790, f"0{idx + 1}", font_en("Syne-Var.ttf", 210, 800), (224, 188, 118, int(82 * p)))
                draw_ar_center(d, W // 2, 1020 + int(24 * (1 - p)), beats[idx], 900, 74, (248, 246, 242, int(255 * p)) if idx < 3 else (224, 188, 118, int(255 * p)))
                d.line((W // 2 - int(240 * p), 1125, W // 2 + int(240 * p), 1125), fill=(224, 188, 118, 175), width=2)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            elif t < 9.0:
                lt = t - 5.6
                frame = cover_crop(scenes[0], W, H, zoom=1.04 + 0.09 * ease_out(lt / 3.4))
                frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                a1 = int(255 * ease_out(min(1.0, lt / 0.45)))
                a2 = int(255 * ease_out(max(0.0, (lt - 0.45) / 0.45)))
                a3 = int(255 * ease_out(max(0.0, (lt - 0.9) / 0.45)))
                draw_ar_center(d, W // 2, 1395, ad["scene_top"], 920, 62, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1488, ad["scene_gold"], 920, 78, (224, 188, 118, a2))
                if a3 > 5:
                    draw_ar_center(d, W // 2, 1592, ad["scene_sub"], 900, 31, (195, 190, 182, a3), extra_bold=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "right", 70, 68, 128)
            else:
                frame = render_brand_outro_frame(end_bg, t - 9.0, ad, brand)

        elif style == "zoom_reveal_quote":
            # Tight dramatic pull-back zoom from dark fabric texture with gold question -> Full Scene Punchline -> Gold Outro!
            if t < 4.2:
                p = ease_out(t / 4.2)
                frame = cover_crop(scenes[0], W, H, zoom=1.42 - 0.36 * p)
                frame = apply_fade(frame, start_ratio=0.05, strength=0.72, top_strength=0.55)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                a1 = int(255 * ease_out(min(1.0, t / 0.6)))
                d.text((W // 2 - 44, 620), "“", font=font_en("Syne-Var.ttf", 170, 800), fill=(224, 188, 118, int(90 * (a1 / 255))))
                draw_ar_center(d, W // 2, 920, ad["quote_top"], 900, 68, (248, 246, 242, a1))
                draw_ar_center(d, W // 2, 1020, ad["quote_gold"], 900, 76, (224, 188, 118, a1))
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            elif t < 9.0:
                lt = t - 4.2
                s_idx = min(1, len(scenes) - 1)
                frame = cover_crop(scenes[s_idx], W, H, zoom=1.02 + 0.09 * ease_out(lt / 4.8))
                frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                a1 = int(255 * ease_out(min(1.0, lt / 0.5)))
                a2 = int(255 * ease_out(max(0.0, (lt - 0.5) / 0.5)))
                a3 = int(255 * ease_out(max(0.0, (lt - 1.0) / 0.5)))
                draw_ar_center(d, W // 2, 1395, ad["reveal_top"], 920, 62, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1488, ad["reveal_gold"], 920, 78, (224, 188, 118, a2))
                if a3 > 5:
                    draw_ar_center(d, W // 2, 1592, ad["reveal_sub"], 900, 31, (195, 190, 182, a3), extra_bold=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            else:
                frame = render_brand_outro_frame(end_bg, t - 9.0, ad, brand)

        else:
            # spotlight_macro
            if t < 4.5:
                p = t / 4.5
                frame = cover_crop(scenes[0], W, H, zoom=1.02 + 0.12 * ease_out(p), pan_y=-30 + 30 * p)
                frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                a1 = int(255 * ease_out(min(1.0, t / 0.55)))
                a2 = int(255 * ease_out(max(0.0, (t - 0.55) / 0.55)))
                draw_ar_center(d, W // 2, 1395, ad["s1_top"], 920, 60, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1488, ad["s1_gold"], 920, 76, (224, 188, 118, a2))
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            elif t < 9.0:
                lt = t - 4.5
                frame = cover_crop(scenes[min(1, len(scenes) - 1)], W, H, zoom=1.03 + 0.11 * ease_out(lt / 4.5), pan_y=30 - 30 * (lt / 4.5))
                frame = apply_fade(frame, start_ratio=0.56, strength=0.98, top_strength=0.30)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
                a1 = int(255 * ease_out(min(1.0, lt / 0.5)))
                a2 = int(255 * ease_out(max(0.0, (lt - 0.5) / 0.5)))
                a3 = int(255 * ease_out(max(0.0, (lt - 1.0) / 0.5)))
                draw_ar_center(d, W // 2, 1395, ad["s2_top"], 920, 60, (248, 246, 242, a1))
                if a2 > 5:
                    draw_ar_center(d, W // 2, 1488, ad["s2_gold"], 920, 78, (224, 188, 118, a2))
                if a3 > 5:
                    draw_ar_center(d, W // 2, 1592, ad["s2_sub"], 900, 31, (195, 190, 182, a3), extra_bold=False)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
                paste_corner_emblem(frame, "left", 70, 68, 128)
            else:
                frame = render_brand_outro_frame(end_bg, t - 9.0, ad, brand)

        db = ImageDraw.Draw(frame)
        db.rectangle((84, H - 118, W - 84, H - 114), fill=(48, 46, 42))
        db.rectangle((84, H - 118, 84 + max(6, int((W - 168) * (t / DUR))), H - 114), fill=GOLD)
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"FFmpeg failed with exit code {rc}")


# ==============================================================================
# PART 4: SLOT SELECTION, ZERO-REPEAT STATE, CDN VERIFICATION, MAKE & TELEGRAM
# ==============================================================================
def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            st = json.load(f)
    else:
        st = {}
    st.setdefault("used_ids", [])
    st.setdefault("cycle", 1)
    st.setdefault("last_type", None)
    st.setdefault("history", [])
    return st


def save_state(st: dict):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)


def pick_next_ad(bank: dict, state: dict, mode: str, forced_id: str = None) -> dict:
    ads = bank["ads"]
    if forced_id:
        for a in ads:
            if a["id"].upper() == forced_id.upper():
                return a
        raise ValueError(f"Ad ID {forced_id} not found in ad_bank.json")

    used = set(state.get("used_ids", []))
    if mode in ("reel", "poster"):
        want_type = mode
    else:
        want_type = "poster" if state.get("last_type") == "reel" else "reel"

    pool = [a for a in ads if a["type"] == want_type and a["id"] not in used]
    if not pool:
        other_used = [uid for uid in used if any(a["id"] == uid and a["type"] != want_type for a in ads)]
        state["used_ids"] = other_used
        if not other_used:
            state["cycle"] = state.get("cycle", 1) + 1
        pool = [a for a in ads if a["type"] == want_type]
    return pool[0]


def build_custom_ad(mode: str, hook: str, punchline: str, subline: str, scene_file: str) -> dict:
    if mode == "reel":
        return {
            "id": "CUSTOM_R",
            "type": "reel",
            "angle": "custom_trend",
            "reel_style": "apple_kinetic",
            "scenes": [scene_file or "s01_blank_canvas.jpg"],
            "beat1": hook,
            "beat2": punchline,
            "beat3": "اطبعو اليوم عند DW SHIRT.",
            "scene_top": hook,
            "scene_gold": punchline,
            "scene_sub": subline or "طباعة فليكس HD حسب الطلب • قسنطينة و 58 ولاية",
            "outro_line": "فكرتك. طبعتك. ستيلك.",
            "caption": f"{hook} — {punchline} 🖤✨\n\n{subline or 'أي فكرة ولا تراند في بالك نطبعوهولك بجودة فليكس HD.'}\n\n📩 ابعتلنا فكرتك فالخاص (DM) | 📞 0662 81 15 91\n🚚 قسنطينة • توصيل متوفر لـ 58 ولاية\n\n#dw_shirt #طباعة_ملابس #قسنطينة #توصيل_58_ولاية #الجزائر"
        }
    return {
        "id": "CUSTOM_P",
        "type": "poster",
        "angle": "custom_trend",
        "poster_style": "standard",
        "scene": scene_file or "s01_blank_canvas.jpg",
        "headline": hook,
        "punchline": punchline,
        "subline": subline or "ابعتلنا فكرتك فالخاص نطبعوهالك بجودة فليكس HD",
        "emblem_pos": "left",
        "caption": f"{hook} {punchline} 🖤✨\n\n{subline or 'ابعتلنا فكرتك فالخاص نطبعوهالك بأعلى جودة.'}\n\n📩 راسلنا فالخاص (DM) | 📞 0662 81 15 91\n🚚 قسنطينة • توصيل 58 ولاية\n\n#dw_shirt #طباعة_حسب_الطلب #قسنطينة #توصيل_58_ولاية #الجزائر"
    }


def cleanup_old_published(keep_last: int = 3):
    files = sorted(glob.glob(os.path.join(PUB_DIR, "dw_*.*")), key=os.path.getmtime, reverse=True)
    for old in files[keep_last:]:
        try:
            os.remove(old)
        except OSError:
            pass


def wait_for_cdn_url(url: str, expected_bytes: int, max_wait: int = 75) -> bool:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            r = requests.head(url, timeout=12, allow_redirects=True)
            cl = int(r.headers.get("Content-Length", "0") or 0)
            if r.status_code == 200 and (cl == expected_bytes or cl > 50_000):
                print(f"[CDN OK] HTTP 200 ({cl} bytes): {url}")
                return True
        except Exception as e:
            print(f"[CDN WAIT] {e}")
        time.sleep(5)
    return False


def trigger_make_webhook(webhook_url: str, payload: dict):
    for attempt in range(1, 5):
        try:
            r = requests.post(webhook_url, json=payload, timeout=45)
            print(f"[MAKE ATTEMPT {attempt}] HTTP {r.status_code} -> {r.text[:200]}")
            if 200 <= r.status_code < 300:
                return True
        except Exception as e:
            print(f"[MAKE ERR {attempt}] {e}")
        time.sleep(4 * attempt)
    raise RuntimeError("Make.com webhook failed after 4 attempts!")


def notify_telegram(token: str, chat_id: str, pending: dict):
    if not token or not chat_id:
        return
    mtype = "🎬 ريل إشهاري" if pending["media_type"] == "reel" else "🖼️ بوستر إشهاري"
    msg = (
        f"✅ <b>DW SHIRT • تم نشر إشهار جديد على إنستغرام!</b>\n\n"
        f"📌 <b>النوع:</b> {mtype} (<code>{pending['concept_id']}</code>)\n"
        f"🎨 <b>الستايل:</b> <code>{pending['style']}</code>\n"
        f"🔗 <b>الرابط:</b> {pending['media_url']}\n\n"
        f"📝 <b>الكابشن:</b>\n{pending['caption'][:650]}"
    )
    try:
        if pending["media_type"] == "photo" and os.path.exists(pending["local_path"]):
            with open(pending["local_path"], "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendPhoto",
                    data={"chat_id": chat_id, "caption": msg[:1000], "parse_mode": "HTML"},
                    files={"photo": f},
                    timeout=30,
                )
        else:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True},
                timeout=20,
            )
    except Exception as e:
        print(f"[TELEGRAM WARN] {e}")


def phase_render(args):
    with open(BANK_PATH, "r", encoding="utf-8") as f:
        bank = json.load(f)
    state = load_state()

    if args.custom_hook and args.custom_punchline:
        mode = "reel" if args.mode == "reel" else "poster"
        ad = build_custom_ad(mode, args.custom_hook, args.custom_punchline, args.custom_subline or "", args.custom_scene or "")
    else:
        ad = pick_next_ad(bank, state, args.mode, forced_id=args.ad_id)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ext = "mp4" if ad["type"] == "reel" else "jpg"
    fname = f"dw_{ad['type']}_{ad['id']}_{ts}.{ext}"
    out_path = os.path.join(PUB_DIR, fname)

    print(f"[RENDER] id={ad['id']} type={ad['type']} angle={ad['angle']} raqm={HAS_RAQM}")
    if ad["type"] == "reel":
        render_reel(ad, bank["brand"], out_path)
        style_used = ad.get("reel_style", "cinema_3beat")
        media_type = "reel"
    else:
        render_poster(ad, bank["brand"], out_path)
        style_used = ad.get("poster_style", "standard")
        media_type = "photo"

    cleanup_old_published(keep_last=3)
    fsize = os.path.getsize(out_path)
    repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/dw-shirt-ig-autopilot")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    media_url = f"https://raw.githubusercontent.com/{repo}/{branch}/published/{fname}"

    pending = {
        "concept_id": ad["id"],
        "angle": ad["angle"],
        "style": style_used,
        "media_type": media_type,
        "filename": fname,
        "local_path": out_path,
        "size_bytes": fsize,
        "media_url": media_url,
        "caption": ad["caption"],
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    print(f"[RENDER DONE] {out_path} ({fsize // 1024} KB) -> {media_url}")


def phase_publish(args):
    if not os.path.exists(PENDING_PATH):
        raise FileNotFoundError("No published/pending.json found. Run --phase render first.")
    with open(PENDING_PATH, "r", encoding="utf-8") as f:
        pending = json.load(f)

    if args.dry_run:
        print("[DRY RUN] Skipping CDN wait & Make webhook:", json.dumps(pending, ensure_ascii=False, indent=2))
        return

    webhook_url = os.environ.get("MAKE_DW_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise RuntimeError("Missing MAKE_DW_WEBHOOK_URL secret!")

    ok = wait_for_cdn_url(pending["media_url"], pending["size_bytes"], max_wait=75)
    if not ok:
        raise RuntimeError(f"CDN URL did not return HTTP 200 in time: {pending['media_url']}")

    payload = {
        "media_type": pending["media_type"],
        "media_url": pending["media_url"],
        "caption": pending["caption"],
        "concept_id": pending["concept_id"],
        "style": pending["style"],
        "angle": pending["angle"],
    }
    trigger_make_webhook(webhook_url, payload)

    state = load_state()
    if not pending["concept_id"].startswith("CUSTOM_"):
        if pending["concept_id"] not in state["used_ids"]:
            state["used_ids"].append(pending["concept_id"])
    state["last_type"] = "reel" if pending["media_type"] == "reel" else "poster"
    state["history"] = (state.get("history", []) + [{
        "id": pending["concept_id"],
        "media_type": pending["media_type"],
        "style": pending["style"],
        "published_utc": datetime.now(timezone.utc).isoformat(),
    }])[-370:]
    save_state(state)

    notify_telegram(
        os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
        os.environ.get("TELEGRAM_CHAT_ID", "").strip(),
        pending,
    )
    try:
        os.remove(PENDING_PATH)
    except OSError:
        pass
    print("[PUBLISH COMPLETE] Instagram post sent via Make #2 & state updated!")


def main():
    ap = argparse.ArgumentParser(description="DW SHIRT 365-Day Luxury Creative Ad Factory")
    ap.add_argument("--phase", choices=["render", "publish", "all"], default="render")
    ap.add_argument("--mode", choices=["auto", "reel", "poster"], default="auto")
    ap.add_argument("--ad-id", default=None, help="Force specific ad ID (e.g., R001, P006)")
    ap.add_argument("--custom-hook", default=None)
    ap.add_argument("--custom-punchline", default=None)
    ap.add_argument("--custom-subline", default=None)
    ap.add_argument("--custom-scene", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.phase in ("render", "all"):
        phase_render(args)
    if args.phase in ("publish", "all"):
        phase_publish(args)


if __name__ == "__main__":
    main()
