"""
character - Parametric Humanoid Character Rig & Animation Synthesizer.
Generates 4-directional animated sprite sheets with swappable equipment, hair, and clothing layers.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any
from pixelkit import Canvas, SheetBuilder

VALID_HAIR_STYLES = {"short", "long", "spiky", "bald"}
VALID_OUTFITS = {"tunic", "armor", "robe"}
VALID_WEAPONS = {"sword", "staff", "bow", "axe", None}
VALID_HELMETS = {"cap", "helm", "hood", None}
VALID_SHIELDS = {"wood_shield", "buckler", None}


@dataclass
class CharacterConfig:
    width: int = 16
    height: int = 24
    skin_tone: str = "peach"
    skin_shadow: str = "sand"
    hair_style: str = "short"     # "short", "long", "spiky", "bald"
    hair_color: str = "brown"
    outfit: str = "tunic"         # "tunic", "armor", "robe"
    outfit_color: str = "dark_blue"
    pants_color: str = "navy"
    shoes_color: str = "wood"
    weapon: str | None = "sword"  # "sword", "staff", "bow", "axe", None
    weapon_color: str = "iron"
    helmet: str | None = None     # "cap", "helm", "hood", None
    shield: str | None = None     # "wood_shield", "buckler", None

    def __post_init__(self):
        def check_field(field_name: str, value: Any, valid_set: set[Any]):
            if value is None and None in valid_set:
                return
            if value not in valid_set:
                candidates = [str(x) for x in sorted(valid_set, key=lambda v: str(v)) if x is not None]
                val_str = str(value)
                matches = difflib.get_close_matches(val_str, candidates, n=3, cutoff=0.4)
                hint = f". Did you mean: {', '.join(repr(m) for m in matches)}?" if matches else ""
                options = ", ".join(repr(x) for x in candidates)
                raise ValueError(
                    f"Invalid {field_name}='{value}'. Supported options: [{options}]{hint}"
                )

        check_field("hair_style", self.hair_style, VALID_HAIR_STYLES)
        check_field("outfit", self.outfit, VALID_OUTFITS)
        check_field("weapon", self.weapon, VALID_WEAPONS)
        check_field("helmet", self.helmet, VALID_HELMETS)
        check_field("shield", self.shield, VALID_SHIELDS)


class CharacterGenerator:
    """Builds multi-directional animated character sprite sheets."""

    def __init__(self, config: CharacterConfig | None = None):
        self.cfg = config or CharacterConfig()
        self.w = self.cfg.width
        self.h = self.cfg.height
        self.cx = self.w // 2

    def draw_figure(
        self,
        facing: str = "down",
        dy: int = 0,
        leg_phase: int = 0,     # -1, 0, 1
        arm_phase: int = 0,     # -1, 0, 1
        attack_phase: int = 0,  # 0=none, 1=windup, 2=strike, 3=recover
        hurt: bool = False,
    ) -> Canvas:
        c = Canvas(self.w, self.h)
        cfg = self.cfg
        cx = self.cx

        skin = "foam" if hurt else cfg.skin_tone
        hair_col = cfg.hair_color
        outfit_col = "coral" if hurt else cfg.outfit_color
        pants_col = cfg.pants_color
        shoes_col = cfg.shoes_color
        weapon_col = cfg.weapon_color

        # Vertical body anchor
        head_y = 4 + dy
        torso_y = head_y + 6
        pelvis_y = torso_y + 6
        feet_y = self.h - 3

        # 1. Legs & Shoes
        if facing in ("down", "up"):
            l_dy = -1 if leg_phase > 0 else 0
            c.rect(cx - 3, pelvis_y, 2, 4 + l_dy, pants_col)
            c.rect(cx - 3, feet_y + l_dy, 2, 2, shoes_col)

            r_dy = -1 if leg_phase < 0 else 0
            c.rect(cx + 1, pelvis_y, 2, 4 + r_dy, pants_col)
            c.rect(cx + 1, feet_y + r_dy, 2, 2, shoes_col)
        else:  # side
            step_off = leg_phase * 2
            c.rect(cx - 1 + step_off, pelvis_y, 3, 4, pants_col)
            c.rect(cx - 1 + step_off, feet_y, 3, 2, shoes_col)
            if abs(leg_phase) > 0:
                c.rect(cx - 1 - step_off, pelvis_y, 3, 4, pants_col)
                c.rect(cx - 1 - step_off, feet_y, 3, 2, shoes_col)

        # 2. Torso & Outfit
        if cfg.outfit == "robe":
            if facing in ("down", "up"):
                c.rect(cx - 3, torso_y, 6, 11, outfit_col)
                c.rect(cx - 3, pelvis_y - 1, 6, 1, "outline")
            else:
                c.rect(cx - 2, torso_y, 5, 11, outfit_col)
                c.rect(cx - 2, pelvis_y - 1, 5, 1, "outline")
        elif cfg.outfit == "armor":
            if facing in ("down", "up"):
                c.rect(cx - 3, torso_y, 6, 6, outfit_col)
                c.rect(cx - 4, torso_y, 1, 3, "iron")
                c.rect(cx + 3, torso_y, 1, 3, "iron")
                c.rect(cx - 2, torso_y + 1, 4, 3, "iron")
                c.px(cx - 1, torso_y + 1, "white")
                c.rect(cx - 3, pelvis_y - 1, 6, 1, "gold")
            else:
                c.rect(cx - 2, torso_y, 5, 6, outfit_col)
                c.rect(cx - 2, torso_y, 4, 3, "iron")
                c.px(cx - 1, torso_y + 1, "white")
                c.rect(cx - 2, pelvis_y - 1, 5, 1, "gold")
        else:  # tunic
            if facing in ("down", "up"):
                c.rect(cx - 3, torso_y, 6, 6, outfit_col)
                c.rect(cx - 3, pelvis_y - 1, 6, 1, "outline")
            else:
                c.rect(cx - 2, torso_y, 5, 6, outfit_col)
                c.rect(cx - 2, pelvis_y - 1, 5, 1, "outline")

        # 3. Head & Skin
        if facing in ("down", "up"):
            c.rect(cx - 3, head_y, 6, 6, skin)
            if facing == "down" and not hurt:
                c.px(cx - 2, head_y + 3, "outline")
                c.px(cx + 1, head_y + 3, "outline")
            elif hurt:
                c.px(cx - 2, head_y + 3, "coral")
                c.px(cx + 1, head_y + 3, "coral")
        else:  # side
            c.rect(cx - 2, head_y, 5, 6, skin)
            if not hurt:
                c.px(cx + 1, head_y + 3, "outline")

        # 4. Hair / Helmet
        if cfg.helmet == "cap":
            c.rect(cx - 4, head_y - 1, 8, 2, outfit_col)
            c.px(cx + 3, head_y, outfit_col)
        elif cfg.helmet == "helm":
            c.rect(cx - 4, head_y - 1, 8, 3, "iron")
            c.rect(cx - 3, head_y - 2, 6, 2, "iron")
        elif cfg.helmet == "hood":
            c.rect(cx - 4, head_y - 1, 8, 4, outfit_col)
            c.rect(cx - 3, head_y - 2, 6, 2, outfit_col)
        elif cfg.hair_style != "bald":
            c.rect(cx - 3, head_y - 1, 6, 2, hair_col)
            if facing == "up":
                c.rect(cx - 3, head_y, 6, 4, hair_col)
            elif facing == "side":
                c.rect(cx - 3, head_y - 1, 4, 3, hair_col)
            if cfg.hair_style == "spiky":
                c.px(cx - 2, head_y - 2, hair_col)
                c.px(cx, head_y - 3, hair_col)
                c.px(cx + 2, head_y - 2, hair_col)
            elif cfg.hair_style == "long":
                c.rect(cx - 4, head_y + 2, 1, 4, hair_col)
                c.rect(cx + 3, head_y + 2, 1, 4, hair_col)

        # 5. Shield on off-hand (left)
        if cfg.shield and attack_phase == 0:
            if cfg.shield == "buckler":
                if facing in ("down", "up"):
                    c.rect(cx - 5, torso_y + 2, 3, 3, "iron")
                    c.px(cx - 4, torso_y + 3, "gold")
                elif facing == "side":
                    c.rect(cx - 3, torso_y + 2, 2, 3, "iron")
            elif cfg.shield == "wood_shield":
                if facing in ("down", "up"):
                    c.rect(cx - 5, torso_y + 1, 3, 5, "wood")
                    c.px(cx - 4, torso_y + 3, "iron")
                elif facing == "side":
                    c.rect(cx - 3, torso_y + 1, 2, 5, "wood")

        # 6. Arms & Weapon
        arm_off = arm_phase * 2
        if attack_phase > 0:
            if attack_phase == 1:  # Windup
                w_x, w_y = cx - 4, head_y - 2
                c.rect(cx - 4, torso_y, 2, 4, skin)
            elif attack_phase == 2:  # Strike
                w_x, w_y = cx + 4, torso_y + 2
                c.rect(cx + 3, torso_y + 1, 3, 2, skin)
            else:  # Recover
                w_x, w_y = cx + 3, torso_y + 4
                c.rect(cx + 2, torso_y + 2, 2, 3, skin)

            if cfg.weapon == "sword":
                c.line(w_x, w_y, w_x + 3, w_y - 5, weapon_col)
                c.px(w_x, w_y, "gold")
            elif cfg.weapon == "staff":
                c.line(w_x, w_y + 3, w_x + 1, w_y - 7, "wood")
                c.px(w_x + 1, w_y - 8, "cyan")
            elif cfg.weapon == "axe":
                c.line(w_x, w_y + 2, w_x + 2, w_y - 5, "wood")
                c.rect(w_x + 1, w_y - 6, 3, 3, weapon_col)
            elif cfg.weapon == "bow":
                c.line(w_x, w_y - 5, w_x + 2, w_y - 2, "wood")
                c.line(w_x + 2, w_y - 2, w_x, w_y + 1, "wood")
                c.line(w_x, w_y - 5, w_x, w_y + 1, "outline")
        else:
            if facing in ("down", "up"):
                c.rect(cx - 4, torso_y + 1 + arm_off, 2, 4, skin)
                c.rect(cx + 3, torso_y + 1 - arm_off, 2, 4, skin)
                if facing == "down":
                    if cfg.weapon == "sword":
                        c.line(cx + 4, torso_y + 4, cx + 4, torso_y + 9, weapon_col)
                        c.px(cx + 4, torso_y + 4, "gold")
                    elif cfg.weapon == "axe":
                        c.line(cx + 4, torso_y + 4, cx + 4, torso_y + 9, "wood")
                        c.rect(cx + 3, torso_y + 4, 3, 2, weapon_col)
                    elif cfg.weapon == "staff":
                        c.line(cx + 4, torso_y + 2, cx + 4, torso_y + 10, "wood")
                        c.px(cx + 4, torso_y + 1, "cyan")
                    elif cfg.weapon == "bow":
                        c.line(cx + 4, torso_y + 3, cx + 4, torso_y + 8, "wood")
            else:  # side
                c.rect(cx + 1, torso_y + 1 + arm_off, 2, 4, skin)
                if cfg.weapon == "sword":
                    c.line(cx + 2, torso_y + 3, cx + 5, torso_y + 6, weapon_col)
                elif cfg.weapon == "axe":
                    c.line(cx + 2, torso_y + 3, cx + 5, torso_y + 6, "wood")
                    c.rect(cx + 4, torso_y + 5, 2, 2, weapon_col)
                elif cfg.weapon == "staff":
                    c.line(cx + 2, torso_y + 1, cx + 5, torso_y + 8, "wood")
                elif cfg.weapon == "bow":
                    c.line(cx + 3, torso_y + 2, cx + 3, torso_y + 7, "wood")

        c.outline()
        return c

    def generate_idle(self, facing: str = "down") -> list[Canvas]:
        frames = []
        for i in range(4):
            dy = 1 if i in (1, 2) else 0
            frames.append(self.draw_figure(facing=facing, dy=dy))
        return frames

    def generate_walk(self, facing: str = "down") -> list[Canvas]:
        phases = [
            (0, 0, 0),
            (1, 1, -1),
            (0, 1, -1),
            (0, 0, 0),
            (-1, -1, 1),
            (0, -1, 1),
        ]
        frames = []
        for dy, leg, arm in phases:
            frames.append(self.draw_figure(facing=facing, dy=dy, leg_phase=leg, arm_phase=arm))
        return frames

    def generate_attack(self, facing: str = "down") -> list[Canvas]:
        frames = []
        for phase in (1, 2, 2, 3):
            frames.append(self.draw_figure(facing=facing, attack_phase=phase))
        return frames

    def generate_hurt(self, facing: str = "down") -> list[Canvas]:
        return [
            self.draw_figure(facing=facing, dy=-1, hurt=True),
            self.draw_figure(facing=facing, dy=1, hurt=True),
            self.draw_figure(facing=facing, dy=0, hurt=False),
        ]

    def generate_sheet(self, sheet_name: str = "character") -> SheetBuilder:
        sb = SheetBuilder(sheet_name, self.w, self.h, origin=(self.cx, self.h - 4))
        for facing in ("down", "up", "side"):
            sb.add(f"idle_{facing}", self.generate_idle(facing), fps=5, loop=True)
            sb.add(f"walk_{facing}", self.generate_walk(facing), fps=9, loop=True)
            sb.add(f"attack_{facing}", self.generate_attack(facing), fps=12, loop=False)
            sb.add(f"hurt_{facing}", self.generate_hurt(facing), fps=8, loop=False)
        return sb
