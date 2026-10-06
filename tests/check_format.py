#!/usr/bin/env python3
"""Issue #6 の受け入れ基準を検証する。

使い方: python tests/check_format.py [比較元コミット]
  基準 2〜6（比較元と同一）は Issue #6 限りの確認なので、比較元コミット
  （アップグレード直前の main = 3909f31）を渡したときだけ実行し、省略時は SKIP する。
  基準 10 は kicad-cli（KiCad 10）が必要。見つからなければ FAIL にする。
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

VERSION = "20260206"
BASE = sys.argv[1] if len(sys.argv) > 1 else ""


ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True,
                      text=True).stdout.strip()


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], check=True, capture_output=True).stdout.decode("utf-8")

DESCR = os.path.join(ROOT, "tests", "fixtures", "descr.tsv")

failed = False


def report(label, problems, total=None):
    global failed
    if problems:
        failed = True
        shown = " ".join(problems[:8]) + (f" ...他 {len(problems) - 8} 件" if len(problems) > 8 else "")
        print(f"FAIL  {label}: {shown}")
    else:
        print(f"PASS  {label}" + (f" ({total} 件)" if total else ""))


def read_tsv(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n").split("\t") for line in f if line.strip()]


mods = [p for p in git("ls-tree", "-r", "--name-only", "HEAD").splitlines() if p.endswith(".kicad_mod")]
head = {p: K.parse(git("show", f"HEAD:{p}")) for p in mods}
names = {p: os.path.basename(p)[: -len(".kicad_mod")] for p in mods}

# 基準 1: 形式
report("1 形式が KiCad 10", [f"[{names[p]}: {K.version(fp)}]" for p, fp in head.items() if K.version(fp) != VERSION],
       len(mods))

# 基準 2〜6: 比較元と同一
CHECKS = [("2 パッド", K.pads), ("3 図形要素", K.graphics), ("4 Reference とユーザーテキスト", K.texts),
          ("5 3D モデル参照", K.models), ("6 attr", K.attr)]
if not BASE:
    for label, _ in CHECKS:
        print(f"SKIP  {label}が比較元と同一（比較元コミットを渡したときだけ実行）")
else:
    # 比較元は再編後なので、HEAD と同じパスで読める
    base_files = set(git("ls-tree", "-r", "--name-only", BASE).splitlines())
    base = {p: K.parse(git("show", f"{BASE}:{p}")) for p in mods if p in base_files}
    for label, fn in CHECKS:
        problems = [f"[{names[p]}]" for p in mods if p not in base or fn(base[p]) != fn(head[p])]
        report(f"{label}が比較元と同一", problems, len(mods))

# 基準 7, 8: descr
want = dict(read_tsv(DESCR))
report("7 descr が表と一致",
       [f"[{names[p]}]" for p in mods if K.descr(head[p]) != want.get(names[p])]
       + [f"[表にあるがファイルがない: {n}]" for n in sorted(set(want) - set(names.values()))],
       len(mods))
report("8 descr が ASCII", [f"[{names[p]}]" for p in mods if not K.descr(head[p]).isascii()], len(mods))

# 基準 9: Value
report("9 Value がフットプリント名",
       [f"[{names[p]}: '{K.prop_value(head[p], 'Value')}']" for p in mods
        if K.prop_value(head[p], "Value") != names[p]], len(mods))

# 基準 10: kicad-cli で読み込める（HEAD の中身を一時ディレクトリへ書き出して試す）
cli = shutil.which("kicad-cli")
if cli is None:
    report("10 kicad-cli で読み込める", ["[kicad-cli が見つからない]"])
else:
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "src"), os.path.join(tmp, "svg")
        for p in mods:
            os.makedirs(os.path.join(src, os.path.dirname(p)), exist_ok=True)
            with open(os.path.join(src, p), "w", encoding="utf-8", newline="\n") as f:
                f.write(git("show", f"HEAD:{p}"))
        problems, count = [], 0
        for lib in sorted({os.path.dirname(p) for p in mods}):
            dest = os.path.join(out, os.path.basename(lib))
            os.makedirs(dest)
            r = subprocess.run([cli, "fp", "export", "svg", "-o", dest, os.path.join(src, lib)],
                               capture_output=True)
            if r.returncode != 0:
                problems.append(f"[{os.path.basename(lib)}: exit {r.returncode}]")
            count += len([f for f in os.listdir(dest) if f.endswith(".svg")])
        if count != len(mods):
            problems.append(f"[SVG {count} 件 / 期待 {len(mods)} 件]")
        report("10 kicad-cli で読み込める", problems, count)

# 基準 11: check_layout.sh が引き続き PASS（HEAD の版を実行）
script = git("show", "HEAD:tests/check_layout.sh")
# "bash" だけを渡すと、Windows では System32 の WSL bash が先に見つかるため、PATH 上のフルパスで起動する
r = subprocess.run([shutil.which("bash"), "-s"], input=script.encode("utf-8"), cwd=ROOT, capture_output=True)
out = r.stdout.decode("utf-8", "replace")
report("11 check_layout.sh", [] if r.returncode == 0 else [line for line in out.splitlines() if line.startswith("FAIL")])

sys.exit(1 if failed else 0)
