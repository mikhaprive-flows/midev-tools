# Author: midev generator
"""Base Recipe Template for new art assets."""
from pixelkit import Canvas, SheetBuilder


def build(ctx):
    sb = SheetBuilder("sample_sprite", 16, 16)
    frames = []
    for i in range(4):
        c = Canvas(16, 16)
        c.circle(8, 8 - (i % 2), 4, "gold" if "gold" in c.pal else 3)
        c.outline()
        frames.append(c)
    sb.add("idle", frames, fps=6)
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
