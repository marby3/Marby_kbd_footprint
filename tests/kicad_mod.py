"""KiCad の .kicad_mod (S 式) を読み、形式の世代差を吸収した比較用の値を取り出す。

KiCad 6 (20211014) から 10 (20260206) まで、形式の変更で表記が変わる部分
（fp_text → property、width → stroke、tstamp → uuid、at の回転省略など）を
同じ値にそろえる。数値は float にして比較する。
"""

import re

_TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


def parse(text):
    """S 式を入れ子のリストにする。文字列は引用符を外した str、それ以外も str のまま。"""
    stack = [[]]
    for tok in _TOKEN.findall(text):
        if tok == "(":
            stack.append([])
        elif tok == ")":
            node = stack.pop()
            stack[-1].append(node)
        elif tok.startswith('"'):
            stack[-1].append(bytes(tok[1:-1], "utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8"))
        else:
            stack[-1].append(tok)
    return stack[0][0]


def children(node, name):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == name]


def child(node, name):
    found = children(node, name)
    return found[0] if found else None


def num(v):
    return round(float(v), 6)


def nums(node, n=None):
    """(at x y [rot]) のような子の数値部分。n を指定すると不足分を 0 で埋める。"""
    if node is None:
        return None
    vals = [num(v) for v in node[1:] if isinstance(v, str) and re.fullmatch(r"-?[0-9.eE+-]+", v)]
    if n is not None:
        vals = (vals + [0.0] * n)[:n]
    return tuple(vals)


# KiCad 10 で表記だけ変わったレイヤー名
_LAYER_ALIASES = {"F&B.Cu": "*.Cu"}


def layers(node):
    lay = child(node, "layers")
    if lay is not None:
        return tuple(sorted(_LAYER_ALIASES.get(v, v) for v in lay[1:]))
    one = child(node, "layer")
    return (one[1],) if one is not None else ()


def line_width(node):
    stroke = child(node, "stroke")
    if stroke is not None:
        w = child(stroke, "width")
        return num(w[1]) if w else None
    w = child(node, "width")
    return num(w[1]) if w else None


def name(fp):
    return fp[1]


def version(fp):
    v = child(fp, "version")
    return v[1] if v else None


def descr(fp):
    d = child(fp, "descr")
    return d[1] if d else ""


def attr(fp):
    a = child(fp, "attr")
    return tuple(a[1:]) if a else ()


def prop(fp, key):
    """Value / Reference。新形式は property、旧形式は fp_text。"""
    for p in children(fp, "property"):
        if p[1] == key:
            return p
    for t in children(fp, "fp_text"):
        if t[1] == key.lower():
            return t
    return None


def prop_value(fp, key):
    p = prop(fp, key)
    if p is None:
        return None
    return p[2]


def pads(fp):
    out = []
    for p in children(fp, "pad"):
        drill = child(p, "drill")
        out.append((
            p[1], p[2], p[3],
            nums(child(p, "at"), 3),
            nums(child(p, "size")),
            tuple(str(v) for v in drill[1:]) if drill else (),
            layers(p),
        ))
    return sorted(out)


_GRAPHICS = ("fp_line", "fp_circle", "fp_arc", "fp_poly", "fp_rect", "fp_curve")
_POINTS = ("start", "end", "mid", "center")


def graphics(fp):
    out = []
    for c in fp[1:]:
        if not (isinstance(c, list) and c and c[0] in _GRAPHICS):
            continue
        pts = tuple((k, nums(child(c, k))) for k in _POINTS if child(c, k) is not None)
        poly = child(c, "pts")
        xy = tuple(nums(p) for p in poly[1:]) if poly is not None else ()
        out.append((c[0], layers(c), pts, xy, line_width(c)))
    return sorted(out, key=repr)


def texts(fp):
    """Reference とユーザーテキストの内容・位置・レイヤー。Value は比較対象外（Issue で変える）。"""
    out = []
    ref = prop(fp, "Reference")
    if ref is not None:
        out.append(("Reference", ref[2], nums(child(ref, "at"), 3), layers(ref)))
    for t in children(fp, "fp_text"):
        if t[1] == "user":
            out.append(("user", t[2], nums(child(t, "at"), 3), layers(t)))
    return sorted(out, key=repr)


def models(fp):
    out = []
    for m in children(fp, "model"):
        vals = []
        for k in ("offset", "scale", "rotate"):
            sub = child(m, k)
            xyz = child(sub, "xyz") if sub is not None else None
            vals.append((k, nums(xyz, 3) if xyz is not None else None))
        out.append((m[1], tuple(vals)))
    return sorted(out)
