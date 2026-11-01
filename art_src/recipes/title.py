# Author: Agent-worker-cody
"""Title screen art recipe: 3-layer 400x224 parallax backgrounds + logo.
Generates:
  - game/assets/backgrounds/title_sky.png (400x224, opaque)
  - game/assets/backgrounds/title_islands.png (400x224, transparent upper)
  - game/assets/backgrounds/title_foreground.png (400x224, transparent upper/center)
  - game/assets/ui/logo.png (220x52, transparent)
  - build/art_preview/title_preview.png (800x448 preview)
"""
from pathlib import Path
from PIL import Image
from pixelkit import svg_doc, svg_frame, hexc, PAL

W, H = 400, 224


def make_sky_svg() -> str:
    body = f'''
    <!-- Sky gradient bands -->
    <rect x="0" y="0" width="400" height="35" fill="{hexc('night')}"/>
    <rect x="0" y="35" width="400" height="30" fill="{hexc('deep_water')}"/>
    <rect x="0" y="65" width="400" height="30" fill="{hexc('water')}"/>
    <rect x="0" y="95" width="400" height="25" fill="{hexc('water_light')}"/>
    <rect x="0" y="120" width="400" height="20" fill="{hexc('sand_light')}"/>

    <!-- Stars in deep night sky -->
    <rect x="25" y="10" width="2" height="2" fill="{hexc('white')}"/>
    <rect x="75" y="18" width="1" height="1" fill="{hexc('foam')}"/>
    <rect x="130" y="8" width="2" height="2" fill="{hexc('gold_light')}"/>
    <rect x="180" y="22" width="1" height="1" fill="{hexc('white')}"/>
    <rect x="235" y="12" width="2" height="2" fill="{hexc('foam')}"/>
    <rect x="290" y="25" width="1" height="1" fill="{hexc('white')}"/>
    <rect x="345" y="15" width="2" height="2" fill="{hexc('gold_light')}"/>
    <rect x="380" y="8" width="1" height="1" fill="{hexc('white')}"/>

    <!-- Gentle distant morning clouds -->
    <rect x="40" y="72" width="55" height="5" rx="2" fill="{hexc('foam')}"/>
    <rect x="52" y="70" width="30" height="4" rx="2" fill="{hexc('white')}"/>
    <rect x="260" y="80" width="65" height="6" rx="3" fill="{hexc('foam')}"/>
    <rect x="275" y="78" width="35" height="4" rx="2" fill="{hexc('white')}"/>

    <!-- Glowing Dawn Sun -->
    <circle cx="200" cy="120" r="28" fill="{hexc('orange')}"/>
    <circle cx="200" cy="120" r="24" fill="{hexc('gold')}"/>
    <circle cx="200" cy="120" r="18" fill="{hexc('gold_light')}"/>
    <circle cx="200" cy="120" r="12" fill="{hexc('white')}"/>

    <!-- Ocean Base -->
    <rect x="0" y="140" width="400" height="84" fill="{hexc('deep_water')}"/>

    <!-- Sun reflection on water -->
    <rect x="180" y="140" width="40" height="3" fill="{hexc('gold_light')}"/>
    <rect x="185" y="144" width="30" height="2" fill="{hexc('gold')}"/>
    <rect x="175" y="148" width="50" height="2" fill="{hexc('orange')}"/>
    <rect x="188" y="152" width="24" height="2" fill="{hexc('gold')}"/>
    <rect x="182" y="156" width="36" height="2" fill="{hexc('water_light')}"/>

    <!-- Distant water ripples -->
    <rect x="20" y="145" width="25" height="1" fill="{hexc('water')}"/>
    <rect x="90" y="152" width="35" height="1" fill="{hexc('water_light')}"/>
    <rect x="280" y="146" width="40" height="1" fill="{hexc('water')}"/>
    <rect x="340" y="154" width="30" height="1" fill="{hexc('water_light')}"/>
    <rect x="60" y="165" width="50" height="1" fill="{hexc('water')}"/>
    <rect x="250" y="168" width="45" height="1" fill="{hexc('water')}"/>
    '''
    return svg_doc(W, H, body)


