"""Issue #5 で決めた attr とコートヤードのルール（期待値の計算）。

kicad_mod.parse() の結果を受け取り、そのフットプリントにあるべき attr とコートヤードの外形を返す。
"""

import math
import re

import kicad_mod as K

VIA_MAX_DRILL = 0.6  # これ未満のメッキ穴はビアとみなして THT の判定に数えない
MARGIN = 0.25  # スイッチ以外のコートヤードの余白
KEY = 19.05  # 1u のキーピッチ
BODY_LAYERS = ("F.Fab", "F.SilkS", "B.SilkS")
MECHANICAL = {
    "Breakaway_Tabs": {"board_only", "exclude_from_pos_files", "exclude_from_bom"},
    "Breakaway_Mousebite": {"board_only", "exclude_from_pos_files", "exclude_from_bom"},
    "Fiducial_1.5mm": {"smd", "exclude_from_bom"},
}
SWITCH = re.compile(r"^(CherryMXSwitch|ChocSwitch)_")
SIZE = re.compile(r"_(\d+)_(\d\d)u(_rev)?$")
ISO_ENTER = {
    "CherryMXSwitch_hotswap_ISO_Enter": [(-11.90625, -19.05), (11.90625, -19.05), (11.90625, 19.05),
                                         (-16.66875, 19.05), (-16.66875, 0.0), (-11.90625, 0.0)],
    "CherryMXSwitch_solder_ISO_Enter": [(-16.66875, -19.05), (11.90625, -19.05), (11.90625, 19.05),
                                        (-11.90625, 19.05), (-11.90625, 0.0), (-16.66875, 0.0)],
}


def is_switch(name):
    return bool(SWITCH.match(name))


def expected_attr(name, fp):
    """attr の集合。メッキ穴（ドリル 0.6mm 以上）があれば through_hole、なければ SMD パッドがあれば smd。"""
    if name in MECHANICAL:
        return MECHANICAL[name]
    pads = K.pads(fp)
    for p in pads:
        drills = [v for v in p[5] if isinstance(v, float)]
        if p[1] == "thru_hole" and drills and max(drills) >= VIA_MAX_DRILL:
            return {"through_hole"}
    if any(p[1] == "smd" for p in pads):
        return {"smd"}
    return set()


def keycap_outline(name):
    """スイッチのキーキャップ外形（頂点の列）。"""
    if name in ISO_ENTER:
        return ISO_ENTER[name]
    m = SIZE.search(name)
    u = int(m.group(1)) + int(m.group(2)) / 100
    w, h = KEY * u / 2, KEY / 2
    return [(-w, -h), (w, -h), (w, h), (-w, h)]


def _pad_points(pad):
    x, y, rot = pad[3]
    w, h = pad[4][0], pad[4][1] if len(pad[4]) > 1 else pad[4][0]
    a = math.radians(rot)
    out = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        out.append((x + dx * math.cos(a) + dy * math.sin(a), y - dx * math.sin(a) + dy * math.cos(a)))
    return out


def _arc_points(start, mid, end):
    """円弧の端点と、円弧が通る上下左右の極点。"""
    (x1, y1), (x2, y2), (x3, y3) = start, mid, end
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:
        return [start, mid, end]
    ux = ((x1 ** 2 + y1 ** 2) * (y2 - y3) + (x2 ** 2 + y2 ** 2) * (y3 - y1) + (x3 ** 2 + y3 ** 2) * (y1 - y2)) / d
    uy = ((x1 ** 2 + y1 ** 2) * (x3 - x2) + (x2 ** 2 + y2 ** 2) * (x1 - x3) + (x3 ** 2 + y3 ** 2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    ang = lambda p: math.atan2(p[1] - uy, p[0] - ux) % (2 * math.pi)  # noqa: E731
    a1, a2, a3 = ang(start), ang(mid), ang(end)
    ccw = (a2 - a1) % (2 * math.pi) < (a3 - a1) % (2 * math.pi)
    span = (a3 - a1) % (2 * math.pi) if ccw else (a1 - a3) % (2 * math.pi)
    lo = a1 if ccw else a3
    pts = [start, mid, end]
    for k in range(4):
        t = k * math.pi / 2
        if (t - lo) % (2 * math.pi) <= span:
            pts.append((ux + r * math.cos(t), uy + r * math.sin(t)))
    return pts


def _graphic_points(g):
    kind, _, pts, xy, _ = g
    p = dict(pts)
    if kind == "fp_circle":
        (cx, cy), (ex, ey) = p["center"], p["end"]
        r = math.hypot(ex - cx, ey - cy)
        return [(cx - r, cy - r), (cx + r, cy + r)]
    if kind == "fp_arc":
        return _arc_points(p["start"], p["mid"], p["end"])
    return [v for v in p.values()] + list(xy)


def body_rect(fp):
    """パッドと F.Fab / F.SilkS / B.SilkS の図形を囲む矩形に余白を付け、0.01mm 単位で外側に丸めたもの。"""
    pts = [pt for pad in K.pads(fp) for pt in _pad_points(pad)]
    pts += [pt for g in K.graphics(fp) if any(l in BODY_LAYERS for l in g[1]) for pt in _graphic_points(g)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    lo = lambda v: math.floor(round((v - MARGIN) * 100, 6)) / 100  # noqa: E731
    hi = lambda v: math.ceil(round((v + MARGIN) * 100, 6)) / 100  # noqa: E731
    x0, y0, x1, y1 = lo(min(xs)), lo(min(ys)), hi(max(xs)), hi(max(ys))
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def edges(points):
    """閉じた多角形の辺（向きなし・丸め済み）の集合。"""
    out = set()
    for a, b in zip(points, points[1:] + points[:1]):
        a, b = (round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4))
        out.add(tuple(sorted((a, b))))
    return out


def courtyard_edges(fp):
    """F.CrtYd の線・矩形・多角形の辺の集合と、円の数。"""
    out, circles = [], 0
    for g in K.graphics(fp):
        if g[1] != ("F.CrtYd",):
            continue
        kind, _, pts, xy, _ = g
        p = dict(pts)
        if kind == "fp_line":
            out.append(tuple(sorted(((round(p["start"][0], 4), round(p["start"][1], 4)),
                                     (round(p["end"][0], 4), round(p["end"][1], 4))))))
        elif kind == "fp_rect":
            (x0, y0), (x1, y1) = p["start"], p["end"]
            out += list(edges([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
        elif kind == "fp_poly":
            out += list(edges(list(xy)))
        elif kind == "fp_circle":
            circles += 1
    return out, circles
