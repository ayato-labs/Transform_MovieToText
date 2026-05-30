<p align="center">
  <img src="assets/icon.png" alt="Transform_MovieToText" width="120"/>
</p>

<h1 align="center">Transform_MovieToText</h1>

<p align="center">
  <strong>100% Local AI Transcription & Knowledge Engine for Windows</strong><br/>
  1バイトも外部に送信しない、完全ローカル完結のAI議事録 & ナレッジ検索
</p>

<p align="center">
  <img src="https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/actions/workflows/ci.yml/badge.svg" alt="CI">
  <img src="https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/actions/workflows/desktop_distribution.yml/badge.svg" alt="Desktop Build">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/privacy-100%25_local-green.svg" alt="Privacy">
  <img src="https://img.shields.io/badge/cost-free-brightgreen.svg" alt="Cost">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/code%20style-ruff-purple.svg" alt="Ruff">
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
- **リアルタイム文字起こし** -- オンライン会議の音声をリアルタイムでキャプチャ
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

## アーキテクチャ

```mermaid
graph TB
    subgraph "Desktop App - Flet"
        UI["UI Layer<br/>File / Live / History / Chat / Settings"]
        CTRL["Controller Layer"]
    end

    subgraph "Core Engine"
        WT["WhisperTranscriber<br/>faster-whisper"]
        TS["TranscriptionService"]
        LP["LiveProcessor<br/>Real-time chunking"]
        RA["ResourceAdvisor<br/>HW-aware model selection"]
    end

    subgraph "AI Provider - Ollama Local Only"
        LLM_F["LLMFactory"]
        OLL["OllamaLocalClient<br/>localhost:11434"]
    end

    subgraph "Non-Embedding RAG"
        QA["QueryAnalyzer<br/>LLM Intent Extraction"]
        META["Metadata Filter<br/>Project / Category / FTS5"]
    end

    subgraph "Persistence"
        DB[("SQLite<br/>history.db + FTS5")]
        FS["Local Filesystem<br/>MP3 / Frames"]
    end

    UI --> CTRL
    CTRL --> TS
    CTRL --> LLM_F
    TS --> WT
    TS --> LP
    TS --> RA
    LLM_F --> OLL
    TS --> DB
    TS --> FS
    CTRL --> QA
    QA --> META
    META --> DB
```

---

## Non-Embedding RAG: 軽量で高速な検索アーキテクチャ

本アプリは、一般的なRAGシステムで用いられるベクトルデータベースや Embedding モデルを**意図的に採用していません**。

| 観点 | 一般的なRAG (Embedding) | 本アプリ (Non-Embedding) |
| :--- | :--- | :--- |
| **検索方式** | ベクトル類似度検索 | SQLite FTS5 全文検索 + LLM意図解析 |
| **追加モデル** | Embeddingモデルのロードが必要 | 不要(既存LLMを流用) |
| **メモリ消費** | 高い(ベクトルインデックス常駐) | 極めて低い(SQLiteのみ) |
| **精度** | 文脈の「雰囲気」で検索 | キーワード＋メタデータでピンポイント検索 |
| **ローカル適性** | GPU/RAMを大量消費 | 8GB RAMのPCでも快適に動作 |

**処理フロー:**
1. ユーザーの質問をLLMが解析し、「検索キーワード」「対象プロジェクト」「対象カテゴリー」を抽出
2. 抽出されたメタデータでSQLite FTS5を高速検索(ハードウェア負荷はほぼゼロ)
3. 絞り込まれたドキュメントのみをLLMに渡し、ソース付きで回答を生成

---

## Local-First Privacy Architecture: 4重の防御策

「ローカルLLMを使っているつもりで、実はクラウドにデータが送られていた」という欺瞞的状況(Deceptive Locality)を排除するため、本アプリは以下の4層にわたるセキュリティ・ガードを実装しています。

| レイヤー | 防御策 | 詳細 |
| :--- | :--- | :--- |
| **Layer 0** | **URL強制固定** | 接続先を `localhost` に強制。外部プロキシや踏み台を排除します。 |
| **Layer 1** | **動的名称フィルタ** | Ollama APIから取得したモデル名に `cloud`, `remote` 等が含まれる場合、UIに表示しません。 |
| **Layer 2** | **メタデータ検証** | 推論前にモデルのメタデータを検査し、ローカルディスクに実体ファイルが存在するか確認します。 |
| **Layer 3** | **実行時ガード** | 最終的な推論API(/chat等)の直前で再度モデル名をチェックし、不正な場合は即座に遮断します。 |

