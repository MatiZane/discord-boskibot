from __future__ import annotations

import hashlib
import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .ship_logic import ShipResult

CARD_W = 820
CARD_H = 320
AVATAR_SIZE = 148

_FONT_CANDIDATES_BOLD = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
_FONT_CANDIDATES_REGULAR = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = _FONT_CANDIDATES_BOLD if bold else _FONT_CANDIDATES_REGULAR
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _truncate_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "…"
    trimmed = text
    while len(trimmed) > 1 and draw.textlength(trimmed + ellipsis, font=font) > max_width:
        trimmed = trimmed[:-1]
    return trimmed + ellipsis


def _accent_for_percent(percent: int) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    if percent >= 75:
        return (245, 132, 178), (125, 196, 245)  # Sakura pink + Miku sky blue
    if percent >= 40:
        return (125, 196, 245), (176, 152, 242)  # Miku sky blue + pastel violet
    return (138, 160, 194), (110, 126, 158)      # Calm muted slate blue


def _monogram_avatar(name: str, size: int) -> Image.Image:
    digest = hashlib.sha256(name.lower().encode("utf-8")).digest()
    palettes = [
        ((70, 128, 194), (132, 196, 246)),
        ((168, 92, 134), (242, 160, 196)),
        ((106, 98, 178), (176, 162, 242)),
        ((64, 146, 156), (134, 214, 220)),
        ((164, 114, 88), (236, 184, 146)),
    ]
    c1, c2 = palettes[digest[0] % len(palettes)]
    img = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    initials = "".join(part[0] for part in name.split()[:2] if part).upper()[:2] or "?"
    font = _load_font(int(size * 0.40), bold=True)
    bbox = draw.textbbox((0, 0), initials, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - bbox[1]), initials, fill=(255, 255, 255, 245), font=font)
    return img


def _prepare_avatar(avatar_bytes: bytes | None, fallback_name: str, size: int) -> Image.Image:
    if avatar_bytes:
        try:
            with Image.open(io.BytesIO(avatar_bytes)) as raw:
                src = ImageOps.fit(raw.convert("RGBA"), (size, size), method=Image.Resampling.LANCZOS)
        except Exception:
            src = _monogram_avatar(fallback_name, size)
    else:
        src = _monogram_avatar(fallback_name, size)

    # Smooth 4x supersampled circular alpha mask
    hi = size * 4
    mask = Image.new("L", (hi, hi), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, hi - 1, hi - 1), fill=255)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(src, (0, 0), mask)
    return out


def _draw_heart(layer: Image.Image, cx: float, cy: float, scale: float, fill: tuple[int, int, int, int]) -> None:
    points: list[tuple[float, float]] = []
    for deg in range(0, 360, 4):
        t = math.radians(deg)
        x = 16.0 * (math.sin(t) ** 3)
        y = -(13.0 * math.cos(t) - 5.0 * math.cos(2 * t) - 2.0 * math.cos(3 * t) - math.cos(4 * t))
        points.append((cx + x * scale, cy + y * scale))
    ImageDraw.Draw(layer).polygon(points, fill=fill)


