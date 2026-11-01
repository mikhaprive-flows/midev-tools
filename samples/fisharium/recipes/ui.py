# Author: Agent-worker-helpy
"""UI art recipe: crisp 32-bit pixel font and ornate 9-slice RPG HUD frame.
Generates:
  - game/assets/ui/font.png (128x64 px, 95 ASCII chars on 16x6 grid of 8x10 cells)
  - game/assets/ui/font.fnt (libGDX BMFont text descriptor)
  - game/assets/ui/hud_frame.png (24x24 px 9-slice RPG frame with 8x8 corners)
  - build/art_preview/ui_preview.png (composite 4x scaled preview)
"""
from pathlib import Path
from PIL import Image, ImageDraw
from pixelkit import PAL, Canvas

# -----------------------------------------------------------------------------
# 5x7 Pixel Font Glyph Definitions (ASCII 32 to 126, 95 chars)
# 8 rows per glyph: rows 0..6 (uppercase / ascenders / baseline), row 7 (descender)
# -----------------------------------------------------------------------------
GLYPHS: dict[int, list[str]] = {
    # 32..47: Space and punctuation
    32: [  # ' '
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
    ],
    33: [  # '!'
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        ".....",
        "..#..",
        ".....",
    ],
    34: [  # '"'
        ".#.#.",
        ".#.#.",
        ".#.#.",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
    ],
    35: [  # '#'
        ".#.#.",
        "#####",
        ".#.#.",
        ".#.#.",
        "#####",
        ".#.#.",
        ".....",
        ".....",
    ],
    36: [  # '$'
        "..#..",
        ".####",
        "#.#..",
        ".###.",
        "..#.#",
        "####.",
        "..#..",
        ".....",
    ],
    37: [  # '%'
        "##..#",
        "##.#.",
        "...#.",
        "..#..",
        ".#...",
        ".#.##",
        "#..##",
        ".....",
    ],
    38: [  # '&'
        ".##..",
        "#..#.",
        "#..#.",
        ".##..",
        "#..#.",
        "#..#.",
        ".##.#",
        ".....",
    ],
    39: [  # '\''
        "..#..",
        "..#..",
        ".#...",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
    ],
    40: [  # '('
        "...#.",
        "..#..",
        ".#...",
        ".#...",
        ".#...",
        "..#..",
        "...#.",
        ".....",
    ],
    41: [  # ')'
        ".#...",
        "..#..",
        "...#.",
        "...#.",
        "...#.",
        "..#..",
        ".#...",
        ".....",
    ],
    42: [  # '*'
        ".....",
        ".#.#.",
        "..#..",
        "#####",
        "..#..",
        ".#.#.",
        ".....",
        ".....",
    ],
    43: [  # '+'
        ".....",
        "..#..",
        "..#..",
        "#####",
        "..#..",
        "..#..",
        ".....",
        ".....",
    ],
    44: [  # ','
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
        "..##.",
        "..#..",
        ".#...",
    ],
    45: [  # '-'
        ".....",
        ".....",
        ".....",
        "#####",
        ".....",
        ".....",
        ".....",
        ".....",
    ],
    46: [  # '.'
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
        ".##..",
        ".##..",
        ".....",
    ],
    47: [  # '/'
        "....#",
        "...#.",
        "..#..",
        "..#..",
        ".#...",
        "#....",
        ".....",
        ".....",
    ],

    # 48..57: Digits '0'..'9'
    48: [  # '0'
        ".###.",
        "#..##",
        "#.#.#",
        "#.#.#",
        "##..#",
        "#...#",
        ".###.",
        ".....",
    ],
    49: [  # '1'
        "..#..",
        ".##..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        ".###.",
        ".....",
    ],
    50: [  # '2'
        ".###.",
        "#...#",
        "....#",
        "..##.",
        ".#...",
        "#....",
        "#####",
        ".....",
    ],
    51: [  # '3'
        "####.",
        "....#",
        "....#",
        ".###.",
        "....#",
        "....#",
        "####.",
        ".....",
    ],
    52: [  # '4'
        "#...#",
        "#...#",
        "#...#",
        "#####",
        "....#",
        "....#",
        "....#",
        ".....",
    ],
    53: [  # '5'
        "#####",
        "#....",
        "####.",
        "....#",
        "....#",
        "#...#",
        ".###.",
        ".....",
    ],
    54: [  # '6'
        ".###.",
        "#....",
        "#....",
        "####.",
        "#...#",
        "#...#",
        ".###.",
        ".....",
    ],
    55: [  # '7'
        "#####",
        "....#",
        "...#.",
        "..#..",
        ".#...",
        ".#...",
        ".#...",
        ".....",
    ],
    56: [  # '8'
        ".###.",
        "#...#",
        "#...#",
        ".###.",
        "#...#",
        "#...#",
        ".###.",
        ".....",
    ],
    57: [  # '9'
        ".###.",
        "#...#",
        "#...#",
        ".####",
        "....#",
        "....#",
        ".###.",
        ".....",
    ],

    # 58..64: Punctuation and symbols
    58: [  # ':'
        ".....",
        ".##..",
        ".##..",
        ".....",
        ".##..",
        ".##..",
        ".....",
        ".....",
    ],
    59: [  # ';'
        ".....",
        ".##..",
        ".##..",
        ".....",
        "..##.",
        "..#..",
        ".#...",
        ".....",
    ],
    60: [  # '<'
        "...#.",
        "..#..",
        ".#...",
        "#....",
        ".#...",
        "..#..",
        "...#.",
        ".....",
    ],
    61: [  # '='
        ".....",
        "#####",
        ".....",
        "#####",
        ".....",
        ".....",
        ".....",
        ".....",
    ],
    62: [  # '>'
        ".#...",
        "..#..",
        "...#.",
        "....#",
        "...#.",
        "..#..",
        ".#...",
        ".....",
    ],
    63: [  # '?'
        ".###.",
        "#...#",
        "....#",
        "..##.",
        "..#..",
        ".....",
        "..#..",
        ".....",
    ],
    64: [  # '@'
        ".###.",
        "#...#",
        "..###",
        ".#..#",
        ".#..#",
        "#...#",
        ".###.",
        ".....",
    ],

    # 65..90: Uppercase Letters 'A'..'Z'
    65: [  # 'A'
        ".###.",
        "#...#",
        "#...#",
        "#####",
        "#...#",
        "#...#",
        "#...#",
        ".....",
    ],
    66: [  # 'B'
        "####.",
        "#...#",
        "#...#",
        "####.",
        "#...#",
        "#...#",
        "####.",
        ".....",
    ],
    67: [  # 'C'
        ".###.",
        "#...#",
        "#....",
        "#....",
        "#....",
        "#...#",
        ".###.",
        ".....",
    ],
    68: [  # 'D'
        "####.",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "####.",
        ".....",
    ],
    69: [  # 'E'
        "#####",
        "#....",
        "#....",
        "####.",
        "#....",
        "#....",
        "#####",
        ".....",
    ],
    70: [  # 'F'
        "#####",
        "#....",
        "#....",
        "####.",
        "#....",
        "#....",
        "#....",
        ".....",
    ],
    71: [  # 'G'
        ".###.",
        "#...#",
        "#....",
        "#..##",
        "#...#",
        "#...#",
        ".###.",
        ".....",
    ],
    72: [  # 'H'
        "#...#",
        "#...#",
        "#...#",
        "#####",
        "#...#",
        "#...#",
        "#...#",
        ".....",
    ],
    73: [  # 'I'
        "#####",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "#####",
        ".....",
    ],
    74: [  # 'J'
        "...##",
        "....#",
        "....#",
        "....#",
        "....#",
        "#...#",
        ".###.",
        ".....",
    ],
    75: [  # 'K'
        "#...#",
        "#..#.",
        "#.#..",
        "##...",
        "#.#..",
        "#..#.",
        "#...#",
        ".....",
    ],
    76: [  # 'L'
        "#....",
        "#....",
        "#....",
        "#....",
        "#....",
        "#....",
        "#####",
        ".....",
    ],
    77: [  # 'M'
        "#...#",
        "##.##",
        "#.#.#",
        "#.#.#",
        "#...#",
        "#...#",
        "#...#",
        ".....",
    ],
    78: [  # 'N'
        "#...#",
        "##..#",
        "#.#.#",
        "#..##",
        "#...#",
        "#...#",
        "#...#",
        ".....",
    ],
    79: [  # 'O'
        ".###.",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        ".###.",
        ".....",
    ],
    80: [  # 'P'
        "####.",
        "#...#",
        "#...#",
        "####.",
        "#....",
        "#....",
        "#....",
        ".....",
    ],
    81: [  # 'Q'
        ".###.",
        "#...#",
        "#...#",
        "#...#",
        "#.#.#",
        "#..#.",
        ".##.#",
        ".....",
    ],
    82: [  # 'R'
        "####.",
        "#...#",
        "#...#",
        "####.",
        "#.#..",
        "#..#.",
        "#...#",
        ".....",
    ],
    83: [  # 'S'
        ".####",
        "#....",
        "#....",
        ".###.",
        "....#",
        "....#",
        "####.",
        ".....",
    ],
    84: [  # 'T'
        "#####",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        ".....",
    ],
    85: [  # 'U'
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        ".###.",
        ".....",
    ],
    86: [  # 'V'
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        ".#.#.",
        "..#..",
        ".....",
    ],
    87: [  # 'W'
        "#...#",
        "#...#",
        "#...#",
        "#.#.#",
        "#.#.#",
        "##.##",
        "#...#",
        ".....",
    ],
    88: [  # 'X'
        "#...#",
        "#...#",
        ".#.#.",
        "..#..",
        ".#.#.",
        "#...#",
        "#...#",
        ".....",
    ],
    89: [  # 'Y'
        "#...#",
        "#...#",
        ".#.#.",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        ".....",
    ],
    90: [  # 'Z'
        "#####",
        "....#",
        "...#.",
        "..#..",
        ".#...",
        "#....",
        "#####",
        ".....",
    ],

    # 91..96: Brackets and symbols
    91: [  # '['
        ".###.",
        ".#...",
        ".#...",
        ".#...",
        ".#...",
        ".#...",
        ".###.",
        ".....",
    ],
    92: [  # '\\'
        "#....",
        ".#...",
        "..#..",
        "..#..",
        "...#.",
        "....#",
        ".....",
        ".....",
    ],
    93: [  # ']'
        ".###.",
        "...#.",
        "...#.",
        "...#.",
        "...#.",
        "...#.",
        ".###.",
        ".....",
    ],
    94: [  # '^'
        "..#..",
        ".#.#.",
        "#...#",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
    ],
    95: [  # '_'
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
        "#####",
        ".....",
    ],
    96: [  # '`'
        ".#...",
        "..#..",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
    ],

    # 97..122: Lowercase Letters 'a'..'z'
    97: [  # 'a'
        ".....",
        ".....",
        ".###.",
        "....#",
        ".####",
        "#...#",
        ".####",
        ".....",
    ],
    98: [  # 'b'
        "#....",
        "#....",
        "####.",
        "#...#",
        "#...#",
        "#...#",
        "####.",
        ".....",
    ],
    99: [  # 'c'
        ".....",
        ".....",
        ".###.",
        "#....",
        "#....",
        "#....",
        ".###.",
        ".....",
    ],
    100: [  # 'd'
        "....#",
        "....#",
        ".####",
        "#...#",
        "#...#",
        "#...#",
        ".####",
        ".....",
    ],
    101: [  # 'e'
        ".....",
        ".....",
        ".###.",
        "#...#",
        "#####",
        "#....",
        ".###.",
        ".....",
    ],
    102: [  # 'f'
        "..##.",
        ".#..#",
        ".#...",
        "####.",
        ".#...",
        ".#...",
        ".#...",
        ".....",
    ],
    103: [  # 'g' (descender)
        ".....",
        ".....",
        ".####",
        "#...#",
        "#...#",
        ".####",
        "....#",
        ".###.",
    ],
    104: [  # 'h'
        "#....",
        "#....",
        "####.",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        ".....",
    ],
    105: [  # 'i'
        "..#..",
        ".....",
        ".##..",
        "..#..",
        "..#..",
        "..#..",
        ".###.",
        ".....",
    ],
    106: [  # 'j' (descender)
        "...#.",
        ".....",
        "..##.",
        "...#.",
        "...#.",
        "...#.",
        "#..#.",
        ".##..",
    ],
    107: [  # 'k'
        "#....",
        "#....",
        "#..#.",
        "#.#..",
        "##...",
        "#.#..",
        "#..#.",
        ".....",
    ],
    108: [  # 'l'
        ".##..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        ".###.",
        ".....",
    ],
    109: [  # 'm'
        ".....",
        ".....",
        "##.##",
        "#.#.#",
        "#.#.#",
        "#...#",
        "#...#",
        ".....",
    ],
    110: [  # 'n'
        ".....",
        ".....",
        "####.",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        ".....",
    ],
    111: [  # 'o'
        ".....",
        ".....",
        ".###.",
        "#...#",
        "#...#",
        "#...#",
        ".###.",
        ".....",
    ],
    112: [  # 'p' (descender)
        ".....",
        ".....",
        "####.",
        "#...#",
        "#...#",
        "####.",
        "#....",
        "#....",
    ],
    113: [  # 'q' (descender)
        ".....",
        ".....",
        ".####",
        "#...#",
        "#...#",
        ".####",
        "....#",
        "....#",
    ],
    114: [  # 'r'
        ".....",
        ".....",
        "####.",
        "#..#.",
        "#....",
        "#....",
        "#....",
        ".....",
    ],
    115: [  # 's'
        ".....",
        ".....",
        ".####",
        "#....",
        ".###.",
        "....#",
        "####.",
        ".....",
    ],
    116: [  # 't'
        ".#...",
        ".#...",
        "####.",
        ".#...",
        ".#...",
        ".#..#",
        "..##.",
        ".....",
    ],
    117: [  # 'u'
        ".....",
        ".....",
        "#...#",
        "#...#",
        "#...#",
        "#...#",
        ".####",
        ".....",
    ],
    118: [  # 'v'
        ".....",
        ".....",
        "#...#",
        "#...#",
        "#...#",
        ".#.#.",
        "..#..",
        ".....",
    ],
    119: [  # 'w'
        ".....",
        ".....",
        "#...#",
        "#...#",
        "#.#.#",
        "#.#.#",
        ".#.#.",
        ".....",
    ],
    120: [  # 'x'
        ".....",
        ".....",
        "#...#",
        ".#.#.",
        "..#..",
        ".#.#.",
        "#...#",
        ".....",
    ],
    121: [  # 'y' (descender)
        ".....",
        ".....",
        "#...#",
        "#...#",
        "#...#",
        ".####",
        "....#",
        ".###.",
    ],
    122: [  # 'z'
        ".....",
        ".....",
        "#####",
        "...#.",
        "..#..",
        ".#...",
        "#####",
        ".....",
    ],

    # 123..126: Braces and tilde
    123: [  # '{'
        "..##.",
        "..#..",
        "..#..",
        ".#...",
        "..#..",
        "..#..",
        "..##.",
        ".....",
    ],
    124: [  # '|'
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        ".....",
    ],
    125: [  # '}'
        ".##..",
        "..#..",
        "..#..",
        "...#.",
        "..#..",
        "..#..",
        ".##..",
        ".....",
    ],
    126: [  # '~'
        ".....",
        ".##.#",
        "#..##",
        ".....",
        ".....",
        ".....",
        ".....",
        ".....",
    ],
}


