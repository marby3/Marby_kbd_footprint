#!/usr/bin/env python3
"""Issue #4 の受け入れ基準を検証する（基準 5 の描画確認は目視なので除く）。

使い方: python tests/check_models.py [比較元コミット]
  基準 6（3D モデル以外が比較元と同一）は Issue #4 限りの確認なので、比較元コミット
  （作業直前の main = 2124bab）を渡したときだけ実行し、省略時は SKIP する。
  基準 2 は KICAD10_3DMODEL_DIR 環境変数、なければ kicad-cli の場所から標準 3D ライブラリを探す。
判定はコミット済みの HEAD に対して行う。
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
model_paths = {p: [m[0] for m in K.models(fp)] for p, fp in head.items()}

# ---- Issue #4 のモデル表 ----
KS = "${MARBY_KBD_DIR}/3dmodels/keyswitch_model/"
MX_SWITCH = KS + "mx/silent_alpaca/KiCad/silent_alpaca.step"
CHOC_SWITCH = KS + "choc/v1/KiCad/red.step"
MX_SOCKET = KS + "socket/KiCad/mx.step"
CHOC_SOCKET = KS + "socket/KiCad/choc.step"
STAB = KS + "stabilizer/screw_in/KiCad/stabilizer_SIZE.step"
MX_STAB = {"2_00u": "2u", "2_25u": "2u", "2_75u": "2u", "ISO_Enter": "2u", "3_00u": "3u",
           "6_00u": "6u", "6_25u": "6_25u", "7_00u": "7u"}
QFN = "${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/QFN-56-1EP_7x7mm_P0.4mm_EP5.6x5.6mm.step"
SWITCH = re.compile(r"(CherryMXSwitch|ChocSwitch)_(hotswap|solder)_(.+?)(_rev)?$")


def expected(name):
    m = SWITCH.match(name)
    if m:
        family, mount, size, _ = m.groups()
        if family == "CherryMXSwitch":
            want = [MX_SWITCH] + ([MX_SOCKET] if mount == "hotswap" else [])
            if size in MX_STAB:
                want.append(STAB.replace("SIZE", MX_STAB[size]))
        else:
            want = [CHOC_SWITCH] + ([CHOC_SOCKET] if mount == "hotswap" else [])
        return sorted(want)
    if name == "RP2040-QFN-56":
        return [QFN]
    return []


def family(name):
    m = SWITCH.match(name)
    return f"{m.group(1)}_{m.group(2)}" if m else None


# 基準 1: パスはすべて 2 つのパス変数のどちらかで始まる
report("1 パス変数で始まる",
       [f"[{names[p]}: {path}]" for p in mods for path in model_paths[p]
        if not path.startswith(("${MARBY_KBD_DIR}/", "${KICAD10_3DMODEL_DIR}/"))], len(mods))


# 基準 2: 展開したパスが実在する
def stock_3d_dir():
    """KICAD10_3DMODEL_DIR、なければ既定のインストール先を順に探す。"""
    candidates = [os.environ.get("KICAD10_3DMODEL_DIR", ""),
                  "C:/Program Files/KiCad/10.0/share/kicad/3dmodels",
                  "/usr/share/kicad/3dmodels",
                  "/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels"]
    return next((c for c in candidates if c and os.path.isdir(c)), None)


stock = stock_3d_dir()
problems = []
if stock is None or not os.path.isdir(stock):
    problems.append(f"[KiCad 10 の標準 3D ライブラリが見つからない: {stock}]")
for p in mods:
    for path in model_paths[p]:
        real = path.replace("${MARBY_KBD_DIR}", ROOT).replace("${KICAD10_3DMODEL_DIR}", stock or "")
        if not os.path.isfile(real):
            problems.append(f"[{names[p]}: {path}]")
report("2 パスが実在する", problems, sum(len(v) for v in model_paths.values()))

# 基準 3: モデル表と一致
report("3 モデル表と一致",
       [f"[{names[p]}]" for p in mods if sorted(model_paths[p]) != expected(names[p])], len(mods))

# 基準 4: 同じ系統ではスイッチとソケットの配置値が同じ
placements = {}
for p in mods:
    fam = family(names[p])
    if fam is None:
        continue
    for path, values in K.models(head[p]):
        if path in (MX_SWITCH, CHOC_SWITCH, MX_SOCKET, CHOC_SOCKET):
            placements.setdefault((fam, path), {}).setdefault(values, []).append(names[p])
problems = [f"[{fam} {os.path.basename(path)}: {len(groups)} 通り]"
            for (fam, path), groups in sorted(placements.items()) if len(groups) > 1]
report("4 系統内でスイッチとソケットの配置が同じ", problems, len(placements))

# 基準 6: 3D モデル以外は比較元と同一
CHECKS = [K.pads, K.graphics, K.texts, K.attr, K.descr, lambda fp: K.prop_value(fp, "Value")]
if not BASE:
    print("SKIP  6 3D モデル以外が比較元と同一（比較元コミットを渡したときだけ実行）")
else:
    base_files = set(git("ls-tree", "-r", "--name-only", BASE).splitlines())
    problems = []
    for p in mods:
        if p not in base_files:
            problems.append(f"[{names[p]}: 比較元にない]")
            continue
        base = K.parse(git("show", f"{BASE}:{p}"))
        if any(fn(base) != fn(head[p]) for fn in CHECKS):
            problems.append(f"[{names[p]}]")
    report("6 3D モデル以外が比較元と同一", problems, len(mods))

# 基準 7, 8: README
readme = git("show", "HEAD:README.md")
problems = [] if ("MARBY_KBD_DIR" in readme and "パスの設定" in readme) else ["[MARBY_KBD_DIR / パスの設定 の記載がない]"]
report("7 README にパス変数の設定手順", problems)
section = readme.split("## 3D モデル", 1)[1].split("\n## ", 1)[0] if "## 3D モデル" in readme else ""
problems = [] if "git submodule update --init" in section else ["[「## 3D モデル」節に git submodule update --init がない]"]
report("8 README に 3D 表示とサブモジュールの関係", problems)


# 基準 9, 10: 既存チェックが通常実行で PASS（HEAD の版を実行）
def run_head(path, cmd):
    script = git("show", f"HEAD:{path}")
    r = subprocess.run(cmd, input=script.encode("utf-8"), cwd=ROOT, capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    return [] if r.returncode == 0 else [line for line in out.splitlines() if line.startswith("FAIL")] or [f"[exit {r.returncode}]"]


# check_format.py は隣の kicad_mod.py を import するので、HEAD の 2 ファイルを一時ディレクトリに並べて実行する
with tempfile.TemporaryDirectory() as tmp:
    for f in ("check_format.py", "kicad_mod.py"):
        with open(os.path.join(tmp, f), "w", encoding="utf-8", newline="\n") as out:
            out.write(git("show", f"HEAD:tests/{f}"))
    r = subprocess.run([sys.executable, os.path.join(tmp, "check_format.py")], cwd=ROOT, capture_output=True)
    lines = r.stdout.decode("utf-8", "replace").splitlines()
    report("9 check_format.py", [] if r.returncode == 0 else [l for l in lines if l.startswith("FAIL")] or [f"[exit {r.returncode}]"])
# "bash" だけを渡すと、Windows では System32 の WSL bash が先に見つかるため、PATH 上のフルパスで起動する
report("10 check_layout.sh", run_head("tests/check_layout.sh", [shutil.which("bash"), "-s"]))

sys.exit(1 if failed else 0)
