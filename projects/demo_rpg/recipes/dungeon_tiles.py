# Author: midev generator
"""47-Tile Wang Blob Autotile Terrain Transition."""
from pixelkit import SheetBuilder
from generators.autotile import AutotileGenerator, AutotileConfig


def build(ctx):
    cfg = AutotileConfig(
        tile_size=16,
        inner_color="green",
        outer_color="dirt",
        style="dungeon",
    )
    gen = AutotileGenerator(cfg)
    sb = gen.generate_sheet("dungeon_tiles")
    sb.save(ctx.tiles)
    sb.preview_gif(ctx.preview)