def make_font_image() -> Image.Image:
    """Generate 128x64 image with 95 ASCII characters in a 16x6 grid of 8x10 cells.
    Glyphs are drawn with 'white' fill and a 1px dark 'outline' shadow (+1, +1, +1/0, 0/+1).
    """
    img = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
    white = PAL["white"]
    outline = PAL["outline"]

    for code in range(32, 127):
        i = code - 32
        col = i % 16
        row = i // 16
        cell_x = col * 8
        cell_y = row * 10

        pattern = GLYPHS.get(code)
        if not pattern:
            continue

        # Collect set of white pixels for this character
        white_pixels: set[tuple[int, int]] = set()
        for r, line in enumerate(pattern):
            for c, char in enumerate(line):
                if char == '#':
                    # String row r maps to cell row (1 + r); col c maps to cell col (1 + c)
                    px = cell_x + 1 + c
                    py = cell_y + 1 + r
                    white_pixels.add((px, py))

        # Collect shadow pixels at (+1, 0), (0, +1), and (+1, +1)
        shadow_pixels: set[tuple[int, int]] = set()
        for px, py in white_pixels:
            for dx, dy in [(1, 0), (0, 1), (1, 1)]:
                sp = (px + dx, py + dy)
                if sp not in white_pixels:
                    shadow_pixels.add(sp)

        # Draw shadow first, then white pixels
        for px, py in shadow_pixels:
            if 0 <= px < 128 and 0 <= py < 64:
                img.putpixel((px, py), outline)

        for px, py in white_pixels:
            if 0 <= px < 128 and 0 <= py < 64:
                img.putpixel((px, py), white)

    return PAL.snap(img)


