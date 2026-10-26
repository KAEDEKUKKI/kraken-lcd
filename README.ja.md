<div align="center">

# 🎮 Kraken Z53 LCD モニター — ネオンゲーミング少女 HUD

**[English](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)**

Linux 環境の **NZXT Kraken Z53**（`320x320` 円形液晶ディスプレイ）向けに設計された、ストリートグラフィティ風 **ネオンゲーミング少女 HUD** システムモニターです。事前ベイク済みの特大グラフィティ数字スプライト、CPU/GPU の負荷や温度に応じた3段階のキャラクター表情変化（`IDLE` ／ `GAMING` ／ `OVERHEAT`）、および白フラッシュを完全に防ぐ **Ping-Pong ゼロフラッシュ更新** を備えています。

![ネオンゲーミング少女 HUD - 3段階ステータスプレビュー](assets/preview_states.png)

</div>

---

## ✨ 主な特徴

- **🎨 3段階の動的キャラクター表情変化（ヒステリシス制御付き）**
  リアルタイムの CPU / GPU 使用率と温度に応じてキャラクターの表情が自動的に切り替わります。しきい値付近でのチラつきを防ぐヒステリシス（履歴現象）バッファを内蔵しています：
  - **🟢 `IDLE`（リラックスした笑顔）**：アイドル・低負荷時（使用率 `< 50%` かつ温度 `< 65°C`）
  - **🟣 `GAMING`（挑発的な舌出し表情）**：ゲームプレイ・中高負荷時（使用率 `>= 50%` または温度 `>= 65°C`）
  - **🔴 `OVERHEAT`（赤面・発汗のオーバーヒート表情）**：高負荷・高温時（温度 `>= 80°C` または使用率 `>= 90%`）
- **⚡ 事前ベイク済み特大グラフィティ数字スプライト（Sprite Sheet）**
  `1254x1254` キャンバス基準の特大イタリック数字スプライト（`assets/sprites/{cpu,gpu,mem}/`）を事前にレンダリング。極太の黒縁取り、ソリッドなネオンオフセットシャドウ、2層のネオングローを備え、**実行時の CPU 負荷をほぼゼロ**に抑えています。
- **🛡️ Ping-Pong ゼロフラッシュ USB 更新 & スマートスキップ**
  `liquidctl` が 16 個のバケットを使い果たした際に `_delete_all_buckets()` を呼び出して画面が白くフラッシュする問題を解決。**Bucket 0（`0 KB`）** と **Bucket 1（`512 KB`）** の2スロットのみを交互に書き換えるダブルバッファリング方式を採用し、数値変動が `< 1%` / `< 1°C` の場合は USB 転送をスキップします。
- **🔄 ポンプ取り付け角度に合わせた画面回転**
  `--orientation {0, 90, 180, 270}` オプションにより、水冷ヘッドの設置向きに合わせて表示を回転できます。

---

## 📁 プロジェクト構成

```text
kraken-lcd/
├── kraken_monitor.py          # メイン CLI エントリーポイント・監視ループ
├── config.py                  # 設定ファイル（解像度、配色、しきい値、パネル座標）
├── build_assets.py            # 背景・グラフィティ数字スプライト生成スクリプト
├── kraken-lcd.service         # Systemd サービスユニット定義
├── install-service.sh         # Systemd サービス自動インストールスクリプト
├── run.sh                     # 起動ヘルパースクリプト
├── requirements.txt           # Python 依存パッケージ一覧
├── monitor/
│   ├── collector.py           # CPU (psutil)・メモリ・GPU (nvidia-smi / sysfs) 情報取得
│   ├── state.py               # ヒステリシス付き3段階ステートマシン
│   ├── renderer.py            # 傾斜 HUD パネル合成・スプライト描画エンジン
│   └── device.py              # liquidctl USB 通信 & Ping-Pong ダブルバッファ転送
├── assets/
│   ├── backgrounds/           # 1254x1254 高解像度ステータス背景 (idle, gaming, overheat)
│   ├── sprites/               # 事前ベイク済みグラフィティ数字スプライト (cpu/, gpu/, mem/)
│   └── fonts/                 # 同梱ディスプレイフォント
└── tests/                     # ユニット・結合テストスイート
```

---

## 🚀 クイックスタート

### 1. 必要環境
- Linux OS、Python **3.10+**
- `libusb` / `hidapi`（`liquidctl` が NZXT Kraken Z53 と通信するために必要）
- NVIDIA ドライバ（`nvidia-smi`）または AMD/Intel `hwmon`/`drm` sysfs インターフェース

### 2. インストール
```bash
git clone https://github.com/KAEDEKUKKI/kraken-lcd.git
cd kraken-lcd

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. 使い方

```bash
# ドライラン（実機に接続せず、320x320 のプレビュー画像を出力）
.venv/bin/python kraken_monitor.py --dry-run --output /tmp/kraken_lcd.png

# 特定の表情ステータスを強制指定して出力 (idle / gaming / overheat)
.venv/bin/python kraken_monitor.py --dry-run --force-state overheat --output /tmp/overheat.png

# Kraken Z53 実機で連続モニタリングを実行（3秒間隔、反時計回り90°回転）
sudo .venv/bin/python kraken_monitor.py --loop --interval 3 --orientation 90
```

#### コマンドラインオプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--loop` | オフ | 1 枚だけ描画せず、継続的に更新する |
| `--interval <秒>` | `3` | ループモードでの更新間隔（秒） |
| `--dry-run` | オフ | デバイスに送信せず、描画結果を PNG に保存する |
| `--output <パス>` | `/tmp/kraken_lcd.png` | ドライラン時の出力先 |
| `--no-gpu` | オフ | GPU の検出をスキップする |
| `--orientation {0,90,180,270}` | `0` | ポンプの取り付け角度に合わせて画像を回転する |
| `--force-state {idle,gaming,overheat}` | 自動 | 自動切り替えを無効にし、表情を固定する |

### 4. Systemd サービスとして登録（OS 起動時に自動実行）
```bash
sudo ./install-service.sh
```
サービス管理コマンド：
```bash
sudo systemctl status kraken-lcd.service
sudo journalctl -u kraken-lcd.service -f
sudo systemctl restart kraken-lcd.service
```

> [!NOTE]
> `kraken-lcd.service` 内の `/home/kukki/kraken-lcd` はプレースホルダーです。`install-service.sh` がインストール時に、実際に clone したディレクトリへ自動的に書き換えます。更新間隔や回転角度を変更する場合は、サービスファイルの `ExecStart` を編集してください。

---

## ⚙️ 設定

調整可能なパラメータはすべて [`config.py`](config.py) にまとめられています：

- `STATE_THRESHOLDS` — `GAMING` / `OVERHEAT` ステータスの移行／解除しきい値（使用率 % と °C）とヒステリシス幅
- `PANEL_CONFIGS` — CPU / GPU / MEMORY 各パネルの位置、傾き角度、フォントサイズ、ネオンカラー、グロー
- カラー定数（`COLOR_PINK`、`COLOR_CYAN`、`COLOR_GOLD` など）

## 🖌️ アセットの再生成

`assets/` には生成済みの背景と数字スプライトが含まれているため、**モニターの実行にビルド作業は不要です**。
`build_assets.py` は `assets/backgrounds/_raw/` の元画像からアセットを再生成しますが、元画像は**このリポジトリには含まれていません**。アートワークを再生成・カスタマイズしたい場合は、元画像を配置してから実行してください：

```bash
.venv/bin/python build_assets.py
```

---

## 🧪 テストの実行
```bash
.venv/bin/python -m unittest discover -s tests -v
```
