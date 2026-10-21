"""Generates the app's original isometric artwork into assets/.

Run once: python tools/make_art.py
Produces assets/hero.svg (front-page banner) and assets/tile_*.svg (tab icons).
All shapes are drawn here from scratch; no external images are used.
"""

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(exist_ok=True)

C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))

PALETTE = {
    "top": "#FFE3C2", "left": "#F4A963", "right": "#DA7B4B",
    "top2": "#FDE7D6", "left2": "#EDB49A", "right2": "#C9836A",
    "glass": "#FFF6EA", "led": "#FFE27A", "line": "#8C5A3C",
    "spark": "#FFD23F", "tree": "#9CC59A", "tree_dark": "#78A878",
    "ground": "#F7E1CB", "ground_edge": "#EBCDB0", "ground_side": "#E2BE9C",
}
DAY = dict(PALETTE)
NIGHT = {
    "top": "#4A3C7A", "left": "#33295C", "right": "#261E47",
    "top2": "#3E3468", "left2": "#2B2350", "right2": "#211A3E",
    "glass": "#5CF2FF", "led": "#FF5CD6", "line": "#8E7FD0",
    "spark": "#7DF9FF", "tree": "#2F7E6E", "tree_dark": "#22665A",
    "ground": "#2C2350", "ground_edge": "#211A3E", "ground_side": "#1A1433",
}
GLOW = ""  # set to a filter attribute when drawing the night scene

GLOW_DEFS = (
    '<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
    '<feGaussianBlur stdDeviation="2.4" result="b"/>'
    '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
    '</filter></defs>'
)


class Iso:
    def __init__(self, ox, oy, s):
        self.ox, self.oy, self.s = ox, oy, s

    def p(self, i, j, k=0.0):
        x = self.ox + (i - j) * C30 * self.s
        y = self.oy + (i + j) * S30 * self.s - k * self.s
        return x, y

    def poly(self, pts, fill, extra=""):
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in (self.p(*q) for q in pts))
        return f'<polygon points="{d}" fill="{fill}" {extra}/>'

    def box(self, i, j, w, d, h, tone=""):
        t, l, r = PALETTE["top" + tone], PALETTE["left" + tone], PALETTE["right" + tone]
        out = [
            self.poly([(i, j + d, 0), (i + w, j + d, 0), (i + w, j + d, h), (i, j + d, h)], l),
            self.poly([(i + w, j, 0), (i + w, j + d, 0), (i + w, j + d, h), (i + w, j, h)], r),
            self.poly([(i, j, h), (i + w, j, h), (i + w, j + d, h), (i, j + d, h)], t),
        ]
        return "\n".join(out)

    def server_slots(self, i, j, w, d, h, rows, seed=0):
        """Rack slots on the left (front) face and blinking lights on the right face."""
        out = []
        gap = h / (rows + 1)
        for r in range(rows):
            k0 = gap * (r + 0.7)
            k1 = k0 + gap * 0.45
            out.append(self.poly(
                [(i + 0.15 * w, j + d, k0), (i + 0.85 * w, j + d, k0),
                 (i + 0.85 * w, j + d, k1), (i + 0.15 * w, j + d, k1)],
                PALETTE["glass"], 'opacity="0.9" ' + GLOW))
            for c in range(2):
                x, y = self.p(i + w, j + d * (0.3 + 0.35 * c), (k0 + k1) / 2)
                dur = 1.1 + ((seed + r * 3 + c * 5) % 7) * 0.23
                out.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{self.s * 0.09:.1f}" fill="{PALETTE["led"]}" {GLOW}>'
                    f'<animate attributeName="opacity" values="1;0.25;1" dur="{dur:.2f}s" '
                    f'repeatCount="indefinite"/></circle>')
        return "\n".join(out)

    def tree(self, i, j, h=1.6):
        bx, by = self.p(i, j, 0)
        tx, ty = self.p(i, j, h)
        r = self.s * 0.45
        return (f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="{r:.1f}" ry="{r * 0.45:.1f}" '
                f'fill="#000" opacity="0.06"/>'
                f'<polygon points="{bx - r:.1f},{by - r * 0.3:.1f} {tx:.1f},{ty:.1f} {bx:.1f},{by:.1f}" '
                f'fill="{PALETTE["tree"]}"/>'
                f'<polygon points="{bx + r:.1f},{by - r * 0.3:.1f} {tx:.1f},{ty:.1f} {bx:.1f},{by:.1f}" '
                f'fill="{PALETTE["tree_dark"]}"/>')

    def pylon(self, i, j, h):
        """A simple lattice power pylon; returns (svg, list of insulator points)."""
        base = [self.p(i - 0.35, j, 0), self.p(i + 0.35, j, 0)]
        top = self.p(i, j, h)
        arm_l, arm_r = self.p(i - 0.9, j, h * 0.82), self.p(i + 0.9, j, h * 0.82)
        mid_l, mid_r = self.p(i - 0.22, j, h * 0.82), self.p(i + 0.22, j, h * 0.82)
        col = PALETTE["line"]
        segs = [
            (base[0], mid_l), (base[1], mid_r), (mid_l, top), (mid_r, top),
            (base[0], mid_r), (base[1], mid_l), (arm_l, arm_r),
        ]
        svg = "".join(
            f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
            f'stroke="{col}" stroke-width="2" stroke-linecap="round"/>' for a, b in segs)
        return svg, [arm_l, arm_r]


