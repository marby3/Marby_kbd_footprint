# Marby_kbd_footprint

自作キーボード向けの KiCad フットプリントライブラリです。

## 構成

```
Marby_kbd_footprint/
├─ footprints/
│  ├─ Marby_Switch.pretty/      キースイッチ（MX / Choc、ホットスワップ / はんだ付け）
│  ├─ Marby_MCU.pretty/         マイコンボード・MCU（BLE Micro Pro, Pico, RP2040, XIAO 変換）
│  ├─ Marby_Input.pretty/       エンコーダー、ジョイスティック、光学センサー、タクトスイッチ
│  ├─ Marby_Connector.pretty/   TRRS ジャック、FPC コネクター、ICSP ヘッダー、OLED 接続用ヘッダー
│  ├─ Marby_Discrete.pretty/    ダイオード、LED
│  └─ Marby_Mechanical.pretty/  ブレークアウェイタブ、マウスバイト、フィデューシャル
├─ 3dmodels/
│  ├─ keyswitch_model/          サブモジュール（キースイッチ・ソケット・スタビライザー）
│  └─ keycap_model/             サブモジュール（キーキャップ）
└─ tests/                       リポジトリ構成のチェックスクリプト（CI 未接続・手動実行）
```

## KiCad への登録

KiCad の「設定」→「フットプリントライブラリーを管理」で、次の 6 つをそれぞれ追加します。表のパスは clone したフォルダの中の位置です。KiCad には、clone 先を含めたフルパスで指定してください。

| nickname | パス |
|---|---|
| `Marby_Switch` | `footprints/Marby_Switch.pretty` |
| `Marby_MCU` | `footprints/Marby_MCU.pretty` |
| `Marby_Input` | `footprints/Marby_Input.pretty` |
| `Marby_Connector` | `footprints/Marby_Connector.pretty` |
| `Marby_Discrete` | `footprints/Marby_Discrete.pretty` |
| `Marby_Mechanical` | `footprints/Marby_Mechanical.pretty` |

nickname は上の表のとおりにそろえておくと、ほかの PC や他人の環境でも基板のリンクがそのまま通ります。

## 3D モデル

スイッチ系フットプリントの 3D モデルは、サブモジュール `3dmodels/keyswitch_model` のファイルを、パス変数 `MARBY_KBD_DIR` を基準に参照しています。3D ビューアーで表示するには、次の 2 つが必要です。

1. サブモジュールを取得しておく。`--recurse-submodules` を付けずに clone した場合は、リポジトリのフォルダで `git submodule update --init` を実行します（[取得方法](#取得方法) も参照）。
2. KiCad の「設定」→「パスの設定」で、名前 `MARBY_KBD_DIR`、パスに clone したフォルダ（例: `C:/Users/<ユーザー名>/Documents/GitHub/Marby_kbd_footprint`）を追加します。

| フットプリント | 3D モデル |
|---|---|
| `CherryMXSwitch_*` | Silent Alpaca。ホットスワップは MX 用ソケット付き、2u 以上と ISO Enter は Screw-in スタビライザー付き |
| `ChocSwitch_*` | Kailh Choc V1 Red。ホットスワップは Choc 用ソケット付き |
| `RP2040-QFN-56` | KiCad 標準ライブラリの QFN-56（`${KICAD10_3DMODEL_DIR}`、設定不要） |
| 上記以外 | なし |

`CherryMXSwitch_hotswap_*` は、裏面（B 面）に置いて使う前提のフットプリントです。表面のまま 3D 表示すると、スイッチが基板の下に表示されます。

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

## 旧構成からの移行

以前はリポジトリ直下に全フットプリントが並んでおり、リポジトリのフォルダを 1 つのライブラリとして登録していました。既存の基板は、フットプリントを基板ファイルの中に持っているので、そのまま開けます。ライブラリから更新できるようにするには、次の手順でリンクを張り直してください。

1. 「フットプリントライブラリーを管理」で、リポジトリ直下を指していた古いライブラリを削除し、[KiCad への登録](#kicad-への登録) の 6 つを追加します。
2. 回路図エディターの「検索と置換」で、シンボルのフットプリントフィールドにある古い nickname を、上の表の新しい nickname に置き換えます。改名したフットプリントは、下の対応表に従って名前も置き換えます。
3. PCB エディターで「回路図から PCB を更新」を実行し、フットプリントのリンクを更新します。
4. 削除したフットプリントを使っている基板では、基板内のフットプリントはそのまま残ります。ライブラリから更新したい場合は、別のフットプリントに差し替えてください。

### 改名・削除したフットプリント

| 旧名 | 新名 | ライブラリ |
|---|---|---|
| `PMW3360DM-T2QU 16Pin_34mmBall` | `OpticalMouseSensor_PMW3360DM-T2QU_34mmBall` | `Marby_Input` |
| `XUNPU FPC-05F-12PH20` | `FPC_XUNPU_FPC-05F-12PH20` | `Marby_Connector` |
| `Diode_TH&SMD` | `Diode_TH_SMD` | `Marby_Discrete` |
| `RP2040-tiny` | `Board_RP2040-Tiny` | `Marby_MCU` |
| `microSwitch_6x6x7.3mm` | `MicroSwitch_6x6x7.3mm` | `Marby_Input` |
| `ICSP` | `ICSP_2x3` | `Marby_Connector` |
| `OLED` | `OLED_4Pin` | `Marby_Connector` |
| `tooling_hole` | `Fiducial_1.5mm` | `Marby_Mechanical` |
| `725996-2` | （削除） | — |
| `FC-030` | （削除） | — |
| `joystick` | （削除） | — |

上の表にないフットプリントは、名前を変えずにいずれかのライブラリへ移しています。

`RotaryEncoder_MER1045-24-x`、`Breakaway_Mousebite`、`Board_XIAO_to_ProMicro` の 3 件は、旧構成に含まれていなかった作業途中のフットプリントを、新しい構成に合わせた名前で追加したものです（#15）。旧構成からの改名ではないので、上の表には載せていません。

## サブモジュールの出典とライセンス

| パス | 出典 | ライセンス |
|---|---|---|
| `3dmodels/keyswitch_model` | https://github.com/koktoh/keyswitch_model | リポジトリに LICENSE ファイルはありません |
| `3dmodels/keycap_model` | https://github.com/koktoh/keycap_model | MIT |

どちらも koktoh さんのリポジトリを参照しているだけで、このリポジトリにはファイルを含めていません。keyswitch_model には LICENSE ファイルがないため、モデルを再配布する場合は出典リポジトリで利用条件を確認してください。

## ライセンス

このリポジトリのフットプリントは [MIT License](LICENSE) です。サブモジュールには、それぞれの出典リポジトリのライセンスが適用されます。
