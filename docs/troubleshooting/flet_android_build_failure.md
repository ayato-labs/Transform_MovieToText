# Troubleshooting: Flet Android Build Silent Failure (Windows/CP932)

Flet CLI における Android ビルド（APK生成）時に、スタックトレースが表示されず「サイレント」に強制終了、または型エラーでクラッシュする問題の記録と再発防止策。

## 1. 症状 (Symptoms)

- `flet build apk` 実行中、`Creating Flutter bootstrap project...` の直後に以下のいずれかが発生する：
  1. **エラー表示**: `str() argument 'encoding' must be str, not None`
  2. **エラー表示**: `name 'unicode' is not defined`
  3. **サイレント終了**: エラー詳細が出ず、Exit Code 1 でビルドが停止する。
  4. **依存関係の崩壊**: `pyproject.toml` の `[project]` セクションが解析されず、Flutter 側のビルドスクリプトが構文エラーを起こす。

## 2. 原因 (Root Causes)

### A. Flet CLI の実装バグ (Surgical Cause)
- **場所**: `flet_cli.commands.build.Command.create_flutter_project`
- **内容**: 内部ツール `cookiecutter` に渡す `extra_context` の生成ロジックにおいて、`template_data` 内の `encoding` 等の値が `None` の場合、それをそのまま辞書に含めていた。
- **結果**: テンプレートエンジン（Jinja2）内部で `str(v)` が呼び出された際、CPython の `str()` 実装が `encoding=None` を受け取れず、不親切な型エラー（TypeError）を吐いてクラッシュした。

### B. Windows のデフォルトエンコーディング衝突
- **内容**: 日本語 Windows (CP932/Shift-JIS) 環境下で、外部コマンド（`flutter` 等）の出力を Flet がキャプチャする際、エンコーディング情報の取得に失敗し `None` が設定されやすい。

### C. 複雑な `pyproject.toml` 構造への未対応
- **内容**: `optional-dependencies` など、PEP 621 標準だが Flet CLI が想定していないネスト構造が `pyproject.toml` にあると、Flet がそれを「1つの巨大な Python 文字列」としてテンプレートに埋め込んでしまい、Dart 側の `pubspec.yaml` 生成が壊れる。

## 3. 解決策 (Solutions)

### 即時対応 (Applied Patches)
1. **Flet CLI へのパッチ適用**:
   - `flet_cli/commands/build.py` 内の `extra_context` 生成部を以下のように修正。
   - `k: str(v) if v is not None else "" for k, v in self.template_data.items()`
   - これにより、`None` を空文字に、それ以外を明示的な文字列に変換して安全に渡す。

2. **環境変数の強制**:
   - `PYTHONUTF8=1` および `PYTHONIOENCODING=utf-8` を設定し、OS ロケールに依存しない UTF-8 処理を強制する。

3. **ビルド用 `requirements.txt` の切り出し**:
   - 複雑な `pyproject.toml` を Flet CLI に見せず、ビルド専用のシンプルな依存関係ファイル（`requirements.txt`）を優先させる。

## 4. 再発防止策 (Prevention)

- **ビルド専用環境**: CI/CD やビルド実行時は、常に `PYTHONUTF8=1` を付与したシェルスクリプト（`build.ps1` 等）を使用する。
- **依存関係のフラット化**: モバイル向けビルドでは `pyproject.toml` の `optional-dependencies` は使用せず、ビルド対象に含めるべきライブラリを明示的に指定する。
- **デバッグログの有効化**: 問題発生時は `FLET_CLI_LOG_LEVEL=debug` を付与するか、今回作成した `tmp/debug_flet_build.py` のようなラッパーでスタックトレースを捕捉する。
