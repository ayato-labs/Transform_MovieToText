<p align="center">
  <img src="assets/icon.png" alt="Transform_MovieToText" width="120"/>
</p>

<h1 align="center">Transform_MovieToText</h1>

<p align="center">
  <strong>100% Local AI Transcription & Knowledge Engine (Windows Exclusive)</strong><br/>
  1バイトも外部に送信しない、完全ローカル完結のAI議事録 & ナレッジ検索
</p>

<p align="center">
  <img src="https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/actions/workflows/ci.yml/badge.svg" alt="CI">
  <img src="https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/actions/workflows/desktop_distribution.yml/badge.svg" alt="Desktop Build">
  <img src="https://img.shields.io/badge/python-3.11-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/platform-Windows%20Only-blue.svg" alt="Platform">
  <img src="https://img.shields.io/badge/privacy-100%25_local-green.svg" alt="Privacy">
  <img src="https://img.shields.io/badge/cost-free-brightgreen.svg" alt="Cost">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
</p>

---

## 課題

| ビジネス上の課題 | 既存SaaSの限界 | 本アプリの回答 |
| :--- | :--- | :--- |
| 機密会議の内容をAIに渡せない | クラウドに音声データが送信される | **全処理がローカル完結。回線を抜いても動作する** |
| SaaS費用が毎月かさむ | Whisper API + GPT-4 で1時間あたり数百円 | **導入費0円、月額0円、利用制限なし** |
| 過去の会議内容を探し出せない | 手動でファイルを検索する必要がある | **AIチャットに質問するだけで即座にソース付き回答** |

---

## 主な機能

### 文字起こし
- **ファイル文字起こし** -- MP4, MP3, WAV 等から高精度なテキストを抽出
- **リアルタイム文字起こし** -- オンライン会議の音声をリアルタイムでキャプチャ (Windows WASAPI Loopback対応)
- **物理カット＋重ね合わせ方式** -- 5秒のオーバーラップで継ぎ目のない長時間処理を実現

### AI議事録
- 文字起こし完了後、ローカルLLMが自動で清書・要約・構造化
- 概要、決定事項、ネクストアクションを一括出力

### ナレッジ検索 (Non-Embedding RAG)
- 過去の全会議データに対して自然言語で質問
- AIの回答には**引用元(会議名・日時)がシステムロジックとして自動付与**
- プロジェクト単位での絞り込みに対応

### ROIダッシュボード
- 処理実績から「節約された作業時間」「回避されたSaaSコスト」をリアルタイム算出
- 導入効果を数値で証明

---

## 🗺️ アーキテクチャの進化とロードマップ (ADR)

本プロジェクトは保守性と配布効率を極限まで高めるため、以下の重要なアーキテクチャ決定(ADR)を行っています。

*   **ADR-0001: Windows特化への方針転換**
    *   開発リソースの集中と依存関係の複雑化を避けるため、Android, macOS, Linux サポートを完全に廃止し、Windows 専用アプリケーションとして進化させます。
*   **ADR-0002: 話者分離 (Speaker Diarization) の導入計画**
    *   将来的に `ECAPA-TDNN` を用いた話者分離機能を実装し、会議における「誰が」「何を」話したかをローカル環境で特定できるようにします。
*   **ADR-0003: PyTorch依存の切り離しとサイズ最適化**
    *   現状、音声リサンプリング等のために PyTorch が同梱されており、バイナリサイズが数GBに達するという「技術負債」を抱えています。
    *   **フェーズ1(完了)**: 仮想環境の隔離と厳格なファイルクリーンアップにより、GitHub Releaseの2GB制限を突破し、直接ダウンロード可能な単一の `.exe` ファイルを提供します。
    *   **フェーズ2(予定)**: `torchaudio` を `scipy` などに置き換え、PyTorch を完全に排除。配布サイズを劇的に(数百MBに)スリム化します。

---

## ハードウェア自動最適化

PCのスペックを自動検出し、最適なAIモデルを選択します。ハイエンドGPUがなくてもCPUフォールバックで動作します。

| Tier | RAM | VRAM | Whisper Model | LLM Model |
| :--- | :--- | :--- | :--- | :--- |
| Entry | 8GB+ | - | `base` | `llama3.2:1b-instruct-q4_K_M` |
| Small GPU | 8GB+ | 4GB+ | `small` | `phi3.5:3.8b-instruct-q4_K_M` |
| Standard | 16GB+ | 8GB+ | `medium` | `llama3.1:8b-instruct-q4_K_M` |
| Pro | 32GB+ | 10GB+ | `large-v3` | `gemma2:9b-instruct-q4_K_M` |
| Monster | 64GB+ | 22GB+ | `large-v3` | `llama3.3:70b-instruct-q4_K_M` |

---

## 💼 商用・ビジネス利用への対応 (Licensing & Security)

本アプリは、企業の法務・コンプライアンス部門や情シス部門による導入検討を容易にするため、**「クリーンなライセンス構成」**と**「法的リスクの排除」**を設計思想の根幹に置いています。

### 1. 依存関係のライセンス透明性
主要な依存ライブラリはすべて **商用利用可能** な「MIT」「Apache 2.0」「BSD」等の許諾ライセンスのみで構成されています。**GPL等のコピーレフト（ソースコード公開義務が発生する）ライブラリは一切含んでいません**。