> [!IMPORTANT]
> この多層防御により、たとえユーザーが Ollama にサインインしてクラウドモデルを有効化していたとしても、本アプリからプライベートな議事録データが外部へ送信されることは決してありません。

---

## ハードウェア自動最適化

PCのスペックを自動検出し、最適なAIモデルを選択します。ハイエンドGPUがなくてもCPUフォールバックで動作します。

| Tier | RAM | VRAM | Whisper Model | LLM Model |
| :--- | :--- | :--- | :--- | :--- |
| Entry | 8GB+ | - | `base` | `llama3.2:1b-instruct-q4_K_M` |
| Small GPU | 8GB+ | 4GB+ | `small` | `phi3.5:3.8b-mini-instruct-q4_K_M` |
| Standard | 16GB+ | 8GB+ | `medium` | `llama3.1:8b-instruct-q4_K_M` |
| Pro | 32GB+ | 10GB+ | `large-v3` | `gemma2:9b-instruct-q4_K_M` |
| Monster | 64GB+ | 22GB+ | `large-v3` | `llama3.3:70b-instruct-q4_K_M` |

---

## テクノロジースタック

| カテゴリ | 技術 | 選定理由 |
| :--- | :--- | :--- |
| **音声認識** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | OpenAI Whisper の CTranslate2 最適化版。CPU/GPU 両対応で高速 |
| **推論エンジン** | [Ollama](https://ollama.com/) | ローカルLLMモデル管理のデファクト。外部通信を遮断した推論 |
| **検索基盤** | SQLite FTS5 | 非Embedding型 RAG。メモリ消費を極限まで抑え秒速検索 |
| **UI** | [Flet](https://flet.dev/) | Flutter ベースの Python UI。美しくクロスプラットフォーム |
| **音声キャプチャ** | [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) | Windows WASAPI loopback によるシステム音キャプチャ |
| **パッケージ管理** | [uv](https://github.com/astral-sh/uv) | Rust製の超高速 Python パッケージマネージャ |
| **リンター** | [Ruff](https://github.com/astral-sh/ruff) | Rust製の Python リンター & フォーマッター |
| **CI/CD** | GitHub Actions | 自動テスト、セマンティックリリース、デスクトップバイナリ自動ビルド |

---

## クイックスタート

### Option 1: デスクトップアプリ(推奨)

Pythonのインストール不要です。

1. [Releases](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/releases) から最新のインストーラーをダウンロード
2. [ollama.com](https://ollama.com/) から Ollama をインストール
3. アプリを起動 -- 以上

### Option 2: Thin Client (Windows)

`run.bat` をダブルクリックするだけで、Python・依存関係・AIモデルがすべて自動構築されます。

### 🧠 Secure Local Knowledge Engine (RAG)
No more searching through endless folders. Chat with all your knowledge sources simultaneously.
- **Meeting Intelligence**: Query across months of meeting transcripts and AI summaries.
- **Local Document Indexing**: Automatically index `.md`, `.txt`, and `.csv` files from your local folders.
- **Decentralized Team Sharing**: Export meetings as `.md` files with **YAML Frontmatter** (Project/Category metadata). Share via Dropbox/NAS to enable "Git-style" local-first team sync.
- **Zero-Cloud RAG**: Context retrieval and answer generation happen 100% on your machine.
- **Smart Citations**: AI responses include clickable source links (Meeting 🎙️ or Document 📄).

---

## 🗺️ Roadmap & Ecosystem

| Feature | Status | Target |
| :--- | :--- | :--- |
| **Local Transcription (Whisper)** | ✅ Ready | Production |
| **Local LLM Summary (Ollama)** | ✅ Ready | Production |
| **Secure Knowledge Engine (.md, .txt)** | ✅ Ready | NEW |
| **CSV Data Analysis** | ✅ Ready | NEW |
| **Local Smart Optimization** | ✅ Ready | Production |
| **PDF / DOCX Parsing** | 🏗️ In Dev | Phase 2 |
| **Excel (.xlsx) Intelligence** | 📅 Planned | Phase 2 |
| **Mobile Companion (Local Sync)** | 📅 Planned | Future |

---

## 品質保証

3層のテスト戦略でソフトウェア品質を担保しています。

```
tests/
  unit/          # 関数・メソッド単位の独立テスト
  integration/   # Whisperモデルの実ロードを含む連携テスト
  e2e/           # ファイル選択 -> 文字起こし -> DB保存 -> AI要約 の全フロー検証
```

- **静的解析**: Ruff による自動リント(CI で強制)
- **自動リリース**: python-semantic-release によるセマンティック・バージョニング
- **バイナリビルド**: GitHub Actions で Windows / macOS のデスクトップバイナリを自動生成

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
