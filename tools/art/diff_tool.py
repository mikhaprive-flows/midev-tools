"""
diff_tool - Visual Delta and Pixel Comparison Engine for midev-tools.
Calculates pixel differences, delta bounding boxes, and generates high-contrast visual diff maps.
Empowers human developers and AI coding agents to verify the visual impact of code edits.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import artkit
import projects
from manifest import Manifest


def compute_image_diff(
    img_a_path_or_obj: Path | str | Image.Image,
    img_b_path_or_obj: Path | str | Image.Image,
    diff_out: Path | str | None = None,
) -> dict[str, Any]:
    """
    Compare two images pixel by pixel.
    Returns delta metrics and optionally generates a visual diff map.
    """
    if isinstance(img_a_path_or_obj, (str, Path)):
        p_a = Path(img_a_path_or_obj)
        if not p_a.exists():
            raise FileNotFoundError(f"Baseline image not found: {p_a}")
        im_a = Image.open(p_a).convert("RGBA")
    else:
        im_a = img_a_path_or_obj.convert("RGBA")

    if isinstance(img_b_path_or_obj, (str, Path)):
        p_b = Path(img_b_path_or_obj)
        if not p_b.exists():
            raise FileNotFoundError(f"Comparison image not found: {p_b}")
        im_b = Image.open(p_b).convert("RGBA")
    else:
        im_b = img_b_path_or_obj.convert("RGBA")

    w = max(im_a.width, im_b.width)
    h = max(im_a.height, im_b.height)
    total_pixels = w * h

    pix_a = im_a.load()
    pix_b = im_b.load()

    changed_pixels = 0
    min_x, min_y = w, h
    max_x, max_y = -1, -1

    diff_img = Image.new("RGBA", (w, h), (0, 0, 0, 0)) if diff_out else None
    diff_pix = diff_img.load() if diff_img else None

    for y in range(h):
        for x in range(w):
            c_a = pix_a[x, y] if (x < im_a.width and y < im_a.height) else (0, 0, 0, 0)
            c_b = pix_b[x, y] if (x < im_b.width and y < im_b.height) else (0, 0, 0, 0)

            if c_a != c_b:
                changed_pixels += 1
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

                if diff_pix:
                    # Highlight change in vivid high-contrast red
                    diff_pix[x, y] = (255, 30, 30, 255)
            else:
                if diff_pix:
                    # Unchanged pixel: dimmed / semi-transparent reference
                    if c_b[3] > 0:
                        diff_pix[x, y] = (c_b[0] // 3, c_b[1] // 3, c_b[2] // 3, 160)
                    else:
                        diff_pix[x, y] = (0, 0, 0, 0)

    delta_bbox = None
    if changed_pixels > 0:
        delta_bbox = [min_x, min_y, max_x - min_x + 1, max_y - min_y + 1]

    percent_changed = round((changed_pixels / total_pixels) * 100, 2) if total_pixels > 0 else 0.0

    saved_diff_path = None
    if diff_img and diff_out:
        out_p = Path(diff_out).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        diff_img.save(out_p, format="PNG")
        saved_diff_path = str(out_p)

    return {
        "status": "ok",
        "identical": (changed_pixels == 0),
        "changedPixels": changed_pixels,
        "totalPixels": total_pixels,
        "percentChanged": percent_changed,
        "deltaBbox": delta_bbox,  # [x, y, width, height]
        "diffImage": saved_diff_path,
        "dimensions": [w, h],
        "sizeA": [im_a.width, im_a.height],
        "sizeB": [im_b.width, im_b.height],
    }


def find_recipe_primary_png(recipe_name: str, base_dir: Path | None = None) -> Path | None:
    """Find the primary compiled spritesheet PNG for a given recipe."""
    cfg = artkit.CONFIG
    out_dir = base_dir or cfg.output_dir

    manifest_p = out_dir / "manifest.json"
    if manifest_p.exists():
        manifest = Manifest(manifest_p)
        entry = manifest.find_primary_asset(recipe_name)
        if entry:
            for f in entry.files:
                p = out_dir / f
                if p.suffix.lower() == ".png" and p.exists():
                    return p

    for cat in ("sprites", "tiles", "ui", "backgrounds"):
        candidate = out_dir / cat / f"{recipe_name}.png"
        if candidate.exists():
            return candidate

    return None


def diff_recipe(
    recipe_name: str,
    target: Path | str | None = None,
    out_diff: Path | str | None = None,
) -> dict[str, Any]:
    """
    Compare current recipe build against a previous build, cache, or target.
    If target is provided, compare target against the primary built asset.
    If no target is provided:
      1. Check for snapshot in .diff_cache/<recipe_name>.png.
      2. If none, render the recipe freshly to a temporary directory and compare
         the current compiled asset against the freshly rendered version.
    """
    cfg = artkit.CONFIG
    out_dir = cfg.output_dir
    prev_dir = cfg.previews_dir

    current_png = find_recipe_primary_png(recipe_name, out_dir)

    default_diff_out = None
    if not out_diff:
        default_diff_out = prev_dir / "diffs" / f"{recipe_name}_diff.png"
    else:
        default_diff_out = Path(out_diff)

    if target:
        target_path = Path(target).resolve()
        if not target_path.exists():
            raise FileNotFoundError(f"Target reference file not found: {target_path}")
        if not current_png or not current_png.exists():
            raise FileNotFoundError(f"Current asset for recipe '{recipe_name}' not found at {out_dir}")
        res = compute_image_diff(target_path, current_png, diff_out=default_diff_out)
        res["recipe"] = recipe_name
        res["baseline"] = str(target_path)
        res["current"] = str(current_png)
        return res

    # Check for previous build snapshot in .diff_cache
    diff_cache_png = out_dir / ".diff_cache" / f"{recipe_name}.png"
    if diff_cache_png.exists() and current_png and current_png.exists():
        res = compute_image_diff(diff_cache_png, current_png, diff_out=default_diff_out)
        res["recipe"] = recipe_name
        res["baseline"] = str(diff_cache_png)
        res["current"] = str(current_png)
        return res

    # If no diff cache exists, compare current compiled asset against a fresh render
    recipe_files = [p for p in artkit.recipes() if p.stem == recipe_name]
    if not recipe_files:
        raise ValueError(f"Recipe '{recipe_name}' not found")
    recipe_path = recipe_files[0]

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        tmp_out = tmp_dir / "out"
        tmp_prev = tmp_dir / "prev"
        tmp_out.mkdir(parents=True, exist_ok=True)
        tmp_prev.mkdir(parents=True, exist_ok=True)

        active_proj = projects.get_active_project()
        proj_id = active_proj.id if active_proj else "unknown"
        pal_key = cfg.palette

        worker_res = artkit._run_recipe_subprocess(
            recipe_path=recipe_path,
            out_dir=tmp_out,
            prev_dir=tmp_prev,
            palette_key=pal_key,
            exporters=["godot", "texturepacker"],
            project_id=proj_id,
            timeout=30.0,
        )
        if worker_res.get("status") != "ok":
            raise RuntimeError(f"Failed to render recipe '{recipe_name}': {worker_res.get('error')}")

        fresh_png = find_recipe_primary_png(recipe_name, tmp_out)
        if not fresh_png or not fresh_png.exists():
            raise FileNotFoundError(f"Fresh render for recipe '{recipe_name}' did not produce a primary PNG")

        if not current_png or not current_png.exists():
            # Brand new recipe (no baseline exists)
            fresh_im = Image.open(fresh_png)
            w, h = fresh_im.size
            return {
                "status": "ok",
                "recipe": recipe_name,
                "identical": False,
                "isNew": True,
                "changedPixels": w * h,
                "totalPixels": w * h,
                "percentChanged": 100.0,
                "deltaBbox": [0, 0, w, h],
                "diffImage": None,
                "dimensions": [w, h],
                "baseline": None,
                "current": str(fresh_png),
            }

        res = compute_image_diff(current_png, fresh_png, diff_out=default_diff_out)
        res["recipe"] = recipe_name
        res["baseline"] = str(current_png)
        res["current"] = "fresh_render"
        return res


def cmd_diff(
    recipe_name: str,
    target: str | None = None,
    out_diff: str | None = None,
    as_json: bool = False,
) -> int:
    """CLI handler for midev diff <recipe>."""
    try:
        data = diff_recipe(recipe_name, target=target, out_diff=out_diff)
        if as_json:
            print(json.dumps(data, indent=2))
        else:
            print("\n" + "=" * 60)
            print(f"  midev Visual Delta: {data.get('recipe', recipe_name)}")
            print("=" * 60)
            print(f"  Identical       : {data['identical']}")
            print(f"  Changed Pixels  : {data['changedPixels']} / {data['totalPixels']} ({data['percentChanged']}%)")
            if data.get("deltaBbox"):
                bbox = data["deltaBbox"]
                print(f"  Delta Bounding  : [x: {bbox[0]}, y: {bbox[1]}, w: {bbox[2]}, h: {bbox[3]}]")
            if data.get("diffImage"):
                print(f"  Diff Image      : {data['diffImage']}")
            if data.get("isNew"):
                print("  Note            : Newly created recipe (no prior baseline)")
            print("=" * 60 + "\n")
        return 0
    except Exception as e:
        if as_json:
            print(json.dumps({"status": "error", "recipe": recipe_name, "message": str(e)}, indent=2))
        else:
            print(f"[diff] Error computing visual delta for '{recipe_name}': {e}", file=sys.stderr)
        return 1
