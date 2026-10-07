"""フットプリントを 1 つずつ基板に載せ、3D 描画した PNG を書き出す（Issue #4 基準 5 の目視確認用）。

KiCad 同梱の Python で実行する（pcbnew モジュールが必要）:
  "C:/Program Files/KiCad/10.0/bin/python.exe" tests/render_models.py <出力先> <フットプリント名>...

- MX ホットスワップは裏面に置く前提のフットプリントなので、裏返して B 面に置く
- 上面（top）・下面（bottom）・側面（front）の 3 枚を書き出す
- 3D モデルのパス変数 MARBY_KBD_DIR はリポジトリのルートに設定して描画する
- kicad-cli は利用者の 3D ビューアー設定（THT を隠す等）に従うため、一時的な設定フォルダ
  （KICAD_CONFIG_HOME）で全種類のモデルを表示させて描画する。利用者の設定は変えない
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOOTPRINTS = os.path.join(ROOT, "footprints")


def library_of(name):
    for lib in sorted(os.listdir(FOOTPRINTS)):
        if os.path.isfile(os.path.join(FOOTPRINTS, lib, name + ".kicad_mod")):
            return os.path.join(FOOTPRINTS, lib)
    raise SystemExit(f"見つからない: {name}")


def board_with(name, path):
    board = pcbnew.BOARD()
    fp = pcbnew.FootprintLoad(library_of(name), name)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    board.Add(fp)
    if name.startswith("CherryMXSwitch_hotswap_"):
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    # フットプリントの外形より一回り大きい基板外形
    box = fp.GetBoundingBox(False)
    margin = pcbnew.FromMM(3)
    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECTANGLE)
    rect.SetStart(pcbnew.VECTOR2I(box.GetLeft() - margin, box.GetTop() - margin))
    rect.SetEnd(pcbnew.VECTOR2I(box.GetRight() + margin, box.GetBottom() + margin))
    rect.SetLayer(pcbnew.Edge_Cuts)
    board.Add(rect)
    board.Save(path)


def config_home(tmp):
    """利用者の KiCad 設定を写し、3D ビューアーで全種類のモデルを表示する設定にした設定フォルダを作る。"""
    src = os.path.join(os.environ.get("APPDATA", ""), "kicad")
    dest = os.path.join(tmp, "kicad")
    if os.path.isdir(src):
        shutil.copytree(src, dest)
    version_dir = os.path.join(dest, "10.0")
    os.makedirs(version_dir, exist_ok=True)
    viewer = os.path.join(version_dir, "3d_viewer.json")
    settings = json.load(open(viewer, encoding="utf-8")) if os.path.isfile(viewer) else {}
    render = settings.setdefault("render", {})
    for key in ("show_footprints_normal", "show_footprints_insert", "show_footprints_virtual",
                "show_footprints_not_in_posfile", "show_footprints_dnp"):
        render[key] = True
    json.dump(settings, open(viewer, "w", encoding="utf-8"), indent=2)
    return dest


def main():
    out = os.path.abspath(sys.argv[1])
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp()
    env = dict(os.environ, MARBY_KBD_DIR=ROOT.replace("\\", "/"), KICAD_CONFIG_HOME=config_home(tmp))
    cli = os.path.join(os.path.dirname(sys.executable), "kicad-cli.exe")
    if not os.path.isfile(cli):
        cli = "kicad-cli"
    for name in sys.argv[2:]:
        pcb = os.path.join(out, name + ".kicad_pcb")
        board_with(name, pcb)
        for side, rotate in (("top", None), ("bottom", None), ("front", None)):
            png = os.path.join(out, f"{name}_{side}.png")
            cmd = [cli, "pcb", "render", "--side", side, "--width", "900", "--height", "700",
                   "--quality", "high", "--background", "opaque", "-D", f"MARBY_KBD_DIR={env['MARBY_KBD_DIR']}",
                   "-o", png, pcb]
            if rotate:
                cmd += ["--rotate", rotate]
            r = subprocess.run(cmd, env=env, capture_output=True, text=True)
            print(f"{name} {side}: exit {r.returncode}")
            if r.returncode != 0:
                print(r.stdout[-500:], r.stderr[-500:])


if __name__ == "__main__":
    main()