def make_islands_svg() -> str:
    body = f'''
    <!-- Left Archipelago (x=20..140) -->
    <polygon points="20,158 55,128 85,122 110,136 140,158" fill="{hexc('forest_dark')}"/>
    <polygon points="35,158 60,132 85,126 105,138 130,158" fill="{hexc('forest')}"/>
    <polygon points="50,158 75,136 85,130 95,140 115,158" fill="{hexc('grass')}"/>

    <!-- Ancient Ruin Pillars on West Island Peak -->
    <rect x="78" y="112" width="4" height="14" fill="{hexc('stone_dark')}"/>
    <rect x="79" y="113" width="2" height="13" fill="{hexc('stone')}"/>
    <rect x="88" y="116" width="4" height="10" fill="{hexc('stone_dark')}"/>
    <rect x="89" y="117" width="2" height="9" fill="{hexc('stone')}"/>
    <rect x="76" y="110" width="18" height="3" fill="{hexc('stone')}"/>

    <!-- Sandy beach cove for West Island -->
    <rect x="30" y="157" width="105" height="4" fill="{hexc('sand')}"/>
    <rect x="45" y="160" width="75" height="2" fill="{hexc('sand_light')}"/>
    <rect x="25" y="161" width="115" height="2" fill="{hexc('foam')}"/>

    <!-- Right Archipelago (x=250..375) -->
    <polygon points="250,160 280,134 315,126 345,138 375,160" fill="{hexc('forest_dark')}"/>
    <polygon points="265,160 285,138 315,130 335,142 360,160" fill="{hexc('forest')}"/>
    <polygon points="280,160 300,142 315,134 325,144 345,160" fill="{hexc('grass')}"/>

    <!-- Ancient Stone Archway on East Ridge -->
    <rect x="308" y="120" width="3" height="10" fill="{hexc('stone_dark')}"/>
    <rect x="319" y="120" width="3" height="10" fill="{hexc('stone_dark')}"/>
    <rect x="306" y="118" width="18" height="3" fill="{hexc('stone')}"/>

    <!-- Sandy beach spit for East Island -->
    <rect x="260" y="159" width="105" height="4" fill="{hexc('sand')}"/>
    <rect x="275" y="162" width="75" height="2" fill="{hexc('sand_light')}"/>
    <rect x="255" y="163" width="115" height="2" fill="{hexc('foam')}"/>

    <!-- Wave crests around mid-ground -->
    <rect x="15" y="166" width="35" height="2" fill="{hexc('water_light')}"/>
    <rect x="145" y="168" width="40" height="2" fill="{hexc('water_light')}"/>
    <rect x="230" y="170" width="35" height="2" fill="{hexc('water_light')}"/>
    <rect x="370" y="168" width="25" height="2" fill="{hexc('water_light')}"/>
    '''
    return svg_doc(W, H, body)


