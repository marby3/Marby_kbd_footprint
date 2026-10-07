#!/usr/bin/env python3
"""Issue #5 の受け入れ基準を検証する。

使い方: python tests/check_attr_courtyard.py [比較元コミット]
  基準 6・7（比較元と同一）は Issue #5 限りの確認なので、比較元コミット（作業直前の main = 3344850）を
  渡したときだけ実行し、省略時は SKIP する。
  基準 11〜14 は既存のチェックを実行する（ネットワークと kicad-cli が必要）。
判定はコミット済みの HEAD に対して行う。
"""

import collections
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


mods = [p for p in git("ls-tree", "-r", "--name-only", "HEAD").splitlines() if p.endswith(".kicad_mod")]
head = {p: K.parse(git("show", f"HEAD:{p}")) for p in mods}
names = {p: os.path.basename(p)[: -len(".kicad_mod")] for p in mods}
by_name = {names[p]: p for p in mods}
HAD_COURTYARD = ("LED_SK6812MINI-E", "RotaryEncoder_EC12E", "RotaryEncoder_EVQWGD001",
                 "RotaryEncoder_MER1045-24-x", "RP2040-QFN-56", "Fiducial_1.5mm")
MOUSEBITE, XIAO = "Breakaway_Mousebite", "Board_XIAO_to_ProMicro"


def crtyd(fp):
    return [g for g in K.graphics(fp) if g[1] == ("F.CrtYd",)]


# 基準 1: attr
report("1 attr がルールどおり",
       [f"[{names[p]}: {sorted(K.attr(fp))} / 期待 {sorted(C.expected_attr(names[p], fp))}]"
        for p, fp in head.items() if set(K.attr(fp)) != C.expected_attr(names[p], fp)], len(mods))

# 基準 2: F.CrtYd があり線幅 0.05
problems = []
for p, fp in head.items():
    gs = crtyd(fp)
    if not gs:
        problems.append(f"[{names[p]}: なし]")
    elif any(g[4] != 0.05 for g in gs):
        problems.append(f"[{names[p]}: 線幅 {sorted(set(g[4] for g in gs))}]")
report("2 F.CrtYd があり線幅 0.05mm", problems, len(mods))

# 基準 3: 閉じた外形
problems = []
for p, fp in head.items():
    es, circles = C.courtyard_edges(fp)
    if not es and not circles:
        problems.append(f"[{names[p]}: 辺なし]")
        continue
    degree = collections.Counter(pt for e in es for pt in e)
    if any(d != 2 for d in degree.values()):
        problems.append(f"[{names[p]}]")
report("3 F.CrtYd が閉じた外形", problems, len(mods))

# 基準 4: スイッチはキーキャップの外形
switches = [p for p in mods if C.is_switch(names[p])]
report("4 スイッチのコートヤードがキーキャップ外形",
       [f"[{names[p]}]" for p in switches
        if set(C.courtyard_edges(head[p])[0]) != C.edges(C.keycap_outline(names[p]))], len(switches))

# 基準 5: スイッチ以外の新規 22 件は外形＋0.25mm
others = [p for p in mods if not C.is_switch(names[p]) and names[p] not in HAD_COURTYARD]
problems = [f"[{names[p]}]" for p in others if set(C.courtyard_edges(head[p])[0]) != C.edges(C.body_rect(head[p]))]
if len(others) != 22:
    problems.append(f"[対象が {len(others)} / 22 件]")
report("5 スイッチ以外の新しいコートヤードが外形+0.25mm", problems, len(others))


# 基準 6, 7: 比較元と同一
def without_crtyd(fp):
    return [g for g in K.graphics(fp) if g[1] != ("F.CrtYd",)]


def pads_for_compare(name, fp):
    # Breakaway_Mousebite の NPTH は基準 8・9 で個別に見るので除く
    return [] if name == MOUSEBITE else K.pads(fp)


if not BASE:
    print("SKIP  6 既存 6 件のコートヤードが比較元と同一（比較元コミットを渡したときだけ実行）")
    print("SKIP  7 attr・コートヤード・個別修正以外が比較元と同一（比較元コミットを渡したときだけ実行）")
else:
    base = {p: K.parse(git("show", f"{BASE}:{p}")) for p in mods}
    report("6 既存 6 件のコートヤードが比較元と同一",
           [f"[{n}]" for n in HAD_COURTYARD if crtyd(base[by_name[n]]) != crtyd(head[by_name[n]])], len(HAD_COURTYARD))
    checks = [lambda n, fp: pads_for_compare(n, fp), lambda n, fp: without_crtyd(fp), lambda n, fp: K.texts(fp),
              lambda n, fp: K.models(fp), lambda n, fp: K.descr(fp), lambda n, fp: K.prop_value(fp, "Value")]
    report("7 attr・コートヤード・個別修正以外が比較元と同一",
           [f"[{names[p]}]" for p in mods if any(c(names[p], base[p]) != c(names[p], head[p]) for c in checks)],
           len(mods))

# 基準 8, 9: Breakaway_Mousebite
mb = [p for p in K.pads(head[by_name[MOUSEBITE]]) if p[1] == "np_thru_hole"]
report("8 マウスバイトの NPTH が *.Cu *.Mask",
       [f"[{p[3][:2]}: {p[6]}]" for p in mb if p[6] != ("*.Cu", "*.Mask")] + ([] if len(mb) == 7 else [f"[NPTH {len(mb)} 個]"]))
positions = sorted(p[3][:2] for p in mb)
report("9 マウスバイトの穴が (3, 0) を含む 1.0mm 刻みの y=0 上",
       [] if positions == [(float(x), 0.0) for x in range(-3, 4)] else [f"[{positions}]"])

# 基準 10: XIAO のパッド 28
pad28 = [p for p in K.children(head[by_name[XIAO]], "pad") if p[1] == "28"]
margin = K.child(pad28[0], "solder_mask_margin") if pad28 else None
report("10 XIAO のパッド 28 に solder_mask_margin 0", [] if margin and K.num(margin[1]) == 0 else [f"[{margin}]"])


# 基準 11〜14: 既存チェック（HEAD の版を実行）
def run(cmd, script=None):
    r = subprocess.run(cmd, input=script.encode("utf-8") if script else None, cwd=ROOT, capture_output=True)
    lines = r.stdout.decode("utf-8", "replace").splitlines()
    return [] if r.returncode == 0 else [l for l in lines if l.startswith("FAIL")] or [f"[exit {r.returncode}]"]


def run_python_check(name):
    with tempfile.TemporaryDirectory() as tmp:
        for f in (name, "kicad_mod.py"):
            with open(os.path.join(tmp, f), "w", encoding="utf-8", newline="\n") as out:
                out.write(git("show", f"HEAD:tests/{f}"))
        return run([sys.executable, os.path.join(tmp, name)])


# "bash" だけを渡すと、Windows では System32 の WSL bash が先に見つかるため、PATH 上のフルパスで起動する
bash = shutil.which("bash")
report("11 check_layout.sh", run([bash, "-s"], git("show", "HEAD:tests/check_layout.sh")) if bash else ["[bash が見つからない]"])
report("12 check_format.py", run_python_check("check_format.py"))
report("13 check_models.py", run_python_check("check_models.py"))
report("14 check_import.py", run_python_check("check_import.py"))

sys.exit(1 if failed else 0)
