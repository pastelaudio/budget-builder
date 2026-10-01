"""One-off script to generate a Frutiger Aero-style app logo/icon for Budget Builder.

Produces:
    assets/logo.png   - 512x512 master artwork
    assets/icon.ico    - multi-size Windows icon (for the .exe)
    web/favicon.ico    - browser favicon

Run with: python scripts/generate_logo.py  (requires: pip install pillow)
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT, "assets")
WEB_DIR = os.path.join(ROOT, "web")


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def vertical_gradient(size, top_color, bottom_color):
    img = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        img.putpixel((0, y), lerp_color(top_color, bottom_color, t))
    return img.resize((size, size))


def build_logo() -> Image.Image:
    sky_top = (140, 221, 251)     # light sky blue
    sky_bottom = (10, 100, 120)   # deep aqua teal
    base = vertical_gradient(SIZE, sky_top, sky_bottom).convert("RGBA")

    mask = rounded_mask(SIZE, radius=int(SIZE * 0.22))
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(base, (0, 0), mask)

    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Glossy top highlight (classic Frutiger Aero glass sheen)
    gloss = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gloss_draw = ImageDraw.Draw(gloss)
    gloss_draw.ellipse(
        [SIZE * -0.15, SIZE * -0.45, SIZE * 1.15, SIZE * 0.55], fill=(255, 255, 255, 110)
    )
    gloss = gloss.filter(ImageFilter.GaussianBlur(SIZE * 0.02))
    overlay = Image.alpha_composite(overlay, gloss)
    draw = ImageDraw.Draw(overlay)

    # Upward "growth" bars in glossy green, representing budget/savings growth
    bar_colors_top = [(176, 240, 150), (150, 230, 140), (120, 220, 150)]
    bar_colors_bottom = [(70, 170, 90), (50, 150, 80), (30, 140, 90)]
    bar_width = SIZE * 0.1
    gap = SIZE * 0.045
    heights = [SIZE * 0.22, SIZE * 0.33, SIZE * 0.46]
    base_y = SIZE * 0.74
    start_x = SIZE * 0.26
    for i, h in enumerate(heights):
        x0 = start_x + i * (bar_width + gap)
        x1 = x0 + bar_width
        y1 = base_y
        y0 = base_y - h
        bar_grad = vertical_gradient(int(h), bar_colors_top[i], bar_colors_bottom[i]).convert("RGBA")
        bar_mask = Image.new("L", (int(bar_width), int(h)), 0)
        ImageDraw.Draw(bar_mask).rounded_rectangle(
            [0, 0, int(bar_width) - 1, int(h) - 1], radius=int(bar_width * 0.3), fill=255
        )
        bar_img = bar_grad.resize((int(bar_width), int(h)))
        overlay.paste(bar_img, (int(x0), int(y0)), bar_mask)
        # thin glossy highlight strip on each bar
        hl = Image.new("RGBA", (int(bar_width), int(h)), (0, 0, 0, 0))
        ImageDraw.Draw(hl).rounded_rectangle(
            [bar_width * 0.12, 0, bar_width * 0.4, h * 0.9], radius=int(bar_width * 0.15),
            fill=(255, 255, 255, 70),
        )
        overlay.paste(hl, (int(x0), int(y0)), hl)

    # Rising trend line + arrowhead over the bars (classic "growth" motif)
    line_pts = [
        (start_x - SIZE * 0.02, base_y - heights[0] + SIZE * 0.02),
        (start_x + bar_width + gap + bar_width * 0.5, base_y - heights[1] - SIZE * 0.01),
        (start_x + 2 * (bar_width + gap) + bar_width * 0.5, base_y - heights[2] - SIZE * 0.04),
    ]
    draw.line(line_pts, fill=(255, 255, 255, 230), width=int(SIZE * 0.018), joint="curve")
    tipx, tipy = line_pts[-1]
    ang = math.atan2(line_pts[-1][1] - line_pts[-2][1], line_pts[-1][0] - line_pts[-2][0])
    arrow_len = SIZE * 0.045
    for side in (0.5, -0.5):
        ax = tipx - arrow_len * math.cos(ang - side * 0.9)
        ay = tipy - arrow_len * math.sin(ang - side * 0.9)
        draw.line([(tipx, tipy), (ax, ay)], fill=(255, 255, 255, 230), width=int(SIZE * 0.018))

    # Scattered aero "water droplet" bubbles
    bubbles = [
        (SIZE * 0.78, SIZE * 0.22, SIZE * 0.07),
        (SIZE * 0.86, SIZE * 0.34, SIZE * 0.035),
        (SIZE * 0.15, SIZE * 0.32, SIZE * 0.045),
        (SIZE * 0.70, SIZE * 0.14, SIZE * 0.025),
    ]
    for bx, by, br in bubbles:
        bubble = Image.new("RGBA", (int(br * 2.4), int(br * 2.4)), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bubble)
        bd.ellipse([0, 0, br * 2.4, br * 2.4], fill=(255, 255, 255, 60))
        bd.ellipse([br * 0.3, br * 0.25, br * 1.3, br * 1.1], fill=(255, 255, 255, 140))
        overlay.paste(bubble, (int(bx - br * 1.2), int(by - br * 1.2)), bubble)

    canvas = Image.alpha_composite(canvas, overlay)

    # Subtle outer rim highlight for a glassy, rounded-icon finish
    rim = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle(
        [SIZE * 0.015, SIZE * 0.015, SIZE * 0.985, SIZE * 0.985],
        radius=int(SIZE * 0.21),
        outline=(255, 255, 255, 90),
        width=max(2, int(SIZE * 0.006)),
    )
    canvas = Image.alpha_composite(canvas, rim)
    return canvas


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    logo = build_logo()
    logo.save(os.path.join(ASSETS_DIR, "logo.png"))

    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    logo.save(os.path.join(ASSETS_DIR, "icon.ico"), sizes=icon_sizes)
    logo.save(os.path.join(WEB_DIR, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    print("Wrote assets/logo.png, assets/icon.ico, web/favicon.ico")


if __name__ == "__main__":
    main()
