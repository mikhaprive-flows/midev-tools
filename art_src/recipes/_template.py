# Author: Agent-worker-cody
"""Recipe TEMPLATE - copy via `tools\\art.ps1 new <name>`.
A recipe = deterministic Python that draws frames and writes assets. Never hand-edit output PNGs;
change the recipe and rebuild so art stays reproducible."""
from pixelkit import Canvas, SheetBuilder, svg_frame, svg_doc, hexc


def build(ctx):
    sb = SheetBuilder("TEMPLATE", 16, 16)
    frames = []
    for i in range(4):
        c = Canvas(16, 16)
        c.circle(8, 8 - (i % 2), 4, "gold")
        c.outline()
        frames.append(c)
    sb.add("idle", frames, fps=6)
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
