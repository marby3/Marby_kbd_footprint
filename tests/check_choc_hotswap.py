#!/usr/bin/env python3
"""Issue #18 の受け入れ基準を検証する（基準 8 の描画確認は目視なので除く）。

使い方: python tests/check_choc_hotswap.py [比較元コミット]
  基準 2・3・5・6・9（比較元との比較）は Issue #18 限りの確認なので、比較元コミット
  （作業直前の main = e4020c5）を渡したときだけ実行し、省略時は SKIP する。
  参考フットプリントは tests/fixtures/choc_hotswap_reference.kicad_mod.ref
  （拡張子を変えて、フットプリントとして数えられないようにしている）。
  基準 10〜14 は既存のチェックを実行する（ネットワークと kicad-cli が必要）。
判定はコミット済みの HEAD に対して行う。
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courtyard as C  # noqa: E402
import kicad_mod as K  # noqa: E402

# Windows のコンソール (cp932) でも日本語を出せるようにする
sys.stdout.reconfigure(encoding="utf-8")

BASE = sys.argv[1] if len(sys.argv) > 1 else ""
ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True,
                      text=True).stdout.strip()


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], check=True, capture_output=True).stdout.decode("utf-8")


failed = False


def report(label, problems, total=None):
    global failed
    if problems:
        failed = True
        shown = " ".join(problems[:8]) + (f" ...他 {len(problems) - 8} 件" if len(problems) > 8 else "")
        print(f"FAIL  {label}: {shown}")
    else:
        print(f"PASS  {label}" + (f" ({total} 件)" if total else ""))


def skip(label):
    print(f"SKIP  {label}（比較元コミットを渡したときだけ実行）")


LIB = "footprints/Marby_Switch.pretty/"
mods = [p for p in git("ls-tree", "-r", "--name-only", "HEAD").splitlines() if p.endswith(".kicad_mod")]
hotswap = [p for p in mods if os.path.basename(p).startswith("ChocSwitch_hotswap_")]
solder = [p for p in mods if os.path.basename(p).startswith("ChocSwitch_solder_")]
head = {p: K.parse(git("show", f"HEAD:{p}")) for p in hotswap + solder}
name = lambda p: os.path.basename(p)[: -len(".kicad_mod")]  # noqa: E731
ref = K.parse(git("show", "HEAD:tests/fixtures/choc_hotswap_reference.kicad_mod.ref"))
base = {p: K.parse(git("show", f"{BASE}:{p}")) for p in hotswap + solder} if BASE else {}


def strip(node, drop=("uuid",)):
    if not isinstance(node, list):
        return node
    return [strip(c, drop) for c in node if not (isinstance(c, list) and c and c[0] in drop)]


def raw_pads(fp):
    """パッドを uuid 以外すべての項目で比べるための形。"""
    return sorted(repr(strip(p)) for p in K.children(fp, "pad"))


SWAP = {"F.SilkS": "B.SilkS", "B.SilkS": "F.SilkS"}


def norm(g):
    """向きのない比較用に、線の端点と矩形の対角を並べ替える。
    上下反転で KiCad が線の始点・終点を入れ替えることがあるため、線の向きは区別しない（幾何としては同じ）。"""
    kind, layers, pts, xy, width = g
    p = dict(pts)
    if kind == "fp_line":
        pts = (("ends", tuple(sorted((p["start"], p["end"])))),)
    elif kind == "fp_rect":
        (x0, y0), (x1, y1) = p["start"], p["end"]
        pts = (("box", (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))),)
    return (kind, layers, pts, xy, width)


def mirror(g):
    """上下反転: y を −y にし、F.SilkS と B.SilkS を入れ替える。"""
    kind, layers, pts, xy, width = g
    flip = lambda v: (v[0], -v[1] + 0.0)  # noqa: E731  -0.0 を 0.0 にそろえる
    return norm((kind, tuple(SWAP.get(l, l) for l in layers),
                 tuple((k, flip(v)) for k, v in pts), tuple(flip(v) for v in xy), width))


def graphics_on(fp, layers):
    return sorted((norm(g) for g in K.graphics(fp) if g[1][0] in layers), key=repr)


def mirrored_on(fp, layers):
    # 反転後の層で絞る（F.SilkS と B.SilkS は入れ替わる）
    return sorted((m for m in (mirror(g) for g in K.graphics(fp)) if m[1][0] in layers), key=repr)


# 基準 1: パッドが参考と同一
report("1 ホットスワップのパッドが参考と同一",
       [f"[{name(p)}]" for p in hotswap if raw_pads(head[p]) != raw_pads(ref)]
       + ([] if len(hotswap) == 8 else [f"[対象 {len(hotswap)} / 8 件]"]), len(hotswap))

# 基準 2, 3, 5, 6: 比較元との比較
MIRRORED = ("F.SilkS", "B.SilkS", "Eco1.User", "Edge.Cuts")
REF_RECTS = [norm(g) for g in K.graphics(ref) if g[0] == "fp_rect" and g[1] == ("Eco2.User",)]
if not BASE:
    for label in ("2 シルク・Eco1・切り欠きが比較元の上下反転", "3 Eco2.User が上下反転＋参考の矩形 2 つ",
                  "5 コートヤード・外形・attr・descr・Value が比較元と同一", "6 3D モデルのパスが比較元と同じ",
                  "9 はんだ付け 8 件が比較元と同一"):
        skip(label)
else:
    report("2 シルク・Eco1・切り欠きが比較元の上下反転",
           [f"[{name(p)}]" for p in hotswap if graphics_on(head[p], MIRRORED) != mirrored_on(base[p], MIRRORED)],
           len(hotswap))
    report("3 Eco2.User が上下反転＋参考の矩形 2 つ",
           [f"[{name(p)}]" for p in hotswap
            if graphics_on(head[p], ("Eco2.User",)) != sorted(mirrored_on(base[p], ("Eco2.User",)) + REF_RECTS, key=repr)]
           + ([] if len(REF_RECTS) == 2 else [f"[参考の矩形 {len(REF_RECTS)} 個]"]), len(hotswap))
    same = [lambda fp: graphics_on(fp, ("F.CrtYd", "Dwgs.User")), K.attr, K.descr, lambda fp: K.prop_value(fp, "Value")]
    report("5 コートヤード・外形・attr・descr・Value が比較元と同一",
           [f"[{name(p)}]" for p in hotswap if any(f(head[p]) != f(base[p]) for f in same)], len(hotswap))
    report("6 3D モデルのパスが比較元と同じ",
           [f"[{name(p)}]" for p in hotswap
            if sorted(m[0] for m in K.models(head[p])) != sorted(m[0] for m in K.models(base[p]))], len(hotswap))
    every = [K.pads, K.graphics, K.texts, K.models, K.attr, K.descr, lambda fp: K.prop_value(fp, "Value")]
    report("9 はんだ付け 8 件が比較元と同一",
           [f"[{name(p)}]" for p in solder if any(f(head[p]) != f(base[p]) for f in every)], len(solder))

# 基準 4: Reference テキストが参考と同じ
def reference(fp):
    return [t for t in K.texts(fp) if t[0] == "Reference"]


def value_at(fp):
    return K.nums(K.child(K.prop(fp, "Value"), "at"), 3)


report("4 Reference が参考と同じ位置・層・向き（Value の位置も参考にそろえる）",
       [f"[{name(p)}]" for p in hotswap if reference(head[p]) != reference(ref)
        or "mirror" not in repr(K.prop(head[p], "Reference")) or value_at(head[p]) != value_at(ref)], len(hotswap))

# 基準 7: スイッチとソケットの配置値が 8 件で同じ
placements = {}
for p in hotswap:
    for path, values in K.models(head[p]):
        placements.setdefault(path, set()).add(values)
report("7 スイッチとソケットの配置値が 8 件で同じ",
       [f"[{os.path.basename(k)}: {len(v)} 通り]" for k, v in placements.items() if len(v) != 1]
       + ([] if len(placements) == 2 else [f"[モデル {len(placements)} 種類]"]))

# 基準 10: attr のルールが番号付きのパッドだけで判定する（参考は番号なしのメッキ穴を持つが SMD）
problems = [] if C.expected_attr("ChocSwitch_hotswap_reference", ref) == {"smd"} else \
    [f"[参考の判定が {sorted(C.expected_attr('ChocSwitch_hotswap_reference', ref))}]"]


def run(cmd, script=None):
    r = subprocess.run(cmd, input=script.encode("utf-8") if script else None, cwd=ROOT, capture_output=True)
    lines = r.stdout.decode("utf-8", "replace").splitlines()
    return [] if r.returncode == 0 else [l for l in lines if l.startswith("FAIL")] or [f"[exit {r.returncode}]"]


def run_python_check(script, helpers=("kicad_mod.py",)):
    with tempfile.TemporaryDirectory() as tmp:
        for f in (script, *helpers):
            with open(os.path.join(tmp, f), "w", encoding="utf-8", newline="\n") as out:
                out.write(git("show", f"HEAD:tests/{f}"))
        return run([sys.executable, os.path.join(tmp, script)])


report("10 attr のルールと check_attr_courtyard.py",
       problems + run_python_check("check_attr_courtyard.py", ("kicad_mod.py", "courtyard.py")))

# 基準 11: check_import.py の基準 1 がはんだ付け 8 件だけを対象にする
problems = [] if "ChocSwitch_solder_" in git("show", "HEAD:tests/check_import.py") else ["[基準 1 がはんだ付けに絞られていない]"]
report("11 check_import.py", problems + run_python_check("check_import.py"))

# 基準 12〜14: 既存チェック
# "bash" だけを渡すと、Windows では System32 の WSL bash が先に見つかるため、PATH 上のフルパスで起動する
bash = shutil.which("bash")
report("12 check_layout.sh", run([bash, "-s"], git("show", "HEAD:tests/check_layout.sh")) if bash else ["[bash が見つからない]"])
report("13 check_format.py", run_python_check("check_format.py"))
report("14 check_models.py", run_python_check("check_models.py"))

sys.exit(1 if failed else 0)
