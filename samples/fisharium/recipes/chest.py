# Author: Agent-worker-helpy
"""Treasure chest - example of the SVG workflow (vector shapes -> crisp pixel frames)."""
from pixelkit import SheetBuilder, svg_frame, svg_doc, hexc

W, H = 16, 16


def chest(glint: int, lid_open: int = 0) -> str:
    o, w, wl, g, gl = hexc("outline"), hexc("wood"), hexc("wood_light"), hexc("gold"), hexc("gold_light")
    body = f"""
      <ellipse cx="8" cy="14" rx="7" ry="2" fill="{hexc('shadow')}"/>
      <rect x="1" y="7" width="14" height="8" fill="{o}"/>
      <rect x="2" y="8" width="12" height="6" fill="{w}"/>
      <rect x="1" y="{3 - lid_open}" width="14" height="5" fill="{o}"/>
      <rect x="2" y="{4 - lid_open}" width="12" height="3" fill="{wl}"/>
      <rect x="7" y="6" width="2" height="4" fill="{g}"/>
      <rect x="2" y="10" width="12" height="1" fill="{hexc('wood_dark')}"/>
    """
    if glint >= 0:
        body += f'<rect x="{3 + glint * 3}" y="{4 - lid_open}" width="1" height="1" fill="{gl}"/>'
    return svg_doc(W, H, body)


def buried_frame(frame: int) -> str:
    sh = hexc("shadow")
    wd = hexc("wood_dark")
    d = hexc("dirt")
    s = hexc("sand")
    red = hexc("red")
    ora = hexc("orange")
    gl = hexc("gold_light") if frame % 2 == 1 else hexc("gold")

    body = f"""
      <ellipse cx="8" cy="14" rx="7" ry="2" fill="{sh}"/>
      <ellipse cx="8" cy="13" rx="6" ry="2.5" fill="{wd}"/>
      <ellipse cx="8" cy="12" rx="5" ry="2" fill="{d}"/>
      <rect x="5" y="12" width="2" height="1" fill="{s}"/>
      <rect x="10" y="13" width="1" height="1" fill="{s}"/>
      <!-- X mark: 5x5 red with orange/gold center -->
      <rect x="6" y="8" width="1" height="1" fill="{red}"/>
      <rect x="10" y="8" width="1" height="1" fill="{red}"/>
      <rect x="7" y="9" width="1" height="1" fill="{ora}"/>
      <rect x="9" y="9" width="1" height="1" fill="{ora}"/>
      <rect x="8" y="10" width="1" height="1" fill="{gl}"/>
      <rect x="7" y="11" width="1" height="1" fill="{ora}"/>
      <rect x="9" y="11" width="1" height="1" fill="{ora}"/>
      <rect x="6" y="12" width="1" height="1" fill="{red}"/>
      <rect x="10" y="12" width="1" height="1" fill="{red}"/>
    """
    return svg_doc(W, H, body)


def dig_frame(k: int) -> str:
    sh = hexc("shadow")
    o = hexc("outline")
    w = hexc("wood")
    wl = hexc("wood_light")
    wd = hexc("wood_dark")
    g = hexc("gold")
    d = hexc("dirt")
    s = hexc("sand")
    sl = hexc("sand_light")
    stl = hexc("stone_light")

    y_rise = [6, 4, 2, 1, 0][k]
    body = f"""
      <ellipse cx="8" cy="14" rx="7" ry="2" fill="{sh}"/>
      <!-- Emerging chest -->
      <rect x="1" y="{7 + y_rise}" width="14" height="{max(0, 8 - y_rise)}" fill="{o}"/>
      <rect x="2" y="{8 + y_rise}" width="12" height="{max(0, 6 - y_rise)}" fill="{w}"/>
      <rect x="1" y="{3 + y_rise}" width="14" height="5" fill="{o}"/>
      <rect x="2" y="{4 + y_rise}" width="12" height="3" fill="{wl}"/>
      <rect x="7" y="{6 + y_rise}" width="2" height="4" fill="{g}"/>
      <rect x="2" y="{10 + y_rise}" width="12" height="1" fill="{wd}"/>
      <!-- Dirt mound & soil base -->
      <ellipse cx="8" cy="14" rx="{max(1, 7 - k)}" ry="2" fill="{wd}"/>
      <ellipse cx="8" cy="13" rx="{max(1, 6 - k)}" ry="1.5" fill="{d}"/>
    """
    if k == 0:
        body += f"""
          <rect x="7" y="10" width="2" height="2" fill="{d}"/>
          <rect x="6" y="8" width="1" height="1" fill="{s}"/>
          <rect x="9" y="8" width="1" height="1" fill="{sl}"/>
        """
    elif k == 1:
        body += f"""
          <rect x="4" y="6" width="2" height="2" fill="{d}"/>
          <rect x="10" y="5" width="2" height="2" fill="{d}"/>
          <rect x="3" y="4" width="1" height="1" fill="{s}"/>
          <rect x="12" y="4" width="1" height="1" fill="{sl}"/>
          <rect x="7" y="3" width="2" height="1" fill="{stl}"/>
        """
    elif k == 2:
        body += f"""
          <rect x="2" y="4" width="2" height="2" fill="{d}"/>
          <rect x="12" y="5" width="2" height="2" fill="{d}"/>
          <rect x="1" y="6" width="1" height="1" fill="{s}"/>
          <rect x="14" y="7" width="1" height="1" fill="{sl}"/>
          <rect x="5" y="2" width="1" height="1" fill="{stl}"/>
          <rect x="10" y="2" width="1" height="1" fill="{s}"/>
        """
    elif k == 3:
        body += f"""
          <rect x="1" y="8" width="2" height="1" fill="{d}"/>
          <rect x="13" y="9" width="2" height="1" fill="{d}"/>
          <rect x="0" y="11" width="1" height="1" fill="{s}"/>
          <rect x="15" y="12" width="1" height="1" fill="{sl}"/>
        """
    elif k == 4:
        body += f"""
          <rect x="1" y="13" width="1" height="1" fill="{d}"/>
          <rect x="14" y="13" width="1" height="1" fill="{s}"/>
        """
    return svg_doc(W, H, body)


def build(ctx):
    sb = SheetBuilder("chest", W, H, origin=(8, 14))
    sb.add("idle", [svg_frame(chest(g), W, H) for g in (-1, -1, 0, 1, 2, 3, -1, -1)], fps=8)
    sb.add("open", [svg_frame(chest(-1, k), W, H) for k in (0, 1, 2, 3)], fps=12, loop=False)
    sb.add("buried", [svg_frame(buried_frame(i), W, H) for i in range(4)], fps=4, loop=True)
    sb.add("dig", [svg_frame(dig_frame(k), W, H) for k in range(5)], fps=14, loop=False)
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