def cable(a, b, sag, dur, delay):
    """A sagging power line with sparks travelling along it."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + sag
    d = f"M{a[0]:.1f},{a[1]:.1f} Q{mx:.1f},{my:.1f} {b[0]:.1f},{b[1]:.1f}"
    sparks = "".join(
        f'<circle r="3.2" fill="{PALETTE["spark"]}" stroke="{PALETTE["spark"]}" stroke-width="1" {GLOW}>'
        f'<animateMotion dur="{dur}s" begin="{delay + n * dur / 2:.2f}s" repeatCount="indefinite" path="{d}"/>'
        f'</circle>' for n in range(2))
    return (f'<path d="{d}" fill="none" stroke="{PALETTE["line"]}" stroke-width="1.6" opacity="0.8" {GLOW}/>'
            + sparks)


def hero(night=False):
    global GLOW
    PALETTE.clear(); PALETTE.update(NIGHT if night else DAY)
    GLOW = 'filter="url(#glow)"' if night else ""
    W, H = 760, 400
    iso = Iso(ox=372, oy=82, s=25)
    parts = [GLOW_DEFS]

    # Sky decorations
    if night:
        parts.append('<circle cx="640" cy="78" r="30" fill="#FFF3C4" filter="url(#glow)"/>')
        parts.append('<circle cx="652" cy="70" r="26" fill="#2A2147" opacity="0.0"/>')
        for n, (sx, sy) in enumerate([(90, 50), (180, 110), (260, 30), (480, 60), (560, 130),
                                      (700, 170), (40, 150), (380, 20), (720, 40)]):
            parts.append(
                f'<circle cx="{sx}" cy="{sy}" r="1.8" fill="#FFFFFF">'
                f'<animate attributeName="opacity" values="1;0.2;1" dur="{1.6 + (n % 4) * 0.5}s" '
                f'repeatCount="indefinite"/></circle>')
    else:
        parts.append('<circle cx="640" cy="78" r="38" fill="#FFD9A0" opacity="0.85"/>')
        parts.append('<circle cx="640" cy="78" r="56" fill="#FFD9A0" opacity="0.25"/>')
    for cx, cy, sc in ([] if night else [(120, 70, 1.0), (520, 40, 0.8)]):
        parts.append(
            f'<g opacity="0.9" transform="translate({cx},{cy}) scale({sc})">'
            '<ellipse cx="0" cy="0" rx="34" ry="14" fill="#fff"/>'
            '<ellipse cx="22" cy="-8" rx="22" ry="14" fill="#fff"/>'
            '<ellipse cx="-20" cy="-4" rx="18" ry="11" fill="#fff"/>'
            '<animateTransform attributeName="transform" type="translate" additive="sum" '
            'values="0 0; 14 0; 0 0" dur="16s" repeatCount="indefinite"/></g>')

    # Ground slab
    parts.append(iso.poly([(-1, -1, 0), (11, -1, 0), (11, 9, 0), (-1, 9, 0)], PALETTE["ground"]))
    parts.append(iso.poly([(-1, 9, 0), (11, 9, 0), (11, 9, -0.5), (-1, 9, -0.5)], PALETTE["ground_edge"]))
    parts.append(iso.poly([(11, -1, 0), (11, 9, 0), (11, 9, -0.5), (11, -1, -0.5)], PALETTE["ground_side"]))

    # Objects, painted back to front
    buildings = [  # i, j, w, d, h, tone, rows
        (2.2, -0.4, 2.4, 1.8, 2.6, "2", 2),
        (7.4, -0.2, 2.6, 2.0, 3.4, "2", 3),
        (4.6, 2.4, 2.6, 2.2, 4.8, "", 4),
        (8.2, 4.4, 2.2, 2.0, 2.8, "", 2),
        (3.4, 6.2, 2.4, 1.8, 2.2, "", 2),
    ]
    objects = []
    for n, (i, j, w, d, h, tone, rows) in enumerate(buildings):
        svg = iso.box(i, j, w, d, h, tone) + iso.server_slots(i, j, w, d, h, rows, seed=n)
        objects.append((i + j + w + d, svg))
    for i, j, h in [(0.4, 1.2, 1.5), (1.2, 3.4, 1.9), (7.0, 8.0, 1.4), (10.2, 2.6, 1.7), (10.2, 7.6, 1.3), (6.2, 6.6, 1.2)]:
        objects.append((i + j + 0.5, iso.tree(i, j, h)))
    pylon_svg, arms = iso.pylon(0.0, 7.2, 4.6)
    objects.append((7.2, pylon_svg))
    for _, svg in sorted(objects, key=lambda t: t[0]):
        parts.append(svg)

    # Power lines from the pylon to roofs, drawn last so sparks are visible
    roofs = [None, iso.p(5.9, 3.5, 4.8), iso.p(4.6, 7.1, 2.2)]
    parts.append(cable(arms[1], roofs[1], 30, 2.4, 0.6))
    parts.append(cable(arms[1], roofs[2], 12, 1.8, 1.1))

    body = "\n".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="Illustration of a data-centre campus powered by the electricity grid">'
            f'{body}</svg>')


def tile(kind):
    """Small isometric icons for the four tab cards."""
    iso = Iso(ox=60, oy=50, s=12)
    p = [iso.poly([(-0.5, -0.5, 0), (4.5, -0.5, 0), (4.5, 4.5, 0), (-0.5, 4.5, 0)], PALETTE["ground"])]
    if kind == "construction":
        p.append(iso.box(0.6, 0.6, 2.8, 2.8, 1.2))
        p.append(iso.box(0.6, 0.6, 2.8, 2.8, 2.2, "2").replace('fill="', 'opacity="0.35" fill="', 3))
        mast, top = iso.p(3.9, 0.3, 0), iso.p(3.9, 0.3, 4.6)
        jib_end = iso.p(0.4, 0.3, 4.6)
        hook = iso.p(1.6, 0.3, 4.6)
        p.append(f'<line x1="{mast[0]}" y1="{mast[1]}" x2="{top[0]}" y2="{top[1]}" stroke="{PALETTE["right"]}" stroke-width="3"/>'
                 f'<line x1="{top[0]}" y1="{top[1]}" x2="{jib_end[0]}" y2="{jib_end[1]}" stroke="{PALETTE["right"]}" stroke-width="3"/>'
                 f'<line x1="{hook[0]}" y1="{hook[1]}" x2="{hook[0]}" y2="{hook[1] + 22}" stroke="{PALETTE["line"]}" stroke-width="1.5"/>')
    elif kind == "builders":
        for i, j, h, t in [(0.2, 0.2, 2.2, "2"), (2.4, 0.4, 3.6, ""), (0.6, 2.5, 1.4, ""), (2.6, 2.6, 2.6, "2")]:
            p.append(iso.box(i, j, 1.5, 1.5, h, t))
    elif kind == "electricity":
        p.append(iso.box(0.8, 0.8, 2.6, 2.6, 2.2))
        bx, by = iso.p(2.1, 2.1, 2.2)
        p.append(f'<polygon transform="translate({bx - 10},{by - 40})" '
                 f'points="12,0 0,20 9,20 5,36 22,12 13,12 18,0" fill="{PALETTE["spark"]}" '
                 f'stroke="#E08A00" stroke-width="2" stroke-linejoin="round"/>')
    elif kind == "demand":
        for n, h in enumerate([1.0, 1.8, 2.4, 3.6]):
            p.append(iso.box(0.2 + n * 1.05, 1.6, 0.8, 0.8, h, "" if n == 3 else "2"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">{"".join(p)}</svg>')


if __name__ == "__main__":
    (OUT / "hero.svg").write_text(hero(night=False))
    (OUT / "hero_night.svg").write_text(hero(night=True))
    PALETTE.clear(); PALETTE.update(DAY); GLOW = ""
    for k in ["construction", "builders", "electricity", "demand"]:
        (OUT / f"tile_{k}.svg").write_text(tile(k))
    print("wrote", sorted(f.name for f in OUT.glob("*.svg")))