def make_bmfont_descriptor() -> str:
    """Generate BMFont text descriptor for font.fnt."""
    lines = [
        'info face="FishariumPixel" size=10 bold=0 italic=0 charset="" unicode=0 stretchH=100 smooth=0 aa=0 padding=0,0,0,0 spacing=1,1',
        'common lineHeight=11 base=8 scaleW=128 scaleH=64 pages=1 packed=0',
        'page id=0 file="font.png"',
        'chars count=95',
    ]
    for code in range(32, 127):
        i = code - 32
        col = i % 16
        row = i // 16
        x = col * 8
        y = row * 10
        # Monospace advance 6 fits 5px glyph + 1px shadow cleanly
        lines.append(f"char id={code} x={x} y={y} width=8 height=10 xoffset=0 yoffset=0 xadvance=6 page=0 chnl=0")

    return "\n".join(lines) + "\n"


def make_hud_frame() -> Image.Image:
    """Generate 24x24 px 9-slice RPG UI frame (8x8 corners/edges, 8x8 center).
    - Outer 1px border: 'outline'
    - Bevel: 'gold' (top/left) and 'wood_dark' (bottom/right)
    - Corner rivets: 'gold_light' (strictly in corners 0..7 and 16..23)
    - Inner 1px rim: 'wood'
    - Center fill: 'night' (opaque dark navy #3d3a5c)
    """
    c = Canvas(24, 24)

    # 1. Fill entire background with opaque 'night'
    c.rect(0, 0, 24, 24, "night", fill=True)

    # 2. Outer 1px border in 'outline'
    c.rect(0, 0, 24, 24, "outline", fill=False)

    # 3. 2px beveled border:
    # Top & Left: 'gold'
    for x in range(1, 23):
        c.px(x, 1, "gold")
        c.px(x, 2, "gold")
    for y in range(1, 23):
        c.px(1, y, "gold")
        c.px(2, y, "gold")

    # Bottom & Right: 'wood_dark'
    for x in range(1, 23):
        c.px(x, 21, "wood_dark")
        c.px(x, 22, "wood_dark")
    for y in range(1, 23):
        c.px(21, y, "wood_dark")
        c.px(22, y, "wood_dark")

    # 4. Inner 1px rim in 'wood'
    c.rect(3, 3, 18, 18, "wood", fill=False)

    # 5. Center fill inside rim (x in 4..19, y in 4..19) is 'night'
    c.rect(4, 4, 16, 16, "night", fill=True)

    # 6. Ornate golden rivets strictly inside 8x8 corner regions:
    # Top-Left corner (around 2, 2)
    c.px(2, 2, "gold_light")
    c.px(3, 2, "gold_light")
    c.px(2, 3, "gold")

    # Top-Right corner (around 21, 2)
    c.px(20, 2, "gold_light")
    c.px(21, 2, "gold_light")
    c.px(21, 3, "wood_dark")

    # Bottom-Left corner (around 2, 21)
    c.px(2, 20, "gold_light")
    c.px(3, 20, "gold_light")
    c.px(2, 21, "wood_dark")

    # Bottom-Right corner (around 21, 21)
    c.px(20, 20, "gold_light")
    c.px(21, 20, "gold_light")
    c.px(21, 21, "outline")

    # Notice: across the stretchable range (8..15):
    # Every column across x in 8..15 is identical.
    # Every row across y in 8..15 is identical.
    return c.done()


