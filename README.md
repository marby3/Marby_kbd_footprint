# Marby_kbd_footprint

自作キーボード向けの KiCad フットプリントライブラリです。

## 構成

```
Marby_kbd_footprint/
├─ footprints/
│  ├─ Marby_Switch.pretty/      キースイッチ（MX / Choc、ホットスワップ / はんだ付け）
│  ├─ Marby_MCU.pretty/         マイコンボード・MCU（BLE Micro Pro, Pico, RP2040）
│  ├─ Marby_Input.pretty/       エンコーダー、ジョイスティック、光学センサー、タクトスイッチ
│  ├─ Marby_Connector.pretty/   TRRS、FPC、ICSP、OLED 用ピンヘッダー
│  ├─ Marby_Discrete.pretty/    ダイオード、LED
│  └─ Marby_Mechanical.pretty/  ブレークアウェイタブ、フィデューシャル
├─ 3dmodels/
│  ├─ keyswitch_model/          サブモジュール（キースイッチ・ソケット・スタビライザー）
│  └─ keycap_model/             サブモジュール（キーキャップ）
└─ tests/                       リポジトリ構成のチェックスクリプト
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
| `725996-2` | （削除） | |
| `FC-030` | （削除） | |
| `joystick` | （削除） | |

上の表にないフットプリントは、名前を変えずにいずれかのライブラリへ移しています。

## サブモジュールの出典とライセンス

| パス | 出典 | ライセンス |
|---|---|---|
| `3dmodels/keyswitch_model` | https://github.com/koktoh/keyswitch_model | リポジトリに LICENSE ファイルはありません |
| `3dmodels/keycap_model` | https://github.com/koktoh/keycap_model | MIT |

どちらも koktoh さんのリポジトリを参照しているだけで、このリポジトリにはファイルを含めていません。keyswitch_model には LICENSE ファイルがないため、モデルを再配布する場合は出典リポジトリで利用条件を確認してください。

## ライセンス

このリポジトリのフットプリントは [MIT License](LICENSE) です。サブモジュールには、それぞれの出典リポジトリのライセンスが適用されます。
