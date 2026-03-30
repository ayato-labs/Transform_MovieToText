<p align="center">
  <img src="assets/icon.png" alt="Ayato Transcriber" width="120"/>
</p>

<h1 align="center">Ayato Transcriber</h1>

<p align="center">
  <strong>Privacy-First, Local AI Transcription & Knowledge Engine</strong>
</p>

<p align="center">
  <img src="https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/actions/workflows/ci.yml/badge.svg" alt="CI">
  <img src="https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/actions/workflows/desktop_distribution.yml/badge.svg" alt="Desktop Build">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green.svg" alt="License">
  <img src="https://img.shields.io/badge/code%20style-ruff-purple.svg" alt="Ruff">
</p>

---

### 🛡️ 「1バイトも送信しない。100%ローカル実行可能なRAG（検索）エンジン」

> **「企業のセキュリティポリシーを一切変更せずに、明日から導入できるAI議事録」**
>
> **「クラウドAIの『見えないコスト』と『プライバシーリスク』からの解放」**

---

> **データはあなたの手元に。** 音声も、文字起こしも、AIの推論も、すべてローカルで完結することを可能にしたデスクトップアプリです。もちろん、APIを使ってクラウドのLLM（GeminiやOllama）も使用可能です。

Ayato Transcriber は、動画ファイルやPC内部のシステム音声を高精度に文字起こしし、LLMと連携して議事録の自動生成、ナレッジベースの構築、AIチャットによる過去会議の検索を行うデスクトップアプリケーションです。

**クラウドに一切のデータを送信しないことが可能な設計**により、モード選択によって設定をすることで、弁護士・研究者・技術者など、機密性の高い情報を扱うプロフェッショナルが安心して利用できます。

---

## Design Philosophy

| 原則 | 説明 |
|------|------|
| **Privacy by Architecture** | 音声データ、文字起こし結果、AIの推論結果がネットワークを通過しません。Whisper と Ollama をローカルで実行します。 |
| **Hardware-Aware Optimization** | システムの RAM / VRAM を自動検出し、最適な AI モデルを推奨します。ハイエンドGPUがなくても動作します。 |
| **Zero Configuration** | `run.bat` をダブルクリックするだけで、Python・依存関係・AIモデルがすべて自動構築されます。 |

---

## Architecture

```mermaid
graph TB
    subgraph "Desktop App (Flet)"
        UI["UI Layer<br/>File / Live / History / Chat / Settings"]
        CTRL["Controller Layer<br/>Transcription / Minutes / History"]
    end

    subgraph "Core Engine"
        WT["WhisperTranscriber<br/>(faster-whisper)"]
        TS["TranscriptionService"]
        LP["LiveProcessor<br/>Real-time chunking"]
        RA["ResourceAdvisor<br/>HW-aware model selection"]
    end

    subgraph "AI Providers (Pluggable)"
        LLM_F["LLMFactory"]
        GEM["Gemini"]
        OLL["Ollama Local"]
        OLC["Ollama Cloud"]
    end

    subgraph "Persistence"
        DB[("SQLite<br/>history.db")]
        EMB["Embedding Cache<br/>(FastEmbed)"]
        FS["Local Filesystem<br/>MP3 / Frames"]
    end

    UI --> CTRL
    CTRL --> TS
    CTRL --> LLM_F
    TS --> WT
    TS --> LP
    TS --> RA
    LLM_F --> GEM
    LLM_F --> OLL
    LLM_F --> OLC
    TS --> DB
    TS --> FS
    CTRL --> DB
    CTRL --> EMB
```

---

## Key Features

### 1. Multi-Source Transcription
- **ファイル文字起こし**: MP4, MP3, WAV 等の動画・音声ファイルから高精度なテキストを抽出。
- **ライブ文字起こし**: システム音声（オンライン会議等）やマイク入力をリアルタイムでキャプチャ。
- **ビジュアル解析**: 画面キャプチャによるスライド変化の検知。音声だけでは失われる「視覚的文脈」を保存。

### 2. AI-Powered Meeting Intelligence
- **自動議事録生成**: 概要、決定事項、ネクストアクションを構造化して出力。
- **マルチプロバイダー**: Gemini / Ollama Local / Ollama Cloud をワンクリックで切り替え。
- **AIチャット**: 過去の全会議データに対して自然言語で質問可能。RAG (Retrieval-Augmented Generation) による文脈検索。

### 3. Hardware-Aware Intelligence
PC のスペックに応じて、最適な AI モデルを自動選択します。

