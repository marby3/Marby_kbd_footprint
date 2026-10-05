#!/usr/bin/env bash
# Issue #3 の受け入れ基準を検証する。
# 使い方: bash tests/check_layout.sh [比較元コミット (既定: d030ebb)]
# 配置表は tests/fixtures/layout.tsv（旧名<TAB>ライブラリ<TAB>新名）。
# 判定はコミット済みの HEAD に対して行う。
set -u

BASE="${1:-d030ebb}"
ROOT="$(git rev-parse --show-toplevel)"
LAYOUT="$ROOT/tests/fixtures/layout.tsv"
LIBS="Marby_Connector Marby_Discrete Marby_Input Marby_MCU Marby_Mechanical Marby_Switch"
DELETED="725996-2 FC-030 joystick"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail=0
pass() { echo "PASS  $1"; }
ng()   { echo "FAIL  $1: $2"; fail=1; }

git -C "$ROOT" ls-tree -r --name-only HEAD > "$TMP/files"
grep '\.kicad_mod$' "$TMP/files" > "$TMP/mods"

# 基準 1: ルートに .kicad_mod がなく、footprints/ 直下は6ライブラリだけ
root_mods="$(grep -v / "$TMP/mods")"
dirs="$(grep '^footprints/' "$TMP/files" | cut -d/ -f2 | sort -u | tr '\n' ' ')"
want_dirs="$(for l in $LIBS; do echo "$l.pretty"; done | sort | tr '\n' ' ')"
if [ -n "$root_mods" ]; then ng "1 フォルダ構成" "直下に $(echo "$root_mods" | wc -l) 個の .kicad_mod"
elif [ "$dirs" != "$want_dirs" ]; then ng "1 フォルダ構成" "footprints/ 直下が '$dirs'"
else pass "1 フォルダ構成"; fi

# 基準 2: 配置表と過不足なく一致
awk -F'\t' '{ print "footprints/" $2 ".pretty/" $3 ".kicad_mod" }' "$LAYOUT" | sort > "$TMP/want"
sort "$TMP/mods" > "$TMP/got"
if diff -q "$TMP/want" "$TMP/got" >/dev/null; then pass "2 配置表と一致 ($(wc -l < "$TMP/want") 件)"
else ng "2 配置表と一致" "不足 $(comm -23 "$TMP/want" "$TMP/got" | wc -l) 件 / 余分 $(comm -13 "$TMP/want" "$TMP/got" | wc -l) 件"; fi

# 基準 3: 改名した旧名がどこにも残っていない
left=""
while IFS=$'\t' read -r old lib new; do
  [ "$old" = "$new" ] && continue
  grep -qF "/$old.kicad_mod" "$TMP/mods" && left="$left [$old]"
  grep -qxF "$old.kicad_mod" "$TMP/mods" && left="$left [$old]"
done < "$LAYOUT"
if [ -z "$left" ]; then pass "3 旧名が残っていない"; else ng "3 旧名が残っていない" "$left"; fi

# 基準 4: 削除対象がどこにも残っていない
left=""
for d in $DELETED; do
  grep -qE "(^|/)$d\.kicad_mod$" "$TMP/mods" && left="$left [$d]"
done
if [ -z "$left" ]; then pass "4 削除対象が残っていない"; else ng "4 削除対象が残っていない" "$left"; fi

# 基準 5: ファイル内のフットプリント名がファイル名と一致
bad=""
while IFS= read -r f; do
  name="$(git -C "$ROOT" show "HEAD:$f" | head -1 | sed -nE 's/^\(footprint "([^"]*)".*/\1/p')"
  base="$(basename "$f" .kicad_mod)"
  [ "$name" = "$base" ] || bad="$bad [$f: '$name']"
done < "$TMP/mods"
if [ -z "$bad" ]; then pass "5 フットプリント名とファイル名が一致"; else ng "5 フットプリント名とファイル名が一致" "$bad"; fi

# 基準 6: (footprint "..." 行以外は BASE の旧ファイルと同一
bad=""
while IFS=$'\t' read -r old lib new; do
  git -C "$ROOT" show "$BASE:$old.kicad_mod" 2>/dev/null | grep -v '^(footprint "' > "$TMP/a"
  git -C "$ROOT" show "HEAD:footprints/$lib.pretty/$new.kicad_mod" 2>/dev/null | grep -v '^(footprint "' > "$TMP/b"
  if [ ! -s "$TMP/b" ] || ! cmp -s "$TMP/a" "$TMP/b"; then bad="$bad [$new]"; fi
done < "$LAYOUT"
if [ -z "$bad" ]; then pass "6 中身が変わっていない"; else ng "6 中身が変わっていない" "$bad"; fi

# 基準 7〜9: README.md
readme="$(git -C "$ROOT" show HEAD:README.md 2>/dev/null)"
missing=""
# 構成図は罫線文字を含むため、正規表現の文字クラスに入れず固定文字列で探す（msys grep が落ちる）
tree="$(echo "$readme" | sed -n '/^## 構成/,/^## /p')"
echo "$tree" | grep -qF 'footprints/' || missing="$missing (構成図に footprints/)"
for l in $LIBS; do echo "$tree" | grep -qF "$l.pretty/" || missing="$missing $l"; done
if [ -z "$missing" ]; then pass "7 README 構成図"; else ng "7 README 構成図" "不足:$missing"; fi

missing=""
for l in $LIBS; do echo "$readme" | grep -qE "^\|.*\`$l\`.*\`footprints/$l\.pretty\`" || missing="$missing $l"; done
if [ -z "$missing" ]; then pass "8 README nickname とパスの表"; else ng "8 README nickname とパスの表" "不足:$missing"; fi

missing=""
echo "$readme" | grep -q '移行' || missing="$missing (移行手順)"
while IFS=$'\t' read -r old lib new; do
  [ "$old" = "$new" ] && continue
  echo "$readme" | grep -F "$old" | grep -qF "$new" || missing="$missing [$old→$new]"
done < "$LAYOUT"
for d in $DELETED; do
  echo "$readme" | grep -E "^\|.*\`$d\`" | grep -q '削除' || missing="$missing [$d 削除]"
done
if [ -z "$missing" ]; then pass "9 README 移行手順と対応表"; else ng "9 README 移行手順と対応表" "不足:$missing"; fi

# 基準 10: check_submodules.sh から無変更チェックが外れ、残りが PASS
if git -C "$ROOT" show HEAD:tests/check_submodules.sh | grep -q '\.kicad_mod 無変更'; then
  ng "10 check_submodules.sh" "「.kicad_mod 無変更」チェックが残っている"
elif out="$(bash "$ROOT/tests/check_submodules.sh" 2>&1)"; then
  pass "10 check_submodules.sh"
else
  ng "10 check_submodules.sh" "$(echo "$out" | grep FAIL | tr '\n' ' ')"
fi

exit "$fail"