| コンポーネント | ライセンス | 用途 | エビデンス (公式) |
| :--- | :--- | :--- | :--- |
| **faster-whisper** | MIT | 音声認識エンジン | [LICENSE](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE) |
| **CTranslate2** | MIT | 推論バックエンド | [LICENSE](https://github.com/OpenNMT/CTranslate2/blob/master/LICENSE) |
| **Ollama** | MIT | ローカルLLM管理 | [LICENSE](https://github.com/ollama/ollama/blob/main/LICENSE) |
| **Flet (Python)** | Apache 2.0 | UIフレームワーク | [LICENSE](https://github.com/flet-dev/flet/blob/main/LICENSE) |
| **PyAudioWPatch** | MIT/Apache 2.0 | 音声キャプチャ | [LICENSE](https://github.com/s0d3s/PyAudioWPatch/blob/master/LICENSE.txt) |
| **google-genai** | Apache 2.0 | AI SDK | [LICENSE](https://github.com/googleapis/python-genai/blob/main/LICENSE) |
| **OpenCV-Python** | Apache 2.0 | 映像処理補助 | [LICENSE](https://github.com/opencv/opencv-python/blob/4.x/LICENSE.txt) |

### 2. エンタープライズ・セキュリティ
- **100% ネットワーク遮断環境対応**: インターネットへの送信を物理的に遮断した状態でも、音声認識・要約・検索のすべてが動作します。
- **データ永続化の局所性**: 会議データやナレッジベースは、すべて Windows 標準の AppData ディレクトリにのみ保存され、クラウドストレージや外部APIへ漏洩することはありません。設定画面からデータフォルダをワンクリックで開くことも可能です。
- **多層防御 (Layer 0-3)**: Ollama を経由した「偽装ローカル（実はクラウド）」な推論も、システムロジックで強制的に遮断しています。

### 3. データ保存場所と同期 (Persistence & Data Locations)
本アプリは Windows の標準ガイドラインに従い、データの性質に合わせて保存場所を最適化しています。

| フォルダ種類 | パス (AppData) | 保存される内容 | 理由 |
| :--- | :--- | :--- | :--- |
| **Roaming** | `%APPDATA%\TransformMovieToText` | `config.json` (設定)<br>`history.db` (履歴DB)<br>`logs` (アプリログ) | **ユーザーと一緒に移動すべきデータ**。PCを変えても履歴や設定が引き継がれます。 |
| **Local** | `%LOCALAPPDATA%\TransformMovieToText` | `models` (AIモデルデータ)<br>`temp` (一時ファイル) | **そのPC固有で持つべき巨大データ**。同期によるPCの起動遅延を防ぐため、ローカルに隔離されます。 |

> [!NOTE]
> エクスプローラーのパス欄に `%APPDATA%\TransformMovieToText` と入力することで、直接データフォルダを開くことができます。

---

## 🛠️ テクノロジースタック

| カテゴリ | 技術 | 選定理由 |
| :--- | :--- | :--- |
| **音声認識** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | OpenAI Whisper の CTranslate2 最適化版。CPU/GPU 両対応で高速 |
| **推論エンジン** | [Ollama](https://ollama.com/) | ローカルLLMモデル管理のデファクト。外部通信を遮断した推論 |
| **検索基盤** | SQLite FTS5 | 非Embedding型 RAG。メモリ消費を極限まで抑え秒速検索 |
| **UI** | [Flet](https://flet.dev/) | Flutter ベースの Python UI。美しくクロスプラットフォーム |
| **音声キャプチャ** | [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) | Windows WASAPI loopback によるシステム音キャプチャ (Windows専用) |
| **パッケージ管理** | [uv](https://github.com/astral-sh/uv) | Rust製の超高速 Python パッケージマネージャ |
| **CI/CD** | GitHub Actions | PyInstaller `--onefile` による `.exe` の自動生成と直接デプロイ |

---

## クイックスタート

### デスクトップアプリ (Windows専用)

PythonのインストールやZIPファイルの解凍すら不要です。[Releases](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/releases) から最新の **`TransformMovieToText.exe`** を直接ダウンロードしてください。

1. **`TransformMovieToText.exe`** をダウンロード。
2. [ollama.com](https://ollama.com/) から Ollama をインストール。
3. ダウンロードした `.exe` をダブルクリックで起動するだけです。

> [!TIP]
> **スマートハードウェア最適化**:
> 本アプリは「単一のスマートバイナリ」として配布されています。起動時に NVIDIA GPU を検知すれば自動的に GPU 加速（爆速）を使用し、そうでない場合は自動的に CPU フォールバックで動作します。ユーザーが手動でバージョンを選ぶ必要はありません。

---

## 品質保証

3層のテスト戦略でソフトウェア品質を担保しています。

```
tests/
  unit/               # 関数・メソッド単位の独立テスト
  integration/        # Whisperモデルの実ロードを含む連携テスト
  platforms/desktop/  # Windowsデスクトップ固有のUIやOS連携テスト
  system/             # ファイル選択 -> 文字起こし -> DB保存 -> AI要約 の全フロー検証
```

- **自動スモークテスト**: CIビルド直後に `.exe` を実際に起動し、DLL欠損がないことを確認してからリリースします。
- **自動リリース**: python-semantic-release によるセマンティック・バージョニング。

---

## バージョニング

[Conventional Commits](https://www.conventionalcommits.org/) に準拠しています。

| Prefix | Effect | Example |
| :--- | :--- | :--- |
| `feat:` | Minor version bump | `2.6.0` -> `2.7.0` |
| `fix:` | Patch version bump | `2.6.0` -> `2.6.1` |
| `BREAKING CHANGE:` | Major version bump | `2.x.x` -> `3.0.0` |

---

## ライセンス

**MIT License**
Copyright (c) 2026 Ayato-AI

本ソフトウェアは MIT ライセンスのもとで公開されています。詳細については [LICENSE](LICENSE) ファイルを参照してください。

---

<p align="center">
  <strong>Transform_MovieToText -- あなたの会議を、検索可能な資産に変える。</strong>
</p>
