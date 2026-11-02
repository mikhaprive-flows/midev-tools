"""
inspect_tool - Multimodal Visual Verification Engine for midev-tools.
Generates high-contrast, annotated inspection sheets (4x scale) with
frame strips, cell bounding boxes, origin crosshairs, and palette swatches.
Ideal for human developers and multimodal AI agents.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import artkit
import pixelkit
import projects
from config import MidevConfig
from manifest import Manifest


def _get_font(size: int = 12) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _hex_color(rgba: tuple[int, int, int, int]) -> str:
    return f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}"


def generate_inspection_sheet(
    recipe_name: str,
    scale: int = 4,
    out_path: Path | str | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    """
    Build and render an annotated visual inspection sheet for the given recipe.
    Returns metadata dictionary with sheet file path, frame dimensions, and color analysis.
    """
    # 1. Build the recipe to ensure fresh assets
    if quiet:
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            build_ret = artkit.cmd_build([recipe_name], force=True)
    else:
        build_ret = artkit.cmd_build([recipe_name], force=True)

    if build_ret != 0:
        raise RuntimeError(f"Build failed for recipe '{recipe_name}'")

    cfg = artkit.CONFIG
    out_dir = cfg.output_dir
    active_proj = projects.get_active_project()

    # 2. Locate primary spritesheet and metadata
    target_png = None
    target_json = None

    manifest = Manifest(out_dir / "manifest.json")
    primary_entry = manifest.find_primary_asset(recipe_name)
    if primary_entry:
        for f in primary_entry.files:
            p = out_dir / f
            if p.suffix.lower() == ".png" and p.exists() and not target_png:
                target_png = p
            elif p.suffix.lower() == ".json" and p.exists() and not target_json:
                target_json = p
        if not target_png:
            candidate = out_dir / primary_entry.category / f"{Path(primary_entry.asset_id).stem}.png"
            if candidate.exists():
                target_png = candidate
                target_json = candidate.with_suffix(".json")

    if not target_png:
        for cat in ("sprites", "tiles", "ui", "backgrounds"):
            candidate_png = out_dir / cat / f"{recipe_name}.png"
            if candidate_png.exists():
                target_png = candidate_png
                target_json = candidate_png.with_suffix(".json")
                break

    if not target_png:
        for cat in ("sprites", "tiles", "ui", "backgrounds"):
            cat_dir = out_dir / cat
            if cat_dir.exists():
                for f in sorted(cat_dir.rglob("*.png")):
                    if f.stem == recipe_name and not f.name.startswith("."):
                        target_png = f
                        target_json = f.with_suffix(".json")
                        break
            if target_png:
                break

    if not target_png or not target_png.exists():
        raise FileNotFoundError(f"No exported spritesheet found for recipe '{recipe_name}' in {out_dir}")

    sheet_img = Image.open(target_png).convert("RGBA")
    meta = {}
    if target_json and target_json.exists():
        try:
            meta = json.loads(target_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    if primary_entry and primary_entry.frame_size and primary_entry.frame_size[0] > 0:
        fw = primary_entry.frame_size[0]
        fh = primary_entry.frame_size[1]
    else:
        fw = meta.get("frameWidth", sheet_img.width)
        fh = meta.get("frameHeight", sheet_img.height)

    if primary_entry and primary_entry.origin and primary_entry.origin != [0, 0]:
        ox = primary_entry.origin[0]
        oy = primary_entry.origin[1]
    else:
        ox = meta.get("originX", fw // 2)
        oy = meta.get("originY", fh - 2)

    anims = meta.get("animations", {})
    if not anims and primary_entry and primary_entry.anims:
        anims = {anim_name: {"row": i, "frames": max(1, sheet_img.width // fw), "fps": 6, "loop": True}
                 for i, anim_name in enumerate(primary_entry.anims)}
    elif not anims:
        anims = {"default": {"row": 0, "frames": max(1, sheet_img.width // fw), "fps": 6, "loop": True}}

    # 3. Extract unique non-transparent colors
    unique_colors: set[tuple[int, int, int, int]] = set()
    alpha_violations = 0
    raw_pixels = sheet_img.load()
    for y in range(sheet_img.height):
        for x in range(sheet_img.width):
            px = raw_pixels[x, y]
            a = px[3]
            if a > 0:
                unique_colors.add(px)
                if 0 < a < 255:
                    alpha_violations += 1

    sorted_colors = sorted(list(unique_colors), key=lambda c: (c[0] + c[1] + c[2]))
    pal = pixelkit.PAL
    off_palette_count = pal.violations(sheet_img) if pal else 0

    # 4. Compose the Inspection Sheet Canvas
    # Dimensions calculation
    max_frames = max(anim_data.get("frames", 1) for anim_data in anims.values())
    cell_w = fw * scale
    cell_h = fh * scale
    pad = 16
    header_h = 70
    swatch_h = 60
    row_gap = 36

    content_w = max(520, pad * 2 + max_frames * (cell_w + 8))
    content_h = header_h + len(anims) * (cell_h + row_gap) + swatch_h + pad * 2

    canvas = Image.new("RGBA", (content_w, content_h), (13, 17, 23, 255))  # #0d1117 dark background
    draw = ImageDraw.Draw(canvas)
    f_title = _get_font(16)
    f_body = _get_font(12)
    f_mono = _get_font(10)

    # 5. Draw Header Bar
    draw.rectangle([0, 0, content_w, header_h], fill=(22, 27, 34, 255))
    draw.line([0, header_h, content_w, header_h], fill=(48, 54, 61, 255), width=1)

    draw.text((pad, 12), f"midev Visual Inspect: {recipe_name}", fill=(0, 240, 255, 255), font=f_title)
    sub_info = (
        f"Project: {active_proj.title} | Frame: {fw}x{fh}px | Origin: ({ox}, {oy}) | "
        f"Palette: {cfg.palette} | Alpha: {'100% Binary' if alpha_violations == 0 else f'{alpha_violations} Semi-trans'}"
    )
    draw.text((pad, 38), sub_info, fill=(139, 148, 158, 255), font=f_body)

    # Compliance Badges top right
    badge_x = content_w - pad - 120
    badge_pal = (46, 160, 67, 255) if off_palette_count == 0 else (218, 54, 51, 255)
    draw.rectangle([badge_x, 14, badge_x + 110, 32], fill=badge_pal)
    draw.text((badge_x + 8, 16), f"PAL: {off_palette_count} bleeds", fill=(255, 255, 255, 255), font=f_mono)

    badge_alpha = (46, 160, 67, 255) if alpha_violations == 0 else (218, 54, 51, 255)
    draw.rectangle([badge_x, 36, badge_x + 110, 54], fill=badge_alpha)
    draw.text((badge_x + 8, 38), f"ALPHA: {'PASS' if alpha_violations == 0 else 'FAIL'}", fill=(255, 255, 255, 255), font=f_mono)

    # 6. Render Animation Tracks
    cur_y = header_h + pad
    for anim_name, anim_data in sorted(anims.items(), key=lambda kv: kv[1].get("row", 0)):
        row = anim_data.get("row", 0)
        num_frames = anim_data.get("frames", 1)
        fps = anim_data.get("fps", 6)
        loop = anim_data.get("loop", True)

        # Track Label
        track_label = f"Track: {anim_name} ({num_frames} frames @ {fps} FPS, loop={loop})"
        draw.text((pad, cur_y), track_label, fill=(255, 209, 102, 255), font=f_body)
        cur_y += 20

        # Frames Row
        for fi in range(num_frames):
            fx = pad + fi * (cell_w + 8)
            fy = cur_y

            # Checkerboard background for transparency visualization
            chk_size = max(4, scale)
            for cy in range(0, cell_h, chk_size):
                for cx in range(0, cell_w, chk_size):
                    col = (26, 32, 44, 255) if ((cx // chk_size + cy // chk_size) % 2 == 0) else (18, 22, 30, 255)
                    draw.rectangle([fx + cx, fy + cy, fx + cx + chk_size - 1, fy + cy + chk_size - 1], fill=col)

            # Crop and scale frame
            src_x = fi * fw
            src_y = row * fh
            if src_x + fw <= sheet_img.width and src_y + fh <= sheet_img.height:
                frame_crop = sheet_img.crop((src_x, src_y, src_x + fw, src_y + fh))
                scaled_frame = frame_crop.resize((cell_w, cell_h), Image.Resampling.NEAREST)
                canvas.alpha_composite(scaled_frame, (fx, fy))

            # Cell Border
            draw.rectangle([fx, fy, fx + cell_w - 1, fy + cell_h - 1], outline=(48, 54, 61, 255), width=1)

            # Frame Index Badge (top-left)
            draw.rectangle([fx + 2, fy + 2, fx + 20, fy + 14], fill=(0, 0, 0, 180))
            draw.text((fx + 4, fy + 3), f"#{fi}", fill=(201, 209, 217, 255), font=f_mono)

            # Origin Point Crosshair (Cyan)
            cross_x = fx + ox * scale
            cross_y = fy + oy * scale
            c_color = (0, 240, 255, 200)
            draw.line([cross_x - 4, cross_y, cross_x + 4, cross_y], fill=c_color, width=1)
            draw.line([cross_x, cross_y - 4, cross_x, cross_y + 4], fill=c_color, width=1)

        cur_y += cell_h + 16

    # 7. Draw Palette Swatch Strip at Bottom
    cur_y += 8
    draw.line([pad, cur_y, content_w - pad, cur_y], fill=(48, 54, 61, 255), width=1)
    cur_y += 8
    draw.text((pad, cur_y), f"Palette Swatches ({len(sorted_colors)} unique colors):", fill=(139, 148, 158, 255), font=f_body)
    cur_y += 20

    swatch_size = 20
    swatch_gap = 6
    for idx, col in enumerate(sorted_colors[:48]):  # Show up to 48 distinct colors
        sx = pad + idx * (swatch_size + swatch_gap)
        if sx + swatch_size > content_w - pad:
            break
        draw.rectangle([sx, cur_y, sx + swatch_size, cur_y + swatch_size], fill=col)
        draw.rectangle([sx, cur_y, sx + swatch_size, cur_y + swatch_size], outline=(48, 54, 61, 255), width=1)

    # 8. Save inspection image
    if out_path is None:
        inspect_dir = out_dir.parent / "inspect"
        inspect_dir.mkdir(parents=True, exist_ok=True)
        final_out = inspect_dir / f"{recipe_name}_inspect.png"
    else:
        final_out = Path(out_path)
        final_out.parent.mkdir(parents=True, exist_ok=True)

    canvas.save(final_out, "PNG")

    return {
        "status": "ok",
        "recipe": recipe_name,
        "inspectionSheet": str(final_out.resolve()),
        "spritesheet": str(target_png.resolve()),
        "frameWidth": fw,
        "frameHeight": fh,
        "origin": [ox, oy],
        "animations": anims,
        "totalColors": len(sorted_colors),
        "colorsHex": [_hex_color(c) for c in sorted_colors],
        "offPaletteBleeds": off_palette_count,
        "alphaViolations": alpha_violations,
    }


def cmd_inspect(
    recipe_name: str,
    scale: int = 4,
    out_file: str | None = None,
    as_json: bool = False,
) -> int:
    try:
        data = generate_inspection_sheet(recipe_name, scale=scale, out_path=out_file, quiet=as_json)
        if as_json:
            print(json.dumps(data, indent=2))
        else:
            print("\n" + "=" * 60)
            print(f"  midev Multimodal Inspection Sheet: {data['recipe']}")
            print("=" * 60)
            print(f"  Inspection Image : {data['inspectionSheet']}")
            print(f"  Frame Size       : {data['frameWidth']}x{data['frameHeight']} px (Origin: {data['origin'][0]}, {data['origin'][1]})")
            anims_str = ", ".join(f"{k} ({v.get('frames', 1)}f)" for k, v in data['animations'].items())
            print(f"  Animations       : {anims_str}")
            print(f"  Unique Colors    : {data['totalColors']} colors")
            print(f"  Quality Status   : {data['offPaletteBleeds']} palette bleeds, {data['alphaViolations']} alpha violations")
            print("=" * 60 + "\n")
        return 0
    except Exception as e:
        if as_json:
            print(json.dumps({"status": "error", "recipe": recipe_name, "message": str(e)}, indent=2))
        else:
            print(f"[inspect] Error inspecting recipe '{recipe_name}': {e}")
        return 1
