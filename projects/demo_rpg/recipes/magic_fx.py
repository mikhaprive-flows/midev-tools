# Author: midev generator
"""Procedural Pixel-Art VFX (Explosions, Slashes, Sparks)."""
from pixelkit import SheetBuilder
from generators.vfx import VFXGenerator


def build(ctx):
    gen = VFXGenerator()
    sb = gen.generate_sheet("magic_fx")
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
