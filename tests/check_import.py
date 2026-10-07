#!/usr/bin/env python3
"""Issue #15 の受け入れ基準を検証する。

使い方: python tests/check_import.py [比較元コミット] [取り込み元フォルダ]
  基準 2（Choc の楕円穴以外が比較元と同一）は比較元コミット（作業直前の main = cb25e17）を、
  基準 4（取り込んだ 3 件が取り込み元と同一）は取り込み元フォルダを渡したときだけ実行し、
  省略時は SKIP する。どちらも Issue #15 限りの確認なので、常用のチェックを RED にしない。
  基準 9〜11 は既存のチェックを実行する（check_layout.sh 経由でネットワークが必要）。
判定はコミット済みの HEAD に対して行う。
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicad_mod as K  # noqa: E402

# Windows のコンソール (cp932) でも日本語を出せるようにする
sys.stdout.reconfigure(encoding="utf-8")

BASE = sys.argv[1] if len(sys.argv) > 1 else ""
SOURCE = sys.argv[2] if len(sys.argv) > 2 else ""
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


def skip(label, why):
    print(f"SKIP  {label}（{why}）")


files = git("ls-tree", "-r", "--name-only", "HEAD").splitlines()
mods = [p for p in files if p.endswith(".kicad_mod")]
head = {p: K.parse(git("show", f"HEAD:{p}")) for p in mods}

# ---- Issue #15 の内容 ----
SLOT_AT = (5.0, -5.55)
SLOT = ("", "np_thru_hole", "oval", (5.0, -5.55, 0.0), (1.0, 0.3), ("'oval'", 1.0, 0.3), ("*.Cu", "*.Mask"))
IMPORTS = {  # 取り込み元の名前: (ライブラリ, 新しい名前, descr。None は取り込み元の descr をそのまま使う)
    "MER1045-24-x": ("Marby_Input", "RotaryEncoder_MER1045-24-x", None),
    "mousebite": ("Marby_Mechanical", "Breakaway_Mousebite",
                  "Mouse bites (perforated breakaway holes) for panel separation"),
    "xiao2promicro": ("Marby_MCU", "Board_XIAO_to_ProMicro",
                      "Seeed XIAO mounted on a Pro Micro footprint (adapter)"),
}
EXCLUDED = ("ChocSwitch_hotswap_1_00u_rev", "名称未設定")
choc = [p for p in mods if os.path.basename(p).startswith("ChocSwitch_")]


def path_of(lib, name):
    return f"footprints/{lib}.pretty/{name}.kicad_mod"


def slot(fp):
    return [p for p in K.pads(fp) if p[3][:2] == SLOT_AT]


def without_slot(fp):
    return [p for p in K.pads(fp) if p[3][:2] != SLOT_AT]


# 基準 1: Choc の楕円穴
problems = [f"[{os.path.basename(p)}]" for p in choc if slot(head[p]) != [SLOT]]
if len(choc) != 16:
    problems.append(f"[Choc が {len(choc)} 件 / 16 件]")
report("1 Choc の楕円穴がメッキなし 1.0x0.3", problems, len(choc))

# 基準 2: 楕円穴以外は比較元と同一
CHECKS = [without_slot, K.graphics, K.texts, K.models, K.attr, K.descr, lambda fp: K.prop_value(fp, "Value")]
if not BASE:
    skip("2 Choc の楕円穴以外が比較元と同一", "比較元コミットを渡したときだけ実行")
else:
    problems = []
    for p in choc:
        base = K.parse(git("show", f"{BASE}:{p}"))
        if any(fn(base) != fn(head[p]) for fn in CHECKS):
            problems.append(f"[{os.path.basename(p)}]")
    report("2 Choc の楕円穴以外が比較元と同一", problems, len(choc))

# 基準 3: 取り込んだ 3 件の場所と名前
problems = []
for src, (lib, name, _) in IMPORTS.items():
    p = path_of(lib, name)
    if p not in head:
        problems.append(f"[{p} がない]")
    elif K.name(head[p]) != name:
        problems.append(f"[{name}: 内部名 '{K.name(head[p])}']")
report("3 取り込んだ 3 件の場所と名前", problems, len(IMPORTS))

present = {src: head[path_of(lib, name)] for src, (lib, name, _) in IMPORTS.items() if path_of(lib, name) in head}

# 基準 4: パッドと図形が取り込み元と同一
if not SOURCE:
    skip("4 取り込んだ 3 件のパッドと図形が取り込み元と同一", "取り込み元フォルダを渡したときだけ実行")
else:
    problems = []
    for src in IMPORTS:
        if src not in present:
            problems.append(f"[{src}: 取り込み先がない]")
            continue
        with open(os.path.join(SOURCE, src + ".kicad_mod"), encoding="utf-8") as f:
            orig = K.parse(f.read())
        if K.pads(orig) != K.pads(present[src]) or K.graphics(orig) != K.graphics(present[src]):
            problems.append(f"[{src}]")
    report("4 取り込んだ 3 件のパッドと図形が取り込み元と同一", problems, len(IMPORTS))


# 基準 5: descr
def want_descr(src):
    descr = IMPORTS[src][2]
    if descr is not None:
        return descr
    # MER1045-24-x は取り込み元の descr をそのまま使う。Issue に全文を載せた文字列の先頭で照合する
    return None


problems = []
for src, fp in present.items():
    want = want_descr(src)
    if want is None:
        if not K.descr(fp).startswith("knitter-switch MER1045-24-x, incremental rotary encoder 24 detents/pulses"):
            problems.append(f"[{src}]")
        elif SOURCE:
            with open(os.path.join(SOURCE, src + ".kicad_mod"), encoding="utf-8") as f:
                if K.descr(K.parse(f.read())) != K.descr(fp):
                    problems.append(f"[{src}: 取り込み元の descr と違う]")
    elif K.descr(fp) != want:
        problems.append(f"[{src}]")
report("5 取り込んだ 3 件の descr", problems + [f"[{s}: なし]" for s in IMPORTS if s not in present], len(IMPORTS))

# 基準 6: Value
report("6 取り込んだ 3 件の Value",
       [f"[{IMPORTS[s][1]}: '{K.prop_value(fp, 'Value')}']" for s, fp in present.items()
        if K.prop_value(fp, "Value") != IMPORTS[s][1]] + [f"[{s}: なし]" for s in IMPORTS if s not in present],
       len(IMPORTS))

# 基準 7: 形式と 3D 参照
report("7 取り込んだ 3 件が KiCad 10 形式で 3D 参照なし",
       [f"[{IMPORTS[s][1]}]" for s, fp in present.items() if K.version(fp) != "20260206" or K.models(fp)]
       + [f"[{s}: なし]" for s in IMPORTS if s not in present], len(IMPORTS))

# 基準 8: 取り込まない 2 件が footprints/ にない
report("8 取り込まない 2 件がない",
       [f"[{p}]" for p in mods if p.startswith("footprints/") and os.path.basename(p)[: -len(".kicad_mod")] in EXCLUDED])

# 基準 9〜11: fixtures への追加と既存チェック
layout = git("show", "HEAD:tests/fixtures/layout.tsv").splitlines()
descr_tsv = git("show", "HEAD:tests/fixtures/descr.tsv").splitlines()
bash = shutil.which("bash")


def run(cmd, script=None):
    r = subprocess.run(cmd, input=script.encode("utf-8") if script else None, cwd=ROOT, capture_output=True)
    lines = r.stdout.decode("utf-8", "replace").splitlines()
    return [] if r.returncode == 0 else [l for l in lines if l.startswith("FAIL")] or [f"[exit {r.returncode}]"]


def run_python_check(name):
    # HEAD の版を実行するため、HEAD のスクリプトと kicad_mod.py を一時ディレクトリに並べる
    with tempfile.TemporaryDirectory() as tmp:
        for f in (name, "kicad_mod.py"):
            with open(os.path.join(tmp, f), "w", encoding="utf-8", newline="\n") as out:
                out.write(git("show", f"HEAD:tests/{f}"))
        return run([sys.executable, os.path.join(tmp, name)])


missing = [n for _, (lib, n, _) in IMPORTS.items() if not any(l.endswith(f"\t{lib}\t{n}") for l in layout)]
# "bash" だけを渡すと、Windows では System32 の WSL bash が先に見つかるため、PATH 上のフルパスで起動する
problems = [f"[layout.tsv に {n} がない]" for n in missing]
problems += (run([bash, "-s"], git("show", "HEAD:tests/check_layout.sh")) if bash else ["[bash が見つからない]"])
report("9 layout.tsv と check_layout.sh", problems)

missing = [n for _, (_, n, _) in IMPORTS.items() if not any(l.startswith(f"{n}\t") for l in descr_tsv)]
report("10 descr.tsv と check_format.py", [f"[descr.tsv に {n} がない]" for n in missing] + run_python_check("check_format.py"))

report("11 check_models.py", run_python_check("check_models.py"))

sys.exit(1 if failed else 0)
