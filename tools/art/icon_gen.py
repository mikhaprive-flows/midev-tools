"""
icon_gen - Procedural Pixel-Art Icon & Favicon Generator for midev-tools.
Generates multi-resolution .ico files with crisp nearest-neighbor scaling.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pixelkit
from pixelkit import Canvas


def create_studio_icon_canvas() -> Canvas:
    """
    Design a 32x32 pixel art emblem for midev Studio.
    Features a dark studio badge, glowing cyan & amber lightning motif,
    and vibrant palette dots.
    """
    c = Canvas(32, 32)

    # 1. Outer Dark Rounded Badge (28x28 centered)
    # Corners clipped for rounded appearance
    # Fill background with dark navy/slate
    bg_color = (15, 23, 42, 255)       # #0f172a
    border_dark = (30, 41, 59, 255)    # #1e293b
    neon_cyan = (0, 240, 255, 255)     # #00f0ff
    neon_amber = (255, 209, 102, 255)  # #ffd166
    dot_red = (255, 77, 109, 255)      # #ff4d6d
    dot_green = (6, 214, 160, 255)     # #06d6a0
    dot_purple = (181, 23, 158, 255)   # #b5179e
    white = (255, 255, 255, 255)

    # Base rounded rect from (2, 2) to (29, 29)
    c.rect(2, 2, 28, 28, bg_color, fill=True)
    # Bevel/border outline
    c.rect(2, 2, 28, 28, border_dark, fill=False)

    # Soften 4 corners
    corner_cuts = [
        (2, 2), (3, 2), (2, 3),
        (29, 2), (28, 2), (29, 3),
        (2, 29), (3, 29), (2, 28),
        (29, 29), (28, 29), (29, 28),
    ]
    for cx, cy in corner_cuts:
        c.px(cx, cy, (0, 0, 0, 0))

    # Inner subtle highlight top border
    c.line(4, 3, 27, 3, (51, 65, 85, 255))
    c.line(3, 4, 3, 27, (51, 65, 85, 255))

    # 2. Glowing Pixel Art Palette Dots
    # Top-Left: Coral Red
    c.rect(6, 6, 3, 3, dot_red, fill=True)
    c.px(6, 6, white)

    # Top-Right: Neon Green
    c.rect(23, 6, 3, 3, dot_green, fill=True)
    c.px(23, 6, white)

    # Bottom-Left: Electric Violet
    c.rect(6, 23, 3, 3, dot_purple, fill=True)
    c.px(6, 23, white)

    # 3. Central Lightning Bolt Motif (Signature ⚡ of midev Studio)
    # Drawn with solid amber body, white core highlights, and neon cyan glow edge
    bolt_pixels = [
        # Top segment
        (18, 7), (19, 7),
        (17, 8), (18, 8), (19, 8),
        (16, 9), (17, 9), (18, 9),
        (15, 10), (16, 10), (17, 10),
        (14, 11), (15, 11), (16, 11),
        (13, 12), (14, 12), (15, 12),
        (12, 13), (13, 13), (14, 13),
        # Horizontal crossbar
        (10, 14), (11, 14), (12, 14), (13, 14), (14, 14), (15, 14), (16, 14), (17, 14), (18, 14), (19, 14), (20, 14),
        (11, 15), (12, 15), (13, 15), (14, 15), (15, 15), (16, 15), (17, 15), (18, 15), (19, 15),
        # Bottom segment
        (13, 16), (14, 16), (15, 16), (16, 16),
        (13, 17), (14, 17), (15, 17),
        (12, 18), (13, 18), (14, 18),
        (12, 19), (13, 19),
        (11, 20), (12, 20),
        (11, 21), (12, 21),
        (10, 22), (11, 22),
        (10, 23),
        (9, 24),
    ]

    # Cyan glow underlay / drop shadow
    for bx, by in bolt_pixels:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = bx + dx, by + dy
            if (nx, ny) not in bolt_pixels and 0 <= nx < 32 and 0 <= ny < 32:
                c.px(nx, ny, neon_cyan)

    # Golden yellow bolt body
    for bx, by in bolt_pixels:
        c.px(bx, by, neon_amber)

    # Specular white highlights down the spine
    spine_highlights = [
        (18, 7), (17, 8), (16, 9), (15, 10), (14, 11), (13, 12),
        (13, 14), (14, 14), (15, 14), (16, 14),
        (14, 16), (13, 18), (12, 20), (10, 23)
    ]
    for hx, hy in spine_highlights:
        c.px(hx, hy, white)

    return c


def generate_studio_icon(
    out_path: Path | str | None = None,
    sizes: list[tuple[int, int]] | None = None,
) -> Path:
    """
    Generate the official midev Studio multi-resolution .ico icon.
    Default targets tools/art/web/favicon.ico with sizes (16, 16), (32, 32), (48, 48).
    """
    if out_path is None:
        out_path = Path(__file__).parent / "web" / "favicon.ico"
    else:
        out_path = Path(out_path)

    sizes = sizes or [(16, 16), (32, 32), (48, 48)]
    canvas = create_studio_icon_canvas()
    return canvas.save_ico(out_path, sizes=sizes)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    saved = generate_studio_icon(target)
    print(f"[icon_gen] Successfully generated studio favicon at: {saved}")