| Tier | RAM | VRAM | Whisper Model | LLM Model |
|------|-----|------|---------------|-----------|
| Entry | 8GB+ | - | `base` | `llama3.2:1b-instruct-q4_K_M` |
| SmallGPU | 8GB+ | 4GB+ | `small` | `phi3.5:3.8b-mini-instruct-q4_K_M` |
| Standard | 16GB+ | 8GB+ | `medium` | `llama3.1:8b-instruct-q4_K_M` |
| Pro | 32GB+ | 10GB+ | `large-v3` | `gemma2:9b-instruct-q4_K_M` |
| Monster | 64GB+ | 22GB+ | `large-v3` | `llama3.3:70b-instruct-q4_K_M` |

---

## Tech Stack

| Category | Technology | Why |
|----------|-----------|-----|
| **Speech-to-Text** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | OpenAI Whisper の CTranslate2 最適化版。CPU/GPU 両対応で高速。 |
| **LLM Integration** | [Ollama](https://ollama.com/) / [Gemini](https://ai.google.dev/) | ローカルLLMとクラウドLLMを同一インターフェースで切り替え可能。 |
| **Desktop UI** | [Flet](https://flet.dev/) | Flutter ベースの Python UI フレームワーク。クロスプラットフォーム対応。 |
| **Audio Capture** | [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) | Windows WASAPI loopback によるシステム音のキャプチャ。 |
| **Embeddings** | [FastEmbed](https://github.com/qdrant/fastembed) | **[デフォルト]** 軽量 ONNX ベースのローカル埋め込みモデル。プライバシー保護のため標準で採用。 |
| **Package Manager** | [uv](https://github.com/astral-sh/uv) | Rust 製の超高速 Python パッケージマネージャ。 |
| **Linter** | [Ruff](https://github.com/astral-sh/ruff) | Rust 製の超高速 Python リンター & フォーマッター。 |
| **CI/CD** | GitHub Actions | 自動テスト、自動リリース、デスクトップバイナリの自動ビルド。 |

---

## Quality Assurance

本プロジェクトでは、3 層のテスト戦略によりソフトウェア品質を担保しています。

```
tests/
  unit/          ... 関数・メソッド単位の独立テスト (モック使用)
  integration/   ... Whisper モデルの実ロードを含む連携テスト
  e2e/           ... ファイル選択 -> 文字起こし -> DB保存 -> AI要約 の全フロー検証
```

- **静的解析**: `ruff` による自動リント & フォーマット (CI で強制)
- **自動リリース**: `python-semantic-release` によるセマンティック・バージョニング
- **クロスプラットフォーム・ビルド**: GitHub Actions で Windows / macOS のデスクトップバイナリを自動生成

---

## Getting Started

### Option 1: Desktop App (推奨)

Python のインストール不要。[Releases](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/releases) から最新バイナリをダウンロードしてください。

### Option 2: Thin Client (Windows)

`run.bat` をダブルクリックするだけで、Python / PyTorch / 全依存関係が自動インストールされます。

```
TransformMovieToText-Windows-ThinClient.zip をダウンロード -> 展開 -> run.bat を実行
```

### Option 3: From Source

```bash
git clone https://github.com/Ayato-AI-for-Auto/Transform_MovieToText.git
cd Transform_MovieToText

# ローカルインストール
uv pip install -e .

# GPU を使う場合
uv pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121

# 起動
uv run main.py
```

---

## System Requirements

| Item | Requirement |
|------|-------------|
| **OS** | Windows 10 / 11 (Primary), macOS (Experimental) |
| **FFmpeg** | システムにインストール済み、PATH が通っていること |
| **RAM** | 8GB 以上 (16GB+ 推奨) |
| **GPU** | NVIDIA CUDA 対応 GPU があれば高速化。なくても動作可能 |

---

## Project Structure

```
.
├── src/
│   ├── core/           # ビジネスロジック (Whisper, LLM, DB, Config)
│   ├── controllers/    # UIとCoreの仲介層
│   ├── llm/            # LLMプロバイダー (Factory Pattern)
│   ├── recorder/       # 音声キャプチャ (Strategy Pattern)
│   ├── ui/             # Flet UI コンポーネント
│   └── utils/          # 共通ユーティリティ
├── tests/
│   ├── unit/           # 単体テスト
│   ├── integration/    # 結合テスト
│   └── e2e/            # 総合テスト
├── data/               # ランタイムデータ (DB, 履歴, 一時ファイル)
├── .github/workflows/  # CI/CD パイプライン
└── docs/               # 設計ドキュメント
```

---

## Versioning

[Conventional Commits](https://www.conventionalcommits.org/) に準拠し、`python-semantic-release` による自動バージョニングを行っています。

| Prefix | Effect | Example |
|--------|--------|---------|
| `feat:` | Minor version bump | `2.6.0` -> `2.7.0` |
| `fix:` | Patch version bump | `2.6.0` -> `2.6.1` |
| `BREAKING CHANGE:` | Major version bump | `2.x.x` -> `3.0.0` |

---

## License

[Apache License 2.0](LICENSE)
