# Author: midev generator
"""9-Slice Dialog Box, Health Bar, and Inventory Slots."""
from pixelkit import SheetBuilder
from generators.uikit import UIKitGenerator


def build(ctx):
    gen = UIKitGenerator()
    sb = gen.generate_sheet("hud_kit")
    sb.save(ctx.ui)
    sb.preview_gif(ctx.preview)