def make_foreground_svg() -> str:
    body = f'''
    <!-- Left Foreground Shore & Palm Canopy (x=0..115) -->
    <polygon points="0,178 40,178 80,188 115,224 0,224" fill="{hexc('dirt')}"/>
    <polygon points="0,180 35,180 75,190 105,224 0,224" fill="{hexc('sand')}"/>
    <polygon points="0,182 30,182 65,192 90,224 0,224" fill="{hexc('sand_light')}"/>

    <!-- Boulder on left shore -->
    <ellipse cx="60" cy="195" rx="16" ry="10" fill="{hexc('outline')}"/>
    <ellipse cx="60" cy="194" rx="14" ry="8" fill="{hexc('stone_dark')}"/>
    <ellipse cx="58" cy="192" rx="9" ry="5" fill="{hexc('stone')}"/>

    <!-- Left Palm Trunk -->
    <path d="M 0,224 Q 15,160 5,100 L 9,100 Q 20,160 8,224 Z" fill="{hexc('wood_dark')}"/>
    <path d="M 1,224 Q 16,160 6,100 L 8,100 Q 18,160 7,224 Z" fill="{hexc('wood')}"/>

    <!-- Left Palm Canopy -->
    <path d="M 7,100 Q 35,80 70,95 Q 40,92 7,102 Z" fill="{hexc('forest_dark')}"/>
    <path d="M 7,100 Q 25,60 55,68 Q 30,75 7,102 Z" fill="{hexc('forest')}"/>
    <path d="M 7,100 Q -10,65 -25,80 Q -10,85 7,102 Z" fill="{hexc('forest_dark')}"/>
    <path d="M 7,100 Q 15,110 45,120 Q 25,118 7,102 Z" fill="{hexc('outline')}"/>

    <!-- Right Foreground Shore with Treasure Chest (x=285..400) -->
    <polygon points="285,224 320,188 360,178 400,178 400,224" fill="{hexc('dirt')}"/>
    <polygon points="295,224 325,190 365,180 400,180 400,224" fill="{hexc('sand')}"/>
    <polygon points="310,224 335,192 370,182 400,182 400,224" fill="{hexc('sand_light')}"/>

    <!-- Right Palm Tree -->
    <path d="M 395,224 Q 380,160 392,95 L 396,95 Q 385,160 399,224 Z" fill="{hexc('wood_dark')}"/>
    <path d="M 394,224 Q 379,160 391,95 L 393,95 Q 383,160 397,224 Z" fill="{hexc('wood')}"/>
    <path d="M 393,95 Q 365,75 330,90 Q 360,88 393,97 Z" fill="{hexc('forest_dark')}"/>
    <path d="M 393,95 Q 375,55 345,64 Q 370,70 393,97 Z" fill="{hexc('forest')}"/>
    <path d="M 393,95 Q 410,60 425,75 Q 410,80 393,97 Z" fill="{hexc('forest_dark')}"/>

    <!-- Gleaming Treasure Chest sitting on Right Shore (x=336, y=186) -->
    <ellipse cx="347" cy="196" rx="14" ry="4" fill="{hexc('shadow')}"/>
    <rect x="336" y="186" width="22" height="9" fill="{hexc('wood_dark')}"/>
    <rect x="337" y="187" width="20" height="7" fill="{hexc('wood')}"/>
    <rect x="336" y="185" width="22" height="2" fill="{hexc('gold')}"/>
    <rect x="340" y="186" width="2" height="9" fill="{hexc('gold')}"/>
    <rect x="352" y="186" width="2" height="9" fill="{hexc('gold')}"/>
    <rect x="345" y="188" width="4" height="4" fill="{hexc('gold')}"/>
    <rect x="346" y="189" width="2" height="2" fill="{hexc('gold_light')}"/>
    <rect x="335" y="183" width="24" height="3" rx="1" fill="{hexc('wood_dark')}"/>
    <rect x="336" y="183" width="22" height="2" fill="{hexc('gold_light')}"/>
    <!-- Sparkle Glint -->
    <polygon points="356,180 357,178 358,180 360,181 358,182 357,184 356,182 354,181" fill="{hexc('white')}"/>
    <rect x="356" y="180" width="2" height="2" fill="{hexc('gold_light')}"/>
    '''
    return svg_doc(W, H, body)