def _draw_background(w: int, h: int, primary: tuple[int, int, int], secondary: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grad = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(grad)
    top_left = (18, 25, 42)
    bottom_right = (30, 37, 58)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top_left[0] + (bottom_right[0] - top_left[0]) * t)
        g = int(top_left[1] + (bottom_right[1] - top_left[1]) * t)
        b = int(top_left[2] + (bottom_right[2] - top_left[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    # Soft ambient glows behind avatars and heart
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((-40, -50, 290, 270), fill=(*secondary, 48))
    gdraw.ellipse((w - 290, -40, w + 40, 280), fill=(*primary, 48))
    gdraw.ellipse((w // 2 - 140, 20, w // 2 + 140, 260), fill=(*primary, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=42))
    grad = Image.alpha_composite(grad, glow)

    # Rounded card clip
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=30, fill=255)
    base.paste(grad, (0, 0), mask)

    # Subtle alpha-blended outer border
    border_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(border_layer).rounded_rectangle(
        (1, 1, w - 2, h - 2), radius=30, outline=(255, 255, 255, 42), width=2
    )
    base = Image.alpha_composite(base, border_layer)
    return base


def render_ship_card(
    result: ShipResult,
    avatar_a_bytes: bytes | None = None,
    avatar_b_bytes: bytes | None = None,
) -> bytes:
    """Render a polished PNG compatibility card (bytes) for Discord."""
    primary, secondary = _accent_for_percent(result.percent)
    card = _draw_background(CARD_W, CARD_H, primary, secondary)
    draw = ImageDraw.Draw(card)

    # Header subtitle + ship blend badge
    header_font = _load_font(15, bold=True)
    ship_font = _load_font(22, bold=True)
    name_font = _load_font(20, bold=True)
    percent_font = _load_font(36, bold=True)
    comment_font = _load_font(15, bold=False)

    draw.text((34, 22), "MIKU SHIP", fill=(*secondary, 220), font=header_font)
    blend_label = f"« {result.ship_name} »"
    blend_w = draw.textlength(blend_label, font=ship_font)
    draw.text(((CARD_W - blend_w) / 2, 18), blend_label, fill=(242, 246, 255, 240), font=ship_font)

    # Circular avatars with glowing rings
    avatar_y = 66
    left_x = 58
    right_x = CARD_W - 58 - AVATAR_SIZE

    for ax, ring_color, raw_bytes, disp_name in (
        (left_x, secondary, avatar_a_bytes, result.name_a),
        (right_x, primary, avatar_b_bytes, result.name_b),
    ):
        pad = 5
        draw.ellipse(
            (ax - pad, avatar_y - pad, ax + AVATAR_SIZE + pad, avatar_y + AVATAR_SIZE + pad),
            fill=(*ring_color, 210),
        )
        av = _prepare_avatar(raw_bytes, disp_name, AVATAR_SIZE)
        card.paste(av, (ax, avatar_y), av)

        label = _truncate_text(draw, disp_name, name_font, max_width=210)
        lw = draw.textlength(label, font=name_font)
        draw.text((ax + (AVATAR_SIZE - lw) / 2, avatar_y + AVATAR_SIZE + 12), label, fill=(238, 244, 255, 245), font=name_font)

    # Center heart + percentage
    cx = CARD_W / 2
    cy = avatar_y + AVATAR_SIZE / 2 - 4
    heart_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    _draw_heart(heart_layer, cx, cy, scale=4.75, fill=(*primary, 85))
    heart_blur = heart_layer.filter(ImageFilter.GaussianBlur(radius=12))
    card = Image.alpha_composite(card, heart_blur)

    crisp_heart = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    _draw_heart(crisp_heart, cx, cy, scale=4.25, fill=(*primary, 240))
    card = Image.alpha_composite(card, crisp_heart)

    # Smooth alpha-blended progress bar track at bottom
    bar_x1 = 58
    bar_x2 = CARD_W - 58
    bar_y1 = 258
    bar_y2 = 274
    bar_w = bar_x2 - bar_x1
    track_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    ImageDraw.Draw(track_layer).rounded_rectangle(
        (bar_x1, bar_y1, bar_x2, bar_y2), radius=8, fill=(255, 255, 255, 30)
    )
    card = Image.alpha_composite(card, track_layer)
    draw = ImageDraw.Draw(card)

    pct_text = f"{result.percent}%"
    pct_bbox = draw.textbbox((0, 0), pct_text, font=percent_font)
    pct_w = pct_bbox[2] - pct_bbox[0]
    pct_h = pct_bbox[3] - pct_bbox[1]
    draw.text(
        (cx - pct_w / 2, cy - pct_h / 2 - pct_bbox[1] - 4),
        pct_text,
        fill=(255, 255, 255, 255),
        font=percent_font,
    )

    fill_w = max(16, int(bar_w * (result.percent / 100.0))) if result.percent > 0 else 0
    if fill_w > 0:
        bar_grad = Image.new("RGBA", (fill_w, bar_y2 - bar_y1))
        bgdraw = ImageDraw.Draw(bar_grad)
        for x in range(fill_w):
            t = x / max(1, fill_w - 1)
            r = int(secondary[0] + (primary[0] - secondary[0]) * t)
            g = int(secondary[1] + (primary[1] - secondary[1]) * t)
            b = int(secondary[2] + (primary[2] - secondary[2]) * t)
            bgdraw.line([(x, 0), (x, bar_y2 - bar_y1)], fill=(r, g, b, 255))
        bar_mask = Image.new("L", (fill_w, bar_y2 - bar_y1), 0)
        ImageDraw.Draw(bar_mask).rounded_rectangle((0, 0, fill_w - 1, bar_y2 - bar_y1 - 1), radius=8, fill=255)
        card.paste(bar_grad, (bar_x1, bar_y1), bar_mask)

    # Footer comment in Miku's voice
    comment = _truncate_text(draw, result.comment, comment_font, max_width=CARD_W - 116)
    cw = draw.textlength(comment, font=comment_font)
    draw.text(((CARD_W - cw) / 2, 284), comment, fill=(195, 210, 232, 235), font=comment_font)

    buf = io.BytesIO()
    card.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
