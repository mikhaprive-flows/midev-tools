# Author: midev generator
"""Player Hero Character Rig with multi-directional animations."""
from pixelkit import SheetBuilder
from generators.character import CharacterGenerator, CharacterConfig


def build(ctx):
    cfg = CharacterConfig(
        width=16,
        height=24,
        skin_tone="peach",
        hair_style="short",
        hair_color="brown",
        outfit="tunic",
        outfit_color="dark_blue",
        weapon="sword",
    )
    gen = CharacterGenerator(cfg)
    sb = gen.generate_sheet("hero")
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
