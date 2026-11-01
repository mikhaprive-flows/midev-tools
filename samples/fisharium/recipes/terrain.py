# Author: Agent-worker-cody
"""Terrain atlas: one 16x16 tile per Tile id (column = id, see shared/.../Types.kt).
Order MUST match the Tile enum. Followed by autotile transitions (M1-1),
tile variants / animated water frames (M1-3), and biome props (M3-2).
v1.1 Update: Procedural ground textures (blades, ripples, leaf litter, pebbles, cracks, drifts),
sliding wave animation (phases 1 & 2 for water and deep_water), and seamless organic wob() borders.
"""
import math
import random
from PIL import Image
from pixelkit import Canvas, PAL

T = 16

KIND = {
    "grass": "grass",
    "sand_light": "sand",
    "forest": "forest",
    "dirt": "dirt",
    "stone": "stone",
    "white": "snow"
}


def ground(kind, dots, seed, density):
    """v1.1 ground textures: blades, ripples, leaf litter, pebbles, cracks, snow drifts (all tile-local)."""
    rnd = random.Random(seed)
    base = {"grass": "grass", "sand": "sand_light", "forest": "forest", "dirt": "dirt", "stone": "stone", "snow": "white"}[kind]
    c = Canvas(T, T).rect(0, 0, T, T, base)
    n = max(2, int(density * 50))
    for i in range(n):
        x, y = rnd.randrange(1, T - 2), rnd.randrange(1, T - 3)
        if kind == "grass":
            c.px(x, y, "grass_light"); c.px(x, y + 1, "grass_light")
            c.px(x + 1, y + 1, "forest") if i % 2 else c.px(x - 1, y + 2, "forest")
        elif kind == "sand":
            L = rnd.choice((3, 4))
            c.line(x, y, min(x + L, T - 1), y, "sand"); c.px(x + 1, y + 1, "white") if i % 3 == 0 else None
        elif kind == "forest":
            c.px(x, y, "grass"); c.rect(x, y + 1, 2, 1, "forest_dark")
            if i % 4 == 0:
                c.line(x, y, x + 2, y + 2, "wood_dark")
        elif kind == "dirt":
            if i % 3 == 0:
                c.rect(x, y, 2, 1, "stone"); c.px(x, y + 1, "wood")
            else:
                c.line(x, y, x + 2, y + 1, "wood"); c.px(x + 3, y + 1, "sand") if i % 2 else None
        elif kind == "stone":
            c.line(x, y, x + 3, y + 1, "stone_dark"); c.px(x, y - 1, "stone_light"); c.px(x + 1, y - 1, "stone_light")
        else:  # snow
            c.px(x, y, "foam" if i % 2 else "stone_light")
            if i % 3 == 0:
                c.line(x, y + 1, x + 2, y + 1, "stone_light")
    for _ in range(max(1, n // 3)):  # accent sprinkle taken from the caller's colour hints (flowers, shells, roots...)
        c.px(rnd.randrange(T), rnd.randrange(T), rnd.choice(dots))
    return c


def speckle(base, dots, seed, density=0.12):
    return ground(KIND[base], dots, seed, density)


def water(base, light, seed):
    """Tileable waves; seeds 741/742 and 761/762 are the animation frames (phase 1/2): the pattern slides sideways."""
    phase = {741: 1, 742: 2, 761: 1, 762: 2}.get(seed, 0)
    c = Canvas(T, T).rect(0, 0, T, T, base)
    for k, y in enumerate((2, 7, 12)):
        x0 = (y * 5 + phase * 5) % T
        for i in range(4):
            c.px((x0 + i) % T, y, light)
        for i in range(2):
            c.px((x0 + 8 + i) % T, (y + 3) % T, light)
        if base == "water":
            c.px((x0 + 2) % T, y - 1, "foam") if (k + phase) % 2 == 0 else None
    return c


def tree():
    c = Canvas(T, T)
    # trunk
    c.rect(7, 10, 2, 5, "wood_dark")
    # foliage base
    c.circle(8, 6, 5, "forest_dark")
    c.circle(7, 5, 4, "forest")
    c.circle(6, 4, 2, "grass")
    c.px(5, 3, "grass_light")
    c.px(6, 3, "grass_light")
    c.outline("outline")
    return c


def rock():
    c = Canvas(T, T)
    c.ellipse(3, 6, 10, 7, "stone_dark")
    c.ellipse(4, 7, 7, 5, "stone")
    c.px(6, 7, "stone_light")
    c.px(7, 7, "stone_light")
    c.outline("outline")
    return c


def bush():
    c = Canvas(T, T)
    # Leafy shrub with lobes
    c.circle(5, 9, 3, "forest_dark")
    c.circle(10, 9, 3, "forest_dark")
    c.circle(7, 7, 3, "forest")
    c.circle(5, 8, 2, "forest")
    c.circle(10, 8, 2, "forest")
    c.circle(7, 6, 2, "grass")
    c.px(6, 5, "grass_light")
    c.px(8, 5, "grass_light")
    c.px(7, 6, "grass_light")
    c.px(4, 8, "grass")
    c.px(10, 8, "grass")
    c.outline("outline")
    return c


def flower():
    c = Canvas(T, T)
    # Green stems / leaves
    c.line(4, 11, 4, 13, "forest")
    c.line(8, 10, 8, 13, "forest")
    c.line(12, 11, 12, 13, "forest")
    c.px(3, 12, "grass")
    c.px(9, 12, "grass")
    c.px(11, 12, "grass")
    # Blossom 1: red with gold center
    c.rect(3, 8, 3, 3, "red")
    c.px(4, 9, "gold")
    # Blossom 2: gold with white center
    c.rect(7, 6, 3, 3, "gold")
    c.px(8, 7, "white")
    # Blossom 3: violet with gold_light center
    c.rect(10, 8, 3, 3, "violet")
    c.px(11, 9, "gold_light")
    c.outline("outline")
    return c


def cactus():
    c = Canvas(T, T)
    # Main trunk
    c.rect(7, 3, 3, 12, "forest")
    c.rect(8, 3, 1, 12, "grass")
    # Left arm
    c.rect(4, 7, 3, 2, "forest")
    c.rect(3, 5, 2, 4, "forest")
    c.rect(4, 5, 1, 3, "grass")
    # Right arm
    c.rect(10, 8, 3, 2, "forest")
    c.rect(11, 6, 2, 4, "forest")
    c.rect(11, 6, 1, 3, "grass")
    # Spine highlights
    c.px(8, 4, "grass_light")
    c.px(8, 7, "grass_light")
    c.px(8, 10, "grass_light")
    c.outline("outline")
    return c


def snow_pine():
    c = Canvas(T, T)
    # Trunk
    c.rect(7, 12, 2, 3, "wood_dark")
    # Bottom tier
    c.rect(3, 10, 10, 2, "forest_dark")
    c.rect(4, 9, 8, 2, "white")
    # Middle tier
    c.rect(5, 7, 6, 2, "forest_dark")
    c.rect(5, 6, 6, 2, "white")
    # Top tier
    c.rect(6, 4, 4, 2, "forest_dark")
    c.rect(7, 2, 2, 3, "white")
    c.px(7, 1, "white")
    # Shadow hints under snow
    c.px(3, 11, "night")
    c.px(12, 11, "night")
    c.outline("outline")
    return c


def shell():
    c = Canvas(T, T)
    # Seashell at (4, 9)
    c.rect(4, 9, 4, 4, "skin")
    c.rect(5, 8, 3, 4, "skin_shade")
    c.px(6, 9, "white")
    c.px(5, 10, "white")
    c.px(7, 11, "sand_light")
    # Starfish at (10, 8)
    c.px(10, 8, "orange")
    c.px(9, 8, "orange")
    c.px(11, 8, "orange")
    c.px(10, 7, "orange")
    c.px(10, 9, "orange")
    c.px(10, 8, "gold_light")
    c.outline("outline")
    return c


def make_transition(base_fn, edge_fill, edge_speckle, accent, mask, seed=0, depth=4):
    c = base_fn()
    if mask == 0:
        return c

    rnd = random.Random(seed + mask * 17)

    def wob(t, ph):  # periodic along the edge (period 16) -> neighbouring tiles join without seams
        return round(1.1 * math.sin(2 * math.pi * (t + ph) / 16) + 0.8 * math.sin(4 * math.pi * (t + 3 * ph) / 16))

    for y in range(T):
        for x in range(T):
            dists = []
            if mask & 1: dists.append(y + wob(x, 1))
            if mask & 2: dists.append(15 - x + wob(y, 2))
            if mask & 4: dists.append(15 - y + wob(x, 3))
            if mask & 8: dists.append(x + wob(y, 4))
            if not dists:
                continue

            d = min(dists)
            if d < depth - 1:
                col = edge_fill
                if edge_speckle and rnd.random() < 0.2:
                    col = rnd.choice(edge_speckle)
                c.px(x, y, col)
            elif d == depth - 1:
                c.px(x, y, accent)

    return c


# Columns 0..14: Base & overlay tiles (index == Tile.id)
TILES = [
    ("deep_water", lambda: water("deep_water", "water", 0)),
    ("water", lambda: water("water", "water_light", 1)),
    ("sand", lambda: speckle("sand_light", ["sand"], 2)),
    ("grass", lambda: speckle("grass", ["grass_light", "forest"], 3)),
    ("forest", lambda: speckle("forest", ["forest_dark", "grass"], 4, 0.18)),
    ("dirt", lambda: speckle("dirt", ["wood", "sand"], 5)),
    ("stone", lambda: speckle("stone", ["stone_dark", "stone_light"], 6)),
    ("snow", lambda: speckle("white", ["stone_light", "foam"], 7, 0.08)),
    ("tree", tree),
    ("rock", rock),
    ("bush", bush),
    ("flower", flower),
    ("cactus", cactus),
    ("snow_pine", snow_pine),
    ("shell", shell),
]


def build(ctx=None):
    if ctx is None:
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        out_tiles = root / "game" / "assets" / "tiles"
        out_preview = root / "build" / "art_preview"
        class DefaultCtx:
            tiles = out_tiles
            preview = out_preview
        ctx = DefaultCtx()

    # 1. Base and overlay tiles (columns 0..14)
    base_imgs = [fn().done() for _, fn in TILES]

    # 2. Autotile transitions (columns 15..78)
    water_sand = [
        make_transition(
            base_fn=lambda m=m: water("water", "water_light", 10 + m),
            edge_fill="sand",
            edge_speckle=["sand_light"],
            accent="foam",
            mask=m,
            seed=100 + m,
            depth=4
        ).done()
        for m in range(16)
    ]

    sand_grass = [
        make_transition(
            base_fn=lambda m=m: speckle("sand_light", ["sand"], 20 + m),
            edge_fill="grass",
            edge_speckle=["forest"],
            accent="grass_light",
            mask=m,
            seed=200 + m,
            depth=4
        ).done()
        for m in range(16)
    ]

    grass_forest = [
        make_transition(
            base_fn=lambda m=m: speckle("grass", ["grass_light", "forest"], 30 + m),
            edge_fill="forest",
            edge_speckle=["forest_dark"],
            accent="forest_dark",
            mask=m,
            seed=300 + m,
            depth=4
        ).done()
        for m in range(16)
    ]

    stone_edge = [
        make_transition(
            base_fn=lambda m=m: speckle("stone", ["stone_dark", "stone_light"], 40 + m),
            edge_fill="stone_dark",
            edge_speckle=["stone"],
            accent="outline",
            mask=m,
            seed=400 + m,
            depth=4
        ).done()
        for m in range(16)
    ]

    # 3. Animated water extra frames (columns 79..82)
    # DEEP_WATER frames 1 and 2 (columns 79..80)
    deep_water_anims = [
        water("deep_water", "water", 741).done(),
        water("deep_water", "water", 742).done(),
    ]
    # WATER frames 1 and 2 (columns 81..82)
    water_anims = [
        water("water", "water_light", 761).done(),
        water("water", "water_light", 762).done(),
    ]

    # 4. Extra variants for 6 walkable ground types (3 per type, columns 83..100)
    # SAND (columns 83..85)
    sand_variants = [
        speckle("sand_light", ["sand"], 781, density=0.07).done(),
        speckle("sand_light", ["sand", "foam"], 782, density=0.15).done(),
        speckle("sand_light", ["sand", "dirt"], 783, density=0.18).done(),
    ]
    # GRASS (columns 86..88) - toned down gold_light density to 0.03 for distinct flowers
    grass_variants = [
        speckle("grass", ["grass_light"], 811, density=0.15).done(),
        speckle("grass", ["grass_light", "gold_light"], 812, density=0.03).done(),
        speckle("grass", ["forest", "grass_light"], 813, density=0.18).done(),
    ]
    # FOREST (columns 89..91)
    forest_variants = [
        speckle("forest", ["forest_dark"], 841, density=0.14).done(),
        speckle("forest", ["forest_dark", "grass"], 842, density=0.22).done(),
        speckle("forest", ["wood_dark", "forest_dark"], 843, density=0.16).done(),
    ]
    # DIRT (columns 92..94)
    dirt_variants = [
        speckle("dirt", ["wood", "sand"], 871, density=0.08).done(),
        speckle("dirt", ["stone", "wood"], 872, density=0.14).done(),
        speckle("dirt", ["sand", "stone_dark"], 873, density=0.16).done(),
    ]
    # STONE (columns 95..97)
    stone_variants = [
        speckle("stone", ["stone_dark"], 901, density=0.14).done(),
        speckle("stone", ["stone_light"], 902, density=0.16).done(),
        speckle("stone", ["stone_dark", "stone_light"], 903, density=0.22).done(),
    ]
    # SNOW (columns 98..100)
    snow_variants = [
        speckle("white", ["foam"], 931, density=0.06).done(),
        speckle("white", ["stone_light", "foam"], 932, density=0.12).done(),
        speckle("white", ["stone_light"], 933, density=0.09).done(),
    ]

    extra_variants = (
        sand_variants +
        grass_variants +
        forest_variants +
        dirt_variants +
        stone_variants +
        snow_variants
    )

    all_tiles = (
        base_imgs +          # 0..14 (15)
        water_sand +         # 15..30 (16)
        sand_grass +         # 31..46 (16)
        grass_forest +       # 47..62 (16)
        stone_edge +         # 63..78 (16)
        deep_water_anims +   # 79..80 (2)
        water_anims +        # 81..82 (2)
        extra_variants       # 83..100 (18)
    )
    assert len(all_tiles) == 101, f"Expected 101 tiles, got {len(all_tiles)}"

    atlas = Image.new("RGBA", (T * len(all_tiles), T), (0, 0, 0, 0))
    for i, im in enumerate(all_tiles):
        atlas.paste(im, (i * T, 0))

    ctx.tiles.mkdir(parents=True, exist_ok=True)
    atlas.save(ctx.tiles / "terrain.png")

    # Save contact sheet for visual review:
    # Row 0: 15 base tiles
    # Row 1: 16 water->sand
    # Row 2: 16 sand->grass
    # Row 3: 16 grass->forest
    # Row 4: 16 stone edge
    # Row 5: 4 water anims + 18 ground variants (total 22 tiles)
    row5 = deep_water_anims + water_anims + extra_variants
    preview_w = max(16, len(row5)) * T * 4
    preview_h = 6 * T * 4
    preview = Image.new("RGBA", (preview_w, preview_h), PAL["preview_bg"])

    rows = [
        base_imgs,
        water_sand,
        sand_grass,
        grass_forest,
        stone_edge,
        row5
    ]
    for r_idx, row in enumerate(rows):
        for c_idx, im in enumerate(row):
            im_scaled = im.resize((T * 4, T * 4), Image.NEAREST)
            preview.paste(im_scaled, (c_idx * T * 4, r_idx * T * 4))

    ctx.preview.mkdir(parents=True, exist_ok=True)
    preview.save(ctx.preview / "terrain_contact.png")
