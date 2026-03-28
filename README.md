# Transform Movie to Text (+ AI Minutes) v2.0.0

動画ファイルやPC内部の音声から高精度に文字起こしし、複数のAIプロバイダー（Gemini / Ollama Local / Ollama Cloud）を活用して議事録を自動生成する **Windows向け** デスクトップアプリケーションです。

> **Note**: 本ツールは **Windows 環境** で開発・テストされています。
> macOS / Linux では、システム音キャプチャ（DirectShow/WASAPI 等）や `run.bat` による自動環境構築など、OS固有の機能が動作しません。
> 他OSでの動作は一切保証しておらず、サポートも行いません。

## 主な機能 (Features)

- **高品質・高速文字起こし**: より高速で軽量な `faster-whisper` エンジンを使用して、動画・音声ファイルからテキストをスピーディーに生成します。
- **マルチソース・ライブ録音 (システム音 / マイク)**: PCから出力されているあらゆる音声（オンライン会議、動画等）や、マイクからの音声（対面の会議、自分の声）をリアルタイムでキャプチャし、文字起こしできます。画面上でソースを自由に選択・切り替え可能です。**録音ファイルは軽量な MP3 形式で永続保存されます。**
- **AI議事録生成（マルチプロバイダー対応）**: Gemini, Ollama Local (ローカルLLM), Ollama Cloud を切り替えて利用可能。文字起こしテキストから「会議の概要」「決定事項」「ネクストアクション」を自動で要約・抽出します。
- **会議履歴管理**: 過去の会議（文字起こし・議事録・音声パス）をSQLiteデータベースで管理。「履歴」タブからいつでも過去の内容を確認したり、音声をエクスポートしたりできます。
- **ハードウェア自動検知**: PCのスペック（VRAM/RAM）を解析し、最適なWhisperモデルを推奨。

## 動作環境

| 項目 | 要件 |
|------|------|
| **OS** | **Windows 10 / 11**（必須） |
| **FFmpeg** | システムにインストールされ、PATHが通っていること |
| **GPU** | NVIDIA GPU（CUDA対応）があれば高速化。なくても動作可能 |
| **Python** | `run.bat` が自動でインストールするため、手動導入は不要 |

### 重要: 録音ソース（システム音 / マイク）について

本ツールでは、録音ソースとして「システム音（Stereo Mix）」と「マイク」をUI上で切り替えて使用できます。

**A. システム音（オンライン会議などのPC出力音）を録音する場合:**
「システム音」を利用するには、Windows 側で **「ステレオ ミキサー」** を有効にする必要があります。

1. **[設定] > [システム] > [サウンド] > [詳細設定] > [サウンドの設定]** (サウンド コントロール パネル) を開きます。
2. **[録音]** タブを選択します。
3. リスト内の **「ステレオ ミキサー」** を右クリックし、**[有効]** を選択します。
   - 表示されない場合は、リストの何もないところを右クリックし、[無効なデバイスの表示] にチェックを入れてください。
4. ステレオ ミキサーが「既定のデバイス」である必要はありませんが、「準備完了」状態でメーターが動く必要があります。

**B. マイク（対面会議や自分の声）を録音する場合:**
「マイク」を選択すると、接続されているデフォルトのマイクを自動的に検出して使用します。特別な設定は不要ですが、Windowsのプライバシー設定でアプリからのマイクアクセスが許可されている必要があります。

## 使い方 (How to Use)

### Thin Client インストール（推奨）

環境構築は `run.bat` が全自動で行います。Pythonのインストールすら不要です。

1. [Releases ページ](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/releases) から最新の `TransformMovieToText-Windows-ThinClient.zip` をダウンロードします。
2. ZIP を展開し、`run.bat` をダブルクリックします。
3. 初回起動時に以下が自動実行されます：
   - **uv**（高速パッケージマネージャ）のダウンロード
   - **Python 3.11** のインストール（システムを汚しません）
   - **PyTorch 等の全依存ライブラリ**のインストール
4. 2回目以降は一瞬で起動します。

### ソースコードから実行する

開発やカスタマイズを行いたい場合：

```bash
git clone https://github.com/Ayato-AI-for-Auto/Transform_MovieToText.git
cd Transform_MovieToText

![Luxurious CI](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/actions/workflows/ci.yml/badge.svg)
![Build Installer](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/actions/workflows/build-exe.yml/badge.svg)

# uvを利用したローカルインストール
uv pip install -e .

# [GPUを使う場合] CUDA版のPyTorchをインストール
uv pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121

# 起動
uv run main.py
```

## 開発スタンスについて

本ツールは**開発者自身が使うために作られたもの**であり、「ついでに公開している」というスタンスです。
詳しくは [docs/設計思想.md](docs/設計思想.md) をご覧ください。

- 環境構築の自動化は提供しますが、**個別環境のバグ対応やサポートは行いません。**
- ご利用は **As-Is（現状有姿）** です。

## 開発者向け: バージョン管理とリリース (For Developers)

本プロジェクトでは `python-semantic-release` を使用して、コミットメッセージに基づいた自動バージョニングを行っています。

### コミットメッセージ規約 (Conventional Commits)
以下の接頭辞を使用してコミットすることで、GitHub へのプッシュ時に自動的にバージョンアップとタグ打ちが行われます。

- **`feat: ...`**: 新機能の追加 (Minor version bump: 2.3.0 -> 2.4.0)
- **`fix: ...`**: バグ修正 (Patch version bump: 2.3.0 -> 2.3.1)
- **`perf: ...`**: パフォーマンス改善 (Patch version bump)
- **`docs: ...`**: ドキュメントのみの更新 (No version bump)
- **`chore: ...`**: ビルドプロセスやライブラリの更新 (No version bump)
- **`BREAKING CHANGE: ...`**: 破壊的変更 (Major version bump: 2.x.x -> 3.0.0)

### リリースの流れ
1. 規約に沿った内容で `main` ブランチへプッシュ。
2. GitHub Actions が自動でバージョン計算、`pyproject.toml` 更新、タグ打ち、`CHANGELOG.md` 生成を実行します。

## License

[Apache License 2.0](LICENSE)