def make_logo_svg() -> str:
    LW, LH = 220, 52

    # Letter definitions for "FISHARIUM" (9 letters)
    # Each letter is a list of rects (x, y, w, h) relative to its origin
    letters = [
        # F (14w)
        [(0, 0, 4, 20), (0, 0, 14, 4), (0, 8, 11, 4)],
        # I (12w)
        [(4, 0, 4, 20), (0, 0, 12, 4), (0, 16, 12, 4)],
        # S (14w)
        [(0, 0, 14, 4), (0, 0, 4, 10), (0, 8, 14, 4), (10, 10, 4, 10), (0, 16, 14, 4)],
        # H (14w)
        [(0, 0, 4, 20), (10, 0, 4, 20), (0, 8, 14, 4)],
        # A (14w)
        [(0, 4, 4, 16), (10, 4, 4, 16), (2, 0, 10, 4), (0, 10, 14, 4)],
        # R (14w)
        [(0, 0, 4, 20), (0, 0, 14, 4), (10, 0, 4, 10), (0, 8, 14, 4), (7, 12, 4, 4), (10, 16, 4, 4)],
        # I (12w)
        [(4, 0, 4, 20), (0, 0, 12, 4), (0, 16, 12, 4)],
        # U (14w)
        [(0, 0, 4, 17), (10, 0, 4, 17), (2, 16, 10, 4)],
        # M (18w)
        [(0, 0, 4, 20), (14, 0, 4, 20), (4, 4, 3, 6), (11, 4, 3, 6), (7, 8, 4, 6)],
    ]

    x_offsets = [12, 30, 46, 64, 82, 100, 118, 134, 152]
    base_y = 16

    parts = []

    # Banner Frame Background
    parts.append(f'''
    <!-- Banner backing -->
    <rect x="4" y="8" width="212" height="36" rx="4" fill="{hexc('outline')}"/>
    <rect x="6" y="10" width="208" height="32" rx="3" fill="{hexc('wood_dark')}"/>
    <rect x="8" y="12" width="204" height="28" rx="2" fill="{hexc('night')}"/>
    <!-- Gold filigree corners -->
    <rect x="10" y="14" width="6" height="2" fill="{hexc('gold')}"/>
    <rect x="10" y="14" width="2" height="6" fill="{hexc('gold')}"/>
    <rect x="204" y="14" width="6" height="2" fill="{hexc('gold')}"/>
    <rect x="208" y="14" width="2" height="6" fill="{hexc('gold')}"/>
    <rect x="10" y="36" width="6" height="2" fill="{hexc('gold')}"/>
    <rect x="10" y="32" width="2" height="6" fill="{hexc('gold')}"/>
    <rect x="204" y="36" width="6" height="2" fill="{hexc('gold')}"/>
    <rect x="208" y="32" width="2" height="6" fill="{hexc('gold')}"/>

    <!-- Compass rose emblem at right -->
    <polygon points="186,26 189,20 192,26 198,29 192,32 189,38 186,32 180,29" fill="{hexc('gold')}"/>
    <polygon points="187,27 189,23 191,27 195,29 191,31 189,35 187,31 183,29" fill="{hexc('gold_light')}"/>
    <circle cx="189" cy="29" r="2" fill="{hexc('white')}"/>
    ''')

    # Draw letters: Shadow (+2, +2), Bevel (+1, +1), Face (0, 0), Top highlight
    for idx, rects in enumerate(letters):
        ox = x_offsets[idx]
        # Shadow
        for (rx, ry, rw, rh) in rects:
            parts.append(f'<rect x="{ox + rx + 2}" y="{base_y + ry + 2}" width="{rw}" height="{rh}" fill="{hexc("outline")}"/>')
        # Extrusion / Bevel
        for (rx, ry, rw, rh) in rects:
            parts.append(f'<rect x="{ox + rx + 1}" y="{base_y + ry + 1}" width="{rw}" height="{rh}" fill="{hexc("orange")}"/>')
        # Face
        for (rx, ry, rw, rh) in rects:
            parts.append(f'<rect x="{ox + rx}" y="{base_y + ry}" width="{rw}" height="{rh}" fill="{hexc("gold_light")}"/>')
        # Subtle top highlight
        for (rx, ry, rw, rh) in rects:
            if ry == 0:
                parts.append(f'<rect x="{ox + rx}" y="{base_y + ry}" width="{rw}" height="2" fill="{hexc("white")}"/>')

    return svg_doc(LW, LH, "".join(parts))


def build(ctx):
    # 1. Generate the 3 parallax layers (400x224 each)
    sky_img = svg_frame(make_sky_svg(), W, H, snap=True)
    islands_img = svg_frame(make_islands_svg(), W, H, snap=True)
    fg_img = svg_frame(make_foreground_svg(), W, H, snap=True)

    # 2. Generate the Logo (220x52)
    logo_img = svg_frame(make_logo_svg(), 220, 52, snap=True)

    # Save to game/assets
    ctx.backgrounds.mkdir(parents=True, exist_ok=True)
    ctx.ui.mkdir(parents=True, exist_ok=True)
    ctx.preview.mkdir(parents=True, exist_ok=True)

    sky_img.save(ctx.backgrounds / "title_sky.png")
    islands_img.save(ctx.backgrounds / "title_islands.png")
    fg_img.save(ctx.backgrounds / "title_foreground.png")
    logo_img.save(ctx.ui / "logo.png")

    # 3. Composite preview (800x448, 2x scaled)
    comp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    comp.alpha_composite(sky_img)
    comp.alpha_composite(islands_img)
    comp.alpha_composite(fg_img)

    # Center the logo on the composite (x = (400 - 220) // 2 = 90, y = 32)
    comp.alpha_composite(logo_img, ((W - logo_img.width) // 2, 32))

    preview = comp.resize((W * 2, H * 2), Image.NEAREST)
    preview.save(ctx.preview / "title_preview.png")
