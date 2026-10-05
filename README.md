# Marby_kbd_footprint

自作キーボード向けの KiCad フットプリントライブラリです。

## 構成

```
Marby_kbd_footprint/
├─ *.kicad_mod              フットプリント本体
├─ 3dmodels/
│  ├─ keyswitch_model/      サブモジュール（キースイッチ・ソケット・スタビライザー）
│  └─ keycap_model/         サブモジュール（キーキャップ）
└─ tests/                   リポジトリ構成のチェックスクリプト
```

KiCad の「フットプリントライブラリを管理」でこのリポジトリのフォルダを登録してください。`3dmodels/` などのサブフォルダは、フットプリントとしては読み込まれません。

## 取得方法

### 新しく clone する

3D モデルをサブモジュールで取り込んでいるので、`--recurse-submodules` を付けて clone します。

```bash
git clone --recurse-submodules https://github.com/marby3/Marby_kbd_footprint.git
```

### clone 済みのリポジトリで 3D モデルを取得する

`--recurse-submodules` を付けずに clone した場合、`3dmodels/` 配下は空のままです。リポジトリのフォルダで次を実行してください。

```bash
git submodule update --init
```

`git pull` でサブモジュールの固定コミットが変わったときも、同じコマンドで手元を合わせます。

### サブモジュールを上流の最新に更新する

サブモジュールは特定のコミットに固定しています。上流の更新を取り込むときは次を実行し、変わった参照をコミットします。

```bash
git submodule update --remote
```

## サブモジュールの出典とライセンス

| パス | 出典 | ライセンス |
|---|---|---|
| `3dmodels/keyswitch_model` | https://github.com/koktoh/keyswitch_model | リポジトリに LICENSE ファイルはありません |
| `3dmodels/keycap_model` | https://github.com/koktoh/keycap_model | MIT |

どちらも koktoh さんのリポジトリを参照しているだけで、このリポジトリにはファイルを含めていません。keyswitch_model には LICENSE ファイルがないため、モデルを再配布する場合は出典リポジトリで利用条件を確認してください。

## ライセンス

このリポジトリのフットプリントは [MIT License](LICENSE) です。サブモジュールには、それぞれの出典リポジトリのライセンスが適用されます。
