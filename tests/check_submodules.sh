#!/usr/bin/env bash
# Issue #2 の受け入れ基準を検証する。
# 使い方: bash tests/check_submodules.sh [比較元ブランチ (既定: origin/main)]
# 基準 3, 4 はコミット済みの状態を一時ディレクトリへ clone して確かめる。
set -u

BASE="${1:-origin/main}"
ROOT="$(git rev-parse --show-toplevel)"
BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail=0
pass() { echo "PASS  $1"; }
ng()   { echo "FAIL  $1: $2"; fail=1; }

# 基準 1, 2: .gitmodules への登録と固定コミット
check_submodule() {
  local label="$1" path="$2" url="$3" sha="$4" name got_url got_sha
  name="$(git -C "$ROOT" config -f .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null \
    | awk -v p="$path" '$2 == p { sub(/^submodule\./, "", $1); sub(/\.path$/, "", $1); print $1 }')"
  if [ -z "$name" ]; then ng "$label" "path $path が .gitmodules にない"; return; fi
  got_url="$(git -C "$ROOT" config -f .gitmodules "submodule.$name.url")"
  if [ "$got_url" != "$url" ]; then ng "$label" "url が $got_url"; return; fi
  got_sha="$(git -C "$ROOT" ls-tree HEAD "$path" | awk '$1 == "160000" { print $3 }')"
  case "$got_sha" in
    "$sha"*) pass "$label" ;;
    *) ng "$label" "固定コミットが '${got_sha:-なし}'" ;;
  esac
}
check_submodule "1 keyswitch_model" 3dmodels/keyswitch_model https://github.com/koktoh/keyswitch_model.git 2b6bcfa
check_submodule "2 keycap_model"    3dmodels/keycap_model    https://github.com/koktoh/keycap_model.git    1c07721

# 基準 3, 4: --recurse-submodules で clone した直後にファイルがある
if git clone -q --recurse-submodules --branch "$BRANCH" "$ROOT" "$TMP/clone" 2>"$TMP/clone.log"; then
  cloned=1
else
  cloned=0
fi
check_cloned_file() {
  local label="$1" file="$2"
  if [ "$cloned" -ne 1 ]; then ng "$label" "clone 失敗 ($(tail -1 "$TMP/clone.log"))"; return; fi
  if [ -f "$TMP/clone/$file" ]; then pass "$label"; else ng "$label" "$file がない"; fi
}
check_cloned_file "3 keyswitch_model の wrl" 3dmodels/keyswitch_model/mx/silent_alpaca/KiCad/silent_alpaca.wrl
check_cloned_file "4 keycap_model の wrl"    3dmodels/keycap_model/cherry/KiCad/wrl/convex_1u.wrl

# 基準 5: README.md の記載
readme="$ROOT/README.md"
if [ ! -f "$readme" ]; then
  ng "5 README" "README.md がない"
else
  missing=""
  grep -q 'git clone --recurse-submodules' "$readme"           || missing="$missing (a)clone手順"
  grep -q 'git submodule update --init' "$readme"              || missing="$missing (b)後から取得"
  grep -q 'git submodule update --remote' "$readme"            || missing="$missing (c)上流へ更新"
  grep -q 'https://github.com/koktoh/keyswitch_model' "$readme" || missing="$missing (d)keyswitch_modelのURL"
  grep -q 'https://github.com/koktoh/keycap_model' "$readme"    || missing="$missing (d)keycap_modelのURL"
  grep -q 'LICENSE' "$readme"                                  || missing="$missing (d)ライセンス状況"
  if [ -z "$missing" ]; then pass "5 README"; else ng "5 README" "不足:$missing"; fi
fi

# 基準 6: 既存の .kicad_mod に変更がない
changed="$(git -C "$ROOT" diff --name-status "$BASE...HEAD" -- '*.kicad_mod')"
if [ -z "$changed" ]; then pass "6 .kicad_mod 無変更"; else ng "6 .kicad_mod 無変更" "$(echo "$changed" | tr '\n' ' ')"; fi

exit "$fail"
