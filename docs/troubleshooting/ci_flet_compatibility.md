# CI & Flet Compatibility Troubleshooting Guide

このドキュメントは、プロジェクトの自動テスト（GitHub Actions）で遭遇した Flet および環境固有のトラブルシューティング記録です。再発防止のためのガイドラインとして活用してください。

## 1. Flet 0.21.0+ プロパティ競合 (Shadowing)

### 問題
`ft.View` や `ft.Column` などを継承したカスタムクラスの `__init__` で `self.page = page` のように `page` プロパティを代入しようとすると、以下のエラーが発生します。
`AttributeError: property 'page' of 'TranscriptionView' object has no setter`

### 原因
Flet 0.21.0+ では、`Control` クラスが持つ `page` プロパティが読み取り専用 (read-only) となり、サブクラスで同名のプロパティを作成・代入することが禁止されました。

### 解決策
内部参照用の変数名を `self._page` のように変更し、Flet 本体の `page` プロパティと衝突しないようにします。
```python
def __init__(self, page: ft.Page):
    super().__init__()
    self._page = page  # self.page は避ける
```

---

## 2. ft.FilePicker 初期化エラー

### 問題
`ft.FilePicker(on_result=callback)` という形式で初期化すると、環境（特に CI の Ubuntu 等）によって以下のエラーが発生することがあります。
`TypeError: FilePicker.__init__() got an unexpected keyword argument 'on_result'`

### 解決策
コンストラクタ引数で渡さず、インスタンス作成直後に属性として代入します。これが最も互換性が高い書き方です。
```python
self.file_picker = ft.FilePicker()
self.file_picker.on_result = self._on_file_picked
```

---

## 3. Windows CI での fastembed/regex エラー

### 問題
`fastembed` ライブラリのインポート時に、Windows 環境特有の文字化け（Unicode 不整合）に起因する正規表現パースエラーが発生します。
`re.error: unterminated character set at position 1`

### 解決策
テスト環境において、ライブラリそのものをロードする必要がない場合は、`import` 前に `sys.modules` を使ってモジュールごとダミー（MagicMock）で差し替えます。
```python
import sys
from unittest.mock import MagicMock
sys.modules["fastembed"] = MagicMock()
# この後に import を行う
```

---

## 4. リファクタリング後の Mock パス不整合

### 問題
ディレクトリ構造を変更（`src/` -> `src/core/` 等）した際、`unittest.mock.patch("src.xxx")` のように文字列で指定しているパスが古いまま残り、テストが失敗します。

### 解決策
リファクタリング時は、ソースコードだけでなく **`tests/` ディレクトリ配下も全文検索**し、全てのモックターゲット文字列を更新してください。

---

## 5. 依存関係のバージョン固定

### 問題
Flet は API の更新が非常に活発で、`flet>=0.21.0` のような指定では CI 環境で常に最新版が入り、破壊的変更の影響を受けやすくなります。

### 解決策
動作確認が取れている範囲で `pyproject.toml` に上限を設けて固定します。
```toml
dependencies = [
    "flet[all]>=0.21.0,<0.80.0",
]
```