def build(ctx):
    """Entry point called by tools/art.ps1 build ui."""
    ctx.ui.mkdir(parents=True, exist_ok=True)
    ctx.preview.mkdir(parents=True, exist_ok=True)

    # 1. Build font.png and font.fnt
    font_img = make_font_image()
    font_img.save(ctx.ui / "font.png")

    fnt_descriptor = make_bmfont_descriptor()
    (ctx.ui / "font.fnt").write_text(fnt_descriptor, encoding="utf-8")

    # 2. Build hud_frame.png
    hud_frame_img = make_hud_frame()
    hud_frame_img.save(ctx.ui / "hud_frame.png")

    # 3. Create composite preview ui_preview.png (scaled 4x)
    # Shows font sheet + sample stretched frames with text
    pw, ph = 560, 320
    preview = Image.new("RGBA", (pw, ph), PAL["night"])
    d = ImageDraw.Draw(preview)

    # Paste 4x font sheet
    font_scaled = font_img.resize((128 * 2, 64 * 2), Image.Resampling.NEAREST)
    preview.paste(font_scaled, (16, 16), font_scaled)

    # Simulate 9-slice frame scaling for status bar (196x20) and inventory panel (140x90)
    def render_9slice(src: Image.Image, dst_w: int, dst_h: int) -> Image.Image:
        res = Image.new("RGBA", (dst_w, dst_h), (0, 0, 0, 0))
        # 4 corners (8x8)
        tl = src.crop((0, 0, 8, 8))
        tr = src.crop((16, 0, 24, 8))
        bl = src.crop((0, 16, 8, 24))
        br = src.crop((16, 16, 24, 24))
        # 4 edges
        top = src.crop((8, 0, 16, 8)).resize((dst_w - 16, 8), Image.Resampling.NEAREST)
        bot = src.crop((8, 16, 16, 24)).resize((dst_w - 16, 8), Image.Resampling.NEAREST)
        left = src.crop((0, 8, 8, 16)).resize((8, dst_h - 16), Image.Resampling.NEAREST)
        right = src.crop((16, 8, 24, 16)).resize((8, dst_h - 16), Image.Resampling.NEAREST)
        # Center
        center = src.crop((8, 8, 16, 16)).resize((dst_w - 16, dst_h - 16), Image.Resampling.NEAREST)

        res.paste(center, (8, 8))
        res.paste(top, (8, 0))
        res.paste(bot, (8, dst_h - 8))
        res.paste(left, (0, 8))
        res.paste(right, (dst_w - 8, 8))
        res.paste(tl, (0, 0))
        res.paste(tr, (dst_w - 8, 0))
        res.paste(bl, (0, dst_h - 8))
        res.paste(br, (dst_w - 8, dst_h - 8))
        return res

    frame_status = render_9slice(hud_frame_img, 240, 24)
    preview.paste(frame_status, (280, 16), frame_status)

    frame_inv = render_9slice(hud_frame_img, 240, 140)
    preview.paste(frame_inv, (280, 52), frame_inv)

    preview_scaled = preview.resize((pw, ph), Image.Resampling.NEAREST)
    preview_scaled.save(ctx.preview / "ui_preview.png")
    print(f"  ok   ui assets generated: font.png (128x64), font.fnt, hud_frame.png (24x24)")
