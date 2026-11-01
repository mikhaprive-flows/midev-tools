"""
artkit - CLI for the Fisharium art pipeline.

  tools\\art.ps1 build             # run every recipe in art_src/recipes -> game/assets/...
  tools\\art.ps1 build player      # run one recipe (file name without .py)
  tools\\art.ps1 validate          # palette / size / alpha checks on game/assets/**.png
  tools\\art.ps1 new <name>        # scaffold a new recipe from the template
  tools\\art.ps1 list              # list recipes

Recipes are plain Python files exposing `build(ctx)`; see art_src/recipes/_template.py.
Previews (scaled GIF/PNG) go to build/art_preview/ - open them with read_file to self-review.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pixelkit
from pixelkit import PAL, ROOT  # noqa: E402
from PIL import Image  # noqa: E402

RECIPES = ROOT / "art_src" / "recipes"
ASSETS = ROOT / "game" / "assets"
PREVIEW = ROOT / "build" / "art_preview"

# Active output targets (default to project game/assets and build/art_preview; overrideable for isolated sandboxes)
CURRENT_OUT_DIR = ASSETS
CURRENT_PREVIEW_DIR = PREVIEW


class Canvas(pixelkit.Canvas):
    @property
    def _px(self):
        pix = self.img.load()
        res = {}
        for y in range(self.h):
            for x in range(self.w):
                if pix[x, y][3] > 0:
                    res[(x, y)] = pix[x, y]
        return res

    def hline(self, x, y, w, c):
        return self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        return self.rect(x, y, 1, h, c)

    def blit(self, other):
        return self.paste(other)


class Sheet:
    def __init__(self, fw: int, fh: int, origin: tuple[int, int] | None = None):
        self.fw, self.fh = fw, fh
        self.origin = origin
        self.anims: list[tuple[str, list, float, bool]] = []

    def add_anim(self, name: str, frames: list, fps: float = 8, loop: bool = True):
        self.anims.append((name, frames, fps, loop))
        return self


def save_sheet(name: str, sheet: Sheet):
    parts = name.split("/")
    sheet_name = parts[-1]
    sub_dir = CURRENT_OUT_DIR / "/".join(parts[:-1]) if len(parts) > 1 else CURRENT_OUT_DIR
    sub_dir.mkdir(parents=True, exist_ok=True)

    sb = pixelkit.SheetBuilder(sheet_name, sheet.fw, sheet.fh, sheet.origin)
    for anim_name, frames, fps, loop in sheet.anims:
        sb.add(anim_name, frames, fps=fps, loop=loop)
    return sb.save(sub_dir)


def save_preview_gif(filename: str, frames: list, fps: float = 10, scale: int = 4):
    CURRENT_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    big = []
    for f in frames:
        im = f.done() if isinstance(f, (Canvas, pixelkit.Canvas)) else (f.img if hasattr(f, "img") else f)
        bg = Image.new("RGBA", im.size, PAL["preview_bg"])
        bg.alpha_composite(im)
        big.append(bg.resize((im.width * scale, im.height * scale), Image.NEAREST).convert("P"))
    if big:
        big[0].save(
            CURRENT_PREVIEW_DIR / filename,
            save_all=True,
            append_images=big[1:],
            duration=int(1000 / fps),
            loop=0,
            disposal=2,
        )


class Ctx:
    def __init__(self):
        self.assets = ASSETS
        self.sprites = ASSETS / "sprites"
        self.tiles = ASSETS / "tiles"
        self.ui = ASSETS / "ui"
        self.backgrounds = ASSETS / "backgrounds"
        self.preview = PREVIEW


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def recipes():
    return sorted(p for p in RECIPES.glob("*.py") if not p.name.startswith("_"))


def cmd_build(names):
    todo = [p for p in recipes() if not names or p.stem in names]
    if not todo:
        print("no matching recipes"); return 1
    ctx = Ctx()
    for p in todo:
        print(f"[art] {p.stem} ...", flush=True)
        load(p).build(ctx)
    return cmd_validate()


def cmd_validate():
    bad = 0
    for png in sorted(ASSETS.rglob("*.png")):
        im = Image.open(png).convert("RGBA")
        rel = png.relative_to(ROOT)
        errs = []
        v = PAL.violations(im)
        if v and "backgrounds" not in png.parts:
            errs.append(f"{v} off-palette px")
        if any(0 < a < 255 for a in im.getchannel("A").tobytes()):
            errs.append("semi-transparent px (alpha must be 0/255)")
        meta = png.with_suffix(".json")
        if meta.exists():
            m = json.loads(meta.read_text())
            if im.width % m["frameWidth"] or im.height % m["frameHeight"]:
                errs.append("sheet size not a multiple of frame size")
        if errs:
            bad += 1
            print(f"  FAIL {rel}: {'; '.join(errs)}")
        else:
            print(f"  ok   {rel} {im.size}")
    print("validate:", "PASSED" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


def cmd_new(name):
    dst = RECIPES / f"{name}.py"
    if dst.exists():
        print("exists:", dst); return 1
    dst.write_text((RECIPES / "_template.py").read_text().replace("TEMPLATE", name))
    print("created", dst); return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    c, rest = argv[0], argv[1:]
    if c == "build": return cmd_build(rest)
    if c == "validate": return cmd_validate()
    if c == "new" and rest: return cmd_new(rest[0])
    if c == "list":
        for p in recipes(): print(p.stem)
        return 0
    print(__doc__); return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
